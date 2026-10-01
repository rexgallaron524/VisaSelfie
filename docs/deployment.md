# Deployment and recovery

The complete application runs in Docker, including HTTPS, video validation,
database, and storage. Use Docker Compose 2.24.4 or newer with Linux-container
support (including Docker Desktop with WSL2 on Windows). Native Windows-container
mode is not supported by these images. The deployment was tested on Windows using
Docker Desktop's Linux engine; a separate Linux host has not yet been tested.

## Before starting

- Use the current source files, including `compose.production.yaml` and `deploy/`.
- Configure a real hostname with DNS pointing to the server. Correct/remove any
  stale IPv6 record as well as checking IPv4.
- Allow incoming TCP 80 and 443 through the server and provider firewalls. No
  other application ports need public access.
- Configure the Docker engine to start after reboot. Container restart policies
  apply once the engine is running; they do not start Docker Desktop or Windows.
- Keep access to the original `.env` and its credentials in secure storage.

No separate installation of Caddy, Python, Node.js, PostgreSQL, or FFmpeg is needed.
DNS/account setup and host firewall/engine management happen outside the containers.

### Windows firewall conflicts

If Caddy responds locally but certificate validation times out, inspect both the
web-port allow rule and any application block rules for `com.docker.backend.exe`.
An explicit block takes precedence over an allow rule. Check the active network
profile too: Docker can be blocked on the Public profile even when TCP 80/443
have a separate allow rule.

For an existing Docker TCP block rule, an administrator can narrow its blocked
ports to `1-79,81-442,444-65535`, preserving the block on other ports while allowing
the existing web-port rule to apply. Do not disable the whole firewall. Verify
TCP 80/443 from a separate computer, then check Caddy's certificate logs and open
the HTTPS site without bypassing certificate validation.

## Start a fresh deployment

Copy `.env.production.example` to `.env` (PowerShell: `Copy-Item`; Linux/macOS: `cp`).
Set strong, distinct database and storage credentials and replace the example
hostname in `FRONTEND_PUBLIC_URL` and `ALLOWED_ORIGINS`. Database passwords must use
URL-safe characters because Compose embeds them in a connection URL. Do not replace
credentials on an existing installation without a deliberate rotation procedure.

```text
docker compose -f compose.yaml -f compose.production.yaml config --quiet
docker compose -f compose.yaml -f compose.production.yaml up --build -d --wait
docker compose -f compose.yaml -f compose.production.yaml ps -a
```

The API, database, and frontend should become healthy. Storage and gateway should
run; migration and storage initialization should finish with exit code 0. Container
health does not prove certificate issuance or public reachability. Check gateway logs:

```text
docker compose -f compose.yaml -f compose.production.yaml logs --tail=100 gateway
```

Caddy stores certificates in `caddy_data`; preserve this volume across redeployments.
The configured site must open through HTTPS without a certificate warning. Access
the public hostname rather than `localhost`, because production cookies require HTTPS.

If there is no administrator yet:

```text
docker compose -f compose.yaml -f compose.production.yaml exec api python -m app.cli create-admin --email admin@example.com
```

Use the actual operator email and enter the password at the hidden prompt. There
are no default administrator credentials.

## Check the delivered application

1. On another laptop, open the public HTTPS URL and sign in.
2. Create a test applicant and check the generated invitation's hostname.
3. Send it through WhatsApp; open it on an iPhone and an Android phone.
4. Register, consent, allow the camera, record, preview, retake, and submit.
5. Check admin playback, download, review, deletion, and the retained consent record.
6. Exercise invalid/replaced links, denied camera permission, and retry after a
   network interruption. Expiration is covered in automated tests; include it in
   user acceptance testing if the client requires manual evidence.
7. Verify restart recovery and that existing client data and videos remain available.

Use test applicant data during acceptance testing. Keep gateway access logging off
and redact private invitation paths in any additional logging or analytics layer.

## Backup (maintenance window)

Backups contain applicant information, private videos, and certificate keys. The
`backups/` directory is ignored by Git, but it still needs restricted access and an
encrypted off-server copy. Keep the matching application version and `.env` securely
alongside the backup; the job does not copy `.env` automatically.

The backup job uses only containers. It exports PostgreSQL and archives the video
and certificate volumes. Stop all writers and storage first to keep them consistent:

```text
docker compose -f compose.yaml -f compose.production.yaml stop gateway web api storage
docker compose -f compose.yaml -f compose.production.yaml -f compose.ops.yaml run --build --rm --no-deps backup
docker compose -f compose.yaml -f compose.production.yaml up -d --wait
```

The database must stay running during backup. These steps temporarily take the
website offline. Resume the application even if backup fails; investigate the failure
before using any partial directory. A successful backup prints its name and creates
`backups/backup-<UTC timestamp>/` containing `database.dump`, `objects.tar.gz`,
`certificates.tar.gz`, and `SHA256SUMS`. Copy only completed backups off-server.
Optionally set `BACKUP_DIR` in `.env` to a dedicated host directory.

## Restore to an empty deployment

Restore must use an empty database and empty video/certificate volumes. The job
refuses to overwrite an existing installation. Do not delete a working installation
to test restoration. Use a separate server or a new Compose project name.

Copy the backup into the target's `backups/` directory, use its original database
name/user and storage credentials, and set `RESTORE_BACKUP=backup-<UTC timestamp>`
in the target `.env`. For a restore drill on the same host, `-p visa-selfie-restore`
below gives the target separate volumes and a separate network:

```text
docker compose -p visa-selfie-restore -f compose.yaml -f compose.production.yaml up -d db --wait
docker compose -p visa-selfie-restore -f compose.yaml -f compose.production.yaml -f compose.ops.yaml run --build --rm --no-deps restore
```

Only PostgreSQL should be running before restore; do not run migrations or storage
initialization first. The job verifies checksums before restoring. If a restore fails,
keep that target offline; it may contain partial data. Start again with a fresh target
after fixing the failure. Use only trusted backups produced by the included job.

After successful restore, start the same project:

```text
docker compose -p visa-selfie-restore -f compose.yaml -f compose.production.yaml up --build -d --wait
```

On a shared host, the original gateway must be stopped before the restored gateway
can use ports 80/443. Use a different hostname and explicit port override for a parallel
drill, or use the automated isolated check below. Database and object storage use
their existing persisted data; migrations can then apply any intended version update.

## Isolated deployment check for maintainers

This development check requires the existing Python/Playwright test environment,
not additional software on the client's runtime host:

```powershell
.\.venv\Scripts\python scripts/check_deployment.py
```

On Linux/macOS, use `.venv/bin/python`. The check creates two uniquely named stacks,
random test credentials, a temporary internal certificate authority, and a loopback-only
HTTPS port. It checks guided capture and rejection of non-face videos, including an
upload larger than 4.5 MiB. It separately seeds synthetic legacy recordings for
download/recovery checks; those fixtures do not prove liveness. It recreates
containers with persisted volumes, verifies automatic API
recovery after process termination, backs up database/video/certificate data, restores
to fresh volumes, verifies the restored video byte-for-byte, and checks that an
overwrite attempt is rejected. It removes only its own stacks and temporary files.
It does not change your host's certificate trust or request a public certificate.

For a running deployment with a public certificate, the existing browser test accepts
`SMOKE_BASE_URL` and `SMOKE_COMPOSE_ARGS` (a JSON array of Compose arguments). Leave
`SMOKE_ALLOW_SELF_SIGNED` unset; that option is exclusively for the isolated test CA.
The test uses a synthetic camera and cannot replace physical iOS/Android testing.

## Operational limits

### Optional database management UI

Adminer is an optional container, bound to the Docker host's loopback interface.
For a Windows VPS, open its URL in the browser inside your Remote Desktop session.
It is not routed through Caddy or published on the application domain.

```powershell
docker compose -f compose.yaml -f compose.production.yaml -f compose.database-ui.yaml --profile tools up -d --no-deps database-ui
```

Open `http://127.0.0.1:8081`. Choose **PostgreSQL**, server **db**, and use
`POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` from your private `.env`.
These are database credentials, separate from the Visa Selfie admin account.
The UI allows browsing, editing, and SQL queries. Direct edits bypass application
validation and audit events; use the application for normal client/video actions.
Deleting a video database row does not delete its corresponding stored video file.

Stop the UI when finished:

```powershell
docker compose -f compose.yaml -f compose.production.yaml -f compose.database-ui.yaml stop database-ui
```

For local development, omit `-f compose.production.yaml` from these commands.
The UI has no automatic restart policy; start it explicitly when needed.
Image reference: [official Adminer Docker image](https://hub.docker.com/_/adminer).

### Server operation

The supplied setup is a single-server deployment. Persistent volumes are not a backup.
An unhealthy container is reported by health checks; Docker's restart policy restarts
exited containers, not merely unhealthy ones. Host reboot and Docker Desktop startup
must be tested separately before unattended delivery. Monitor service health, free
disk space, backup completion, and certificate renewal. No host reboot is performed
by the automated deployment test.

References: [Docker Compose merge behavior](https://docs.docker.com/reference/compose-file/merge/)
and [Caddy's official image](https://hub.docker.com/_/caddy).
