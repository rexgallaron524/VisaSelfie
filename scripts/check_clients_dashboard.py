"""Exercise client pagination and contact registration with disposable records.

Uses SMOKE_BASE_URL/SMOKE_COMPOSE_ARGS and PLAYWRIGHT_CHROMIUM_EXECUTABLE.
Only this run's temporary admin and client records are removed afterward.
"""

import os
import secrets
import uuid

from check_responsive import check_layout
from playwright.sync_api import expect, sync_playwright
from smoke_phase1 import ALLOW_SELF_SIGNED, BASE, remote


def main():
    admin_id = str(uuid.uuid4())
    ids = [str(uuid.uuid4()) for _ in range(65)]
    prefix = "Pagination" + uuid.uuid4().hex
    email = f"dashboard-{admin_id}@example.com"
    password = secrets.token_urlsafe(24)
    remote(
        """
import uuid
from app.core.database import get_session_factory
from app.core.security import password_hasher
from app.auth.models import AdminUser
from app.processes.models import ClientProcess
with get_session_factory()() as db:
    db.add(AdminUser(id=uuid.UUID(data['admin']), email=data['email'],
                     password_hash=password_hasher.hash(data['password'])))
    for i, process_id in enumerate(data['ids']):
        db.add(ClientProcess(id=uuid.UUID(process_id), full_name=f"{data['prefix']} {i:03}",
                             phone_number='+244923456789', status='registered'))
    db.commit()
""",
        {
            "admin": admin_id,
            "ids": ids,
            "prefix": prefix,
            "email": email,
            "password": password,
        },
    )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None
            )
            context = browser.new_context(
                ignore_https_errors=ALLOW_SELF_SIGNED, reduced_motion="reduce"
            )
            page = context.new_page()
            page.goto(BASE + "/login")
            page.get_by_label("Email address").fill(email)
            page.get_by_label("Password", exact=True).fill(password)
            page.get_by_role("button", name="Sign in to your workspace").click()
            expect(page).to_have_url(BASE + "/dashboard")
            for width, height in [(320, 568), (768, 1024), (1440, 900)]:
                page.set_viewport_size({"width": width, "height": height})
                page.goto(BASE + f"/dashboard/clients?q={prefix}&status=registered")
                top = page.get_by_role("navigation", name="Client pagination top")
                bottom = page.get_by_role("navigation", name="Client pagination bottom")
                expect(top).to_contain_text("Showing 1–10 of 65 clients")
                expect(bottom).to_contain_text("Showing 1–10 of 65 clients")
                check_layout(page, "pagination-10")
                top.get_by_role("link", name="Next page").click()
                expect(top).to_contain_text("Showing 11–20 of 65 clients")
                bottom.get_by_role("link", name="Next page").click()
                expect(top).to_contain_text("Showing 21–30 of 65 clients")
                bottom.get_by_label("Clients per page").select_option("30")
                expect(top).to_contain_text("Showing 1–30 of 65 clients")
                expect(top.get_by_label("Clients per page")).to_have_value("30")
                assert f"q={prefix}" in page.url and "status=registered" in page.url
                top.get_by_label("Clients per page").select_option("50")
                expect(bottom).to_contain_text("Showing 1–50 of 65 clients")
                expect(bottom.get_by_label("Clients per page")).to_have_value("50")
                check_layout(page, "pagination-50")
                page.evaluate("window.scrollTo(0, 900)")
                back = page.get_by_role("button", name="Back to top")
                expect(back).to_be_visible()
                back.click()
                page.wait_for_function("window.scrollY < 2")
                expect(page.locator("#clients-top")).to_be_focused()
                bottom.get_by_role("link", name="Next page").click()
                expect(top).to_contain_text("Showing 51–65 of 65 clients")
                page.goto(
                    BASE
                    + f"/dashboard/clients?q={prefix}&status=registered&page_size=50&page=999"
                )
                expect(top).to_contain_text("Showing 51–65 of 65 clients")
                page.get_by_label("Search by name").fill(prefix + "Missing")
                page.get_by_role("button", name="Filter", exact=True).click()
                expect(top).to_contain_text("No clients to display")
                expect(top).to_contain_text("Page 1 of 1")
                expect(top.get_by_label("Clients per page")).to_have_value("50")
                check_layout(page, "empty-pagination")
                print(
                    f"PASS: pagination, filters and Back to top at {width}px",
                    flush=True,
                )

            page.goto(BASE + "/dashboard/clients/new")
            page.get_by_label("Full name").fill(prefix + " Contact")
            page.get_by_label("Phone number including country code", exact=True).fill(
                "+244923456789"
            )
            with page.expect_response("**/api/admin/processes") as created:
                page.get_by_role("button", name="Create client and link").click()
            issued = created.value.json()
            ids.append(issued["process_id"])
            applicant = browser.new_context(
                ignore_https_errors=ALLOW_SELF_SIGNED,
                viewport={"width": 390, "height": 844},
            )
            form = applicant.new_page()
            form.goto(issued["registration_url"])
            form.get_by_label("Date of birth").fill("1990-06-15")
            form.get_by_label("Passport number").fill("TEST12345")
            form.get_by_label("Email address", exact=True).fill("applicant@example.com")
            form.get_by_label("Alternative phone number including country code").fill(
                "+244923456780"
            )
            form.get_by_label("Residential address", exact=True).fill(
                "Rua de Teste 12\nLuanda, Angola"
            )
            check_layout(form, "contact-registration")
            form.get_by_role("button", name="Continue", exact=True).click()
            expect(
                form.get_by_role("heading", name="Your privacy and consent")
            ).to_be_visible()
            form.get_by_role("checkbox").check()
            form.get_by_role("button", name="Agree and continue").click()
            expect(
                form.get_by_role("heading", name="Before you record")
            ).to_be_visible()
            page.goto(BASE + "/dashboard/clients?q=" + prefix)
            page.get_by_role("link", name=prefix + " Contact", exact=True).filter(
                visible=True
            ).click()
            expect(
                page.get_by_role("heading", name="Client information")
            ).to_be_visible()
            for value in ["applicant@example.com", "+244923456780", "Rua de Teste 12"]:
                expect(page.locator("dd").filter(has_text=value)).to_be_visible()
            for width, height in [(320, 568), (768, 1024), (1440, 900)]:
                page.set_viewport_size({"width": width, "height": height})
                check_layout(page, "contact-detail")
            browser.close()
            print(
                "PASS: applicant contact details saved and displayed on client detail",
                flush=True,
            )
    finally:
        remote(
            """
import uuid
from sqlalchemy import delete, or_, select
from app.core.database import get_session_factory
from app.auth.models import AdminUser, AdminSession
from app.audit.models import AuditLog
from app.processes.models import ClientProcess, ConsentRecord, RecordingChallenge, RegistrationLink, VideoSubmission
admin_id = uuid.UUID(data['admin'])
ids = [uuid.UUID(value) for value in data['ids']]
with get_session_factory()() as db:
    ids += list(db.scalars(select(AuditLog.entity_id).where(
        AuditLog.actor_id == admin_id, AuditLog.action == 'process.created')))
    for model in [VideoSubmission, ConsentRecord, RecordingChallenge, RegistrationLink]:
        db.execute(delete(model).where(model.client_process_id.in_(ids)))
    db.execute(delete(AuditLog).where(or_(AuditLog.entity_id.in_(ids), AuditLog.actor_id == admin_id)))
    db.execute(delete(ClientProcess).where(ClientProcess.id.in_(ids)))
    db.execute(delete(AdminSession).where(AdminSession.admin_id == admin_id))
    db.execute(delete(AdminUser).where(AdminUser.id == admin_id))
    db.commit()
""",
            {"admin": admin_id, "ids": ids},
        )


if __name__ == "__main__":
    main()
