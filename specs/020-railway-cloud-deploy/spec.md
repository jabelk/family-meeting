# Feature Specification: Railway Cloud Deployment

**Feature Branch**: `020-railway-cloud-deploy`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Multi-tenant cloud deployment of MomBot on Railway for self-service setup by non-technical users (starting with pastor). Secure hosting with access to email, finances, calendars. Template repo pattern so each family gets their own isolated instance with their own WhatsApp app, API keys, and data. Support A/B testing between NUC and Railway for existing deployment, then full migration."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Deploy MomBot to Railway (A/B with NUC) (Priority: P1)

Jason deploys a second instance of MomBot on Railway that runs alongside the existing NUC deployment. Both instances are fully functional. Jason can compare reliability, latency, and cost between the two, then cut over to Railway by updating the WhatsApp webhook URL. The NUC can be decommissioned once Railway proves stable.

**Why this priority**: Jason cannot offer the system to others until he's validated that Railway works for his own family first. This also proves out the deployment pattern and surfaces any cloud-specific issues (storage, OAuth, scheduling) before anyone else onboards.

**Independent Test**: Deploy the app to Railway with all integrations working (WhatsApp, Notion, Google Calendar, YNAB, AnyList). Send a WhatsApp message to the Railway instance and receive a correct response. Run the daily briefing and verify it includes calendar events, meal plans, and budget data.

**Acceptance Scenarios**:

1. **Given** the codebase is pushed to a Railway project, **When** Railway builds and starts the service, **Then** the health endpoint returns 200 and all integrations are reachable.
2. **Given** a WhatsApp webhook is pointed at the Railway URL, **When** a user sends a message, **Then** the response is identical in quality to the NUC deployment.
3. **Given** both NUC and Railway instances exist, **When** Jason updates the WhatsApp webhook URL in Meta's dashboard, **Then** traffic switches to Railway with zero message loss.
4. **Given** the Railway instance has been running for 7+ days, **When** Jason reviews uptime and response times, **Then** Railway meets or exceeds NUC reliability.
5. **Given** Railway deployment is validated, **When** Jason decides to migrate, **Then** the NUC can be decommissioned without affecting the family's experience.

---

### User Story 2 — Persistent Storage Without Local Files (Priority: P1)

All data currently stored in local JSON files (conversations, preferences, sync records, work calendar, usage counters) is persisted in a way that survives Railway redeploys. Data is not lost when the container restarts or a new version is deployed.

**Why this priority**: Without persistent storage, the Railway deployment is unusable — conversations reset on every deploy, sync records are lost, and preferences disappear. This is a hard blocker for US1.

**Independent Test**: Push test data (conversation, preferences, work calendar events) to the Railway instance via the API. Trigger a redeploy. Verify all data is intact after the new container starts.

**Acceptance Scenarios**:

1. **Given** a conversation is in progress on Railway, **When** a new version is deployed, **Then** the conversation context is preserved.
2. **Given** user preferences and sync records exist, **When** the container restarts, **Then** all data files are intact.
3. **Given** the storage solution is configured, **When** a new family instance is created, **Then** their data is completely isolated from other instances.

---

### User Story 3 — Scheduled Jobs Without n8n (Priority: P1)

All scheduled automations (daily briefing, weekly meal plan, budget scans, nudge processing, etc.) run reliably on Railway without requiring an n8n instance. The scheduling mechanism is simple to configure and doesn't require a separate service.

**Why this priority**: n8n is a stateful service that's complex to deploy on Railway and overkill for simple cron-triggered HTTP calls. Without a scheduling replacement, the daily briefing and all proactive features stop working.

**Independent Test**: Configure the scheduling mechanism. Wait for the daily briefing trigger time. Verify the briefing is generated and sent via WhatsApp without manual intervention.

**Acceptance Scenarios**:

1. **Given** scheduled jobs are configured, **When** the daily briefing time arrives (7 AM Pacific), **Then** the briefing is generated and sent to Erin's WhatsApp.
2. **Given** a schedule includes 15-minute intervals (nudge scan), **When** the interval elapses, **Then** the nudge scan endpoint is called reliably.
3. **Given** a new family instance is created, **When** they configure their schedule, **Then** jobs run at their specified times in their timezone.

---

### User Story 4 — Google OAuth in Containers (Priority: P1)

Google Calendar integration works in a containerized environment without manual browser-based OAuth flows. Tokens are managed automatically and don't expire in a way that breaks the daily briefing.

**Why this priority**: The current OAuth flow requires opening a browser on the NUC, and tokens expire every 7 days (Google testing mode). This is a hard blocker for self-service — a pastor can't SSH into a container to refresh tokens.

**Independent Test**: Deploy to Railway with Google Calendar credentials configured. Verify the daily briefing includes calendar events. Wait 8+ days and verify calendar access still works without manual intervention.

**Acceptance Scenarios**:

1. **Given** Google Calendar credentials are configured via environment variables, **When** the app starts, **Then** it can read and write calendar events without any browser interaction.
2. **Given** the OAuth app is published (not in testing mode), **When** the app has been running for 30+ days, **Then** Google Calendar tokens auto-refresh and events are included in briefings without manual intervention.
3. **Given** a new family is onboarding, **When** they follow the setup guide to create and publish their own Google Cloud OAuth app, **Then** they can generate long-lived credentials locally and configure them in Railway.

---

### User Story 5 — Template Repo for Self-Service Onboarding (Priority: P2)

A non-technical user (the pastor) can create their own MomBot instance by following a guided setup process. They get their own GitHub repo, Railway project, WhatsApp Business app, and API keys. Their data is completely isolated. Claude Code guides them through the setup.

**Why this priority**: This is the core goal — making MomBot available to other families — but it depends on US1-US4 being proven first. The pastor is the first external user and validates the self-service flow.

**Independent Test**: A person with no programming experience follows the onboarding guide using Claude Code. They end up with a working MomBot instance that responds to WhatsApp messages and includes their own calendar, Notion, and budget data.

**Acceptance Scenarios**:

1. **Given** the template repo exists on GitHub, **When** a new user clicks "Use this template", **Then** they get a clean repo with all MomBot code and a setup guide.
2. **Given** a new user has their repo, **When** they run the onboarding assistant (Claude Code), **Then** it walks them through creating a Railway project, setting environment variables, and connecting integrations one by one.
3. **Given** a new user has completed onboarding, **When** they send a WhatsApp message, **Then** MomBot responds using their own Notion, Calendar, and budget data.
4. **Given** an upstream improvement is made to the template repo, **When** the user wants to update, **Then** they can pull changes without losing their configuration or data.

---

### User Story 6 — Security Lockdown for Sensitive Integrations (Priority: P2)

All sensitive credentials (Gmail OAuth, YNAB tokens, Notion tokens, WhatsApp secrets) are stored securely and never exposed in logs, error messages, or to other tenants. The system follows the principle of least privilege for all integrations.

**Why this priority**: MomBot has read/write access to email, finances, and calendars. A security breach could expose deeply personal family data. This must be airtight before offering to others.

**Independent Test**: Review Railway environment variable configuration. Attempt to access another tenant's data. Verify credentials are not logged. Verify the app rejects requests without valid authentication.

**Acceptance Scenarios**:

1. **Given** credentials are stored in Railway environment variables, **When** the app logs errors or exceptions, **Then** no credentials, tokens, or secrets appear in log output.
2. **Given** each family has their own Railway project, **When** one family's instance is compromised, **Then** no other family's data or credentials are accessible.
3. **Given** the WhatsApp webhook is public, **When** an unauthenticated request is received, **Then** it is rejected with appropriate error codes.
4. **Given** a user wants to revoke MomBot's access, **When** they remove the integration credentials, **Then** MomBot immediately loses access and fails gracefully with user-friendly messages.

---

### User Story 7 — AnyList Sidecar on Railway (Priority: P3)

The AnyList grocery integration works on Railway. The Node.js sidecar runs as a separate Railway service or is integrated into the main app, and the two services can communicate.

**Why this priority**: AnyList is a "nice to have" integration — many families may not use it. The core value (WhatsApp chat, calendar, budget, meal planning) works without it.

**Independent Test**: Deploy the AnyList sidecar to Railway. Send a WhatsApp message asking to add items to the grocery list. Verify items appear in AnyList.

**Acceptance Scenarios**:

1. **Given** the AnyList sidecar is deployed on Railway, **When** the main app sends a request to add grocery items, **Then** the items appear in the family's AnyList.
2. **Given** a family doesn't use AnyList, **When** they skip the AnyList configuration, **Then** MomBot works normally and grocery features degrade gracefully.

---

### Edge Cases

- What happens when Railway has an outage during the daily briefing window? The system should retry the briefing within a reasonable window or notify the user that it was missed.
- What happens when a user's Google Calendar token expires and auto-refresh fails? The system should degrade gracefully (skip calendar data in briefing) and notify the user.
- What happens when a template repo user's Railway project runs out of free-tier resources? The system should surface clear error messages and the onboarding guide should document expected costs.
- What happens when two family members send messages simultaneously to the same instance? The existing concurrency handling should work, but must be verified under Railway's threading model.
- What happens when the onboarding user has no Notion account or YNAB account? Integrations should be optional — core chat and calendar features still work without them.
- What happens when a redeploy occurs mid-conversation? In-flight requests should complete; the next message should work normally even if conversation context was briefly unavailable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST deploy to Railway from a single `git push` to the main branch with no manual steps beyond initial setup.
- **FR-002**: System MUST persist all application data (conversations, preferences, sync records, work calendar, usage counters) across container restarts and redeploys.
- **FR-003**: System MUST execute all scheduled automations (daily briefing, weekly meal plan, budget scans, nudge processing, Amazon/email sync) without an n8n instance.
- **FR-004**: System MUST authenticate with Google Calendar without browser-based OAuth flows or manual token refresh.
- **FR-005**: System MUST provide a GitHub template repo that new users can create from to set up their own isolated instance.
- **FR-006**: System MUST include an onboarding guide that a non-technical user can follow with Claude Code assistance to set up all integrations.
- **FR-007**: System MUST ensure complete data isolation between family instances — no shared databases, no shared credentials, no cross-tenant access.
- **FR-008**: System MUST never log, display, or transmit credentials, tokens, or secrets in plain text.
- **FR-009**: System MUST validate WhatsApp webhook signatures and reject unauthenticated requests on all endpoints.
- **FR-010**: System MUST support the AnyList Node.js sidecar as an optional separate service on Railway.
- **FR-011**: System MUST allow Jason to run both NUC and Railway instances simultaneously and switch between them by changing the WhatsApp webhook URL.
- **FR-012**: System MUST handle optional integrations gracefully — WhatsApp is the only required integration. Google Calendar, Notion, YNAB, and AnyList are all optional add-ons that can be configured at any time after initial setup. The system works as a standalone chat assistant without any of them.
- **FR-013**: System MUST support timezone configuration per family instance.
- **~~FR-014~~**: *(Deferred to future feature — see GitHub issue #30)* Upstream update notification via WhatsApp.
- **~~FR-015~~**: *(Deferred to future feature — see GitHub issue #30)* Data backup before upstream updates.
- **~~FR-016~~**: *(Deferred to future feature — see GitHub issue #30)* Rollback of updates via WhatsApp.

### Key Entities

- **Family Instance**: A complete, isolated deployment of MomBot for one family. Includes its own Railway project, environment variables, WhatsApp Business app, and data store.
- **Template Repo**: The canonical GitHub repository containing MomBot code, onboarding guide, and Railway configuration. Used as the starting point for new family instances.
- **Integration Credential**: A secret (API key, OAuth token, webhook secret) that connects a family instance to an external service (Google, Notion, YNAB, WhatsApp, AnyList).
- **Scheduled Job**: A recurring automation (daily briefing, nudge scan, etc.) that runs at a configured time without external orchestration.

## Clarifications

### Session 2026-03-08

- Q: How should Google Calendar auth work in containers given personal Gmail accounts can't use service accounts? → A: Each family publishes their own Google OAuth app (same as Jason's current pattern, moved out of testing mode). Tokens auto-refresh indefinitely. Onboarding guide walks through Google Cloud project setup.
- Q: Which integrations are required vs optional for new families? → A: WhatsApp only is the minimum. Google Calendar, Notion, YNAB, AnyList are all optional add-ons configurable at any time. Core chat assistant works standalone.
- Q: How should new families set up WhatsApp Business? → A: Each family creates their own Meta developer account and WhatsApp Business app (Cloud API). Fully isolated, onboarding guide walks through it step by step.

## Non-Functional Requirements

- **NFR-001**: Railway deployment MUST start serving requests within 60 seconds of container launch.
- **NFR-002**: Onboarding a new family instance MUST be completable in under 2 hours by a non-technical user with Claude Code assistance.
- **NFR-003**: The system MUST maintain the same response latency as the NUC deployment (messages answered within 15 seconds for simple queries).
- **NFR-004**: Credentials MUST be stored only in Railway's encrypted environment variable system — never in code, config files, or container filesystem.
- **NFR-005**: Each family instance MUST run independently — one instance going down does not affect others.

## Assumptions

- Each family gets their own Railway project (single-tenant per Railway project, not multi-tenant in one app).
- Railway's persistent volume or an external database will be used for data persistence — the specific mechanism will be determined during planning.
- Google Calendar will use published OAuth apps (one per family). Each family creates their own Google Cloud project and publishes the OAuth app (removes testing-mode 7-day token expiry). Tokens auto-refresh indefinitely. Same pattern as Jason's current setup, just published instead of testing mode.
- Each family creates their own Meta developer account and WhatsApp Business app (Cloud API). The onboarding guide provides step-by-step instructions. This ensures full isolation — each family owns their own WhatsApp app credentials.
- Railway's Hobby tier provides sufficient resources for a single family instance.
- The existing Dockerfile is compatible with Railway's build system (confirmed by companion-ai pattern).
- Scheduled jobs will use Railway's built-in cron feature or a lightweight in-app scheduler — n8n will not be deployed to Railway.
- The template repo relationship will use GitHub's "Use this template" feature, with upstream updates pulled via git remote.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Jason's family can use MomBot on Railway with identical functionality to the NUC deployment for 14+ consecutive days without manual intervention.
- **SC-002**: A non-technical user (the pastor) can go from zero to a working MomBot instance in under 2 hours using Claude Code guidance.
- **SC-003**: All 14 scheduled automations fire reliably on Railway (zero missed triggers over a 7-day test period).
- **SC-004**: Google Calendar access works for 30+ days without manual token refresh.
- **SC-005**: No credentials appear in Railway logs or application error output (verified by log audit).
- **SC-006**: Data persists across at least 5 consecutive redeploys with zero data loss.
- **SC-007**: The pastor's instance is completely isolated — cannot access Jason's Notion, Calendar, YNAB, or conversation data.
