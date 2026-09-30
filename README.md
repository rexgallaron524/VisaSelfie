# Visa Selfie

A working Phase 1 demo: administrators create applicant processes and 48-hour
registration links; applicants register, consent, record, preview/retake, and submit
a facial video; administrators track, review, download, and delete recordings.
WhatsApp sharing is manual. Appointment monitoring is not enabled or part of this phase.

## Start locally with Docker

Requirements: Docker Desktop/Engine with Compose 2.24.4 or later and support for
the project's Linux container images. Windows with Docker Desktop's WSL2 backend
is supported. No host installation of Node.js, Python, PostgreSQL, FFmpeg, or Caddy
is required to run the application. From this repository:

```powershell
# First setup only; keep your existing .env if you already have one.
Copy-Item .env.example .env
```

Edit `.env`: set a random `POSTGRES_PASSWORD`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY`.
For local development set `FRONTEND_PUBLIC_URL=http://localhost:3000`,
`APP_ENV=development`, `COOKIE_SECURE=false`, and
`ALLOWED_ORIGINS=http://localhost:3000` (JSON arrays are also supported).
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

For phone testing use the HTTPS deployment described below. A configured URL alone
does not provision DNS, certificates, or internet hosting; deploy to a server with
a reachable domain. Do not expose or tunnel the local development server.

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
are in the registration path (`/register/<token>`); the page sends the token to API
endpoints only in an authorization header. Links expire after 48 hours and are
consumed on successful submission. Treat the complete link as private. Registration
pages disable caching, referrers, and indexing. Disable or redact registration URL
logging at your CDN, hosting platform, reverse proxy, and web server, since the
initial page request contains the token. Do not attach analytics to this route.
Previously issued `/register#<token>` links remain supported until they expire.

Consent records contain the notice version, acceptance time, connection IP, and user
agent. In the local proxy setup the connection IP is the internal proxy address;
the API intentionally does not trust arbitrary forwarded-IP headers. The local rate
limit is also shared by requests from that proxy. Configure verified client IP handling
and a shared rate limiter at your trusted edge before a multi-instance deployment.

## HTTPS deployment and canonical registration links

On a new deployment host, create its own private `.env` from `.env.production.example`, supply
the database/storage credentials, and set:

```dotenv
APP_ENV=production
FRONTEND_PUBLIC_URL=https://demo.example.com
ALLOWED_ORIGINS=https://demo.example.com
COOKIE_SECURE=true
FORWARDED_ALLOW_IPS=
```

`FRONTEND_PUBLIC_URL` is the canonical frontend origin. The backend returns
`registration_url` for both new and replacement invitations, for example
`https://demo.example.com/register/<token>`. The admin page copies this exact value,
regardless of its current browser address or incoming Host/forwarded headers.
Trailing slashes are removed; invalid URLs, credentials, paths, query strings, and
fragments are rejected. Production rejects HTTP public URLs and HTTP allowed origins.
The public origin must appear in `ALLOWED_ORIGINS`; use comma-separated origins or
a JSON array when more than one origin is needed. Wildcards are rejected.

```powershell
docker compose -f compose.yaml -f compose.production.yaml up --build -d
```

The production override includes Caddy as the HTTPS gateway, a built Next.js app,
secure production API settings, persistent database/video/certificate volumes, and
restart policies for long-running services. Only Caddy publishes host ports: TCP
80 and 443. The frontend, API, database, and storage have no published production ports.
Point the hostname's DNS records to the server and allow TCP 80/443 through the host
and provider firewalls. Caddy obtains and renews certificates, redirects HTTP to
HTTPS, and forwards requests to `web:3000`. There is no separate Caddy installation.
Access logging is disabled because registration paths contain tokens. If another
CDN or proxy is added, disable/redact those paths there too. Do not log request bodies.

See [the deployment and recovery guide](docs/deployment.md) for startup checks,
client handover, cold backup/restore, and the isolated deployment test.

The browser uses the same public origin for pages and `/api/`; Next.js streams API
requests to `API_INTERNAL_URL` (Docker sets `http://api:8000`). No
`NEXT_PUBLIC_APP_URL` is needed. Cookies remain HttpOnly, SameSite=Lax, and host-only
(no Domain attribute), so they belong to the public frontend host. `COOKIE_SECURE`
can be omitted: it defaults to true for an HTTPS public URL and false for local HTTP.
An explicit false value is rejected in production. No cross-domain cookie setting
is needed for this same-origin architecture. Explicit origins also protect API
mutations against CSRF; credentialed CORS responses never use `*`.

Forwarded headers are ignored by default. With the included Next.js API proxy, leave
`FORWARDED_ALLOW_IPS` empty: that proxy intentionally strips untrusted forwarding
headers. If your deployment instead routes `/api/` directly from a trusted edge to
FastAPI, set `FORWARDED_ALLOW_IPS` to only that proxy's IP addresses or CIDRs (comma
separated), and make the edge overwrite `X-Forwarded-Proto` and `X-Forwarded-For`.
The API applies Uvicorn's proxy-header middleware to these trusted peers only;
wildcard trust is rejected. Its server command disables Uvicorn's separate automatic
proxy handling so this application policy is authoritative. Never use forwarded
headers to choose the canonical registration URL. See
[Uvicorn proxy settings](https://www.uvicorn.org/settings/#http) and
[FastAPI behind a proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).

After deploying, sign in at the HTTPS domain, create a client, and open the generated
link on a phone. Grant camera permission in Safari/Chrome. HTTPS is required for
mobile camera access; a real device and valid certificate are still needed to verify
platform-specific permissions. Existing 48-hour expiration and replacement behavior
is unchanged; already shared links retain their original hostname.

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
`backend/tests/test_public_url.py` also covers canonical local/HTTPS links (including
replacement), normalization, invalid settings, 48-hour expiry, secure login/logout
cookies, production origins/CORS, spoofed hosts, and trusted/untrusted proxy headers.
The browser smoke test uses `/register/<token>` and checks registration privacy headers.

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
