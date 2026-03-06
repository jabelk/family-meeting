# Tasks: Conversation Log Backup

**Input**: Design documents from `/specs/018-conversation-log-backup/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not requested — no test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create archive directory and ensure infrastructure is ready

- [x] T001 Create archive directory `data/conversation_archives/` on NUC via SSH and verify `data/` bind mount is accessible from host

---

## Phase 2: User Story 1 - Daily Conversation Archival (Priority: P1) MVP

**Goal**: Automatically archive conversations.json daily so historical context is preserved for debugging

**Independent Test**: Run the backup script manually on the NUC, verify a timestamped archive file is created in `data/conversation_archives/`, then confirm the live `data/conversations.json` is unmodified

### Implementation for User Story 1

- [x] T002 [US1] Create backup script at `scripts/backup-conversations.sh` that: (1) copies `~/family-meeting/data/conversations.json` to `~/family-meeting/data/conversation_archives/conversations-YYYY-MM-DD.json` using `cp` with date-stamped filename, (2) logs timestamp + file size + status to stdout, (3) uses strict mode (`set -euo pipefail`), (4) creates archive directory if it doesn't exist, (5) skips with warning if conversations.json doesn't exist
- [x] T003 [US1] Deploy backup script to NUC (`./scripts/nuc.sh deploy`) and run it manually via SSH to verify it creates an archive file correctly
- [x] T004 [US1] Install cron job on NUC: `30 23 * * * /home/jabelk/family-meeting/scripts/backup-conversations.sh >> /home/jabelk/family-meeting/data/conversation_archives/backup.log 2>&1` — verify with `crontab -l`

**Checkpoint**: Backup script runs daily at 11:30 PM Pacific, creating dated archive files. Verify next morning that archive was created.

---

## Phase 3: User Story 2 - Archive Retention and Cleanup (Priority: P2)

**Goal**: Automatically delete archives older than 30 days to prevent unbounded disk growth

**Independent Test**: Create fake archive files with dates >30 days old, run the cleanup, verify only old files are deleted and recent ones are preserved

### Implementation for User Story 2

- [x] T005 [US2] Add retention pruning to `scripts/backup-conversations.sh`: after the copy step, use `find` to delete `conversations-*.json` files in the archive directory older than 30 days, log count of pruned files to stdout

**Checkpoint**: Backup script now copies + prunes in a single run. Old archives are automatically cleaned up.

---

## Phase 4: User Story 3 - On-Demand Log Retrieval (Priority: P3)

**Goal**: Developer can pull archived logs from NUC to local machine via `nuc.sh` subcommand

**Independent Test**: Run `./scripts/nuc.sh chat-logs` to list archives, then `./scripts/nuc.sh chat-logs <date>` to pull a specific one and verify it appears locally in `data/conversation_archives/`

### Implementation for User Story 3

- [x] T006 [US3] Add `chat-logs` subcommand to `scripts/nuc.sh` with these modes: (1) no args — SSH to NUC and `ls -la` the archive directory to show available dates, (2) `latest` — scp the most recent archive file to local `data/conversation_archives/`, (3) `<date>` — scp a specific `conversations-YYYY-MM-DD.json` to local `data/conversation_archives/`, (4) `<start> <end>` — scp all archives in that date range. Create local `data/conversation_archives/` directory if it doesn't exist.
- [x] T007 [US3] Update the help text in `scripts/nuc.sh` `help|*` case to include the `chat-logs` subcommand with usage examples

**Checkpoint**: Developer can list and retrieve archived conversations from the NUC with a single command.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation

- [x] T008 Run quickstart.md validation: follow all steps in `specs/018-conversation-log-backup/quickstart.md` end-to-end and verify each command works
- [x] T009 Update `CLAUDE.md` Deployment section to mention conversation log backup cron job and `chat-logs` subcommand

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup (T001)
- **User Story 2 (Phase 3)**: Depends on US1 completion (modifies same file T002 created)
- **User Story 3 (Phase 4)**: Can start after Setup — independent of US1/US2 (different file: `nuc.sh`)
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: T001 → T002 → T003 → T004 (sequential — create, deploy, cron)
- **User Story 2 (P2)**: T005 depends on T002 (modifies backup script)
- **User Story 3 (P3)**: T006, T007 are independent of US1/US2 — can be implemented in parallel

### Parallel Opportunities

- T006 and T007 (US3) can run in parallel with T002-T005 (US1/US2) since they modify different files (`nuc.sh` vs `backup-conversations.sh`)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001: Setup archive directory
2. Complete T002-T004: Backup script + cron
3. **STOP and VALIDATE**: Check next morning that archive was created
4. Deploy if ready — backups are running

### Incremental Delivery

1. T001 → T002-T004 → Daily backups working (MVP)
2. T005 → Retention pruning added (prevents disk growth)
3. T006-T007 → Developer retrieval convenience (quality of life)
4. T008-T009 → Documentation and validation

---

## Notes

- All tasks modify files in `scripts/` — no Python code changes
- The backup script runs on the NUC host (not inside Docker) since `data/` is a bind mount
- Cron job installation (T004) is manual — requires SSH to NUC
- Total: 9 tasks across 5 phases
