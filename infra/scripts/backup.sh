#!/bin/sh
# Daily backup: database dump and uploaded files, the last 7 days are kept.
# Cron on the server (as the user that runs Docker), from the repository root:
#   15 4 * * * cd /srv/blockcraft && sh infra/scripts/backup.sh >> backups/backup.log 2>&1
set -eu

# Single values from .env (sourcing it breaks on values such as «Name <mail>»)
env_value() { grep -E "^$1=" .env | head -n 1 | cut -d= -f2-; }
COMPOSE=${COMPOSE:-docker compose -f docker-compose.prod.yml}
POSTGRES_USER=${POSTGRES_USER:-$(env_value POSTGRES_USER)}
POSTGRES_DB=${POSTGRES_DB:-$(env_value POSTGRES_DB)}
STAMP=$(date +%Y-%m-%d_%H%M)
KEEP_DAYS=${BACKUP_KEEP_DAYS:-7}
mkdir -p backups

# Custom format: compressed, restorable table by table with pg_restore
$COMPOSE exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "backups/db_$STAMP.dump"
$COMPOSE run --rm --no-deps -T --entrypoint tar backend -czf - -C /app media > "backups/media_$STAMP.tar.gz"

find backups -name 'db_*.dump' -mtime +"$KEEP_DAYS" -delete
find backups -name 'media_*.tar.gz' -mtime +"$KEEP_DAYS" -delete
echo "$(date -Iseconds) backup $STAMP: $(du -h "backups/db_$STAMP.dump" | cut -f1) db, $(du -h "backups/media_$STAMP.tar.gz" | cut -f1) media"
