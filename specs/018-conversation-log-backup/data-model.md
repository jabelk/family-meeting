# Data Model: Conversation Log Backup

## Entities

### Conversation Archive

A dated snapshot of the live conversation log file.

| Attribute | Description |
|-----------|-------------|
| Date | The calendar date of the snapshot (YYYY-MM-DD), derived from filename |
| Content | Full copy of conversations.json at time of backup |
| File path | `data/conversation_archives/conversations-YYYY-MM-DD.json` |

**Identity**: Each archive is uniquely identified by its date. One archive per day maximum — if the backup runs twice on the same day, the second overwrites the first.

**Lifecycle**:
1. Created: Daily at 11:30 PM Pacific by cron
2. Available: Immediately after creation, readable via `nuc.sh chat-logs`
3. Pruned: Automatically deleted when older than 30 days

### Backup Log

Append-only text log of backup operations.

| Attribute | Description |
|-----------|-------------|
| Timestamp | When the backup ran |
| Status | Success or failure |
| Details | File size, pruned count, any errors |
| File path | `data/conversation_archives/backup.log` |

## Relationships

- One Conversation Archive per calendar day (1:1 with date)
- Backup Log records all archive create/prune operations (1:many)

## Storage Layout

```
data/
├── conversations.json                           # Live file (unchanged)
└── conversation_archives/
    ├── conversations-2026-03-05.json            # Daily snapshots
    ├── conversations-2026-03-04.json
    ├── conversations-2026-03-03.json
    ├── ...
    └── backup.log                               # Operation log
```
