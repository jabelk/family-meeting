# Feature Specification: Template Repo Readiness & Service Packaging

**Feature Branch**: `028-template-repo-readiness`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "Competitive research on pricing, personal and corporate pricing options, and research what we need to do on the WhatsApp number side to make setup less painful and streamlined"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Externalize Family Identity & Configuration (Priority: P1)

A service operator (Jason or a future client) clones the template repo and configures their family's identity, preferences, and integrations through a single configuration file rather than editing source code. All hardcoded family names, locations, schedules, and tool-specific references (e.g., "Whole Foods") are replaced with configuration-driven values. The system prompt, tool behaviors, and daily briefings all reflect the configured family's identity.

**Why this priority**: Without externalizing identity, the codebase cannot be reused for other families. This is the foundational prerequisite for any multi-client deployment — every other feature depends on having a configurable identity layer.

**Independent Test**: Clone the repo, fill out the config file with a different family's details (different names, city, kids, grocery store), and verify the system prompt, daily briefing, and tool outputs all reflect the new family — with zero source code changes.

**Acceptance Scenarios**:

1. **Given** a fresh clone of the template repo, **When** an operator fills out the family configuration with their family details (names, city, timezone, kids, grocery store preference), **Then** the system prompt addresses the correct family members and references the correct location and stores.
2. **Given** a configured instance with "Sprouts" as the grocery store, **When** a user asks to add items to the grocery list, **Then** the assistant references "Sprouts" (not "Whole Foods") in its responses.
3. **Given** two separate instances with different family configs, **When** each receives the same message, **Then** each responds using its own family's names, preferences, and context.

---

### User Story 2 - Streamlined WhatsApp Number Setup (Priority: P2)

A new client can get a working WhatsApp number connected to their family assistant within a guided setup process. The operator follows a documented onboarding flow that handles Meta Business verification, WhatsApp Business API provisioning, and webhook configuration with minimal friction. For the first 10 clients, the Direct Cloud API path is used; the system is designed to migrate to a Business Solution Provider at scale.

**Why this priority**: WhatsApp is the primary user interface. Without a streamlined number setup, onboarding each new client requires extensive manual Meta Business Portal work, which is the biggest friction point for scaling.

**Independent Test**: Follow the onboarding guide to provision a new WhatsApp number for a test family, send a message, and verify the webhook receives it and responds.

**Acceptance Scenarios**:

1. **Given** a new client who has signed up for the service, **When** the operator follows the WhatsApp setup guide, **Then** they can provision a dedicated WhatsApp number and connect it to the client's instance within one business day.
2. **Given** a provisioned WhatsApp number, **When** the webhook URL and auth token are configured, **Then** messages sent to that number are received by the correct client instance.
3. **Given** a client using Meta's Embedded Signup flow, **When** the client connects their Facebook Business Manager, **Then** the system automatically provisions a WhatsApp number and configures the webhook without manual Meta portal steps.

---

### User Story 3 - Service Pricing & Packaging (Priority: P3)

The service is offered in clear pricing tiers that reflect the value delivered and the cost structure. Personal (individual family) and corporate (employer benefit / family services org) pricing options exist. Pricing covers infrastructure costs with healthy margins and positions the service competitively against human virtual assistants and other AI family tools.

**Why this priority**: Pricing needs to be defined before actively marketing the service, but the product must work first (US1 & US2). This story defines the business model that makes the service sustainable.

**Independent Test**: Present the pricing page to 3-5 prospective clients and validate that they understand the tiers, see the value proposition, and can identify which tier fits their needs.

**Acceptance Scenarios**:

1. **Given** a prospective personal client, **When** they view the pricing options, **Then** they see a clear personal tier with monthly pricing, setup fee, and what's included (WhatsApp assistant, calendar management, grocery lists, budget tracking).
2. **Given** a corporate HR department, **When** they inquire about the corporate/group plan, **Then** they receive a proposal with volume pricing, white-glove onboarding, and dedicated support terms.
3. **Given** the defined pricing tiers, **When** infrastructure costs are calculated per client, **Then** the gross margin is at least 65% on the personal tier and at least 75% on the corporate tier.

---

### User Story 4 - One-Click Deployment & Health Validation (Priority: P4)

A new client instance can be deployed to a cloud platform with a single command or one-click deploy button. The deployment includes a health check endpoint that validates all configured integrations (Notion, Google Calendar, YNAB, WhatsApp) and reports which are active vs. missing. This allows partial deployments where only some integrations are enabled.

**Why this priority**: Reduces deployment friction and ensures operators can quickly verify a new instance is working. Builds on US1 (config) and supports the white-glove onboarding process.

**Independent Test**: Click the deploy button, fill in required env vars, and verify the health endpoint returns a status showing which integrations are connected and which are pending.

**Acceptance Scenarios**:

1. **Given** a configured family config and required environment variables, **When** the operator runs the deploy command, **Then** the instance starts successfully and the health endpoint returns 200.
2. **Given** a deployed instance with only WhatsApp and Google Calendar configured, **When** the health endpoint is called, **Then** it reports WhatsApp and Calendar as "connected" and Notion/YNAB as "not configured" (not as errors).
3. **Given** a deploy with missing required env vars (e.g., no AI API key), **When** the app starts, **Then** it fails fast with a clear error message listing the missing required configuration.

---

### Out of Scope

- Automated billing / payment processing (invoicing is manual for initial clients)
- Self-service client portal for sign-up or account management
- Multi-region deployment or data residency controls
- Embedded Signup flow implementation (documented as future enhancement; initial clients use manual Meta Business Portal setup)
- Mobile app or web dashboard for family members

### Edge Cases

- What happens when a family has no children? The system should not reference kids-related features or ask about school schedules.
- What happens when a client only wants 2 of the 5 integrations? Unused integrations should be gracefully disabled, not error.
- What happens when the WhatsApp Business API rate limits are hit during onboarding? The setup guide should document retry procedures.
- How does the system handle timezone differences between family members? Config should support per-member timezone overrides.
- What happens when a client's Meta Business verification is rejected? The onboarding guide should include troubleshooting steps and escalation path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load all family-specific identity (names, location, timezone, children, preferences) from a configuration file rather than hardcoded values in source code.
- **FR-002**: System MUST replace all hardcoded references to specific family members in system prompts and tool descriptions with configuration-driven values.
- **FR-003**: System MUST replace hardcoded grocery store references with a configurable grocery store name.
- **FR-004**: System MUST provide a documented WhatsApp number onboarding flow covering Meta Business verification, number provisioning, and webhook configuration.
- **FR-005**: The onboarding guide MUST document the Embedded Signup flow as a future enhancement path. Initial clients will use the manual Meta Business Portal setup guided by the operator.
- **FR-006**: System MUST define at least two pricing tiers: a personal/family tier and a corporate/group tier.
- **FR-007**: System MUST include a health check endpoint that reports the status of each configured integration individually.
- **FR-008**: System MUST validate required configuration on startup — only WhatsApp credentials and an AI API key are required. All other integrations are optional. System MUST fail fast with clear error messages if required values are missing.
- **FR-009**: System MUST gracefully handle missing optional integrations (Notion, Google Calendar, YNAB, AnyList) without errors. The assistant MUST still function as a conversational family chat when only WhatsApp + AI are configured.
- **FR-010**: System MUST support one-click or single-command deployment to a cloud platform.
- **FR-011**: System MUST maintain a per-client infrastructure cost under $30/month to support target pricing margins.
- **FR-012**: Service MUST be positioned as a "family management service" (not a general-purpose AI chatbot) to comply with Meta's WhatsApp policies on AI-powered bots.
- **FR-013**: System MUST support configurable calendar sources (Google Calendar, Outlook ICS, iOS Shortcut push, or none).
- **FR-014**: System MUST include an onboarding guide document covering end-to-end setup for a new client.
- **FR-015**: Each client MUST run as a fully separate single-tenant deployment with its own service instance, data directory, and configuration — no shared infrastructure between client families.
- **FR-016**: The operator MUST NOT access client conversation data or family information without explicit per-incident consent from the client. The service agreement MUST disclose this access model.
- **FR-017**: The onboarding guide MUST include a service agreement template covering data privacy, operator access consent process, and data ownership.

### Key Entities

- **Family Profile**: The identity configuration for a single family instance — member names, roles, children (names + ages), location, timezone, preferences (grocery store, dietary restrictions), enabled integrations.
- **Service Tier**: A pricing package defining what's included — tier name, monthly fee, setup fee, included integrations, support level, max family members.
- **Client Instance**: A single-tenant deployed family assistant — associated family profile, WhatsApp number, dedicated deployment environment (own service, own data directory, own config), integration status, billing status. Each instance is fully isolated from other clients.
- **Integration Status**: Per-integration connection state — integration name, configured (yes/no), connected (yes/no), last health check result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new family instance can be configured (config file + env vars) and deployed in under 30 minutes by a technical operator, with zero source code modifications.
- **SC-002**: WhatsApp number provisioning and webhook setup can be completed in under 1 business day per client (down from current multi-day manual process).
- **SC-003**: The health check endpoint accurately reports the status of all integrations within 10 seconds of being called.
- **SC-004**: At least 2 prospective clients express willingness to pay the proposed personal tier price in validation interviews.
- **SC-005**: Per-client infrastructure cost stays under $30/month, achieving at least 65% gross margin on the personal tier.
- **SC-006**: The system correctly reflects a configured family's identity in 100% of system prompts and tool outputs with no references to the template family's details.

## Clarifications

### Session 2026-03-09

- Q: What is the client data isolation model — single-tenant (separate deployment per client), multi-tenant (shared deployment), or hybrid? → A: Single-tenant — each client gets a fully separate deployment (own Railway service, own data, own config).
- Q: Can the service operator (Jason) access client family data for support/debugging? → A: Operator access requires per-incident client consent before viewing any client data.
- Q: What integrations are required for a minimum viable client instance? → A: Only WhatsApp + AI API key. All other integrations (Notion, Google Calendar, YNAB, AnyList) are optional and added incrementally.
- Q: What is explicitly out of scope for this feature? → A: Billing automation, self-service client portal, and multi-region deployment are out of scope. In scope: config externalization, health check, onboarding docs, pricing docs.

## Assumptions

- The first 10 clients will use Meta's Direct Cloud API; migration to a Business Solution Provider (e.g., Twilio ISV) will happen as volume grows beyond 10.
- White-glove onboarding will be performed by Jason (Sierra Code Co) for initial clients, so the setup process does not need to be fully self-service yet — just documented and repeatable.
- Railway is the target cloud platform for client deployments; the existing deployment configuration and Docker setup will be reused.
- Pricing research indicates: personal tier at $79-99/month with $499-999 setup fee; corporate tier at custom pricing starting $149/month per family with volume discounts. These are starting points subject to market validation.
- Per-client infrastructure cost breakdown: cloud hosting ($5-7/mo), WhatsApp conversations ($5-15/mo), AI API usage ($2-5/mo), minor storage ($0-1/mo) = $12-28/month total.
- Meta's January 2026 policy update prohibits general-purpose AI chatbots on WhatsApp. The service must be positioned as a structured family management tool where AI assists with specific tasks (calendar, grocery, budget) rather than open-ended chat.
- Competitive landscape: human virtual assistants charge $380-3,000/month; AI family tools like OpenClaw are self-hosted at $19-25/month (BYOK); chatbot development agencies charge $2,500-7,500 for setup. This service fills the gap between DIY and full-price VA.
