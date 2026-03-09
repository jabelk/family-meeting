# Quickstart: Testing Feature 030

## Prerequisites
- Working development environment with Python 3.12+
- Valid `.env` file with at least ANTHROPIC_API_KEY and WHATSAPP_* vars
- `config/family.yaml` from example template

## Test Scenarios

### 1. Validation Script (US1, US3)

```bash
# Happy path — full config
python scripts/validate_setup.py
# Expected: "READY TO DEPLOY" with all integrations listed

# Missing required var
# Remove ANTHROPIC_API_KEY from .env, then:
python scripts/validate_setup.py
# Expected: Exit code 1, error message about missing key

# Partial integration
# Set NOTION_TOKEN but remove NOTION_ACTION_ITEMS_DB from .env, then:
python scripts/validate_setup.py
# Expected: Warning about partial Notion configuration
```

### 2. Dynamic Tool Filtering (US2)

```bash
# Start app with minimal config (only WhatsApp + Anthropic)
# Remove all Notion/Calendar/YNAB vars from .env
TESTING=1 python -c "
from src.config import FAMILY_CONFIG
from src.integrations import get_enabled_integrations
enabled = get_enabled_integrations()
print('Enabled:', [i.name for i in enabled])
print('Disabled:', [name for name in ALL_INTEGRATIONS if name not in enabled])
"

# Verify tool count
TESTING=1 python -c "
from src.assistant import TOOLS
print(f'Tools registered: {len(TOOLS)}')
for t in TOOLS:
    print(f'  - {t[\"name\"]}')
"
# Expected: Only core tools (preferences, daily context), no Notion/Calendar/YNAB tools
```

### 3. Health Endpoint (US4)

```bash
# Start app with minimal config
uvicorn src.app:app --host 0.0.0.0 --port 8000 &

# Check health
curl -s http://localhost:8000/health | python3 -m json.tool
# Expected: "status": "healthy" (not "degraded") with unconfigured integrations showing "configured": false
```

### 4. System Prompt Filtering (US2)

```bash
# Verify system prompt sections are filtered
TESTING=1 python -c "
from src.prompts import load_system_prompt
from src.integrations import get_enabled_integrations
enabled = get_enabled_integrations()
prompt = load_system_prompt(enabled_integrations=enabled)
print(f'Prompt length: {len(prompt)} chars')
# Check that Notion/Calendar sections are excluded
assert 'action items' not in prompt.lower() or 'notion' in [i.name for i in enabled]
print('PASS: Prompt correctly filtered')
"
```

### 5. End-to-End (All US)

```bash
# Full deployment with minimal config → send WhatsApp message
# 1. Run validation
python scripts/validate_setup.py

# 2. Start app
uvicorn src.app:app --host 0.0.0.0 --port 8000

# 3. Send test message asking about calendar (not configured)
# Expected: Bot gracefully explains calendar isn't set up

# 4. Add Google Calendar vars to .env, restart
# Expected: Bot now offers calendar features
```
