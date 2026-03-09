# Quickstart: Template Repo Readiness

## Test Scenarios

### Scenario 1: Config Loading & Validation

**Setup**: Create `config/family.yaml` with a test family

```yaml
bot:
  name: "Test Bot"
family:
  name: "The Test Family"
  timezone: "America/New_York"
  partners:
    - name: "Alice"
    - name: "Bob"
  children:
    - name: "Charlie"
      age: 7
preferences:
  grocery_store: "Trader Joe's"
```

**Test**:
```bash
python3 -c "
from src.family_config import load_family_config
cfg = load_family_config()
assert cfg['bot_name'] == 'Test Bot'
assert cfg['partner1_name'] == 'Alice'
assert cfg['partner2_name'] == 'Bob'
assert cfg['grocery_store'] == \"Trader Joe's\"
assert cfg['child1_name'] == 'Charlie'
print('Config loading: PASS')
"
```

**Expected**: All assertions pass, config loads without errors.

### Scenario 2: Config Validation — Missing Required Fields

**Setup**: Create `config/family.yaml` missing `bot.name`

```yaml
family:
  name: "Test"
  timezone: "America/New_York"
  partners:
    - name: "Alice"
```

**Test**:
```bash
python3 -c "
from src.family_config import load_family_config
try:
    cfg = load_family_config()
    print('FAIL: should have raised error')
except ValueError as e:
    assert 'bot.name' in str(e) or 'bot' in str(e)
    print(f'Validation error: {e}')
    print('Config validation: PASS')
"
```

**Expected**: `ValueError` raised mentioning missing bot name.

### Scenario 3: System Prompt Rendering

**Setup**: Config from Scenario 1 loaded.

**Test**:
```bash
python3 -c "
from src.family_config import load_family_config
from src.prompts import render_system_prompt
cfg = load_family_config()
prompt = render_system_prompt(cfg)
assert 'Alice' in prompt, 'Partner 1 name not in prompt'
assert 'Bob' in prompt, 'Partner 2 name not in prompt'
assert 'Charlie' in prompt, 'Child name not in prompt'
assert 'Test Bot' in prompt, 'Bot name not in prompt'
assert 'Jason' not in prompt, 'Hardcoded name still present'
assert 'Erin' not in prompt, 'Hardcoded name still present'
print('System prompt rendering: PASS')
"
```

**Expected**: All placeholder values replaced, no hardcoded names remain.

### Scenario 4: Health Check — All Integrations

**Setup**: App running with full `.env` configuration.

**Test**:
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

**Expected**: JSON response with `"status": "healthy"` or `"degraded"`, each integration listed with configured/connected status.

### Scenario 5: Health Check — Minimal Config

**Setup**: App running with only ANTHROPIC_API_KEY and WHATSAPP_* env vars.

**Test**:
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

**Expected**: `"status": "healthy"`, required integrations show `"connected": true`, optional integrations show `"configured": false`.

### Scenario 6: No-Kids Config

**Setup**: Create config with no children:

```yaml
bot:
  name: "Home Helper"
family:
  name: "The Duo"
  timezone: "US/Eastern"
  partners:
    - name: "Sam"
    - name: "Pat"
preferences:
  grocery_store: "Costco"
```

**Test**:
```bash
python3 -c "
from src.family_config import load_family_config
from src.prompts import render_system_prompt
cfg = load_family_config()
prompt = render_system_prompt(cfg)
assert 'children' not in prompt.lower() or 'no children' in prompt.lower(), 'Prompt references children when none configured'
assert cfg['children_summary'] == ''
print('No-kids config: PASS')
"
```

**Expected**: System prompt doesn't reference children-specific features.

### Scenario 7: Tool Descriptions Rendered

**Test**:
```bash
python3 -c "
from src.family_config import load_family_config
from src.prompts import render_tool_descriptions
cfg = load_family_config()
descs = render_tool_descriptions(cfg)
# Check grocery tool mentions configured store
anylist_desc = descs.get('push_grocery_list', '')
assert 'Trader' in anylist_desc or cfg['grocery_store'] in anylist_desc, 'Grocery store not in tool description'
print('Tool descriptions: PASS')
"
```

### Scenario 8: Backward Compatibility — Existing Tests Pass

**Test**:
```bash
pytest tests/ -v
```

**Expected**: All existing tests continue to pass with the Jason/Erin family config in place.
