# Research: Conversation Log Backup

## Decision 1: Scheduling Mechanism — cron vs n8n

**Decision**: Use system cron on the NUC host

**Rationale**: This is a simple file copy with no API calls, webhooks, or complex logic. System cron is the right tool — it's already available on Ubuntu 24.04, requires zero dependencies, and is more reliable for simple scheduled tasks than routing through n8n's workflow engine.

**Alternatives considered**:
- n8n workflow: Overkill for a file copy. Adds unnecessary complexity and a dependency on the n8n container being healthy. n8n is better suited for API orchestration workflows.
- Docker cron container: Adds another container to manage. The file is on a bind mount accessible from the host, so there's no need to run inside Docker.
- systemd timer: More complex than cron for this use case with no meaningful benefit.

## Decision 2: Archive Location — on-NUC vs external

**Decision**: Archive on the NUC itself at `~/family-meeting/data/conversation_archives/`

**Rationale**: The `data/` directory is already a Docker bind mount, so archives are accessible from both host and container. At ~200KB per file and 30-day retention, total storage is ~6MB — negligible on the NUC's disk. External storage (NAS, cloud) would add complexity for no benefit at this scale.

**Alternatives considered**:
- Cloud storage (S3/R2): Massive overkill for 6MB of archives. Adds credentials management and network dependency.
- Local MacBook sync: Would require the MacBook to be on and connected. The NUC is always-on, making it the right primary archive location. Retrieval via `nuc.sh` handles the "pull to laptop" need.

## Decision 3: Archive Format — full copy vs incremental

**Decision**: Full file copy with date-stamped filename

**Rationale**: conversations.json is small (~200KB). A full copy per day is simpler to implement, simpler to read (each file is self-contained), and the storage cost is negligible (6MB for 30 days). Incremental/diff approaches would add complexity for zero practical benefit.

**Alternatives considered**:
- Git-based versioning: Would track diffs efficiently but adds git operations and a separate repo to manage. Over-engineered for this use case.
- Append-only log: Would capture every message as it arrives. More complete but requires code changes to the FastAPI app. Out of scope for this feature — the goal is a simple backup of existing data.

## Decision 4: Retrieval Interface — nuc.sh subcommand vs standalone script

**Decision**: Add `chat-logs` subcommand to existing `nuc.sh`

**Rationale**: `nuc.sh` is already the canonical interface for NUC operations. Adding a subcommand follows the established pattern and keeps all NUC management in one place. No new scripts for the developer to discover or remember.

**Alternatives considered**:
- Standalone `fetch-logs.sh`: Would duplicate SSH/host configuration already in `nuc.sh`. Fragmentation of tooling.
- Rsync daemon: Overkill for occasional ad-hoc retrieval.
