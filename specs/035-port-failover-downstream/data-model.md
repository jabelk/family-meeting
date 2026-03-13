# Data Model: Port AI Failover & Resilience

## Entities

### AI Provider Abstraction (SCC: `src/services/ai_provider.py`)

Centralized module managing provider selection and format conversion.

**Fields/Constants**:
- `PRIMARY_TIMEOUT`: float — seconds before failover (45.0)
- `BACKUP_TIMEOUT`: float — seconds for backup attempt (30.0)
- `PRIMARY_MODEL`: str — Claude model identifier (from config)
- `BACKUP_MODEL`: str — OpenAI model identifier (from config)

**Public functions** (5, matching claude_svc.py signatures):
- `classify_intent(message, conversation_history, active_jobs) → dict`
- `parse_receipt(image_data, media_type) → dict`
- `generate_social_caption(photo_data, media_type, context) → str`
- `generate_paired_caption(before_data, after_data, media_type, context) → str`
- `suggest_category(vendor, line_items, available_categories) → dict`

**Internal converters**:
- `_convert_tool_for_openai(tool_def) → dict` — Anthropic tool → OpenAI function
- `_convert_tool_choice_for_openai(tool_choice) → str|dict` — forced tool mapping
- `_convert_image_for_openai(image_block) → dict` — base64 source → data URI
- `_convert_messages_for_openai(system, messages) → list[dict]` — full message conversion

**Exception**:
- `AllProvidersDownError(Exception)` — raised when both providers fail

### Configuration Extension (SCC: `src/config.py`)

New environment variables:
- `OPENAI_API_KEY`: str — backup provider API key (optional)
- `OPENAI_MODEL`: str — backup model, default `gpt-4o-mini`

### Resilience Prompts (SCC: `src/prompts/system/05-resilience.md`)

New system prompt section with rules:
- Error transparency: always mention tool failures to the user
- Diagnostic specificity: name the service and suggest actionable steps
- Never present a failed action as successful

### Template Scaffolding (speckit-template)

Template versions of the above with `{{PLACEHOLDER}}` syntax:
- `src/services/ai_provider.py` — 2 example functions, all converters, customization comments
- `src/prompts/system/05-resilience.md` — template rules with `{{BUSINESS_NAME}}`

## Relationships

```
config.py (env vars) ─────→ ai_provider.py (uses keys + model names)
claude_svc.py ─────────────→ ai_provider.py (delegates all AI calls)
router_svc.py ─────────────→ ai_provider.py (catches AllProvidersDownError)
router_svc.py ─────────────→ _build_fallback_message() (both-down UX)
health_svc.py ──────────────→ ai_provider.py (checks backup availability)
05-resilience.md ──────────→ loaded by prompt system at startup
```

## State Transitions

No new database entities. The failover is stateless — each request independently tries Claude then OpenAI. The existing `pending_actions` table in SCC is unaffected.

Provider selection per request:
```
START → Try Claude → SUCCESS → Return (provider="claude")
                   → FAIL (500/529/timeout) → Try OpenAI → SUCCESS → Return (provider="openai")
                                                         → FAIL → Raise AllProvidersDownError
```
