#!/usr/bin/env bash
# Backup conversations.json to a dated archive file and prune old archives.
# Runs on the NUC via cron at 11:30 PM Pacific daily.
# Usage: ~/family-meeting/scripts/backup-conversations.sh

set -euo pipefail

BASE_DIR="$HOME/family-meeting"
DATA_DIR="$BASE_DIR/data"
ARCHIVE_DIR="$DATA_DIR/conversation_archives"
SOURCE="$DATA_DIR/conversations.json"
RETENTION_DAYS=30

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DEST="$ARCHIVE_DIR/conversations-${DATE}.json"

# Ensure archive directory exists
mkdir -p "$ARCHIVE_DIR"

# Check source file exists
if [ ! -f "$SOURCE" ]; then
    echo "[$TIMESTAMP] WARNING: $SOURCE not found — skipping backup"
    exit 0
fi

# Copy with date stamp
cp "$SOURCE" "$DEST"
SIZE=$(stat -c%s "$DEST" 2>/dev/null || stat -f%z "$DEST")
echo "[$TIMESTAMP] OK: Archived conversations ($SIZE bytes) → $DEST"

# Prune archives older than retention period
PRUNED=$(find "$ARCHIVE_DIR" -name 'conversations-*.json' -mtime +$RETENTION_DAYS -print -delete | wc -l)
if [ "$PRUNED" -gt 0 ]; then
    echo "[$TIMESTAMP] PRUNED: Deleted $PRUNED archives older than $RETENTION_DAYS days"
fi
