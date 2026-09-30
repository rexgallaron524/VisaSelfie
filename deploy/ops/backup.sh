#!/bin/sh
set -eu
umask 077
# Stop gateway/web/api/storage before running: database and video snapshot must agree.
dest="/backups/backup-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$dest"
pg_dump --format=custom --no-owner --no-acl --file="$dest/database.dump"
tar -czf "$dest/objects.tar.gz" -C /objects .
tar -czf "$dest/certificates.tar.gz" -C /certificates .
cd "$dest"
sha256sum database.dump objects.tar.gz certificates.tar.gz > SHA256SUMS
printf 'Backup complete: %s\n' "${dest##*/}"
