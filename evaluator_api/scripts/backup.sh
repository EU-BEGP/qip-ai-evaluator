#!/bin/bash
# Nightly Postgres backup for evaluator_api.
#
# Dumps the DB from the running `db` container, gzips it, and keeps the newest
# $KEEP dumps. Run from the evaluator_api/ directory (where docker-compose.yml is).
#
#   ./scripts/backup.sh
#
# Cron (nightly at 02:30), edit the path then `crontab -e`:
#   30 2 * * * cd /path/to/evaluator_api && ./scripts/backup.sh >> backups/backup.log 2>&1
#
# Restore a dump into the running db:
#   gunzip -c backups/db-YYYY-MM-DD_HHMM.sql.gz | \
#     docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
set -euo pipefail

# --- config (override via env if needed) ---
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP="${KEEP:-7}"          # how many dumps to retain
SERVICE="${SERVICE:-db}"    # compose service name of Postgres

# --- load DB credentials from .env ---
set -a; [ -f .env ] && . ./.env; set +a
: "${POSTGRES_USER:?POSTGRES_USER not set (check .env)}"
: "${POSTGRES_DB:?POSTGRES_DB not set (check .env)}"

mkdir -p "$BACKUP_DIR"
OUT="$BACKUP_DIR/db-$(date +%F_%H%M).sql.gz"

echo "--> Dumping '$POSTGRES_DB' ..."
docker compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$SERVICE" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$OUT"
echo "--> Wrote $OUT ($(du -h "$OUT" | cut -f1))"

# --- rotate: keep newest $KEEP ---
ls -1t "$BACKUP_DIR"/db-*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
echo "--> Retained newest $KEEP dump(s) in $BACKUP_DIR"
