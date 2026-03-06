# Quickstart: Conversation Log Backup

## Setup (one-time, on NUC)

1. Deploy the backup script:
   ```bash
   ./scripts/nuc.sh deploy
   ```

2. SSH to the NUC and install the cron job:
   ```bash
   ./scripts/nuc.sh ssh
   crontab -e
   # Add this line:
   30 23 * * * /home/jabelk/family-meeting/scripts/backup-conversations.sh >> /home/jabelk/family-meeting/data/conversation_archives/backup.log 2>&1
   ```

3. Verify the archive directory was created:
   ```bash
   ls ~/family-meeting/data/conversation_archives/
   ```

## Daily Usage

### List available archives
```bash
./scripts/nuc.sh chat-logs
```

### Pull a specific day's log
```bash
./scripts/nuc.sh chat-logs 2026-03-05
```

### Pull the most recent archive
```bash
./scripts/nuc.sh chat-logs latest
```

### Pull a date range
```bash
./scripts/nuc.sh chat-logs 2026-03-01 2026-03-05
```

### Search archived conversations
After pulling locally:
```bash
cat data/conversation_archives/conversations-2026-03-05.json | python3 -m json.tool | grep -i "breakfast"
```

## Verification

Run the backup script manually to test:
```bash
./scripts/nuc.sh ssh
~/family-meeting/scripts/backup-conversations.sh
ls -la ~/family-meeting/data/conversation_archives/
```
