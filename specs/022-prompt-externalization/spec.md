# Feature Specification: Prompt Externalization

**Feature Branch**: `022-prompt-externalization`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Move prompts from string literals to external files (GitHub issue #31)"

## Overview

The family assistant's prompts — system prompt (~375 lines), 50+ tool descriptions (~2,000 lines), and 8 LLM classification/generation prompts — are currently embedded as Python string literals. This makes prompt changes indistinguishable from code changes, prevents non-developers from reviewing or suggesting prompt improvements, and couples prompt engineering to application deployments.

This feature separates prompt content from application logic by moving prompts to external files, loaded at startup. The result: prompt changes produce clean diffs, can be reviewed independently, and are editable without understanding Python.

## Clarifications

### Session 2026-03-08

- Q: Should the system prompt be one monolithic file or split into composable sections? → A: Composable sections (~6-8 files like `identity.md`, `rules.md`, `daily_planner.md`) assembled in a defined order at startup.
- Q: Should tool definitions use YAML (descriptions + schemas) or Markdown (descriptions only, schemas stay in code)? → A: Descriptions in Markdown, parameter schemas stay in Python. Only prompt text is externalized; structured schema data remains as code.

## User Scenarios & Testing

### User Story 1 - System Prompt Externalization (Priority: P1)

A developer (Jason) wants to tweak the assistant's personality rules or add a new behavioral rule. Currently he must edit a 375-line Python string in `src/assistant.py`, mentally parsing escape characters, indentation, and surrounding code. Instead, the system prompt is split into ~6-8 composable section files (e.g., identity, rules, daily planner, calendar, tool guidance). He opens the relevant section file, edits plain text, and commits. The diff clearly shows what changed in that specific section without any Python noise or unrelated prompt sections.

**Why this priority**: The system prompt is the single largest prompt (~375 lines) and changes most frequently (new rules added with almost every feature). Externalizing it delivers the most immediate value.

**Independent Test**: Edit the externalized system prompt file (e.g., add a new rule), restart the app, and verify the assistant follows the new rule. The git diff should show only the prompt text change, not Python code changes.

**Acceptance Scenarios**:

1. **Given** the system prompt lives in an external file, **When** a developer adds a new behavioral rule to the file and restarts the app, **Then** the assistant follows the new rule in subsequent conversations.
2. **Given** the system prompt is externalized, **When** a developer reviews a PR that changes the prompt, **Then** the diff shows only natural-language prompt text, not Python string syntax or surrounding code.
3. **Given** the system prompt file is missing or empty, **When** the app starts, **Then** it fails fast with a clear error message identifying the missing file.

---

### User Story 2 - Tool Description Externalization (Priority: P2)

A developer wants to improve a tool's description so Claude uses it more accurately. Currently, tool descriptions are embedded in a 2,000+ line Python array in `src/assistant.py`. Finding and editing the right description requires scrolling through dense Python dict/list syntax. Instead, tool description text lives in external Markdown files organized by module, while parameter schemas (names, types, required fields) remain in Python code. This makes descriptions easy to find, edit, and review without disrupting the structural schema definitions.

**Why this priority**: Tool descriptions are the second-largest body of prompt text and directly affect how well the assistant selects and uses tools. However, they change less frequently than the system prompt.

**Independent Test**: Edit a tool's description in its external file, restart the app, and verify Claude receives the updated description. Confirm the TOOLS array is correctly assembled from external files at startup.

**Acceptance Scenarios**:

1. **Given** tool descriptions are stored externally, **When** a developer edits a tool's description and restarts, **Then** Claude receives the updated description in subsequent API calls.
2. **Given** tool descriptions are externalized, **When** a new tool is added to the codebase, **Then** the developer adds the description to the appropriate external file (not inline in Python).
3. **Given** tool descriptions are loaded at startup, **When** a referenced tool description is missing, **Then** the app logs a warning and uses a fallback (tool name as description) rather than crashing.

---

### User Story 3 - LLM Classification Prompt Externalization (Priority: P3)

A developer wants to improve the Amazon item categorization prompt or the email parsing prompt. Currently these are f-string templates scattered across 5 different Python files. Instead, the template text lives in external files with clear placeholder markers, and dynamic values are injected at runtime.

**Why this priority**: These prompts are smaller (3-20 lines each), change infrequently, and use dynamic templating — making them more complex to externalize. The value is primarily organizational rather than urgent.

**Independent Test**: Edit a classification prompt template externally, restart the app, and verify the updated prompt is used when classifying an Amazon item or parsing an email.

**Acceptance Scenarios**:

1. **Given** classification prompts are stored externally with placeholder syntax, **When** the app processes an Amazon order, **Then** the prompt template is loaded, dynamic values are injected, and categorization works correctly.
2. **Given** a classification prompt template has invalid placeholders, **When** the app attempts to use it, **Then** a clear error is raised identifying the missing placeholder.

---

### Edge Cases

- What happens when a prompt file is missing at startup? The app should fail fast with a clear error for critical prompts (system prompt) and log warnings for non-critical ones (individual tool descriptions).
- What happens when a prompt file contains invalid encoding? The loader should enforce UTF-8 and raise a clear error.
- What happens when a prompt template references a placeholder that isn't provided at runtime? The app should raise an error rather than silently producing a broken prompt.
- How are prompts loaded in test environments? Tests should be able to override prompt files or use test-specific prompts without modifying production files.

## Requirements

### Functional Requirements

- **FR-001**: System MUST load the system prompt from composable section files (~6-8 files such as identity, rules, daily planner, calendar, tool guidance) and assemble them in a defined order at startup.
- **FR-002**: System MUST load tool description text from external Markdown files and merge them with parameter schemas (which remain in code) to assemble the tool definitions array at startup.
- **FR-003**: System MUST load LLM classification/generation prompt templates from external files and inject dynamic values at runtime.
- **FR-004**: System MUST validate at startup that all required prompt files exist and are non-empty, failing fast with descriptive errors for missing critical files.
- **FR-005**: System MUST preserve all existing assistant behavior — externalization is a refactor with zero functional changes to the user experience.
- **FR-006**: System MUST support simple placeholder substitution in prompt templates (e.g., `{category_list}`, `{item_title}`) for dynamic prompts.
- **FR-007**: System MUST load prompt files once at startup and cache them in memory for the lifetime of the process (no per-request file I/O).
- **FR-008**: System MUST organize prompt files in a dedicated directory structure that groups prompts by function (system prompt, tool descriptions, classification prompts).

### Key Entities

- **Prompt File**: An external text file containing prompt content. Has a name, path, content, and type (system, tool description, or template).
- **Prompt Template**: A prompt file containing placeholders that are filled with dynamic values at runtime. Has a set of required placeholder names.
- **Prompt Registry**: An in-memory collection of loaded prompts, assembled at startup, providing named access to prompt content.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of prompt text (system prompt, tool descriptions, classification prompts) resides in external files, with zero prompt string literals remaining in Python source files.
- **SC-002**: A prompt-only change (e.g., rewording a rule) produces a diff that contains only natural-language text changes — no Python syntax, no import changes, no code structure changes.
- **SC-003**: All existing assistant behaviors are preserved — the assistant responds identically before and after externalization for the same inputs (verified by running existing tests).
- **SC-004**: A developer can find and edit any prompt in under 30 seconds by navigating the prompt file directory structure.
- **SC-005**: The app fails within 5 seconds of startup if a required prompt file is missing, with an error message that names the missing file.

## Assumptions

- Markdown is the preferred file format for prompt content (aligns with Anthropic's recommendations for XML-tagged, Markdown-structured prompts and requires no new dependencies).
- Simple Python string `.format()` or f-string substitution is sufficient for dynamic prompts — no Jinja2 or templating library is needed given the project's scale (8 dynamic prompts with simple variable injection).
- Prompt files are loaded once at startup and cached; hot-reloading of prompt files during runtime is not needed for a 2-user family assistant.
- The existing test suite (smoke tests + CI pipeline) is sufficient to verify behavioral equivalence after migration.
- No new Python dependencies are required — the standard library's `pathlib` and string formatting cover all needs.

## Out of Scope

- Prompt versioning or A/B testing infrastructure (can be added later if needed).
- A web UI or admin interface for editing prompts.
- Per-environment prompt overrides (e.g., different prompts for staging vs production).
- Automated prompt quality testing (e.g., Promptfoo integration).
- Hot-reloading of prompt files without restarting the app.
