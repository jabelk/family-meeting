# Feature Specification: Upstream Update Notification & Rollback

**Feature Branch**: `026-upstream-update-notify`
**Created**: 2026-03-09
**Status**: Draft
**Input**: GitHub issue #30 — Upstream update notification & rollback via WhatsApp

## User Scenarios & Testing

### User Story 1 - Update Available Notification (Priority: P1)

A family running their own MomBot instance receives a WhatsApp message when new updates are available upstream. The notification describes what changed in plain language and tells them how to apply it. The check runs automatically on a schedule so the family doesn't need to monitor GitHub.

**Why this priority**: Without notifications, families have no way to know updates exist. This is the core value — awareness that improvements are available.

**Independent Test**: Configure an upstream remote pointing to a repo with newer commits. Wait for the scheduled check (or trigger manually). Receive a WhatsApp message describing the available update with a human-readable summary of changes.

**Acceptance Scenarios**:

1. **Given** the upstream remote has commits ahead of the local deployment, **When** the scheduled update check runs, **Then** the bot sends a WhatsApp message to the admin listing what changed and how to apply the update.
2. **Given** the upstream remote has no new commits, **When** the scheduled update check runs, **Then** no notification is sent (silent pass).
3. **Given** the upstream remote is unreachable (network error), **When** the scheduled update check runs, **Then** the failure is logged but no notification is sent to the user.
4. **Given** an update notification was already sent for the current upstream HEAD, **When** the scheduled check runs again, **Then** no duplicate notification is sent.

---

### User Story 2 - Apply Update via WhatsApp (Priority: P2)

After receiving an update notification, the admin replies "update" to apply it. The system backs up data, pulls the latest code, redeploys, and confirms success — all without the admin needing SSH access or technical knowledge.

**Why this priority**: Knowing about updates is only useful if applying them is easy. One-message updates make the system maintainable by non-technical family members.

**Independent Test**: Trigger an update notification, reply "update", and confirm the system pulls new code, redeploys, and sends a success confirmation.

**Acceptance Scenarios**:

1. **Given** an update is available and the admin replies "update", **When** the system processes the command, **Then** it backs up persistent data, pulls upstream changes, triggers a redeploy, and confirms success via WhatsApp.
2. **Given** the admin replies "update" but no update is available, **When** the system processes the command, **Then** it responds that the system is already up to date.
3. **Given** the upstream merge has conflicts, **When** the system attempts to apply the update, **Then** it aborts the merge, restores the previous state, and notifies the admin that manual intervention is needed.
4. **Given** the admin replies "skip", **When** the system processes the command, **Then** it acknowledges and suppresses re-notification for that specific update.

---

### User Story 3 - Rollback After Update (Priority: P3)

If an update causes problems, the admin replies "undo update" within a grace period. The system restores the pre-update code and data backup, redeploys, and confirms the rollback.

**Why this priority**: Safety net — families need confidence that updates won't break their bot permanently. Without rollback, they may hesitate to apply updates.

**Independent Test**: Apply an update, then reply "undo update". Confirm the system reverts to the previous version and data is restored.

**Acceptance Scenarios**:

1. **Given** an update was recently applied and the admin replies "undo update", **When** the system processes the command, **Then** it reverts the code to the pre-update version, restores the data backup, redeploys, and confirms success.
2. **Given** no update was recently applied, **When** the admin replies "undo update", **Then** the system responds that there is no recent update to undo.
3. **Given** the rollback grace period has expired (more than 7 days since the update), **When** the admin replies "undo update", **Then** the system informs the admin that the rollback window has passed and suggests manual steps.

---

### Edge Cases

- **Multiple updates queued**: If several upstream releases accumulate between checks, the notification should summarize all changes since the last applied version, not send separate notifications for each commit.
- **Breaking changes requiring env var updates**: If the upstream changelog indicates new required environment variables, the notification should warn the admin that manual configuration may be needed before or after updating.
- **Update during active conversation**: If a user is mid-conversation when an update/redeploy happens, the conversation context should be preserved (already persisted to disk).
- **Partial deploy failure**: If the redeploy health check fails after pulling code, the system should automatically roll back and notify the admin.
- **Admin identification**: Only designated admin users should be able to trigger "update" and "undo update" commands. Other family members seeing the notification should not accidentally trigger an update.
- **Concurrent update attempts**: If "update" is sent twice, the second request should be ignored while the first is in progress.

## Requirements

### Functional Requirements

- **FR-001**: System MUST check for upstream updates on a configurable schedule (default: daily).
- **FR-002**: System MUST compare the local deployed version against the upstream remote and detect when new commits are available.
- **FR-003**: System MUST generate a human-readable summary of changes (not raw git log) when notifying about available updates.
- **FR-004**: System MUST send update notifications via WhatsApp to the designated admin phone number only.
- **FR-005**: System MUST NOT send duplicate notifications for the same upstream version.
- **FR-006**: System MUST back up persistent data before applying any update.
- **FR-007**: System MUST pull upstream changes and trigger a redeploy when the admin replies "update".
- **FR-008**: System MUST verify the redeploy succeeded via health check before confirming to the admin.
- **FR-009**: System MUST support rollback to the pre-update version when the admin replies "undo update" within the grace period.
- **FR-010**: System MUST restore the data backup when rolling back.
- **FR-011**: System MUST abort and restore the previous state if the upstream merge produces conflicts.
- **FR-012**: System MUST restrict update and rollback commands to the admin phone number.

### Key Entities

- **Update State**: Tracks the current deployed version, last checked version, last notified version, and last update timestamp. Persists across restarts.
- **Data Backup**: A snapshot of the persistent data directory taken before an update is applied. Retained until the rollback grace period expires or a new update is applied.
- **Changelog Summary**: A human-readable description of changes between the current version and the available upstream version.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Admin receives update notification within 24 hours of a new upstream release being published.
- **SC-002**: Applying an update via "update" reply completes within 5 minutes from command to confirmation.
- **SC-003**: Rollback via "undo update" restores the previous working version within 5 minutes.
- **SC-004**: Zero data loss during update or rollback — all persistent data is preserved or restored.
- **SC-005**: 100% of failed deploys (health check failure) are automatically rolled back without admin intervention.

## Assumptions

- Each family instance has an upstream git remote configured pointing to the template repository (documented in ONBOARDING.md).
- The deployment platform supports programmatic redeploy (Railway CLI `railway up` or equivalent).
- The admin phone number is configured as an environment variable and is distinct from other family members (or the same if the family has a single admin).
- The bot has git access to fetch from the upstream remote within its deployment environment.
- Data backups are stored locally on the persistent volume — no external backup service is needed.
- The upstream repository follows a main-branch release model (no tagged releases required).

## Out of Scope

- Multi-step migration scripts for database schema changes — this feature handles code updates only.
- Automatic resolution of merge conflicts — conflicts require manual intervention.
- Update scheduling preferences (e.g., "only update on weekends") — updates are applied immediately when the admin replies.
- Notification channels other than WhatsApp (email, SMS, push notifications).
- Support for non-Railway deployment platforms in this iteration.
