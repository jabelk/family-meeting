# Contract: validate_setup CLI Command

**Type**: CLI script
**Location**: `scripts/validate_setup.py`

## Usage

```bash
python scripts/validate_setup.py [--env-file .env] [--config-file config/family.yaml]
```

## Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--env-file` | `.env` | Path to the environment file |
| `--config-file` | `config/family.yaml` | Path to the family config file |

## Output Format

Structured text output to stdout. Exit code 0 if all required checks pass, 1 if any required check fails.

### Success Output

```
=== Family Meeting Setup Validation ===

Family Config: config/family.yaml
  ✓ File exists and parses correctly
  ✓ Family name: The Garcia Family
  ✓ Bot name: Home Helper
  ✓ Timezone: America/Chicago (valid)
  ✓ Partners: Maria, Carlos

Environment: .env
  ✓ ANTHROPIC_API_KEY: set (sk-ant-***...)
  ✓ WHATSAPP_PHONE_NUMBER_ID: set
  ✓ WHATSAPP_ACCESS_TOKEN: set
  ✓ WHATSAPP_VERIFY_TOKEN: set
  ✓ WHATSAPP_APP_SECRET: set
  ✓ N8N_WEBHOOK_SECRET: set
  ✓ PARTNER1_PHONE: 15551234567 (valid format)
  ✓ PARTNER2_PHONE: 15552345678 (valid format)

Integrations:
  ✓ Notion: enabled (5/5 env vars set)
  ✓ Google Calendar: enabled (2/2 env vars set)
  ✗ YNAB: disabled (0/2 env vars set)
  ✗ AnyList: disabled (not configured)
  ✗ Outlook: disabled (not configured)
  ✗ Recipes: disabled (0/3 env vars set)

Summary: READY TO DEPLOY
  Required: 8/8 checks passed
  Integrations: 2 enabled, 4 disabled
  Tools available: 23/70
```

### Error Output

```
=== Family Meeting Setup Validation ===

Family Config: config/family.yaml
  ✗ ERROR: Missing required field 'family.partners' (at least one partner required)

Environment: .env
  ✗ ERROR: ANTHROPIC_API_KEY not set
    → Get your API key at https://console.anthropic.com/
  ✗ WARNING: PARTNER1_PHONE format invalid: "+15551234567" (remove + prefix)

Integrations:
  ⚠ Notion: partially configured (3/5 env vars set)
    Missing: NOTION_MEAL_PLANS_DB, NOTION_MEETINGS_DB
    → See: docs/notion-setup.md Step 3

Summary: NOT READY
  Required: 6/8 checks passed (2 errors)
  Fix the errors above before deploying.
```

## Behavior

1. Reads family.yaml — validates structure, required fields, timezone validity
2. Reads .env — checks all required env vars, validates format patterns
3. Cross-references phone numbers between .env and family.yaml partner count
4. Checks each integration group for completeness (all-or-nothing)
5. Reports summary with tool count based on enabled integrations
6. Exit code: 0 = ready, 1 = errors found
