# Feature Specification: Port AI Failover & Resilience to Downstream Repos

**Feature Branch**: `035-port-failover-downstream`
**Created**: 2026-03-13
**Status**: Draft
**Input**: User description: "Refactor downstream repos (claude-speckit-template and client-scc-tom-construction) to incorporate AI failover & resilience patterns from family-meeting feature 034."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - SCC App: Backup AI Provider Failover (Priority: P1)

When Claude is unavailable (500/529/timeout), Tom's construction bookkeeper bot should automatically switch to a backup AI provider so Tom still gets responses for intent classification, receipt parsing, and social caption generation. Today, if Claude goes down, the bot falls back to keyword-only commands with no AI capability — Tom can only approve/reject pending actions.

**Why this priority**: Tom relies on the bot for daily bookkeeping. A Claude outage means no receipt parsing, no intent classification, and no social media posts — core revenue-impacting features go offline.

**Independent Test**: Simulate a Claude API failure in the SCC app, verify that intent classification, receipt parsing, and caption generation all respond via the backup provider.

**Acceptance Scenarios**:

1. **Given** Claude API returns a 529 overloaded error, **When** Tom sends a text message with a receipt photo, **Then** the receipt is parsed via the backup provider and Tom receives a confirmation prompt as normal.
2. **Given** Claude API times out after the configured threshold, **When** Tom sends a text describing an expense, **Then** intent classification happens via the backup provider and the expense flow proceeds normally.
3. **Given** both Claude and the backup provider are unavailable, **When** Tom sends any message, **Then** the bot sends a static fallback message explaining the issue and listing keyword commands still available.
4. **Given** Claude is available, **When** Tom sends a message, **Then** the primary provider handles it with no change in behavior or latency.

---

### User Story 2 - Template Repo: Resilience Scaffolding for New Projects (Priority: P2)

When a developer scaffolds a new project from the claude-speckit-template, the project should include ready-to-customize patterns for AI failover, tool result auditing, and resilience prompts — so every new project starts with resilience built in rather than bolting it on later.

**Why this priority**: The template is the starting point for all new client projects. Including resilience patterns from day one prevents the same technical debt from accumulating in every downstream project.

**Independent Test**: Fork the template, verify that the resilience scaffolding files exist with clear customization instructions, and confirm placeholder patterns match the family-meeting reference implementation.

**Acceptance Scenarios**:

1. **Given** a developer creates a new project from the template, **When** they review the project structure, **Then** they find a template AI provider module with failover patterns and customization comments.
2. **Given** a developer creates a new project from the template, **When** they review the prompt directory structure, **Then** they find a resilience prompt template for lost message detection and error surfacing rules.
3. **Given** a developer creates a new project from the template, **When** they review CLAUDE.md, **Then** the active technologies section documents the backup AI provider pattern and the resilience architecture.

---

### User Story 3 - SCC App: Tool Result Auditing & Error Surfacing (Priority: P2)

When a tool call in the SCC app fails (QuickBooks API error, Twilio send failure, Ayrshare posting error), the bot should detect the error and inform Tom explicitly — never presenting a failed action as successful or silently swallowing the error.

**Why this priority**: Silent tool failures in a financial bookkeeping app can lead to missing expense records, duplicate invoices, or lost receipts — directly impacting Tom's business finances.

**Independent Test**: Simulate a QuickBooks API failure during expense creation, verify the bot tells Tom the expense was not recorded and suggests next steps.

**Acceptance Scenarios**:

1. **Given** QuickBooks API returns an error during expense creation, **When** Tom is waiting for confirmation, **Then** the bot explicitly tells Tom the expense was not recorded and suggests retrying or manually entering it.
2. **Given** Twilio fails to send a response SMS, **When** any handler tries to reply, **Then** the failure is logged with diagnostic context.
3. **Given** Ayrshare returns an error during social media posting, **When** Tom sent a photo to post, **Then** the bot tells Tom the post failed and why.

---

### User Story 4 - SCC App: Resilience Prompt Rules (Priority: P3)

The SCC bot should include prompt-level rules for error reporting and diagnostic transparency — ensuring Claude always mentions failures to Tom and provides actionable guidance rather than vague error messages.

**Why this priority**: Prompt rules are low-effort, high-impact improvements that complement the code-level changes in US1 and US3.

**Independent Test**: Verify the SCC system prompts include rules about error reporting, and test that Claude references specific error details when a tool failure occurs.

**Acceptance Scenarios**:

1. **Given** a tool result contains an error indicator, **When** Claude generates a response, **Then** the response mentions the specific failure and provides actionable guidance.
2. **Given** an external service is unavailable, **When** Claude generates a response, **Then** the response names the specific service and suggests what Tom can do.

---

### Edge Cases

- What happens when the backup provider's vision call fails? The system converts image formats and always attempts vision on the backup; if it still fails, the user receives a specific error message explaining the image could not be processed and to try again later.
- What happens when the backup provider returns a different tool call format than expected for forced tool_choice patterns?
- How does the template handle projects that don't use AI at all? (Template resilience patterns should be opt-in, not mandatory)
- What happens when the SCC app is mid-conversation and fails over? (Conversation context must be preserved across providers)
- What happens when the backup provider's category suggestion differs from what QuickBooks expects?

## Clarifications

### Session 2026-03-13

- Q: Should the SCC app get a new centralized `ai_provider.py` module (Option A), wrap failover inline in existing functions (Option B), or use a client factory (Option C)? → A: Option A — New centralized `ai_provider.py` module. This supports multi-client reuse: one portable module per project, single place to add providers/change config, and new AI functions don't need failover boilerplate.
- Q: When vision-based functions (receipt parsing, caption generation) fail over to the backup provider, should vision be attempted, skipped, or degraded to text-only? → A: Option A — Always attempt vision on backup provider with image format conversion. Fail gracefully with an error message if vision specifically fails.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The SCC app MUST attempt the backup AI provider when Claude returns HTTP 500, 529, or times out — matching the family-meeting failover trigger conditions.
- **FR-002**: The SCC app's backup provider MUST support all four Claude call patterns: intent classification (forced tool use), receipt parsing (vision + forced tool use), social caption generation (vision + forced tool use), and category suggestion (text completion).
- **FR-003**: The SCC app MUST send a static fallback message listing keyword commands when both AI providers are unavailable, preserving the existing `_build_fallback_message()` behavior.
- **FR-004**: The SCC app MUST add error detection that identifies failure indicators in service call results (QuickBooks errors, Twilio failures, Ayrshare errors) and surfaces them in responses to the user.
- **FR-005**: The SCC app MUST add prompt rules for error transparency — the AI must mention failures and provide specific diagnostic context rather than vague messages.
- **FR-006**: The template repo MUST include a scaffolding file for AI provider failover with clear customization comments and placeholder patterns.
- **FR-007**: The template repo MUST include a resilience prompt template in the system prompts directory.
- **FR-008**: The template repo MUST update CLAUDE.md to document the resilience architecture patterns.
- **FR-009**: All changes to the SCC app MUST pass the existing test suite with no regressions.
- **FR-010**: The SCC app MUST introduce a new centralized `ai_provider.py` module that encapsulates all provider selection, format conversion, and failover logic. Existing `claude_svc.py` functions MUST be refactored to route through this module. The module MUST be designed for portability across client projects — one file to copy, single place to configure providers, models, and timeouts.

### Key Entities

- **AI Provider Abstraction**: Centralized module managing primary (Claude) and backup provider selection, format conversion, and failover logic — adapted to each repo's architecture.
- **Tool Result Audit**: Error detection layer that inspects service call results for failure indicators and prepends warning context before passing to the AI.
- **Resilience Prompts**: System-level prompt rules that instruct the AI to surface errors, provide diagnostic context, and never present failures as successes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The SCC app continues to respond to user messages within 60 seconds even when Claude is completely unavailable — verified by simulating Claude outage and measuring response time.
- **SC-002**: 100% of tool/service failures in the SCC app are surfaced to the user with a specific error description — verified by simulating failures for each integration (QBO, Twilio, Ayrshare) and checking response text.
- **SC-003**: New projects created from the template include resilience scaffolding files — verified by creating a test project and checking for the expected files.
- **SC-004**: All existing tests in both repos continue to pass after changes — zero regressions.
- **SC-005**: The SCC app's forced tool_choice patterns work correctly with the backup provider — verified by running each AI function (classify, parse, caption, suggest) against the backup.

## Assumptions

- The backup AI provider for the SCC app will be OpenAI GPT (same as family-meeting), since it has the broadest tool-use and vision support.
- The SCC app's forced `tool_choice` pattern will be adapted to OpenAI's equivalent (`tool_choice: {"type": "function", "function": {"name": "..."}}` or similar).
- The template repo changes are documentation/scaffolding only — no production code runs in the template.
- The SCC app uses `claude-haiku-4-5-20251001` as its model; the backup will be `gpt-4o-mini` (matching family-meeting's choice).
- Vision-based functions (receipt parsing, caption generation) will need special handling since OpenAI uses a different image input format than Anthropic.
- The SCC app's existing `_build_fallback_message()` in router_svc.py provides the both-providers-down user experience and should be preserved.
