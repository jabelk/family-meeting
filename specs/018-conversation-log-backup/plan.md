# Implementation Plan: Conversation Log Backup

**Branch**: `018-conversation-log-backup` | **Date**: 2026-03-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/018-conversation-log-backup/spec.md`

## Summary

Add automated daily backup of `data/conversations.json` on the NUC to preserve historical chat context for debugging. A shell script runs via cron, copies the file with a date stamp, prunes archives older than 30 days, and a new `nuc.sh` subcommand retrieves archives to the developer's local machine.

## Technical Context

**Language/Version**: Bash (shell script on NUC) — no Python changes needed
**Primary Dependencies**: cron (already on NUC Ubuntu 24.04), scp/ssh (already configured)
**Storage**: Flat JSON files in `data/conversation_archives/` on NUC (same Docker volume mount)
**Testing**: Manual verification — copy script, check archive exists, check pruning
**Target Platform**: Ubuntu 24.04 (NUC) + macOS (developer laptop)
**Project Type**: DevOps/infrastructure script
**Performance Goals**: N/A — runs once daily, copies a single file
**Constraints**: Archive storage < 500 MB over 30 days (conversations.json is ~200KB, so ~6 MB total)
**Scale/Scope**: 1 file backed up daily, 30-day retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | Uses existing cron infrastructure on NUC, no new services |
| II. Mobile-First Access | N/A | Developer-only tool, not user-facing |
| III. Simplicity & Low Friction | PASS | Zero end-user impact; developer uses existing `nuc.sh` pattern |
| IV. Structured Output | N/A | Not meeting-related output |
| V. Incremental Value | PASS | Standalone — works without any other feature |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/018-conversation-log-backup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── quickstart.md        # Phase 1 output
```

### Source Code (repository root)

```text
scripts/
├── nuc.sh                      # Modified — add `chat-logs` subcommand
└── backup-conversations.sh     # New — backup + prune script (runs on NUC via cron)
```

**Structure Decision**: No new Python code, no contracts directory. This is purely a DevOps script addition to the existing `scripts/` directory, plus a cron job on the NUC.

## Implementation Approach

### Backup Script (`scripts/backup-conversations.sh`)

Runs on the NUC via cron. Does three things:
1. Copies `data/conversations.json` → `data/conversation_archives/conversations-YYYY-MM-DD.json`
2. Deletes archives older than 30 days
3. Logs success/failure to stdout (cron captures in syslog)

The script operates on host-level paths (`~/family-meeting/data/`) — not inside Docker — since the `data/` directory is a bind mount visible from both the container and the host.

### Retrieval via `nuc.sh`

Add a `chat-logs` subcommand to `scripts/nuc.sh`:
- `./scripts/nuc.sh chat-logs` — list available archive dates
- `./scripts/nuc.sh chat-logs <date>` — pull a specific day's archive to local `data/conversation_archives/`
- `./scripts/nuc.sh chat-logs latest` — pull the most recent archive
- `./scripts/nuc.sh chat-logs <start> <end>` — pull a date range

### Scheduling

Use the NUC's system cron (not n8n) since this is a simple file copy with no API calls or webhooks. Cron entry:

```
30 23 * * * /home/jabelk/family-meeting/scripts/backup-conversations.sh >> /home/jabelk/family-meeting/data/conversation_archives/backup.log 2>&1
```

Runs at 11:30 PM Pacific daily — after the day's conversations are done but before midnight.
