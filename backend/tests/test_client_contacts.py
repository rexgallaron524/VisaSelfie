import uuid

import pytest
from sqlalchemy import select

from app.processes.models import ClientProcess, ConsentRecord
from app.processes.schemas import CONSENT_VERSION
from tests.test_auth import sign_in
from tests.test_processes import create


def payload(**contacts):
    return {
        "full_name": "Test Applicant",
        "phone_number": "+44 7700 900123",
        "date_of_birth": "1990-06-15",
        "passport_number": "TEST12345",
        **contacts,
    }


def test_contact_details_saved_privately_and_covered_by_consent(client, db):
    issued, headers = create(client)
    contacts = {
        "email": "applicant@example.com",
        "alternative_phone_number": "+244 923 456 789",
        "address": "Rua de Teste 12\nLuanda, Angola",
    }
    response = client.post("/api/public/register", headers=headers, json=payload(**contacts))
    assert response.status_code == 204
    detail = client.get(f"/api/admin/processes/{issued['process_id']}").json()
    for field, value in contacts.items():
        assert detail[field] == value
    opened = client.post("/api/public/open", headers=headers).json()
    assert not set(contacts).intersection(opened)
    assert "residential address" in opened["consent_text"]
    assert (
        client.post(
            "/api/public/consent",
            headers=headers,
            json={"accepted": True, "version": "2026-09-30-video-checks"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/public/consent",
            headers=headers,
            json={"accepted": True, "version": CONSENT_VERSION},
        ).status_code
        == 204
    )
    assert db.scalar(select(ConsentRecord)).consent_version == CONSENT_VERSION
    assert (
        client.post(
            "/api/public/register", headers=headers, json=payload(email="replacement@example.com")
        ).status_code
        == 409
    )
    client.cookies.clear()
    assert (
        client.get(f"/api/admin/processes/{issued['process_id']}", headers=headers).status_code
        == 401
    )


@pytest.mark.parametrize(
    "contacts",
    [
        {},
        {"email": " ", "alternative_phone_number": "", "address": "\n "},
        {"email": None, "alternative_phone_number": None, "address": None},
    ],
)
def test_optional_contacts_can_be_omitted(client, db, contacts):
    issued, headers = create(client)
    assert (
        client.post("/api/public/register", headers=headers, json=payload(**contacts)).status_code
        == 204
    )
    process = db.get(ClientProcess, uuid.UUID(issued["process_id"]))
    assert process.email is None
    assert process.alternative_phone_number is None
    assert process.address is None


@pytest.mark.parametrize(
    "contacts",
    [
        {"email": "invalid-email"},
        {"email": "a" * 250 + "@example.com"},
        {"alternative_phone_number": "abc1234567"},
        {"alternative_phone_number": "123"},
        {"alternative_phone_number": "+" + "1" * 16},
        {"address": "A" * 501},
    ],
)
def test_invalid_contacts_do_not_save_registration(client, db, contacts):
    issued, headers = create(client)
    response = client.post("/api/public/register", headers=headers, json=payload(**contacts))
    assert response.status_code == 422
    for value in contacts.values():
        assert value not in response.text
    process = db.get(ClientProcess, uuid.UUID(issued["process_id"]))
    assert process.date_of_birth is None
    assert process.email is None
    assert process.phone_number == "+44 7700 900123"


@pytest.mark.parametrize("size", [10, 30, 50])
def test_pagination_sizes_and_filters_cover_all_clients_without_duplicates(client, db, size):
    sign_in(client)
    db.add_all(
        [
            ClientProcess(
                full_name=f"Pagination Test {i:03}",
                phone_number="+244923456789",
                status="registered",
            )
            for i in range(65)
        ]
    )
    db.add(ClientProcess(full_name="Other Test", phone_number="+244923456789", status="created"))
    db.commit()
    ids = []
    for page in range(1, (65 + size - 1) // size + 1):
        data = client.get(
            f"/api/admin/processes?q=Pagination&status=registered&page_size={size}&page={page}"
        ).json()
        assert data["total"] == 65
        assert data["page_size"] == size
        assert len(data["items"]) == min(size, 65 - (page - 1) * size)
        ids.extend(row["id"] for row in data["items"])
    assert len(ids) == len(set(ids)) == 65
    assert len(client.get("/api/admin/processes").json()["items"]) == 10
    assert client.get("/api/admin/processes?q=missing").json()["total"] == 0
