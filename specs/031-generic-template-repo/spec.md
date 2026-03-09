# Feature Specification: Generic Template Repository

**Feature Branch**: `031-generic-template-repo`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "generic template repo"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Eliminate Remaining Hardcoded Family References (Priority: P1)

A new operator clones the template repo and configures their family via `config/family.yaml` and `.env`. When they start the system, all response messages, tool outputs, default values, and sync routing reflect their configured family — not the original developer's family. No source code contains hardcoded names (Jason, Erin, Vienna, Zoey), locations (Reno), or store preferences (Whole Foods) outside of configuration files and historical documentation.

**Why this priority**: Features 028 and 030 externalized system prompts and tool descriptions via placeholders, but ~10 hardcoded references remain in Python source code (response messages, default function parameters, sync routing). These cause a new operator's assistant to reference the wrong family names in specific scenarios, making the deployment feel broken.

**Independent Test**: Clone the repo, configure `family.yaml` with a completely different family (e.g., "The Smith Family" in Portland with "New Seasons" as their grocery store). Start the system. Trigger every tool that currently has hardcoded names (drive times, outlook, chores, notion assignee, sync routing). Verify zero references to the original family appear in any response.

**Acceptance Scenarios**:

1. **Given** a configured instance with Partner1="Alex" and Partner2="Jordan", **When** the user asks about drive times and none are stored, **Then** the response says "Jordan can add them" (not "Erin can add them").
2. **Given** a configured instance with Partner1="Alex", **When** work calendar events are retrieved, **Then** responses say "Alex has no work meetings" or "Alex's work meetings" (not "Jason's").
3. **Given** a configured instance, **When** Amazon/email sync processes pending transactions, **Then** the detailed review message is sent to the configured Partner2 (not hardcoded to Erin's phone number).
4. **Given** a configured instance with Partner2="Jordan", **When** the chore scheduling tool runs, **Then** it references "Jordan's day" in descriptions and uses the configured partner name as the default assignee for backlog items.

---

### User Story 2 - Remove Default Config Fallback (Priority: P1)

When an operator deploys without creating a `family.yaml`, the system fails fast with a clear error message directing them to set up configuration — rather than silently falling back to the original developer's family details. This prevents accidental deployments that reference the wrong family.

**Why this priority**: The current `_DEFAULT_CONFIG` fallback means a misconfigured deployment silently uses the original family's names and details, which is confusing and potentially privacy-violating. Fail-fast is essential for template safety.

**Independent Test**: Start the system without a `family.yaml` file. Verify it exits immediately with an error message pointing to `config/family.yaml.example`.

**Acceptance Scenarios**:

1. **Given** a deployment without `config/family.yaml`, **When** the application starts, **Then** it fails immediately with an error message: "Missing config/family.yaml — copy config/family.yaml.example and fill in your family's details."
2. **Given** a deployment with a `family.yaml` that is missing required fields (e.g., no partner names), **When** the application starts, **Then** it fails with a specific error listing the missing required fields.
3. **Given** the existing personal deployment (Jason & Erin) with a properly configured `family.yaml`, **When** the application starts, **Then** it works exactly as before (no regression).

---

### User Story 3 - Create Separate GitHub Template Repository (Priority: P2)

A clean GitHub template repository exists that any operator can use via "Use this template" on GitHub. The template contains all source code, configuration examples, documentation, CI/CD workflows, and Docker setup — but none of the original family's data, specs, memory files, or conversation archives. The README is rewritten as a product README for new operators.

**Why this priority**: The existing `family-meeting` repo remains Jason & Erin's personal instance. A separate template repo provides a clean starting point without exposing personal data or cluttering new deployments with 30 historical feature specs.

**Independent Test**: Click "Use this template" on GitHub, clone the new repo, fill in `family.yaml` and `.env`, deploy to Railway, and exchange a WhatsApp message — all following only the template repo's README and ONBOARDING.md.

**Acceptance Scenarios**:

1. **Given** the template repository on GitHub, **When** an operator clicks "Use this template", **Then** they get a clean repo with source code, config examples, docs, and CI/CD — but no `specs/`, `memory/`, `data/conversation_archives/`, or `.claude/` directories.
2. **Given** the template repo README, **When** a new operator reads it, **Then** they understand what the product does, what integrations are available, and how to get started — with no references to "MomBot", "Jason", "Erin", or "Sierra Story Co".
3. **Given** the template repo, **When** an operator searches all files for original family names, **Then** zero results are found (excluding git history).

---

### User Story 4 - Genericize Documentation (Priority: P2)

All user-facing documentation (README, ONBOARDING.md, WHATSAPP_SETUP.md, PRICING.md) uses generic language and placeholder references instead of original family-specific details. URLs like `mombot.sierrastoryco.com` are replaced with placeholders or instructions for the operator to configure their own domain.

**Why this priority**: Documentation with hardcoded personal details (phone numbers, domain names, family references) confuses new operators and leaks personal information. Must be generic for the template repo.

**Independent Test**: Read through all documentation files and verify zero references to the original family's personal details (names, phone numbers, domain, company name).

**Acceptance Scenarios**:

1. **Given** the ONBOARDING.md in the template repo, **When** an operator follows it, **Then** all examples use generic placeholders (e.g., "your-domain.com", "Partner 1", "Partner 2") and instructions reference configurable values.
2. **Given** the README.md in the template repo, **When** a prospective operator reads it, **Then** they see a product description, feature list, architecture overview, and quick start — with no original family references.
3. **Given** `docs/ios-shortcut-setup.md`, **When** an operator follows it, **Then** URLs reference `<your-domain>` instead of hardcoded domains.

---

### Out of Scope

- Automated repo sync between personal instance and template (manual cherry-pick process)
- GitHub Marketplace or Railway template marketplace listing
- Multi-tenant architecture changes
- New features or integrations — this is purely about making the existing codebase generic
- Rewriting CLAUDE.md from scratch — the template version is derived from the existing one with personal references removed and generic language substituted

### Edge Cases

- What happens when an operator's `family.yaml` has only one partner (single parent)? Both partners are required fields; validation rejects configs with a missing partner2. Single-parent support is deferred to a future feature.
- What happens when the Docker service is named `n8n-mombot`? Template repo should use a generic service name.
- What happens when CI/CD workflows reference the original repo's GHCR path? Workflows should use `github.repository` variables so they automatically adapt.
- What happens when a tool's input schema has example values with hardcoded names? New operators see confusing examples that reference the wrong family.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All Python source files MUST use configuration-driven values (from `family_config`) for family member names, locations, store names, and preferences in any user-facing output — no hardcoded family references in response messages, default parameters, or routing logic.
- **FR-002**: The system MUST fail fast on startup if `config/family.yaml` is missing or lacks required fields, with an actionable error message. The `_DEFAULT_CONFIG` fallback MUST be removed.
- **FR-003**: Tool input schema examples and descriptions in the assistant MUST use placeholder values derived from family config rather than hardcoded names.
- **FR-004**: Sync message routing (Amazon sync, email sync) MUST send messages to the configured partner phone number, not a hardcoded number.
- **FR-005**: A separate GitHub template repository MUST be created containing all source code, config examples, generic documentation, CI/CD workflows, Docker configuration, and the `.specify/` speckit development framework (including `.claude/commands/speckit.*`) — excluding personal data, specs, memory, conversation archives, and operator-specific business documents (PRICING.md, SERVICE_AGREEMENT.md).
- **FR-006**: The template repo README MUST describe the product generically: what it does, available integrations, architecture overview, and quick start guide.
- **FR-007**: All documentation files in the template repo MUST use generic placeholders instead of original family-specific details (names, phone numbers, domains, company names).
- **FR-008**: Docker Compose service names MUST be generic (no product-specific branding like "mombot").
- **FR-009**: CI/CD workflows MUST use dynamic variables (e.g., `github.repository`) so they work in any fork without modification.
- **FR-010**: The template repo MUST include a `.gitignore` that excludes runtime data files, conversation archives, and user-specific memory/config files.
- **FR-011**: All comments and docstrings in Python source files MUST use generic role-based references ("Partner 1", "Partner 2") instead of specific family member names. This applies across the entire codebase, not just user-facing code paths.
- **FR-012**: The template repo MUST include a generic CLAUDE.md that documents the project architecture, development workflow, conventions, and deployment — with no references to the original family, domain, or company. The CLAUDE.md serves as the AI coding assistant's project guide for operators who use Claude Code.

### Key Entities

- **Template Repository**: A GitHub template repo that serves as the clean starting point for new operator deployments. Contains source code, config examples, generic docs, CI/CD, and Docker setup. Excludes personal data and historical artifacts.
- **Personal Instance Repository**: The existing `family-meeting` repo, which remains Jason & Erin's active deployment. Receives the hardcoded-reference fixes (US1, US2) but retains specs, memory, and personal docs.
- **Hardcoded Reference**: Any source code string literal that contains a specific family member's name, location, phone number, or preference where a config-driven value should be used instead.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A search for hardcoded family names (Jason, Erin, Vienna, Zoey, Reno, Whole Foods) across all Python source files returns zero results (excluding imports, config example files, and test fixtures).
- **SC-002**: The system starts successfully with a test family config containing completely different names and produces correct personalized output for all tools.
- **SC-003**: The system fails fast with a clear error when `family.yaml` is missing — no silent fallback to default values.
- **SC-004**: The template repository contains zero references to the original family in any non-git-history file.
- **SC-005**: A new operator can go from "Use this template" to first WhatsApp message in under 30 minutes (excluding Meta Business verification wait time), following only the template repo's documentation.
- **SC-006**: All CI/CD workflows in the template repo pass without modification when run in a new GitHub repository.

## Clarifications

### Session 2026-03-09

- Q: Should single-parent households be supported (partner2 optional)? → A: No. Both partners are required fields. Target household is a couple (typically one working partner, one managing home/kids and possibly also working). Single-parent support is a future feature.
- Q: Should PRICING.md and SERVICE_AGREEMENT.md ship in the template repo? → A: No. Exclude business docs entirely — operators create their own. Template focuses on technical setup only.
- Q: Should the `.specify/` speckit framework be included in the template repo? → A: Yes. Include `.specify/` and `.claude/commands/speckit.*` so operators can use speckit for their own feature development.

## Assumptions

- The existing `family-meeting` repo stays as Jason & Erin's personal active deployment — it is not converted to a template itself.
- The template repo is created under the same GitHub account (jabelk) or organization.
- Git history is not preserved in the template repo (fresh init with a single initial commit from the cleaned source).
- Cherry-picking updates from the personal repo to the template is a manual process for now.
- The ~10 hardcoded references identified in the codebase audit are the complete set; no additional ones exist in less-commonly-triggered code paths (to be verified during implementation).
- The existing test suite (`pytest tests/`) continues to pass after all changes, potentially with test fixtures updated to use a test family config.
