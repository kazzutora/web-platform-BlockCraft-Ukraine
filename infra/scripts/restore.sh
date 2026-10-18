#!/bin/sh
# Restore a backup made by backup.sh into this stack (an empty server or after a failure):
#   sh infra/scripts/restore.sh backups/db_2026-10-18_0415.dump backups/media_2026-10-18_0415.tar.gz
# The database is replaced: everything written since the dump is lost.
set -eu

DUMP=${1:?usage: restore.sh <db_*.dump> [media_*.tar.gz]}
MEDIA=${2:-}
# Single values from .env (sourcing it breaks on values such as «Name <mail>»)
env_value() { grep -E "^$1=" .env | head -n 1 | cut -d= -f2-; }
COMPOSE=${COMPOSE:-docker compose -f docker-compose.prod.yml}
POSTGRES_USER=${POSTGRES_USER:-$(env_value POSTGRES_USER)}
POSTGRES_DB=${POSTGRES_DB:-$(env_value POSTGRES_DB)}

$COMPOSE up -d db
$COMPOSE stop backend worker beat 2>/dev/null || true
until $COMPOSE exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do sleep 1; done

$COMPOSE exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner < "$DUMP"
if [ -n "$MEDIA" ]; then
  $COMPOSE run --rm --no-deps -T --entrypoint tar backend -xzf - -C /app < "$MEDIA"
fi

$COMPOSE up -d
# The search index is rebuilt from the restored database
$COMPOSE exec -T backend python manage.py reindex_search
echo "Restored from $DUMP"
