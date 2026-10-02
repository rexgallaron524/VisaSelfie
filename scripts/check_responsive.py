"""Check responsive layouts on the running demo using disposable test records.

Uses the same SMOKE_BASE_URL, SMOKE_COMPOSE_ARGS and Chromium settings as
smoke_phase1.py. Screenshots go to ignored test-results/responsive/.
Camera responses are mocked for layout coverage, not media-validation testing.
"""

import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from playwright.sync_api import expect, sync_playwright
from smoke_phase1 import ALLOW_SELF_SIGNED, BASE, ROOT, remote

SIZES = [
    (320, 568),
    (390, 844),
    (768, 1024),
    (1024, 768),
    (844, 390),
    (1440, 900),
    (1920, 1080),
]
ARTIFACTS = ROOT / "test-results" / "responsive"


def check_layout(page, label, screenshots=False):
    page.evaluate("document.fonts.ready")
    findings = page.evaluate("""() => {
      const issues = [];
      const width = document.documentElement.clientWidth;
      if (document.documentElement.scrollWidth > width + 1) issues.push('page overflow');
      for (const el of document.querySelectorAll('input, select, textarea, button, a, video')) {
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height || getComputedStyle(el).visibility === 'hidden') continue;
        if (r.left < -1 || r.right > width + 1) issues.push(el.tagName + ': outside viewport');
        if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) && el.type !== 'checkbox' &&
            parseFloat(getComputedStyle(el).fontSize) < 16) issues.push('small form text');
        if (['BUTTON', 'A'].includes(el.tagName) && r.height < 43)
          issues.push(el.tagName + ': small touch target');
      }
      return issues;
    }""")
    assert not findings, f"{label} {page.viewport_size}: {findings}"
    if screenshots:
        page.screenshot(
            path=str(ARTIFACTS / f"{label}-{page.viewport_size['width']}.png"),
            full_page=True,
        )


def all_sizes(page, label, screenshots=False):
    for width, height in SIZES:
        page.set_viewport_size({"width": width, "height": height})
        check_layout(page, label, screenshots and width in (320, 768, 1440))


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    admin_id, process_id, video_process_id = [str(uuid.uuid4()) for _ in range(3)]
    email = f"responsive-{admin_id}@example.com"
    password = secrets.token_urlsafe(24)
    # Maximum-length unbroken text exercises grid/table intrinsic sizing.
    full_name = "Responsive" + "A" * 190
    remote(
        """
import uuid
from app.core.database import get_session_factory
from app.core.security import password_hasher
from app.auth.models import AdminUser
from app.processes.models import ClientProcess, VideoSubmission
with get_session_factory()() as db:
    db.add(AdminUser(id=uuid.UUID(data['admin']), email=data['email'],
                     password_hash=password_hasher.hash(data['password'])))
    for key, status in [('process', 'link_generated'), ('video_process', 'submitted')]:
        db.add(ClientProcess(id=uuid.UUID(data[key]), full_name=data['name'],
                             phone_number='+244 923 456 789', status=status))
    db.flush()
    # Metadata-only fixture for layout. Playback is covered by smoke_phase1.py.
    db.add(VideoSubmission(client_process_id=uuid.UUID(data['video_process']),
        storage_key='responsive-layout/' + data['video_process'], original_filename='fixture.webm',
        mime_type='video/webm', file_size=1000, duration=18.0))
    db.commit()
""",
        {
            "admin": admin_id,
            "process": process_id,
            "video_process": video_process_id,
            "email": email,
            "password": password,
            "name": full_name,
        },
    )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
                or None,
                args=[
                    "--use-fake-device-for-media-stream",
                    "--use-fake-ui-for-media-stream",
                ],
            )
            context = browser.new_context(
                ignore_https_errors=ALLOW_SELF_SIGNED, permissions=["camera"]
            )
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(BASE + "/login")
            expect(
                page.get_by_role("button", name="Sign in to your workspace")
            ).to_be_enabled()
            all_sizes(page, "login", True)
            page.get_by_label("Email address").fill(email)
            page.get_by_label("Password", exact=True).fill(password)
            page.get_by_role("button", name="Sign in to your workspace").click()
            expect(page).to_have_url(BASE + "/dashboard")
            all_sizes(page, "dashboard", True)
            for path, heading, label in [
                ("/dashboard/clients?q=Responsive", "Clients", "clients"),
                (
                    "/dashboard/clients?q=" + uuid.uuid4().hex,
                    "Clients",
                    "empty-clients",
                ),
                ("/dashboard/clients/new", "Create a client", "new-client"),
                ("/dashboard/clients/" + process_id, full_name, "client-detail"),
                ("/dashboard/clients/" + video_process_id, full_name, "video-detail"),
            ]:
                page.goto(BASE + path)
                expect(
                    page.get_by_role("heading", name=heading, exact=True)
                ).to_be_visible()
                all_sizes(page, label, True)
            delete_button = page.get_by_role("button", name="Delete video", exact=True)
            delete_button.click()
            modal = page.get_by_role("alertdialog")
            expect(modal).to_be_visible()
            expect(
                modal.get_by_role("heading", name="Delete facial video?")
            ).to_be_visible()
            all_sizes(page, "confirmation", True)
            page.keyboard.press("Escape")
            expect(modal).not_to_be_visible()
            expect(delete_button).to_be_focused()
            page.goto(BASE + "/dashboard/clients/" + process_id)
            page.get_by_role("button", name="Generate new link").click()
            modal = page.get_by_role("alertdialog")
            expect(
                modal.get_by_role("heading", name="Replace registration link?")
            ).to_be_visible()
            modal.get_by_role("button", name="Generate replacement").click()
            expect(page.get_by_label("Private registration link")).to_be_visible()
            all_sizes(page, "invitation", True)
            # Reflow equivalent to a 1280px viewport at 200% desktop zoom.
            page.set_viewport_size({"width": 640, "height": 450})
            check_layout(page, "narrow-reflow")
            print(
                "PASS: admin pages, long names, invitation, confirmation and narrow reflow",
                flush=True,
            )

            state = {"mode": "registration"}
            expires = (datetime.now(UTC) + timedelta(hours=48)).isoformat()

            def public_response(route):
                path = route.request.url.split("/api/public/")[-1]
                if path == "open":
                    mode = state["mode"]
                    statuses = {
                        "invalid": 404,
                        "expired": 410,
                        "success": 409,
                        "error": 503,
                    }
                    if mode in statuses:
                        route.fulfill(
                            status=statuses[mode],
                            json={
                                "detail": "This recording has already been submitted."
                                if mode == "success"
                                else "Please contact the operator who sent you this link."
                            },
                        )
                    else:
                        route.fulfill(
                            json={
                                "full_name": full_name,
                                "phone_number": "+244 923 456 789",
                                "registered": mode != "registration",
                                "consent_accepted": mode == "camera",
                                "expires_at": expires,
                                "consent_version": "responsive-test",
                                "consent_text": "I consent to this test recording for layout verification. "
                                * 12,
                                "max_upload_bytes": 52428800,
                                "max_video_seconds": 30,
                            }
                        )
                elif path == "recording":
                    route.fulfill(
                        json={
                            "id": str(uuid.uuid4()),
                            "expires_at": expires,
                            "duration_seconds": 18,
                            "baseline_seconds": 2,
                            "action_seconds": 5,
                            "actions": [
                                {
                                    "key": "blink",
                                    "instruction": "Close and open your eyes.",
                                },
                                {
                                    "key": "mouth",
                                    "instruction": "Open and close your mouth.",
                                },
                                {
                                    "key": "turn",
                                    "instruction": "Turn your head and face forward again.",
                                },
                            ],
                        }
                    )
                elif path == "video":
                    route.fulfill(
                        status=422,
                        json={
                            "detail": {
                                "message": "Please retake your recording.",
                                "assessment": {
                                    "passed": False,
                                    "checks": [
                                        {
                                            "code": "lighting",
                                            "passed": False,
                                            "message": "Move toward a light source and keep your whole face visible.",
                                        }
                                    ],
                                },
                            }
                        },
                    )
                else:
                    route.fulfill(status=204)

            page.route("**/api/public/**", public_response)
            for mode, heading in [
                ("registration", "Your details"),
                ("consent", "Your privacy and consent"),
                ("invalid", "This link isn’t valid"),
                ("expired", "Your link has expired"),
                ("success", "Recording submitted"),
                ("error", "We couldn’t check your link"),
            ]:
                state["mode"] = mode
                page.goto(BASE + "/register/responsive-layout-test")
                expect(
                    page.get_by_role("heading", name=heading, exact=True)
                ).to_be_visible()
                all_sizes(page, mode, True)
            state["mode"] = "camera"
            page.goto(BASE + "/register/responsive-layout-test")
            expect(
                page.get_by_role("heading", name="Before you record")
            ).to_be_visible()
            all_sizes(page, "instructions")
            page.get_by_role("button", name="Continue to camera").click()
            all_sizes(page, "camera-idle", True)
            page.get_by_role("button", name="Enable camera").click()
            expect(page.get_by_role("button", name="Start recording")).to_be_visible()
            all_sizes(page, "camera-ready")
            page.get_by_role("button", name="Start recording").click()
            expect(page.get_by_role("button", name="Cancel recording")).to_be_visible()
            all_sizes(page, "camera-recording")
            expect(
                page.get_by_role("heading", name="Preview your recording")
            ).to_be_visible(timeout=30000)
            all_sizes(page, "camera-preview", True)
            page.get_by_role("button", name="Confirm and submit").click()
            expect(page.get_by_label("Recording feedback")).to_be_visible()
            all_sizes(page, "camera-feedback")
            # Short viewport approximates the available space with a mobile keyboard open.
            state["mode"] = "registration"
            page.goto(BASE + "/register/responsive-layout-test")
            page.set_viewport_size({"width": 390, "height": 360})
            page.get_by_label("Passport number").focus()
            page.get_by_label("Passport number").scroll_into_view_if_needed()
            check_layout(page, "short-viewport")
            assert not errors, errors
            browser.close()
            print(
                "PASS: applicant states, camera controls/preview/feedback across seven screen sizes",
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
ids = [uuid.UUID(data['process']), uuid.UUID(data['video_process'])]
with get_session_factory()() as db:
    for model in [VideoSubmission, ConsentRecord, RecordingChallenge, RegistrationLink]:
        db.execute(delete(model).where(model.client_process_id.in_(ids)))
    db.execute(delete(AuditLog).where(or_(AuditLog.entity_id.in_(ids), AuditLog.actor_id == admin_id)))
    db.execute(delete(ClientProcess).where(ClientProcess.id.in_(ids)))
    db.execute(delete(AdminSession).where(AdminSession.admin_id == admin_id))
    db.execute(delete(AdminUser).where(AdminUser.id == admin_id))
    db.commit()
""",
            {
                "admin": admin_id,
                "process": process_id,
                "video_process": video_process_id,
            },
        )


if __name__ == "__main__":
    main()
