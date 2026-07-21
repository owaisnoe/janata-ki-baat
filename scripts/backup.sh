#!/bin/sh
# Nightly backup (plan §8): DB dump + proof photos tarball.
# cPanel cron:  15 3 * * *  cd ~/janata-ki-baat && sh scripts/backup.sh
# Pull the backups/ folder off-server weekly — shared-host backups are
# not a promise.
set -e
STAMP=$(date +%Y%m%d)
mkdir -p backups

if [ -n "$DB_NAME" ]; then
  mysqldump --single-transaction "$DB_NAME" | gzip > "backups/db-$STAMP.sql.gz"
else
  # SQLite dev fallback
  [ -f instance/jkb.db ] && cp instance/jkb.db "backups/db-$STAMP.sqlite"
fi

tar -czf "backups/proofs-$STAMP.tar.gz" uploads/ 2>/dev/null || true

# keep 14 days
find backups -type f -mtime +14 -delete
echo "backup done: $STAMP"
