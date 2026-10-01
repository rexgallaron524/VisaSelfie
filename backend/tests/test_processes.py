import io
import uuid
from datetime import timedelta

import pytest
from botocore.exceptions import EndpointConnectionError
from sqlalchemy import select

from app.audit.models import AuditLog
from app.core.security import hash_token, utcnow
from app.processes.models import (
    ClientProcess,
    ConsentRecord,
    RecordingChallenge,
    RegistrationLink,
    VideoSubmission,
)
from app.processes.schemas import CONSENT_VERSION
from app.processes.services import aware
from app.storage import get_store
from tests.test_auth import sign_in


class Body(io.BytesIO):
    def iter_chunks(self, chunk_size):
        while data := self.read(chunk_size):
            yield data


class MemoryStore:
    def __init__(self):
        self.objects = {}
        self.fail_put = False
        self.fail_delete = False

    def put(self, key, file, size, mime):
        if self.fail_put:
            raise EndpointConnectionError(endpoint_url="test-storage")
        self.objects[key] = file.read()

    def get(self, key, byte_range):
        data = self.objects[key]
        result = {}
        if byte_range:
            start, end = byte_range.removeprefix("bytes=").split("-")
            start, end = int(start), int(end)
            result["ContentRange"] = f"bytes {start}-{end}/{len(data)}"
            data = data[start : end + 1]
        return {**result, "Body": Body(data), "ContentLength": len(data)}

    def delete(self, key):
        if self.fail_delete:
            raise EndpointConnectionError(endpoint_url="test-storage")
        self.objects.pop(key, None)


@pytest.fixture
def store(client, monkeypatch):
    store = MemoryStore()
    client.app.dependency_overrides[get_store] = lambda: store
    # Multimedia decoding is exercised with real recordings by the Docker browser test.
    monkeypatch.setattr("app.processes.routes.inspect_video", lambda *args: 18.0)
    # Lifecycle tests isolate media inference. Dedicated assessment tests cover its policy.
    monkeypatch.setattr(
        "app.processes.routes.assess_video",
        lambda *args: {
            "passed": True,
            "status": "guided_checks_passed",
            "version": "guided-v1",
            "liveness": "not_verified",
            "manual_review_required": True,
            "checks": [{"code": "test_stub", "passed": True, "message": "Test fixture"}],
        },
    )
    return store


def create(client):
    assert sign_in(client).status_code == 200
    response = client.post(
        "/api/admin/processes",
        json={
            "full_name": "Test Applicant",
            "phone_number": "+44 7700 900123",
        },
    )
    assert response.status_code == 201, response.text
    issued = response.json()
    return issued, {"Authorization": f"Bearer {issued['token']}"}


def register(client, headers):
    response = client.post(
        "/api/public/register",
        headers=headers,
        json={
            "full_name": "Test Applicant",
            "phone_number": "+44 7700 900123",
            "date_of_birth": "1990-06-15",
            "passport_number": "TEST12345",
        },
    )
    assert response.status_code == 204, response.text


def prepare(client, headers):
    register(client, headers)
    assert (
        client.post(
            "/api/public/consent",
            headers=headers,
            json={
                "accepted": True,
                "version": CONSENT_VERSION,
            },
        ).status_code
        == 204
    )
    response = client.post("/api/public/recording", headers=headers)
    assert response.status_code == 200
    headers["X-Recording-Challenge"] = response.json()["id"]
    challenge = client.test_db.get(RecordingChallenge, uuid.UUID(response.json()["id"]))
    challenge.created_at = utcnow() - timedelta(seconds=20)
    client.test_db.commit()


def upload(client, headers, data=b"test-video-bytes"):
    return client.post(
        "/api/public/video", content=data, headers={**headers, "Content-Type": "video/webm"}
    )


def test_complete_process_and_private_video_lifecycle(client, db, store):
    issued, headers = create(client)
    process_id = issued["process_id"]
    base = f"/api/admin/processes/{process_id}"
    link = db.scalar(select(RegistrationLink))
    assert link.token_hash == hash_token(issued["token"])
    assert 47.99 < (aware(link.expires_at) - utcnow()).total_seconds() / 3600 <= 48
    assert client.post("/api/public/open", headers=headers).status_code == 200
    prepare(client, headers)
    assert upload(client, headers).status_code == 201
    assert len(store.objects) == 1
    detail = client.get(base).json()
    assert detail["status"] == "submitted"
    assert detail["passport_number"] == "TEST12345"
    assert "storage_key" not in detail["video"]
    assert detail["consent"]["consent_version"] == CONSENT_VERSION
    assert client.get(base + "/video").content == b"test-video-bytes"
    partial = client.get(base + "/video", headers={"Range": "bytes=0-3"})
    assert partial.status_code == 206
    assert partial.content == b"test"
    assert partial.headers["Content-Range"] == "bytes 0-3/16"
    assert "attachment" in client.get(base + "/video?download=true").headers["Content-Disposition"]
    assert client.post(base + "/review").status_code == 204
    assert client.get(base).json()["status"] == "reviewed"
    assert client.get("/api/admin/processes/summary").json()["submitted_videos"] == 1
    assert upload(client, headers).status_code == 409
    assert client.post(base + "/link").status_code == 409
    assert client.delete(base + "/video").status_code == 204
    assert not store.objects
    assert client.get(base + "/video").status_code == 410
    assert client.get(base).json()["status"] == "deleted"
    assert client.delete(base + "/video").status_code == 204
    assert client.post("/api/public/open", headers=headers).status_code == 409
    actions = set(db.scalars(select(AuditLog.action)))
    assert {
        "consent.accepted",
        "video.submitted",
        "video.viewed",
        "video.downloaded",
        "video.reviewed",
        "video.deleted",
    } <= actions
    assert db.scalar(select(ConsentRecord)).ip_address == "testclient"


def test_replacement_revokes_old_link_and_expiry_is_enforced(client, db):
    issued, old = create(client)
    base = f"/api/admin/processes/{issued['process_id']}"
    new = client.post(base + "/link").json()
    assert new["token"] != issued["token"]
    assert client.post("/api/public/open", headers=old).status_code == 404
    link = db.scalar(select(RegistrationLink).where(RegistrationLink.status == "active"))
    link.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    headers = {"Authorization": f"Bearer {new['token']}"}
    assert client.post("/api/public/open", headers=headers).status_code == 410
    assert client.get(base).json()["status"] == "expired"
    assert client.get("/api/admin/processes?status=expired").json()["total"] == 1
    assert client.get("/api/admin/processes/summary").json()["expired_links"] == 1
    assert client.post(base + "/link").status_code == 200
    assert client.get("/api/admin/processes/summary").json()["expired_links"] == 0


def test_consent_and_registration_are_required(client, store):
    _, headers = create(client)
    assert client.post("/api/public/recording", headers=headers).status_code == 409
    assert upload(client, headers).status_code == 409
    assert (
        client.post(
            "/api/public/consent",
            headers=headers,
            json={
                "accepted": True,
                "version": CONSENT_VERSION,
            },
        ).status_code
        == 409
    )
    register(client, headers)
    for value in [
        {"accepted": False, "version": CONSENT_VERSION},
        {"accepted": True, "version": "obsolete"},
    ]:
        assert client.post("/api/public/consent", headers=headers, json=value).status_code == 422
    assert upload(client, headers).status_code == 409


def test_failed_storage_upload_is_retryable(client, db, store):
    _, headers = create(client)
    prepare(client, headers)
    store.fail_put = True
    assert upload(client, headers).status_code == 503
    assert db.scalar(select(VideoSubmission)) is None
    assert db.scalar(select(RegistrationLink)).used_at is None
    store.fail_put = False
    assert upload(client, headers).status_code == 201


def test_failed_deletion_hides_video_and_can_be_retried(client, db, store):
    issued, headers = create(client)
    prepare(client, headers)
    assert upload(client, headers).status_code == 201
    base = f"/api/admin/processes/{issued['process_id']}"
    store.fail_delete = True
    assert client.delete(base + "/video").status_code == 503
    assert client.get(base + "/video").status_code == 410
    assert db.scalar(select(VideoSubmission)).status == "deleting"
    assert db.scalar(select(VideoSubmission)).deleted_at is None
    store.fail_delete = False
    assert client.delete(base + "/video").status_code == 204
    assert db.scalar(select(VideoSubmission)).deleted_at is not None


def test_size_mime_invalid_video_and_missing_token(client, store, monkeypatch):
    from fastapi import HTTPException

    _, headers = create(client)
    prepare(client, headers)
    assert upload(client, {}).status_code == 404
    assert (
        client.post(
            "/api/public/video", headers={**headers, "Content-Type": "text/html"}, content=b"bad"
        ).status_code
        == 415
    )
    client.app.state.settings.max_upload_bytes = 8
    assert upload(client, headers).status_code == 413
    client.app.state.settings.max_upload_bytes = 1024

    def reject(*args):
        raise HTTPException(422, "Invalid recording")

    monkeypatch.setattr("app.processes.routes.inspect_video", reject)
    assert upload(client, headers, b"not a video").status_code == 422
    assert not store.objects


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/admin/processes"),
        ("get", "/admin/processes/summary"),
        ("get", "/admin/processes/{id}"),
        ("get", "/admin/processes/{id}/video"),
        ("post", "/admin/processes/{id}/link"),
        ("post", "/admin/processes/{id}/review"),
        ("delete", "/admin/processes/{id}/video"),
    ],
)
def test_all_process_admin_routes_protected(client, store, method, path):
    assert getattr(client, method)("/api" + path.format(id=uuid.uuid4())).status_code == 401


def test_applicant_cannot_change_other_process_or_admin_read(client, db):
    issued, headers = create(client)
    second = client.post(
        "/api/admin/processes",
        json={
            "full_name": "Other Applicant",
            "phone_number": "+44 7700 900999",
        },
    ).json()
    client.cookies.clear()
    register(client, headers)
    other = db.get(ClientProcess, uuid.UUID(second["process_id"]))
    assert other.date_of_birth is None
    assert (
        client.get(f"/api/admin/processes/{issued['process_id']}", headers=headers).status_code
        == 401
    )


def test_invitation_returns_operator_phone_only_with_valid_link(client, db):
    issued, headers = create(client)
    client.cookies.clear()
    response = client.post("/api/public/open", headers=headers)
    assert response.status_code == 200
    assert response.json()["phone_number"] == "+44 7700 900123"
    assert response.headers["cache-control"] == "no-store"
    for invalid in [{}, {"Authorization": "Bearer " + "x" * 32}]:
        response = client.post("/api/public/open", headers=invalid)
        assert response.status_code == 404
        assert "+44 7700 900123" not in response.text
    link = db.scalar(select(RegistrationLink))
    link.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    response = client.post("/api/public/open", headers=headers)
    assert response.status_code == 410
    assert "+44 7700 900123" not in response.text


@pytest.mark.parametrize("phone", ["+44 7700 900123", "+44(7700)-900123", "447700900123"])
def test_registration_preserves_operator_phone_with_equivalent_formatting(client, db, phone):
    issued, headers = create(client)
    response = client.post(
        "/api/public/register",
        headers=headers,
        json={
            "full_name": "Applicant Updated Name",
            "phone_number": phone,
            "date_of_birth": "1990-06-15",
            "passport_number": "TEST12345",
        },
    )
    assert response.status_code == 204
    db.expire_all()
    process = db.get(ClientProcess, uuid.UUID(issued["process_id"]))
    assert process.phone_number == "+44 7700 900123"
    assert process.full_name == "Applicant Updated Name"
    assert process.status == "registered"


@pytest.mark.parametrize("phone", ["+44 7700 900999", "+33 7700 900123", "7700900123"])
def test_registration_rejects_phone_changes_without_saving_any_details(client, db, phone):
    issued, headers = create(client)
    process = db.get(ClientProcess, uuid.UUID(issued["process_id"]))
    previous_status, previous_updated = process.status, aware(process.updated_at)
    response = client.post(
        "/api/public/register",
        headers=headers,
        json={
            "full_name": "Should Not Be Saved",
            "phone_number": phone,
            "date_of_birth": "1990-06-15",
            "passport_number": "TEST12345",
        },
    )
    assert response.status_code == 422
    assert "does not match your invitation" in response.json()["detail"]
    assert process.phone_number not in response.text
    db.expire_all()
    assert process.phone_number == "+44 7700 900123"
    assert process.full_name == "Test Applicant"
    assert process.date_of_birth is None
    assert process.passport_number is None
    assert process.status == previous_status
    assert aware(process.updated_at) == previous_updated
    assert db.scalar(select(AuditLog).where(AuditLog.action == "client.registered")) is None
    assert db.scalar(select(RegistrationLink)).used_at is None
    # A rejected request does not consume the invitation or prevent a correct retry.
    register(client, headers)


def test_registration_validates_and_redacts_invalid_values(client):
    _, headers = create(client)
    payload = {
        "full_name": "A",
        "phone_number": "not-a-number",
        "date_of_birth": "2999-01-01",
        "passport_number": "secret<script>",
    }
    response = client.post("/api/public/register", headers=headers, json=payload)
    assert response.status_code == 422
    assert payload["passport_number"] not in response.text


def test_search_pagination_and_creation_origin(client):
    create(client)
    assert client.get("/api/admin/processes?q=Test&page_size=1").json()["total"] == 1
    assert client.get("/api/admin/processes?q=Missing").json()["items"] == []
    assert client.get("/api/admin/processes?page_size=1&page=2").json()["items"] == []
    assert (
        client.post(
            "/api/admin/processes",
            headers={"Origin": "https://evil.example"},
            json={"full_name": "Test", "phone_number": "+123456789"},
        ).status_code
        == 403
    )
