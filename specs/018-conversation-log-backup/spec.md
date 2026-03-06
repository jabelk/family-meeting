# Feature Specification: Conversation Log Backup

**Feature Branch**: `018-conversation-log-backup`
**Created**: 2026-03-05
**Status**: Draft
**Input**: User description: "Conversation log backup — automatically back up chat conversation logs from the NUC to local machine on a cron schedule so we have historical context for debugging issues. Currently conversations.json only keeps recent turns and we lose older context. Need a scheduled backup that preserves historical conversation data so we can review past interactions when users report issues."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Daily Conversation Archival (Priority: P1)

As a developer, I want conversation logs automatically archived on a daily schedule so that when a user reports an issue (e.g., "it said breakfast at nighttime"), I can look back at the actual conversation that triggered the complaint — even if the live conversations.json has already rotated those turns out.

**Why this priority**: Without historical logs, debugging user-reported issues is impossible. The live conversations.json only keeps recent turns per phone number, so older interactions are permanently lost. This is the core problem.

**Independent Test**: Can be fully tested by triggering the backup process and verifying that a timestamped copy of conversations.json is created and preserved, then confirming that rotating the live file does not affect the archived copy.

**Acceptance Scenarios**:

1. **Given** the NUC is running and conversations.json exists, **When** the scheduled backup fires, **Then** a timestamped copy of conversations.json is saved to the archive location
2. **Given** the backup has run for several days, **When** a developer needs to investigate a past conversation, **Then** they can find and read the archived file for that date
3. **Given** the NUC has no new conversations since the last backup, **When** the backup fires, **Then** it still creates the archive (captures the current state)

---

### User Story 2 - Archive Retention and Cleanup (Priority: P2)

As a developer, I want old archives automatically cleaned up so the backup directory doesn't grow unbounded on the NUC's limited disk space.

**Why this priority**: Without retention limits, daily backups of a growing JSON file will eventually fill the NUC's disk. This is important but secondary to having backups at all.

**Independent Test**: Can be tested by creating archives older than the retention period and running the cleanup process to verify they are removed while recent archives are preserved.

**Acceptance Scenarios**:

1. **Given** archived logs older than the retention period exist, **When** the cleanup runs, **Then** archives older than the retention period are deleted
2. **Given** all archives are within the retention period, **When** the cleanup runs, **Then** no archives are deleted

---

### User Story 3 - On-Demand Log Retrieval (Priority: P3)

As a developer, I want a simple way to pull archived logs from the NUC to my local machine so I can search and analyze past conversations without SSH-ing in and manually navigating files.

**Why this priority**: Convenience layer — the archives exist on the NUC, but pulling them locally for analysis (grep, jq, etc.) makes debugging faster. Lower priority because manual scp works as a fallback.

**Independent Test**: Can be tested by running the retrieval command and verifying the correct archive files appear on the local machine.

**Acceptance Scenarios**:

1. **Given** archived logs exist on the NUC, **When** the developer runs the retrieval command, **Then** the specified date range of archives is copied to the local machine
2. **Given** the developer requests archives for a date with no backup, **When** the retrieval runs, **Then** a clear message indicates no archive exists for that date

---

### Edge Cases

- What happens when the NUC is offline or unreachable at backup time? Backup runs locally on the NUC itself, so network issues don't affect archival. Only retrieval (US3) requires network.
- What happens when conversations.json is empty or corrupt? The backup archives whatever exists (even an empty file), so the state is captured.
- What happens when disk space is critically low on the NUC? The backup should check available space and skip archival if below a safe threshold, logging a warning.
- What happens when conversations.json is being written to during backup? The copy should be atomic or use a snapshot approach to avoid capturing a partial write.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create a timestamped copy of the live conversation log file on a daily schedule
- **FR-002**: System MUST preserve archived logs independently from the live file (archiving must not modify or truncate the live file)
- **FR-003**: System MUST retain archived logs for at least 30 days
- **FR-004**: System MUST automatically delete archived logs older than the retention period
- **FR-005**: System MUST provide a command to retrieve archived logs from the NUC to the developer's local machine, filtered by date or date range
- **FR-006**: System MUST log each backup operation (success or failure) for auditability

### Key Entities

- **Conversation Archive**: A timestamped snapshot of the conversation log file, identified by the date it was captured. Contains all conversation turns that existed at the time of backup.
- **Retention Policy**: The configurable period (default 30 days) after which archived logs are automatically deleted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can retrieve any conversation from the past 30 days within 2 minutes of starting the retrieval process
- **SC-002**: Backup runs daily with 99% reliability (missed backups due to NUC downtime are acceptable but logged)
- **SC-003**: Archive storage uses less than 500 MB of disk space on the NUC over a 30-day retention period
- **SC-004**: Zero manual intervention required for routine backup and cleanup operations after initial setup

## Assumptions

- The NUC runs 24/7 and is available for scheduled tasks via its existing n8n or cron infrastructure
- The conversations.json file is the sole source of conversation history (no other log files need archival)
- The developer's local machine is a MacBook on the same local network as the NUC (or reachable via SSH)
- 30 days of retention is sufficient for debugging reported issues (users typically report problems within a few days)
