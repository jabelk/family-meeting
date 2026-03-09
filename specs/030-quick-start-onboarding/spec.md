# Feature Specification: Quick Start Onboarding

**Feature Branch**: `030-quick-start-onboarding`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "No Quick Start path. Currently 8 steps across 4 platforms (3-4 hours). Need a minimal setup: WhatsApp + AI only (~30 min) with integrations as optional add-ons. Automate as much as possible — operator fills in a YAML file and the system does the rest."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Setup from Config File (Priority: P1)

An operator fills in family.yaml with family details and preferences (committed to git), and .env with credentials and API keys (not committed). They run a validation script that validates both files together, checks integration completeness, and reports readiness. The operator then deploys with one command. The validation script cross-references family.yaml and .env to ensure all required values are present for configured integrations. Future enhancement: support secrets managers (e.g., HashiCorp Vault) as an alternative credential source.

**Why this priority**: This is the highest-impact change. Today operators must manually edit both family.yaml AND .env with no automated cross-validation. A validation script that validates both files together, detects partial integration configs, and reports exactly what's ready eliminates the most error-prone part of setup.

**Independent Test**: Fill in family.yaml with test values (API keys, phone numbers, integration credentials). Run the validation script. Verify it validates both files and reports what integrations are enabled. Deploy and send a WhatsApp message.

**Acceptance Scenarios**:

1. **Given** a filled-in family.yaml with required fields (API keys, WhatsApp credentials, phone numbers), **When** the operator runs the validation script, **Then** it validates the .env file and reports all checks passed.
2. **Given** a family.yaml with only minimal required fields (Anthropic key, WhatsApp credentials, partner phones), **When** the operator runs the validation script, **Then** it confirms only required vars are present, reports which optional integrations are disabled, and reports "Minimal deployment ready."
3. **Given** a family.yaml with a Notion token but missing database IDs, **When** the operator runs the validation script, **Then** it warns that Notion is partially configured and lists the missing database IDs.
4. **Given** a family.yaml with an invalid phone number format, **When** the operator runs the validation script, **Then** it reports the specific validation error with the expected format.

---

### User Story 2 - Bot Adapts to Configured Integrations (Priority: P1)

When integrations are not configured, the bot must not reference unavailable features in its system prompt or attempt unavailable tool calls. If Notion is not set up, the bot should not offer to "add that to your action items." The bot's available tools and system prompt dynamically reflect what's actually configured, so a minimal deployment feels intentional — not broken.

**Why this priority**: Tied with US1 because a minimal deployment that constantly references unavailable features feels broken. This is essential for the Quick Start experience to feel polished and professional.

**Independent Test**: Deploy with only WhatsApp + AI configured. Send messages that would normally trigger Notion/Calendar/YNAB tools (e.g., "what's on my calendar today?"). The bot should gracefully explain it doesn't have calendar access, rather than attempting a tool call that fails.

**Acceptance Scenarios**:

1. **Given** a deployment without Google Calendar configured, **When** a user asks "what's on my calendar?", **Then** the bot responds that calendar integration is not set up, without attempting the calendar tool call.
2. **Given** a deployment without Notion configured, **When** a user asks to add an action item, **Then** the bot acknowledges the request but explains task management is not available in this deployment.
3. **Given** a deployment with all integrations configured, **When** a user asks about their calendar, **Then** the bot uses the calendar tool as it does today (no regression).
4. **Given** a minimal deployment, **When** the bot generates its tool list, **Then** tools for unconfigured integrations are excluded entirely — they do not appear in the system prompt.

---

### User Story 3 - Pre-Deployment Validation (Priority: P2)

Before deploying, the operator runs a validation command that checks all configuration is correct: required env vars exist, API key formats are valid, family.yaml parses correctly, phone numbers are in expected format, and optional integrations are properly configured (all-or-nothing per integration group). This catches errors before they result in a failed deployment.

**Why this priority**: Prevents the most common failure mode (deploy, wait for startup, discover misconfiguration, fix, redeploy). Important but not blocking — an operator can deploy without validation and rely on health endpoint and startup logs.

**Independent Test**: Run the validation tool with intentionally incorrect config (missing API key, malformed phone number, partial Notion setup) and verify it reports each error clearly.

**Acceptance Scenarios**:

1. **Given** a correctly configured environment, **When** the operator runs validation, **Then** it reports all checks passed with a summary of enabled integrations.
2. **Given** a missing required env var (e.g., ANTHROPIC_API_KEY), **When** the operator runs validation, **Then** it identifies the variable, explains what it's for, and shows which family.yaml field maps to it.
3. **Given** a partial integration setup (e.g., NOTION_TOKEN set but NOTION_ACTION_ITEMS_DB missing), **When** the operator runs validation, **Then** it reports the integration as "partially configured" and lists specific missing values.

---

### User Story 4 - Health Endpoint Reflects Configured State (Priority: P2)

The health endpoint reports "healthy" when all configured integrations are working, rather than "degraded" when optional integrations are simply not configured. An operator with a minimal deployment should see "healthy" status, not be alarmed by a "degraded" status for integrations they intentionally chose not to set up.

**Why this priority**: Quality-of-life improvement. A "degraded" health status for a minimal deployment creates unnecessary concern and confusion.

**Independent Test**: Deploy with only WhatsApp + AI. Hit the health endpoint. Verify it returns "healthy" with unconfigured integrations listed as "not configured" (not "failing").

**Acceptance Scenarios**:

1. **Given** a minimal deployment (WhatsApp + AI only), **When** the operator checks the health endpoint, **Then** it returns "healthy" status.
2. **Given** a full deployment with all integrations, **When** one optional integration fails (e.g., Notion API is down), **Then** it returns "degraded" as it does today.
3. **Given** a deployment where an integration is configured but failing, **When** the operator checks health, **Then** the failing integration shows as "configured: true, connected: false" with the error — distinct from "configured: false."

---

### Edge Cases

- What happens when an operator deploys with zero configuration (no family.yaml, no .env)? The app should fail at startup with a clear error pointing to the validation script.
- What happens when an operator partially configures an integration (e.g., sets NOTION_TOKEN but not database IDs)? The validation tool should warn, and at runtime the integration should be treated as disabled with a startup log warning.
- What happens when an operator removes an integration that was previously configured (deletes env vars and restarts)? The bot should immediately stop offering those features with no leftover tool references.
- What happens when family.yaml contains credentials for an integration the operator hasn't provisioned yet (e.g., a placeholder Google Calendar ID)? Validation should distinguish between "missing" and "invalid format."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST use family.yaml for family identity and preferences (safe to commit) and .env for credentials and secrets (never committed). The validation script validates both files together as a unified configuration surface.
- **FR-002**: The system MUST provide a validation script that reads family.yaml, cross-references .env, validates all configuration, and reports deployment readiness — including which integrations are enabled, disabled, or partially configured.
- **FR-003**: The system MUST function as a useful conversational assistant with only WhatsApp and Anthropic API configured — no other integrations required.
- **FR-004**: The system MUST dynamically exclude tools for unconfigured integrations from the assistant's available tool set and system prompt at startup. System prompt sections are tagged with their required integration and filtered at load time — sections for disabled integrations are omitted entirely.
- **FR-005**: The bot MUST NOT attempt tool calls for unconfigured integrations, and MUST NOT reference unavailable features in its responses.
- **FR-006**: The health endpoint MUST distinguish between "not configured" (operator choice) and "configured but failing" (error), and MUST report "healthy" when all configured integrations are operational.
- **FR-007**: The system MUST provide a validation command that checks all configuration before deployment: env var presence, format validation, family.yaml parsing, and integration group completeness.
- **FR-008**: The validation command MUST provide specific, actionable error messages for each issue found.
- **FR-009**: Adding or removing an integration MUST require only updating env vars and restarting — no code changes or migrations.
- **FR-010**: The system MUST log which integrations are enabled vs disabled at startup.
- **FR-011**: The validation script MUST be idempotent — running it multiple times with the same configuration produces identical results with no side effects.

### Key Entities

- **Integration**: A configurable external service (e.g., Notion, Google Calendar, YNAB). Has a name, required credential fields, enabled/disabled status, and associated bot tools. Integrations are all-or-nothing: either fully configured or fully disabled.
- **Operator**: The person deploying and managing the assistant for a family. Fills in family.yaml, runs the setup/validation commands, deploys to Railway.
- **family.yaml**: Configuration file for family identity (names, timezone, preferences) and integration declarations (which integrations are desired). Safe to commit to version control. Drives the bot's personality and declares which features should be enabled.
- **.env**: Credentials file for API keys, tokens, and secrets. Never committed to version control. Provides the sensitive values that family.yaml's integration declarations require. Future: may be replaced by a secrets manager (e.g., HashiCorp Vault).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new operator completes setup and exchanges their first WhatsApp message within 30 minutes (excluding Meta Business verification wait time).
- **SC-002**: Operator fills in two files (family.yaml for identity, .env for credentials) and runs one command to validate and report deployment readiness.
- **SC-003**: A minimal deployment (WhatsApp + AI only) passes the health check as "healthy" with zero integration-related errors in startup logs.
- **SC-004**: When an integration is not configured, 0% of bot responses reference that integration's features.
- **SC-005**: The validation command catches 100% of missing required fields, malformed values, and partial integration configurations before deployment.
- **SC-006**: An operator can add any single integration by adding credentials to .env, running the validation script, and restarting — under 15 minutes per integration.

## Clarifications

### Session 2026-03-09

- Q: Should credentials live in family.yaml (convenient) or .env (secure)? → A: Split approach — family.yaml for identity/preferences (committed to git), .env for credentials/secrets (not committed). Setup command validates both. Future enhancement: support secrets managers (e.g., HashiCorp Vault) for sensitive values.
- Q: How should the system prompt handle unconfigured integrations? → A: Tag prompt sections with required integrations; filter at load time (omit sections for disabled integrations). Research best practices and tradeoffs for Markdown-based prompt management at scale during planning phase.

## Assumptions

- Meta Business verification and WhatsApp Business API provisioning are external dependencies with variable wait times (hours to days). The Quick Start guide clearly flags this as a prerequisite completed before starting the timer.
- Railway remains the primary deployment platform. The setup automation targets Railway.
- Credentials stay in .env (not family.yaml) for security. family.yaml may declare which integrations are desired, but secrets are always sourced from .env or a secrets manager.
- Google Calendar OAuth still requires an interactive browser flow (setup_calendar.py) — this cannot be fully automated via YAML. The validation script handles everything except OAuth flows, which are flagged as manual steps.
- Markdown-based prompt management (9 numbered files, tag-and-filter) is sufficient for the current scale (~6 integration groups, ~22 tools). Planning phase should research best practices and tradeoffs for this approach vs alternatives if feature count grows significantly.
- The Anthropic API key is readily obtainable by operators (sign up at console.anthropic.com, generate key).

## Out of Scope

- Multi-tenant deployments (one instance serving multiple families).
- Automated Notion database schema creation (Notion API limitation).
- Automated WhatsApp Business API provisioning (requires manual Meta Business verification).
- Interactive setup wizard or web-based configuration UI — the YAML file approach is sufficient.
- One-click deploy buttons (Railway template marketplace).
- Operator dashboard for managing multiple family deployments.
