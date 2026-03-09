# Quickstart: Prompt Externalization

## Verification Scenarios

### Scenario 1: System Prompt Loads from Files

1. Start the application
2. Send a WhatsApp message to Mom Bot
3. Verify the assistant responds normally (identity, rules, formatting all intact)
4. Check logs: no startup errors about missing prompt files

**Expected**: Behavior identical to pre-migration. No user-visible changes.

### Scenario 2: Edit a System Prompt Section

1. Open `src/prompts/system/02-response-rules.md`
2. Add a new rule: "Always end responses with a fun fact about Reno."
3. Restart the application
4. Send a message to Mom Bot
5. Verify the response includes a Reno fun fact

**Expected**: New rule is followed. Git diff shows only the Markdown file change.

### Scenario 3: Edit a Tool Description

1. Open `src/prompts/tools/calendar.md`
2. Change the description of `get_calendar_events` (e.g., add "Returns events in chronological order")
3. Restart the application
4. Ask Mom Bot about upcoming events
5. Verify Claude uses the tool correctly

**Expected**: Tool still works. Description change is reflected in API calls.

### Scenario 4: Missing System Prompt File

1. Rename `src/prompts/system/01-identity.md` to `01-identity.md.bak`
2. Attempt to start the application
3. Verify the app fails immediately with a clear error naming the missing file

**Expected**: Startup failure with message like "Missing required prompt file: src/prompts/system/01-identity.md"

### Scenario 5: Missing Tool Description (Non-Fatal)

1. Delete the `## get_help` section from `src/prompts/tools/proactive.md`
2. Restart the application
3. Verify the app starts with a warning log
4. Verify `get_help` tool still works (falls back to tool name as description)

**Expected**: Warning logged, app continues, tool works with degraded description.

### Scenario 6: Template Rendering

1. Trigger an Amazon sync (or simulate one)
2. Verify the classification prompt is loaded from `src/prompts/templates/amazon_classification.md`
3. Verify dynamic values (categories, item title, price) are injected correctly
4. Verify categorization works as before

**Expected**: Same categorization behavior. Template loaded from file, not inline string.

### Scenario 7: CI Pipeline Passes

1. Push the prompt externalization changes to a branch
2. Open a PR
3. Verify all CI checks pass (lint, test, security, gate)

**Expected**: No regressions. Ruff passes on new `src/prompts.py`. Tests pass.

### Scenario 8: Prompt-Only PR Diff

1. Create a branch with only a prompt text change (e.g., reword a rule in `05-chores-nudges.md`)
2. Open a PR
3. Review the diff

**Expected**: Diff contains only Markdown text changes. No Python files modified.
