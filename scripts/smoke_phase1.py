"""Exercise the running Docker demo with a synthetic camera and disposable records.

Run from the repository root after `docker compose up --build -d`:
  .venv/Scripts/python scripts/smoke_phase1.py
Requires Playwright (`uv pip install --python .venv/Scripts/python.exe playwright`)
and Chromium (`.venv/Scripts/python -m playwright install chromium`).
Optionally set PLAYWRIGHT_CHROMIUM_EXECUTABLE to an existing Chromium binary.
Only records belonging to this run's random admin/process IDs are cleaned up.
"""

import json
import os
import secrets
import shutil
import subprocess
import uuid
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("SMOKE_BASE_URL", "http://localhost:3000").rstrip("/")
COMPOSE_ARGS = json.loads(os.environ.get("SMOKE_COMPOSE_ARGS", "[]"))
# Only for the isolated deployment check, which uses its own temporary CA.
ALLOW_SELF_SIGNED = os.environ.get("SMOKE_ALLOW_SELF_SIGNED") == "1"
DOCKER = shutil.which("docker") or str(
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "Programs/DockerDesktop/resources/bin/docker.exe"
)


def remote(source, data):
    result = subprocess.run(
        [
            DOCKER,
            "compose",
            *COMPOSE_ARGS,
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            "import json, sys\ndata = json.load(sys.stdin)\n" + source,
        ],
        check=False,
        input=json.dumps(data),
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=ROOT,
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def main():
    admin_id = str(uuid.uuid4())
    email = f"smoke-{admin_id}@example.com"
    password = secrets.token_urlsafe(24)
    processes = []
    remote(
        """
import uuid
from app.core.database import get_session_factory
from app.core.security import password_hasher
from app.auth.models import AdminUser
with get_session_factory()() as db:
    db.add(AdminUser(id=uuid.UUID(data['id']), email=data['email'],
                     password_hash=password_hasher.hash(data['password'])))
    db.commit()
""",
        {"id": admin_id, "email": email, "password": password},
    )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
                or None,
                headless=True,
                args=[
                    "--use-fake-device-for-media-stream",
                    "--use-fake-ui-for-media-stream",
                ],
            )
            no_js = browser.new_context(
                java_script_enabled=False, ignore_https_errors=ALLOW_SELF_SIGNED
            )
            fallback = no_js.new_page()
            fallback.goto(BASE + "/login")
            expect(
                fallback.get_by_role("button", name="Sign in to your workspace")
            ).to_be_disabled()
            assert fallback.locator("form").get_attribute("method") == "post"
            no_js.close()
            admin_context = browser.new_context(
                viewport={"width": 1365, "height": 900},
                ignore_https_errors=ALLOW_SELF_SIGNED,
            )
            admin = admin_context.new_page()
            errors = []
            admin.on("pageerror", lambda e: errors.append(str(e)))
            admin.goto(BASE + "/login")
            admin.get_by_label("Email address").fill(email)
            admin.get_by_label("Password", exact=True).fill(password)
            admin.get_by_role("button", name="Sign in to your workspace").click()
            expect(admin).to_have_url(BASE + "/dashboard", timeout=30000)
            print("PASS: protected login and safe pre-hydration form", flush=True)
            admin.get_by_role("link", name="+ Create client").click()
            admin.get_by_label("Full name").fill("Phase One Browser Test")
            admin.get_by_label("Phone number including country code").fill(
                "+44 7700 900123"
            )
            with admin.expect_response("**/api/admin/processes") as response:
                admin.get_by_role("button", name="Create client and link").click()
            issued = response.value.json()
            process_id = issued["process_id"]
            processes.append(process_id)
            invitation = admin.get_by_label("Private registration link").input_value()
            assert invitation == issued["registration_url"]
            assert invitation == BASE + "/register/" + issued["token"]
            admin.get_by_role("link", name="View client process").click()

            applicant_context = browser.new_context(
                ignore_https_errors=ALLOW_SELF_SIGNED,
                viewport={"width": 390, "height": 844},
                permissions=["camera"],
            )
            page = applicant_context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            requested_urls = []
            page.on("request", lambda request: requested_urls.append(request.url))
            navigation = page.goto(invitation)
            assert navigation.headers["referrer-policy"] == "no-referrer"
            # Next dev overrides Cache-Control; production uses private, no-store.
            assert any(
                directive in navigation.headers["cache-control"]
                for directive in ("no-store", "no-cache")
            )
            assert "noindex" in navigation.headers["x-robots-tag"]
            expect(page.get_by_role("heading", name="Your details")).to_be_visible()
            page.get_by_label("Date of birth").fill("1990-06-15")
            page.get_by_label("Passport number").fill("TEST123456")
            phone = page.get_by_label("Phone number including country code", exact=True)
            expect(phone).to_have_value("+44 7700 900123")
            expect(phone).to_have_attribute("readonly", "")
            phone.press("End")
            phone.press("Backspace")
            expect(phone).to_have_value("+44 7700 900123")
            # Simulate bypassing the read-only field; the server must still reject changes.
            phone.evaluate("input => { input.value = '+44 7700 900999'; }")
            page.get_by_role("button", name="Continue", exact=True).click()
            expect(
                page.get_by_role("alert").filter(
                    has_text="This phone number does not match your invitation"
                )
            ).to_be_visible()
            expect(page.get_by_role("heading", name="Your details")).to_be_visible()
            expect(phone).to_have_value("+44 7700 900123")
            page.get_by_role("button", name="Continue", exact=True).click()
            expect(
                page.get_by_role("heading", name="Your privacy and consent")
            ).to_be_visible()
            print("PASS: prefilled read-only phone, tampering rejected, correct retry accepted", flush=True)
            page.get_by_role("checkbox").check()
            page.get_by_role("button", name="Agree and continue").click()
            page.get_by_role("button", name="Continue to camera").click()
            page.get_by_role("button", name="Enable camera").click()

            def record():
                page.get_by_role("button", name="Start recording", exact=True).click()
                expect(
                    page.get_by_role("heading", name="Preview your recording")
                ).to_be_visible(timeout=25000)

            record()
            page.get_by_role("button", name="Retake", exact=True).click()
            record()
            with page.expect_response("**/api/public/video", timeout=120000) as checked:
                page.get_by_role("button", name="Confirm and submit").click()
            assert checked.value.status == 422, checked.value.text()
            assert checked.value.json()["detail"]["assessment"]["passed"] is False
            expect(page.get_by_label("Recording feedback")).to_be_visible()
            expect(
                page.get_by_role("button", name="Confirm and submit")
            ).to_be_disabled()
            expect(
                page.get_by_role("button", name="Retake", exact=True)
            ).to_be_enabled()
            print(
                "PASS: guided recording, retake, server rejection of a non-face camera feed, feedback",
                flush=True,
            )
            # Seed a legacy synthetic video ONLY for admin/storage lifecycle checks.
            # This is not a successful face/liveness verification or a production bypass.
            encoded = page.evaluate("""async () => {
                const video = document.querySelector('video[src]');
                const blob = await (await fetch(video.src)).blob();
                return await new Promise(resolve => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result.split(',')[1]);
                    reader.readAsDataURL(blob);
                });
            }""")
            remote(
                """
import base64, uuid
from sqlalchemy import select
from app.core.database import get_session_factory
from app.core.config import get_settings
from app.core.security import utcnow
from app.processes.models import ClientProcess, RegistrationLink, VideoSubmission
from app.storage import ObjectStore
process_id = uuid.UUID(data['id'])
key = f'videos/{process_id}/synthetic-test.webm'
store = ObjectStore(get_settings())
video = base64.b64decode(data['video'])
with get_session_factory()() as db:
    assert db.scalar(select(VideoSubmission).where(VideoSubmission.client_process_id == process_id)) is None
    store.client.put_object(Bucket=store.bucket, Key=key, Body=video, ContentType='video/webm')
    db.add(VideoSubmission(client_process_id=process_id, storage_key=key,
        original_filename='recording.webm', mime_type='video/webm', file_size=len(video), duration=18))
    db.get(ClientProcess, process_id).status = 'submitted'
    link = db.scalar(select(RegistrationLink).where(RegistrationLink.client_process_id == process_id))
    link.used_at = utcnow()
    link.status = 'used'
    db.commit()
""",
                {"id": process_id, "video": encoded},
            )
            assert not any(
                issued["token"] in url for url in requested_urls if "/api/" in url
            ), "Token leaked in API URL"
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            assert (
                page.request.get(
                    BASE + f"/api/admin/processes/{process_id}/video"
                ).status
                == 401
            )
            admin.reload()
            expect(admin.get_by_text("Submitted", exact=True)).to_be_visible()
            admin.get_by_role("button", name="View recording").click()
            admin.wait_for_function(
                "document.querySelector('video')?.readyState >= 1", timeout=20000
            )
            print("PASS: authenticated video metadata/playback", flush=True)
            video_response = admin_context.request.get(
                BASE + f"/api/admin/processes/{process_id}/video",
                headers={"Range": "bytes=0-31"},
            )
            assert video_response.status == 206 and len(video_response.body()) == 32
            with admin.expect_download() as download:
                admin.get_by_role("link", name="Download video").click()
            assert download.value.suggested_filename == "recording.webm"
            admin.get_by_role("button", name="Mark reviewed").click()
            expect(admin.get_by_text("Reviewed", exact=True)).to_be_visible()

            # Verify the stored object cannot be read without S3 authentication.
            assert (
                remote(
                    """
import uuid, urllib.request, urllib.error
from sqlalchemy import select
from app.core.database import get_session_factory
from app.core.config import get_settings
from app.processes.models import VideoSubmission
with get_session_factory()() as db:
    key = db.scalar(select(VideoSubmission.storage_key).where(
        VideoSubmission.client_process_id == uuid.UUID(data['id'])))
settings = get_settings()
try:
    response = urllib.request.urlopen(f'{settings.s3_endpoint_url}/{settings.s3_bucket}/{key}')
    print(response.status)
except urllib.error.HTTPError as e:
    print(e.code)
""",
                    {"id": process_id},
                )
                == "403"
            )

            admin.get_by_role("button", name="Delete video", exact=True).click()
            admin.get_by_role("button", name="Confirm", exact=True).click()
            expect(admin.get_by_text("Deleted", exact=True)).to_be_visible()
            assert (
                admin_context.request.get(
                    BASE + f"/api/admin/processes/{process_id}/video"
                ).status
                == 410
            )
            page.reload()
            expect(
                page.get_by_role("heading", name="Recording submitted")
            ).to_be_visible()
            page.goto(BASE + "/register#invalid")
            expect(
                page.get_by_role("heading", name="This link isn’t valid")
            ).to_be_visible()

            # Expired-link page, followed by replacement invalidation.
            resp = admin_context.request.post(
                BASE + "/api/admin/processes",
                headers={"Origin": BASE},
                data={
                    "full_name": "Phase One Expiry Test",
                    "phone_number": "+44 7700 900555",
                },
            )
            assert resp.status == 201
            expiring = resp.json()
            processes.append(expiring["process_id"])
            remote(
                """
import uuid
from datetime import timedelta
from sqlalchemy import select
from app.core.database import get_session_factory
from app.core.security import utcnow
from app.processes.models import RegistrationLink
with get_session_factory()() as db:
    link = db.scalar(select(RegistrationLink).where(
        RegistrationLink.client_process_id == uuid.UUID(data['id'])))
    link.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
""",
                {"id": expiring["process_id"]},
            )
            page.goto(expiring["registration_url"])
            expect(
                page.get_by_role("heading", name="Your link has expired")
            ).to_be_visible()
            replacement = admin_context.request.post(
                BASE + f"/api/admin/processes/{expiring['process_id']}/link",
                headers={"Origin": BASE},
            )
            assert replacement.status == 200
            page.reload()
            expect(
                page.get_by_role("heading", name="This link isn’t valid")
            ).to_be_visible()
            # Invitations issued before canonical path URLs remain usable.
            page.goto(BASE + "/register#" + replacement.json()["token"])
            expect(page.get_by_label("Full name")).to_be_visible()
            assert not errors, errors
            browser.close()
        print(
            "PASS: guided capture and non-face rejection; seeded legacy video: private S3, "
            "admin playback/ranges/download/review/deletion, expired/replaced links."
        )
    finally:
        remote(
            """
import uuid
from sqlalchemy import select, delete, or_
from app.core.database import get_session_factory
from app.core.config import get_settings
from app.auth.models import AdminUser, AdminSession
from app.audit.models import AuditLog
from app.processes.models import ClientProcess, ConsentRecord, RecordingChallenge, RegistrationLink, VideoSubmission
from app.storage import ObjectStore
ids = [uuid.UUID(value) for value in data['processes']]
admin_id = uuid.UUID(data['admin_id'])
with get_session_factory()() as db:
    # Include a process if creation succeeded but a later browser assertion failed.
    ids += list(db.scalars(select(AuditLog.entity_id).where(
        AuditLog.actor_id == admin_id, AuditLog.action == 'process.created')))
    store = ObjectStore(get_settings())
    for key in db.scalars(select(VideoSubmission.storage_key).where(
        VideoSubmission.client_process_id.in_(ids))):
        store.delete(key)
    for model in [VideoSubmission, ConsentRecord, RecordingChallenge, RegistrationLink]:
        db.execute(delete(model).where(model.client_process_id.in_(ids)))
    db.execute(delete(AuditLog).where(or_(
        AuditLog.entity_id.in_(ids), AuditLog.actor_id == admin_id)))
    db.execute(delete(ClientProcess).where(ClientProcess.id.in_(ids)))
    db.execute(delete(AdminSession).where(AdminSession.admin_id == admin_id))
    db.execute(delete(AdminUser).where(AdminUser.id == admin_id))
    db.commit()
""",
            {"processes": processes, "admin_id": admin_id},
        )


if __name__ == "__main__":
    main()
