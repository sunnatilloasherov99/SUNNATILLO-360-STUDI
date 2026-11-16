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

docker compose up -d db api
echo "Pausing API writes for a consistent database/media backup..."
docker compose stop api
restart_api() { docker compose start api >/dev/null 2>&1 || true; }
trap restart_api EXIT

echo "Backing up PostgreSQL database..."
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DB_FILE"

echo "Backing up original media files..."
docker compose run --rm --no-deps --entrypoint sh api -c 'tar -czf - -C /data media' > "$MEDIA_FILE"

chmod 600 "$DB_FILE" "$MEDIA_FILE"
(
  cd "$BACKUP_DIR"
  sha256sum "$(basename "$DB_FILE")" "$(basename "$MEDIA_FILE")" > "studio-$STAMP.sha256"
  chmod 600 "studio-$STAMP.sha256"
)

docker compose start api
trap - EXIT
echo "Backup completed:"
echo "$DB_FILE"
echo "$MEDIA_FILE"
