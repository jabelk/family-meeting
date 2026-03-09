# Research: Generic Template Repository

**Feature**: 031-generic-template-repo
**Date**: 2026-03-09

## R1: Complete Inventory of Hardcoded References in Python Source

### Decision
31 hardcoded family references found across 11 Python source files. 3 are critical (runtime output), ~20 are comments/docstrings (must all be updated per FR-011), ~8 are in `_DEFAULT_CONFIG` (removed entirely per FR-002).

### Findings

#### Critical — Runtime Output Strings

| File | Line(s) | Content | Fix |
|------|---------|---------|-----|
| `src/tools/outlook.py` | 110, 130, 164, 184, 189 | `f"Jason has no work meetings..."`, `f"Jason's work meetings on..."` | Use `FAMILY_CONFIG["partner1_name"]` |
| `src/tools/notion.py` | 458, 555 | `assignee: str = "Erin"` default parameter | Default to `FAMILY_CONFIG["partner2_name"]` |
| `src/drive_times.py` | 91 | `"Erin can add them by saying..."` | Use `FAMILY_CONFIG["partner2_name"]` |
| `src/assistant.py` | 1374 | `"Ask Jason to re-run setup_calendar.py on the NUC."` | Use generic error: "Ask the operator to re-run setup_calendar.py" |

#### Medium — Tool Schema Examples (FR-003)

| File | Line(s) | Content | Fix |
|------|---------|---------|-----|
| `src/assistant.py` | 79 | `"'jason', 'erin', 'family'"` in calendar tool enum | Use config-driven calendar names |
| `src/assistant.py` | 129 | `"Who this is assigned to (Jason or Erin)."` | Use `f"Who this is assigned to ({p1} or {p2})."` |
| `src/assistant.py` | 463 | `"'Erin -> Jason: pick up dog'"` | Use `f"'{p2} -> {p1}: pick up dog'"` |
| `src/assistant.py` | 488 | `"'Erin said: remind Jason to pick up the dog'"` | Use `f"'{p2} said: remind {p1} to pick up the dog'"` |
| `src/assistant.py` | 1645 | `"'no Jason appointment reminders'"` | Use `f"'no {p1} appointment reminders'"` |
| `src/tools/discovery.py` | 49, 204 | `"remind Jason to pick up dog at 12:30"` | Use `f"remind {p1} to pick up dog at 12:30"` |

#### Comments & Docstrings (FR-011)

| File | Line(s) | Content |
|------|---------|---------|
| `src/app.py` | 615 | `"""Receive Jason's work calendar events from iOS Shortcut."""` |
| `src/tools/outlook.py` | 135, 193 | `"""Fetch Jason's work calendar events...` / `"""Get Jason's busy windows...` |
| `src/tools/calendar.py` | 346, 350 | `"both Jason and Erin can see it"`, `"Erin → Jason: pick up dog"` |
| `src/tools/chores.py` | 50 | `"""Find free windows in Erin's day...` |
| `src/tools/nudges.py` | 97, 261 | `"""Scan Erin's and family calendars...`, `# Check Erin's preferences` |
| `src/tools/amazon_sync.py` | 36, 41 | `"""A record of Erin correcting...`, `# Erin's adjustment message` |
| `src/context.py` | 276 | `Falls back to "With Erin..."` |
| `src/config.py` | 98 | `# Outlook (optional — Jason's work calendar ICS feed)` |

#### `_DEFAULT_CONFIG` (Removed Entirely)

`src/family_config.py` lines 16-40: Contains Jason, Erin, Vienna, Zoey, Sandy, Belk, Reno, Whole Foods, BSF, Roy Gomm, Gymnastics, Milestones. All removed — system requires `config/family.yaml`.

### Alternatives Considered
- Keep `_DEFAULT_CONFIG` for backward compatibility → Rejected per FR-002 (fail-fast required, prevents accidental wrong-family output).
- Only fix runtime strings, leave comments → Rejected per clarification (user chose Option B: update ALL comments/docstrings).

---

## R2: Sync Message Routing Architecture

### Decision
Sync routing (Amazon sync, email sync) currently hardcodes Erin's phone number via `PARTNER2_PHONE` config. The routing itself is config-driven but some surrounding strings reference names.

### Findings
- `src/assistant.py` lines 1361-1396: Sync messages sent to `PARTNER2_PHONE` — already config-driven via `src/config.py`.
- String literals like `"sent to Erin for review"` need to use `FAMILY_CONFIG["partner2_name"]`.
- Error message `"Ask Jason to re-run setup_calendar.py"` should be generic.

### Rationale
The phone routing is already correct (uses env var). Only the human-readable strings need updating.

---

## R3: Test Suite Impact of Removing `_DEFAULT_CONFIG`

### Decision
Tests are safe. They use their own generic fixtures and do not depend on `_DEFAULT_CONFIG`.

### Findings
- Tests use generic template data (`TestBot`, `The Test Family`, `Alice`, `Bob`, `Charlie`)
- Test fixtures generate fresh config dicts
- No test imports or references `_DEFAULT_CONFIG`
- `pytest tests/` will continue to pass after removal

### Rationale
Feature 028 designed the test suite to be independent of the default config.

---

## R4: Non-Python Files for Template Repo

### Decision
Template repo excludes personal data and business docs. Documentation files need heavy genericization.

### Findings — Files to Genericize

| File | Issue | Action |
|------|-------|--------|
| CLAUDE.md | Family names, URL, NUC details, feature history | Use generic sample from `contracts/CLAUDE.md.sample` |
| ONBOARDING.md | "MomBot" (5 refs) | Replace with generic "Family Assistant" |
| docs/ios-shortcut-setup.md | `mombot.sierrastoryco.com`, "Jason", "Erin" | Use `<your-domain>` placeholder |
| docs/n8n-setup.md | `n8n-mombot`, `192.168.4.152`, "Erin", "Sandy" | Generic service name, `<server-ip>` |
| docs/notion-setup.md | Extensive family data (lines 124-236) | Replace with placeholder instructions |
| docs/ynab-budget-rules.md | Personal subscription details, partner names | Generic examples |
| .github/workflows/ci.yml | `mombot.sierracodeco.com/health` fallback | Remove hardcoded fallback, use var only |
| docker-compose.yml | `n8n-mombot` service name | Rename to `n8n` or `n8n-scheduler` |
| scripts/nuc.sh | `warp-nuc` hostname | Make configurable via env var |

### Findings — Files Excluded from Template

| File | Reason |
|------|--------|
| PRICING.md | Business doc (per clarification) |
| SERVICE_AGREEMENT.md | Business doc (per clarification) |
| specs/ | Historical feature artifacts |
| memory/ | User-specific Claude memory |
| data/conversation_archives/ | Personal conversation data |
| .claude/settings.local.json | User-specific settings |
| config/family.yaml | Instance-specific (only .example ships) |
| .env | Secrets (only .example ships) |

### Findings — Files Already Clean

| File | Status |
|------|--------|
| config/family.yaml.example | Uses generic names (Alex, Sam, Max, Lily) |
| .env.example | Uses generic PARTNER1/PARTNER2 vars |
| Dockerfile | No personal references |
| railway.toml | No personal references |
| pyproject.toml | No personal references |
| scripts/validate_setup.py | No personal references |
| scripts/setup_calendar.py | No personal references |

---

## R5: Template Repository Creation Strategy

### Decision
Use `gh` CLI to create a public template repo with fresh git history.

### Approach
1. Create temp directory
2. Copy all source files (excluding personal data) from family-meeting
3. Apply all genericization changes
4. Initialize fresh git repo
5. Create GitHub repo with `gh repo create --template` flag
6. Push initial commit

### Alternatives Considered
- Fork existing repo → Rejected (carries full git history with personal data)
- GitHub "Use this template" from existing repo → Rejected (existing repo has personal data that would be in template)
- Separate branch in same repo → Rejected (doesn't separate personal from template)

### Template Repo Name
To be decided during implementation. Candidates: `family-assistant`, `whatsapp-family-assistant`, `family-meeting-template`.

---

## R6: `.env.example` Legacy Aliases

### Decision
Keep legacy alias comments in `.env.example` for the template repo.

### Rationale
Comments like `# Legacy aliases also supported: JASON_PHONE, ERIN_PHONE` document backward compatibility. While they reference original names, they're developer documentation explaining the alias system. New operators understand these are legacy names from the original project. Low confusion risk.

### Alternative
Remove legacy alias comments entirely → Rejected (operators who read the source code might encounter the fallback logic and wonder why).
