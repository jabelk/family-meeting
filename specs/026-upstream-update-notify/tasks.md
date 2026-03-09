# Tasks: Upstream Update Notification & Rollback

**Input**: Design documents from `/specs/026-upstream-update-notify/`
**Prerequisites**: spec.md (no plan.md needed — feature extends existing scheduler + WhatsApp patterns)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new dependencies needed — uses git (subprocess), existing APScheduler, existing WhatsApp messaging. No setup tasks.

*(No tasks)*

---

## Phase 2: Foundational

**Purpose**: Create the update state management module and admin config — needed by all user stories.

- [x] T001 Add `ADMIN_PHONE` config var to src/config.py. Default to `ERIN_PHONE` if not set (`os.environ.get("ADMIN_PHONE", "") or ERIN_PHONE`). Add `UPSTREAM_REMOTE` config var (default `"upstream"`). Add to `OPTIONAL_GROUPS` under an "Updates" group with both vars. This identifies who can trigger update/rollback commands and which git remote to check.
- [x] T002 Create src/tools/updater.py with the update state persistence layer. Use the atomic JSON file pattern (same as drive_times.py, routines.py). State file: `data/update_state.json`. Schema: `{"deployed_sha": str, "last_checked_sha": str, "last_notified_sha": str, "last_update_time": str|null, "pre_update_sha": str|null, "pre_update_backup_path": str|null, "skipped_sha": str|null}`. Functions: `_load_state() -> dict`, `_save_state(state: dict)`, `get_update_state() -> dict`. Initialize with empty/null defaults if file doesn't exist. Use `_DATA_DIR` pattern from scheduler.py (`Path("/app/data")` if exists, else `Path("data")`).

**Checkpoint**: Update state infrastructure ready for all user stories.

---

## Phase 3: User Story 1 — Update Available Notification (Priority: P1) MVP

**Goal**: Scheduled check detects upstream updates and sends a WhatsApp notification with a human-readable changelog summary.

**Independent Test**: Configure an upstream remote with newer commits. Trigger the update check. Receive a WhatsApp notification describing changes.

### Implementation for User Story 1

- [x] T003 [US1] Add `check_for_updates() -> dict` function to src/tools/updater.py. Steps: (1) Run `git fetch {UPSTREAM_REMOTE}` via subprocess. (2) Get local HEAD sha via `git rev-parse HEAD`. (3) Get upstream HEAD sha via `git rev-parse {UPSTREAM_REMOTE}/main`. (4) If SHAs match, return `{"update_available": False}`. (5) Load state; if `last_notified_sha == upstream_sha` or `skipped_sha == upstream_sha`, return `{"update_available": False, "already_notified": True}`. (6) Get commit log between local and upstream: `git log HEAD..{UPSTREAM_REMOTE}/main --oneline --no-merges`. (7) Return `{"update_available": True, "local_sha": local_sha, "upstream_sha": upstream_sha, "commit_count": N, "raw_log": log_text}`. Wrap all git subprocess calls in try/except and return `{"update_available": False, "error": str}` on failure.
- [x] T004 [US1] Add `generate_changelog_summary(raw_log: str, commit_count: int) -> str` function to src/tools/updater.py. Use Claude Haiku 4.5 (via the anthropic SDK, same pattern as amazon_classification in src/tools/amazon_sync.py) to summarize the raw git log into 2-4 bullet points of user-facing changes. Prompt: "Summarize these git commits into 2-4 plain-language bullet points describing what changed for a non-technical user. Focus on new features, bug fixes, and improvements. Ignore refactoring or CI changes. Commits:\n{raw_log}". Return the summary string.
- [x] T005 [US1] Add `async notify_update_available(upstream_sha: str, summary: str, commit_count: int)` function to src/tools/updater.py. Compose WhatsApp message: "🔄 *Update Available*\n\n{commit_count} improvement(s) since your last update:\n\n{summary}\n\nReply *update* to apply, or *skip* to ignore this update." Send via `send_message(ADMIN_PHONE, message)`. Update state: set `last_notified_sha = upstream_sha`. Save state.
- [x] T006 [US1] Add `_run_update_check()` async handler to src/scheduler.py. Import `check_for_updates`, `generate_changelog_summary`, `notify_update_available` from src/tools/updater.py. Call `check_for_updates()`; if `update_available` is True, call `generate_changelog_summary()` then `await notify_update_available()`. Add `"updates/check": _run_update_check` to `ENDPOINT_HANDLERS` dict.
- [x] T007 [P] [US1] Add update check job to data/schedules.json: `{"id": "update_check", "endpoint": "updates/check", "schedule": {"hour": 6, "minute": 0}, "enabled": true}`. Runs daily at 6 AM before the daily briefing.
- [ ] T008 [US1] Verify US1 works: set up a test upstream remote (`git remote add test-upstream <url>` or use a local bare repo with commits ahead). Trigger the update check handler manually or wait for schedule. Confirm: (1) git fetch succeeds, (2) commit diff detected, (3) WhatsApp notification received with human-readable summary, (4) re-running the check does NOT send a duplicate notification.

**Checkpoint**: Families are notified when updates are available. MVP complete.

---

## Phase 4: User Story 2 — Apply Update via WhatsApp (Priority: P2)

**Goal**: Admin replies "update" to apply upstream changes — system backs up data, pulls code, redeploys, confirms success.

**Depends on**: US1 (need update notification and state tracking in place)

**Independent Test**: With an update available, reply "update" in WhatsApp. Confirm data is backed up, code is pulled, redeployed, and success is confirmed.

### Implementation for User Story 2

- [x] T009 [US2] Add `backup_data() -> str` function to src/tools/updater.py. Create a timestamped copy of the data directory: `data/backups/pre-update-{YYYYMMDD-HHMMSS}/`. Use `shutil.copytree()` to copy the data dir, excluding the `backups/` subdirectory itself and any `__pycache__`. Return the backup path. Keep only the 3 most recent backups (delete older ones). Log the backup path and size.
- [x] T010 [US2] Add `async apply_update() -> dict` function to src/tools/updater.py. Steps: (1) Call `check_for_updates()`; if no update available, return `{"success": False, "reason": "already_up_to_date"}`. (2) Call `backup_data()` to create data backup. (3) Run `git merge {UPSTREAM_REMOTE}/main --no-edit` via subprocess. (4) If merge fails (non-zero exit), run `git merge --abort`, return `{"success": False, "reason": "merge_conflict", "backup_path": path}`. (5) If merge succeeds, update state: `pre_update_sha = old_local_sha`, `deployed_sha = new_sha`, `last_update_time = now`, `pre_update_backup_path = backup_path`, `skipped_sha = null`. (6) Trigger redeploy via `railway up --detach --service fastapi` subprocess (or return instructions if Railway CLI not available). (7) Return `{"success": True, "old_sha": old, "new_sha": new, "backup_path": path}`.
- [x] T011 [US2] Add `async handle_update_command(sender_phone: str)` function to src/tools/updater.py. Check `sender_phone == ADMIN_PHONE`; if not, return "Only the admin can apply updates." Call `await apply_update()`. On success, send confirmation via WhatsApp: "✅ *Update Applied*\n\nUpdated from {old_sha[:7]} to {new_sha[:7]}. Data backed up. The app will restart shortly.\n\nReply *undo update* within 7 days to rollback." On failure, send appropriate error message (merge conflict, already up to date, etc.).
- [x] T012 [US2] Add `async handle_skip_command(sender_phone: str)` function to src/tools/updater.py. Check admin. Load state, set `skipped_sha = last_notified_sha`, save. Reply "Got it — I'll skip this update. I'll notify you when the next one is available."
- [x] T013 [US2] Integrate update commands into the message handling pipeline. In src/app.py (or src/assistant.py), add a pre-processing check before the Claude tool loop: if the message text (lowercased, stripped) is exactly `"update"`, call `await handle_update_command(sender_phone)` and return early (don't pass to Claude). If exactly `"skip"`, call `await handle_skip_command(sender_phone)` and return early. This avoids Claude interpreting these as general conversation.
- [ ] T014 [US2] Verify US2 works: with an update available, reply "update" in WhatsApp. Confirm: (1) data backup created in data/backups/, (2) git merge succeeds, (3) confirmation message received, (4) replying "update" again says "already up to date". Test "skip" command: trigger new notification, reply "skip", confirm no re-notification.

**Checkpoint**: Admin can apply updates with one message.

---

## Phase 5: User Story 3 — Rollback After Update (Priority: P3)

**Goal**: Admin replies "undo update" to revert to pre-update version and restore data backup.

**Depends on**: US2 (need update application and backup infrastructure)

**Independent Test**: Apply an update, then reply "undo update". Confirm code reverts and data backup is restored.

### Implementation for User Story 3

- [x] T015 [US3] Add `async rollback_update() -> dict` function to src/tools/updater.py. Steps: (1) Load state; check `pre_update_sha` exists and `last_update_time` is within 7 days. If not, return `{"success": False, "reason": "no_recent_update"}` or `{"success": False, "reason": "grace_period_expired"}`. (2) Run `git reset --hard {pre_update_sha}` via subprocess. (3) If `pre_update_backup_path` exists, restore data from backup using `shutil.copytree()` (clear current data dir first, excluding backups/). (4) Update state: clear `pre_update_sha`, `pre_update_backup_path`, `last_update_time`. Set `deployed_sha` to the reverted SHA. (5) Trigger redeploy. (6) Return `{"success": True, "reverted_to": pre_update_sha}`.
- [x] T016 [US3] Add `async handle_undo_command(sender_phone: str)` function to src/tools/updater.py. Check admin. Call `await rollback_update()`. On success, send: "⏪ *Update Rolled Back*\n\nReverted to previous version ({sha[:7]}). Data restored from backup. The app will restart shortly." On failure, send appropriate message (no recent update, grace period expired).
- [x] T017 [US3] Add "undo update" to the pre-processing check in src/app.py (from T013). If message text (lowercased, stripped) is `"undo update"`, call `await handle_undo_command(sender_phone)` and return early.
- [ ] T018 [US3] Verify US3 works: apply an update (T014), then reply "undo update". Confirm: (1) code reverted to pre-update SHA, (2) data restored from backup, (3) confirmation message received. Test edge cases: "undo update" with no recent update, "undo update" after 7+ days.

**Checkpoint**: Full update lifecycle — notify, apply, rollback.

---

## Phase 6: Polish & Validation

**Purpose**: Final checks and deployment.

- [x] T019 Run `ruff check src/` and `ruff format --check src/` — fix any issues in new/modified files.
- [x] T020 Run `pytest tests/` — verify all existing tests still pass.
- [ ] T021 Commit all changes, push to branch, create PR for merge to main.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: N/A
- **Foundational (Phase 2)**: T001-T002 — Config vars + state persistence. Blocks all user stories.
- **US1 (Phase 3)**: T003-T008 — Depends on Phase 2. Core update checking + notification.
- **US2 (Phase 4)**: T009-T014 — Depends on US1 (needs state tracking). Backup + apply + commands.
- **US3 (Phase 5)**: T015-T018 — Depends on US2 (needs backup + apply infrastructure). Rollback.
- **Polish (Phase 6)**: T019-T021 — After all user stories.

### User Story Dependencies

- **US1 (P1)**: Independent — MVP. Scheduled check + notification.
- **US2 (P2)**: Depends on US1 (state tracking, admin config). Adds apply + skip commands.
- **US3 (P3)**: Depends on US2 (backup infrastructure, pre_update_sha tracking). Adds rollback.

### Parallel Opportunities

- T007 (schedules.json) can run in parallel with T003-T006 (different file)
- T001 (config.py) and T002 (updater.py) can run in parallel (different files)

---

## Implementation Strategy

### MVP First (US1 Only)

1. T001-T002 — Config vars + update state module
2. T003-T006 — Update checking, changelog summary, notification, scheduler handler
3. T007 — Add scheduled job
4. T008 — Verify end-to-end
5. **STOP and VALIDATE**: Families receive update notifications
6. Deploy — non-technical families know when updates exist

### Incremental Delivery

1. T001-T008 → US1 complete → Update notifications work
2. T009-T014 → US2 complete → Can apply updates via "update" reply
3. T015-T018 → US3 complete → Can rollback via "undo update"
4. T019-T021 → Polish → CI passes, PR created

---

## Notes

- Total: 21 tasks
- New files: src/tools/updater.py (core logic), data/update_state.json (auto-created)
- Modified files: src/config.py (2 vars), src/scheduler.py (1 handler + endpoint), src/app.py (command pre-processing), data/schedules.json (1 job)
- No new Python dependencies — uses subprocess for git, shutil for backups, existing anthropic SDK for changelog summary
- Claude Haiku 4.5 generates human-readable changelog from raw git log (same pattern as Amazon classification)
- Admin phone restriction prevents non-admin family members from triggering updates
- Data backup uses shutil.copytree with 3-backup retention
- Railway CLI (`railway up`) assumed available in the deployment environment for redeploy
- The "update", "skip", and "undo update" commands are intercepted before Claude to avoid misinterpretation
