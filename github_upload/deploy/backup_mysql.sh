#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/sput}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sput}"
ENV_FILE="$APP_DIR/.env"

set -a
source "$ENV_FILE"
set +a

mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
DB_BACKUP="$BACKUP_DIR/${DB_NAME}-${STAMP}.sql.gz"
DOCX_BACKUP="$BACKUP_DIR/docx_ordenes-${STAMP}.tar.gz"

mysqldump \
  --host="${DB_HOST:-127.0.0.1}" \
  --port="${DB_PORT:-3306}" \
  --user="$DB_USER" \
  --password="$DB_PASSWORD" \
  "$DB_NAME" | gzip > "$DB_BACKUP"

tar -czf "$DOCX_BACKUP" -C "$APP_DIR" docx_ordenes

find "$BACKUP_DIR" -type f -mtime +14 -delete

echo "Backups creados:"
echo "$DB_BACKUP"
echo "$DOCX_BACKUP"
