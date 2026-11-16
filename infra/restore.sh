#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: ./restore.sh <database.dump> <media.tar.gz>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
DB_FILE="$(realpath "$1")"
MEDIA_FILE="$(realpath "$2")"

[[ -f "$DB_FILE" && -f "$MEDIA_FILE" ]] || { echo "Backup file not found." >&2; exit 2; }
DB_NAME="$(basename "$DB_FILE")"
if [[ "$DB_NAME" =~ ^studio-db-(.+)\.dump$ ]]; then
  STAMP="${BASH_REMATCH[1]}"
  CHECKSUM_FILE="$(dirname "$DB_FILE")/studio-$STAMP.sha256"
  [[ -f "$CHECKSUM_FILE" ]] || { echo "Matching SHA-256 file not found: $CHECKSUM_FILE" >&2; exit 2; }
  (cd "$(dirname "$CHECKSUM_FILE")" && sha256sum -c "$(basename "$CHECKSUM_FILE")")
else
  echo "Unexpected database backup filename." >&2
  exit 2
fi
[[ "$(basename "$MEDIA_FILE")" == "studio-media-$STAMP.tar.gz" ]] || { echo "Database and media backup timestamps do not match." >&2; exit 2; }

echo "WARNING: this replaces the current database and media files."
read -r -p 'Type RESTORE to continue: ' CONFIRM
[[ "$CONFIRM" == "RESTORE" ]] || { echo "Restore cancelled."; exit 1; }

docker compose up -d db api
echo "Stopping API while restoring database and media..."
docker compose stop api
restart_api() { docker compose start api >/dev/null 2>&1 || true; }
trap restart_api EXIT

echo "Restoring original media files..."
docker compose run --rm --no-deps --entrypoint sh api -c 'rm -rf /data/media && mkdir -p /data/media && tar -xzf - -C /data' < "$MEDIA_FILE"

echo "Restoring PostgreSQL database..."
docker compose exec -T db sh -c 'pg_restore --clean --if-exists --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$DB_FILE"

docker compose start api
trap - EXIT
echo "Restore completed."
