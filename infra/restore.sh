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

echo "WARNING: this replaces the current database and media files."
read -r -p 'Type RESTORE to continue: ' CONFIRM
[[ "$CONFIRM" == "RESTORE" ]] || { echo "Restore cancelled."; exit 1; }

docker compose up -d db api

echo "Restoring media files..."
docker compose exec -T api sh -c 'rm -rf /data/media && mkdir -p /data/media && tar -xzf - -C /data' < "$MEDIA_FILE"

echo "Stopping API while restoring database..."
docker compose stop api
restart_api() { docker compose start api >/dev/null 2>&1 || true; }
trap restart_api EXIT

echo "Restoring PostgreSQL database..."
docker compose exec -T db sh -c 'pg_restore --clean --if-exists --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$DB_FILE"

docker compose start api
trap - EXIT
echo "Restore completed."
