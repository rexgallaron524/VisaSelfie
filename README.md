# Visa Selfie

A working Phase 1 demo: administrators create applicant processes and 48-hour
registration links; applicants register, consent, record, preview/retake, and submit
a facial video; administrators track, review, download, and delete recordings.
WhatsApp sharing is manual. Appointment monitoring is not enabled or part of this phase.

## Start locally with Docker

Requirements: Docker Desktop/Engine with Compose. From this repository:

```powershell
# First setup only; keep your existing .env if you already have one.
Copy-Item .env.example .env
```

Edit `.env`: set a random `POSTGRES_PASSWORD`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY`.
Use different credentials for the database and storage. Use URL-safe characters
(letters, numbers, `_`, `-`) for the database password because Compose embeds it in
the connection URL. Never commit `.env` or copies containing secrets.

```powershell
docker compose up --build -d
docker compose ps -a
```

The `db` and `api` services should become healthy; `web` and `storage` should run.
`migrate` and `storage-init` should exit with code 0. These one-off services apply
database migrations and initialize the private S3 bucket before the API starts.
Existing database data is preserved during upgrades; do not remove the volumes.

If you have no admin account yet:

```powershell
docker compose exec api python -m app.cli create-admin --email admin@example.com
```

Enter a password with 12–128 characters. Input is hidden. Existing admin accounts
continue working; there is no default password or public signup.

Open **http://localhost:3000**. Use `localhost` consistently because that is the
default allowed browser origin. API docs are at http://localhost:8000/api/docs.

## Try the complete workflow

1. Sign in. Select **Create client**, enter a name and phone number, and create the process.
2. Copy the generated link. It is shown only once; send it manually through WhatsApp.
   For testing, open it in another browser tab or private window on the same computer.
3. Enter the applicant's name, birth date, passport number, and phone number.
4. Read and accept the privacy notice, then follow the recording instructions.
5. Allow front-camera access, record for 3–30 seconds, and stop. No microphone is needed.
6. Preview or retake, then select **Confirm and submit**. Keep the page open until
   the success confirmation appears. Interrupted uploads can be retried from the preview.
7. Return to the admin client detail page and select **Refresh status**. Play or
   download the video and mark it reviewed.
8. Select **Delete video** and confirm. The stored object becomes inaccessible;
   client details, consent, timestamps, and audit history remain.

The overview shows client counts, pending registrations, submitted/reviewed videos,
expired links, recent processes, and activity. The client list supports name search,
status filters, and pagination. An expired link can be replaced from client details;
replacement immediately revokes the old link and preserves existing registration/consent.
Completed/deleted processes are closed; create a new process for another recording.

## Camera and mobile testing

Modern Chrome and Safari support the recording flow. Camera access requires a
secure browser context: `http://localhost` works on your own computer; a phone needs
a reachable **HTTPS** address. A link to `localhost` on a phone refers to the phone,
not your computer. The local Compose ports deliberately bind to loopback.

For phone testing, put the web service behind your HTTPS reverse proxy on a reachable
hostname, set `ALLOWED_ORIGINS=["https://your-hostname"]`, `COOKIE_SECURE=true`, and
`APP_ENV=production`, then rebuild/restart. Generate links while using that hostname.
Route browser traffic through Next.js, keep API/database/storage private, and configure
the proxy to accept 30 MiB request bodies and at least 180-second upload timeouts.
Do not enable request-body logging. Set HSTS at the HTTPS edge.

If a WhatsApp embedded browser blocks camera access, open the link in Safari/Chrome.
Camera-denied, unsupported-browser, invalid-link, expired-link, oversized-recording,
and upload-failure states have recovery instructions. A preview exists only in the
current page's memory; refreshing before submission requires recording again.

## Storage and privacy

Docker uses **SeaweedFS 4.47**, a verified available S3-compatible image, with a private
named volume. Its ports are not published to the host. Only the backend has storage
credentials. The earlier unavailable MinIO image is no longer used; old `MINIO_ROOT_*`
entries can be removed from `.env`.

Uploads stream through the API into a bounded temporary file, are inspected by
`ffprobe`, and are stored in S3 only after validation. Accepted formats are WebM/MP4
with supported video codecs; the default maximum is 30 MiB and 30 seconds. The browser
records at 640×480 where supported. The API checks actual format, dimensions, and packet
duration rather than trusting the filename or a claimed duration. Files never go in PostgreSQL.

Admin playback/download streams through authenticated API routes, supports HTTP
byte ranges, disables caching, and creates audit events. No public video URLs are
issued. Deletion first disables video access, removes the object, then records success;
if storage is unavailable, **Retry deletion** completes the operation later.

Tokens use 256 bits of randomness and are stored only as hashes. Invitation tokens
are in the link fragment (`/register#...`), which is not sent in HTTP request URLs;
the page sends the token in an authorization header. Links expire after 48 hours
and are consumed on successful submission. Treat the complete link as private.

Consent records contain the notice version, acceptance time, connection IP, and user
agent. In the local proxy setup the connection IP is the internal proxy address;
the API intentionally does not trust arbitrary forwarded-IP headers. The local rate
limit is also shared by requests from that proxy. Configure verified client IP handling
and a shared rate limiter at your trusted edge before a multi-instance deployment.

Video deletion is manual in Phase 1. Operators must decide their retention schedule
and handle backups accordingly. This demo collects recordings for human review; it
does not perform automated face matching, liveness detection, or embassy submission.

## Stop, restart, and troubleshoot

```powershell
docker compose down
docker compose up -d
docker compose logs --tail=100 migrate storage-init api web
```

Stopping containers preserves database and object volumes. After code changes use
`docker compose up --build -d` to rebuild. The web container runs Next.js development
mode for the local demo; source is copied at build time, not mounted from the host.
If storage credentials change after initialization, rotate them in the storage service
as well; do not discard populated volumes to reset credentials.

## Development and checks

Backend: Python 3.12+, PostgreSQL, an S3-compatible service, and `ffprobe` from FFmpeg.
Frontend: Node.js 20.9+. Docker includes all runtime prerequisites. To run the API
directly, copy `backend/.env.example` to `backend/.env`, configure your reachable
database/S3 endpoints and credentials, and put `ffprobe` on PATH or set `FFPROBE_PATH`.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.lock
.\.venv\Scripts\python -m pip install -e './backend[dev]'
cd backend
..\.venv\Scripts\alembic upgrade head
..\.venv\Scripts\python -m app.storage
..\.venv\Scripts\uvicorn app.main:create_app --factory --reload --no-access-log --no-proxy-headers
```

In another terminal, `cd frontend`, copy `.env.local.example` to `.env.local`, then
run `npm ci` and `npm run dev`. On macOS/Linux use `python3`, `.venv/bin/`, and `cp`.

Checks from `backend/`:

```powershell
..\.venv\Scripts\pytest -q
..\.venv\Scripts\ruff check app migrations tests
..\.venv\Scripts\ruff format --check app migrations tests
```

Checks from `frontend/`: `npm run lint`, `npm run typecheck`, and `npm run build`.
Unit/API tests use temporary SQLite databases and a memory storage double. They test
authorization, consent gating, link expiry/replacement, replay prevention, upload
limits, storage failures, private downloads, deletion retries, and migrations.

For a real PostgreSQL/S3/browser check, start Docker, install Playwright into the
development environment, and run from the root:

```powershell
.\.venv\Scripts\python -m pip install playwright
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python scripts/smoke_phase1.py
```

This records a synthetic camera stream in Chromium, exercises registration through
deletion, checks unauthorized S3 access, and cleans up only its own disposable records.
Physical iOS/Android devices still need manual camera/permission testing over HTTPS.

Runtime dependencies are pinned in `backend/requirements.lock` and
`frontend/package-lock.json`. Refresh Python pins with
`uv pip compile backend/pyproject.toml --universal --output-file backend/requirements.lock`.

See [architecture](docs/architecture.md) for the data model, routes, and security boundaries.
