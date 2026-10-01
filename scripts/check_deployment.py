"""Test production containers without touching the running application or public ports.

Requires Docker Compose 2.24.4+, Python, and Playwright/Chromium for smoke_phase1.py.
Creates two uniquely named Compose projects and removes ONLY their containers/volumes.
Uses a temporary internal CA; never requests a public certificate or changes host trust.
"""

import base64
import hashlib
import http.cookiejar
import json
import os
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKER = shutil.which("docker") or str(
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "Programs/DockerDesktop/resources/bin/docker.exe"
)


def run(args, *, env, input=None, check=True, timeout=600):
    result = subprocess.run(
        args,
        check=False,
        cwd=ROOT,
        env=env,
        input=input,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )
    if check and result.returncode:
        raise RuntimeError(
            f"Command failed ({args[:3]}):\n{result.stdout[-3000:]}\n{result.stderr[-3000:]}"
        )
    return result


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    suffix = uuid.uuid4().hex[:12]
    projects = [f"visaselfie-check-{suffix}", f"visaselfie-restore-{suffix}"]
    temp_base = Path(tempfile.gettempdir()).resolve()
    work = Path(tempfile.mkdtemp(prefix="visaselfie-deploy-check-")).resolve()
    # Explicitly constrain the eventual recursive cleanup to this generated directory.
    if work.parent != temp_base or not work.name.startswith("visaselfie-deploy-check-"):
        raise RuntimeError("Unexpected temporary directory")
    backup_dir = work / "backups"
    backup_dir.mkdir()
    caddy_dir = work / "caddy"
    caddy_dir.mkdir()
    (caddy_dir / "Caddyfile").write_text(
        "https://localhost {\n tls internal\n header Strict-Transport-Security max-age=31536000\n"
        " reverse_proxy web:3000\n}\n",
        encoding="utf-8",
    )
    port = available_port()
    base = f"https://localhost:{port}"
    env_file = work / "test.env"
    env_file.write_text(
        f"POSTGRES_USER=visaselfie\nPOSTGRES_DB=visaselfie\n"
        f"POSTGRES_PASSWORD={secrets.token_hex(24)}\n"
        f"S3_ACCESS_KEY={secrets.token_hex(16)}\nS3_SECRET_KEY={secrets.token_hex(24)}\n"
        f"APP_ENV=production\nCOOKIE_SECURE=true\nFRONTEND_PUBLIC_URL={base}\n"
        f"ALLOWED_ORIGINS={base}\nFORWARDED_ALLOW_IPS=\n",
        encoding="utf-8",
    )
    override = work / "check.yaml"
    override.write_text(
        "services:\n  gateway:\n    ports: !override\n"
        f'      - "127.0.0.1:{port}:443"\n    volumes:\n'
        f"      - type: bind\n        source: {json.dumps(caddy_dir.as_posix())}\n"
        "        target: /etc/caddy\n        read_only: true\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Prevent the caller's shell from overriding the isolated env file.
    for key in [
        "POSTGRES_USER",
        "POSTGRES_DB",
        "POSTGRES_PASSWORD",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "APP_ENV",
        "COOKIE_SECURE",
        "FRONTEND_PUBLIC_URL",
        "ALLOWED_ORIGINS",
        "FORWARDED_ALLOW_IPS",
    ]:
        env.pop(key, None)
    env.update(ENV_FILE=str(env_file), BACKUP_DIR=str(backup_dir))
    common = [
        "--env-file",
        str(env_file),
        "-f",
        "compose.yaml",
        "-f",
        "compose.production.yaml",
        "-f",
        "compose.ops.yaml",
    ]

    def compose(project, *args, check=True):
        return run(
            [DOCKER, "compose", *common, "-f", str(override), "-p", project, *args],
            env=env,
            check=check,
        )

    def remote(project, code):
        return compose(
            project, "exec", "-T", "api", "python", "-c", code
        ).stdout.strip()

    def trusted_context(project):
        for attempt in range(30):
            result = compose(
                project,
                "exec",
                "-T",
                "gateway",
                "cat",
                "/data/caddy/pki/authorities/local/root.crt",
                check=False,
            )
            if result.returncode == 0:
                return ssl.create_default_context(cadata=result.stdout)
            time.sleep(1)
        raise RuntimeError("Test CA did not become available")

    def check_https(context):
        for attempt in range(30):
            try:
                with urllib.request.urlopen(
                    base + "/api/ready", context=context, timeout=5
                ) as r:
                    assert json.load(r)["status"] == "ready"
                with urllib.request.urlopen(
                    base + "/register/test-link", context=context, timeout=5
                ) as r:
                    assert "no-store" in r.headers["Cache-Control"]
                    assert r.headers["Referrer-Policy"] == "no-referrer"
                    assert "noindex" in r.headers["X-Robots-Tag"]
                return
            except (OSError, ValueError):
                if attempt == 29:
                    raise
                time.sleep(1)

    try:
        # Check actual production configuration BEFORE the loopback test override.
        config = json.loads(
            run(
                [
                    DOCKER,
                    "compose",
                    *common,
                    "-p",
                    projects[0],
                    "config",
                    "--format",
                    "json",
                ],
                env=env,
            ).stdout
        )
        for name in ("db", "storage", "api", "web"):
            assert not config["services"][name].get("ports"), (
                f"Unexpected public port: {name}"
            )
            assert config["services"][name]["restart"] == "unless-stopped"
        assert {
            str(p["published"]) for p in config["services"]["gateway"]["ports"]
        } == {"80", "443"}
        print(
            "PASS: production exposes only HTTPS gateway ports; restart policies configured",
            flush=True,
        )
        compose(projects[0], "up", "--build", "-d", "--wait", "--wait-timeout", "180")
        context = trusted_context(projects[0])
        check_https(context)
        print(
            "PASS: clean production stack, trusted test TLS, private registration headers",
            flush=True,
        )
        smoke_env = env | {
            "SMOKE_BASE_URL": base,
            "SMOKE_COMPOSE_ARGS": json.dumps(
                [*common, "-f", str(override), "-p", projects[0]]
            ),
            "SMOKE_ALLOW_SELF_SIGNED": "1",
        }
        result = run([sys.executable, "scripts/smoke_phase1.py"], env=smoke_env)
        print(result.stdout, end="", flush=True)
        # A large non-face upload must be rejected. Seed it separately for storage/recovery checks.
        password = secrets.token_urlsafe(24)
        remote(
            projects[0],
            f"""
from app.auth.models import AdminUser
from app.core.database import get_session_factory
from app.core.security import password_hasher
with get_session_factory()() as db:
    db.add(AdminUser(email='large-video@example.com', password_hash=password_hasher.hash({password!r})))
    db.commit()
""",
        )
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )

        def request(path, payload=None, bearer=None, video=None):
            headers = {"Origin": base}
            data = None
            if payload is not None:
                data = json.dumps(payload).encode()
                headers["Content-Type"] = "application/json"
            if video is not None:
                data = video
                headers["Content-Type"] = "video/mp4"
                headers["X-Recording-Challenge"] = challenge_id
            if bearer:
                headers["Authorization"] = f"Bearer {bearer}"
            req = urllib.request.Request(base + path, data=data, headers=headers)
            with opener.open(req, timeout=180) as response:
                return response.read()

        request(
            "/api/auth/login",
            {"email": "large-video@example.com", "password": password},
        )
        issued = json.loads(
            request(
                "/api/admin/processes",
                {
                    "full_name": "Large Video Test",
                    "phone_number": "+44 7700 900123",
                },
            )
        )
        token = issued["token"]
        state = json.loads(request("/api/public/open", {}, token))
        request(
            "/api/public/register",
            {
                "full_name": "Large Video Test",
                "phone_number": "+44 7700 900123",
                "date_of_birth": "1990-06-15",
                "passport_number": "TEST12345",
            },
            token,
        )
        request(
            "/api/public/consent",
            {"accepted": True, "version": state["consent_version"]},
            token,
        )
        challenge_id = json.loads(request("/api/public/recording", {}, token))["id"]
        video = base64.b64decode(
            remote(
                projects[0],
                """
import base64, subprocess, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'large.mp4'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i',
        'testsrc2=size=640x480:rate=24', '-t', '18', '-c:v', 'libx264',
        '-preset', 'ultrafast', '-b:v', '8M', '-minrate', '8M', '-maxrate', '8M',
        '-bufsize', '8M', '-x264-params', 'nal-hrd=cbr:filler=1',
        '-pix_fmt', 'yuv420p', '-an', '-movflags', '+faststart', str(path)],
        check=True, timeout=60)
    import shutil
    shutil.copyfile(path, '/tmp/visaselfie-large-test.mp4')
    print(base64.b64encode(path.read_bytes()).decode())
""",
            )
        )
        assert 4.5 * 1024 * 1024 < len(video) < 30 * 1024 * 1024
        remote(
            projects[0],
            f"""
from datetime import timedelta
from app.core.database import get_session_factory
from app.core.security import utcnow
from app.processes.models import RecordingChallenge
import uuid
with get_session_factory()() as db:
    db.get(RecordingChallenge, uuid.UUID({challenge_id!r})).created_at = utcnow() - timedelta(seconds=20)
    db.commit()
""",
        )
        try:
            request("/api/public/video", bearer=token, video=video)
            raise AssertionError("Synthetic non-face video was accepted")
        except urllib.error.HTTPError as error:
            assert error.code == 422
            assert not json.load(error)["detail"]["assessment"]["passed"]
        remote(
            projects[0],
            f"""
import uuid
from pathlib import Path
from app.core.database import get_session_factory
from app.core.config import get_settings
from app.processes.models import ClientProcess, VideoSubmission
from app.storage import ObjectStore
process_id = uuid.UUID({issued["process_id"]!r})
path = Path('/tmp/visaselfie-large-test.mp4')
key = f'videos/{{process_id}}/synthetic-large.mp4'
store = ObjectStore(get_settings())
with path.open('rb') as file:
    store.put(key, file, path.stat().st_size, 'video/mp4')
with get_session_factory()() as db:
    db.add(VideoSubmission(client_process_id=process_id, storage_key=key,
        original_filename='recording.mp4', mime_type='video/mp4', file_size=path.stat().st_size, duration=18))
    db.get(ClientProcess, process_id).status = 'submitted'
    db.commit()
path.unlink()
""",
        )
        video_path = f"/api/admin/processes/{issued['process_id']}/video"
        video_hash = hashlib.sha256(video).digest()
        assert hashlib.sha256(request(video_path)).digest() == video_hash
        print(
            f"PASS: {len(video) / 1024 / 1024:.1f} MiB non-face upload rejected; seeded video downloaded for recovery checks",
            flush=True,
        )
        marker = secrets.token_hex(32)
        remote(
            projects[0],
            f"""
from sqlalchemy import text
from app.core.database import get_session_factory
from app.core.config import get_settings
from app.storage import ObjectStore
with get_session_factory()() as db:
    db.execute(text('CREATE TABLE deployment_probe (value text NOT NULL)'))
    db.execute(text('INSERT INTO deployment_probe VALUES (:value)'), {{'value': {marker!r}}})
    db.commit()
store = ObjectStore(get_settings())
store.client.put_object(Bucket=store.bucket, Key='deployment-probe', Body={marker!r}.encode())
""",
        )
        verify = """
from sqlalchemy import text
from app.core.database import get_session_factory
from app.core.config import get_settings
from app.storage import ObjectStore
with get_session_factory()() as db:
    value = db.scalar(text('SELECT value FROM deployment_probe'))
store = ObjectStore(get_settings())
assert store.client.get_object(Bucket=store.bucket, Key='deployment-probe')['Body'].read().decode() == value
print(value)
"""
        # Exercise container recreation with the existing volumes, not just a graceful reload.
        compose(projects[0], "down")
        compose(projects[0], "up", "-d", "--wait", "--wait-timeout", "180")
        check_https(context)
        assert remote(projects[0], verify) == marker
        assert hashlib.sha256(request(video_path)).digest() == video_hash
        print(
            "PASS: container recreation retains database, stored object, and TLS CA",
            flush=True,
        )
        api_id = compose(projects[0], "ps", "-q", "api").stdout.strip()
        compose(
            projects[0],
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            "import os, signal; os.kill(1, signal.SIGTERM)",
            check=False,
        )
        for attempt in range(30):
            restarted = run(
                [DOCKER, "inspect", "--format", "{{.RestartCount}}", api_id], env=env
            )
            if int(restarted.stdout.strip()) > 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("API did not restart after process exit")
        check_https(context)
        assert remote(projects[0], verify) == marker
        print("PASS: automatic API process-exit recovery", flush=True)
        # Cold backup: stop writers and storage, leave only PostgreSQL running.
        compose(projects[0], "stop", "gateway", "web", "api", "storage")
        result = compose(projects[0], "run", "--build", "--rm", "--no-deps", "backup")
        print(
            "\n".join(
                line
                for line in result.stdout.splitlines()
                if line.startswith("Backup complete:")
            ),
            flush=True,
        )
        snapshots = list(backup_dir.glob("backup-*"))
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        cert_hash = hashlib.sha256(
            (snapshot / "certificates.tar.gz").read_bytes()
        ).hexdigest()
        env["RESTORE_BACKUP"] = snapshot.name
        compose(projects[1], "up", "-d", "db", "--wait", "--wait-timeout", "90")
        compose(projects[1], "run", "--build", "--rm", "--no-deps", "restore")
        refused = compose(
            projects[1], "run", "--rm", "--no-deps", "restore", check=False
        )
        assert (
            refused.returncode != 0 and "not empty" in refused.stderr + refused.stdout
        )
        assert (
            hashlib.sha256((snapshot / "certificates.tar.gz").read_bytes()).hexdigest()
            == cert_hash
        )
        compose(projects[1], "up", "--build", "-d", "--wait", "--wait-timeout", "180")
        check_https(
            context
        )  # Original CA still trusted after restoring certificate data.
        assert remote(projects[1], verify) == marker
        assert hashlib.sha256(request(video_path)).digest() == video_hash
        print(
            "PASS: backup restores DB, objects, and TLS data to a fresh deployment; overwrite refused",
            flush=True,
        )
    finally:
        for project in projects:
            # Both names were generated here; never target the user's visa-selfie project.
            compose(project, "down", "--volumes", "--remove-orphans", check=False)
        if work.parent == temp_base and work.name.startswith(
            "visaselfie-deploy-check-"
        ):
            shutil.rmtree(work)


if __name__ == "__main__":
    main()
