#!/bin/sh
set -eu
case "${RESTORE_BACKUP:-}" in
  backup-*) ;;
  *) echo 'Set RESTORE_BACKUP to the backup directory name.' >&2; exit 1 ;;
esac
case "$RESTORE_BACKUP" in
  *[!a-zA-Z0-9_-]*) echo 'Invalid backup directory name.' >&2; exit 1 ;;
esac
cd "/backups/$RESTORE_BACKUP"
sha256sum -c SHA256SUMS
tables=$(psql -X -A -t -v ON_ERROR_STOP=1 -c "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')")
if [ "$tables" != '0' ]; then
  echo 'Restore refused: target database is not empty. Use a fresh deployment.' >&2
  exit 1
fi
if [ -n "$(find /objects /certificates -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  echo 'Restore refused: target data volumes are not empty. Use a fresh deployment.' >&2
  exit 1
fi
# Only restore trusted archives created by backup.sh. Services must remain stopped.
pg_restore --exit-on-error --no-owner --no-acl --dbname="$PGDATABASE" database.dump
tar -xzf objects.tar.gz -C /objects
tar -xzf certificates.tar.gz -C /certificates
echo 'Restore complete. Start the production stack with the original storage credentials.'
