#!/bin/bash

# Database backup script for MySQL via Docker container
# Uses docker exec to run mysqldump and saves timestamped backups
# Requires: MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE environment variables
# or defaults to: wakou/wakou_password/wakou

set -e

# Configuration
CONTAINER_NAME="${CONTAINER_NAME:-wakou-db}"
MYSQL_USER="${MYSQL_USER:-wakou}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-wakou_password}"
MYSQL_DATABASE="${MYSQL_DATABASE:-wakou}"
BACKUP_DIR="$(pwd)/backups"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamped filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/${MYSQL_DATABASE}_backup_${TIMESTAMP}.sql"

echo "Starting database backup..."
echo "Container: $CONTAINER_NAME"
echo "Database: $MYSQL_DATABASE"
echo "Backup file: $BACKUP_FILE"

# Execute mysqldump via docker exec
docker exec "$CONTAINER_NAME" \
  mysqldump \
  -u "$MYSQL_USER" \
  -p"$MYSQL_PASSWORD" \
  "$MYSQL_DATABASE" \
  > "$BACKUP_FILE"

# Verify the backup was created and has content
if [ -s "$BACKUP_FILE" ]; then
  FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  echo "✓ Backup completed successfully"
  echo "  File: $BACKUP_FILE"
  echo "  Size: $FILESIZE"
else
  echo "✗ Backup failed or is empty"
  rm -f "$BACKUP_FILE"
  exit 1
fi
