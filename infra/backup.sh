#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/../backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

DB_FILE="$BACKUP_DIR/studio-db-$STAMP.dump"
MEDIA_FILE="$BACKUP_DIR/studio-media-$STAMP.tar.gz"

echo "Backing up PostgreSQL database..."
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DB_FILE"

echo "Backing up original media files..."
docker compose exec -T api sh -c 'tar -czf - -C /data media' > "$MEDIA_FILE"

chmod 600 "$DB_FILE" "$MEDIA_FILE"
(
  cd "$BACKUP_DIR"
  sha256sum "$(basename "$DB_FILE")" "$(basename "$MEDIA_FILE")" > "studio-$STAMP.sha256"
  chmod 600 "studio-$STAMP.sha256"
)

echo "Backup completed:"
echo "$DB_FILE"
echo "$MEDIA_FILE"
