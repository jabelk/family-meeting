# Implementation Plan: Generic Template Repository

**Branch**: `031-generic-template-repo` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/031-generic-template-repo/spec.md`

## Summary

Eliminate ~31 remaining hardcoded family references across 11 Python source files, remove the `_DEFAULT_CONFIG` fallback (fail-fast on missing config), and create a separate GitHub template repository with genericized documentation, CI/CD, and Docker configuration. The codebase is ~95% template-ready from features 028 and 030; this feature closes the remaining gaps.

## Technical Context

**Language/Version**: Python 3.12 (existing)
**Primary Dependencies**: FastAPI, anthropic SDK, PyYAML (existing — no new deps)
**Storage**: JSON files in `data/` (unchanged)
**Testing**: pytest (existing suite uses generic fixtures, no dependency on `_DEFAULT_CONFIG`)
**Target Platform**: Linux server (Railway) / Docker (self-hosted)
**Project Type**: Web service (existing)
**Performance Goals**: N/A (no performance-sensitive changes)
**Constraints**: Zero hardcoded family references in source; fail-fast on missing config
**Scale/Scope**: 11 Python files modified, ~6 doc files genericized, 1 new GitHub repo created

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Integration Over Building | PASS | No new services built; removes hardcoded values from existing integrations |
| II. Mobile-First Access | PASS | No UX changes; WhatsApp interface unchanged |
| III. Simplicity & Low Friction | PASS | Reduces friction for new operators (config-driven, fail-fast) |
| IV. Structured Output | PASS | No output format changes |
| V. Incremental Value | PASS | Each phase delivers standalone value: Phase 1 fixes the personal instance; Phase 2 creates the template |

**Post-Phase 1 re-check**: All principles remain satisfied. No new violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/031-generic-template-repo/
├── plan.md              # This file
├── research.md          # Hardcoded reference audit + template strategy
├── data-model.md        # Config validation changes
├── quickstart.md        # Implementation guide
├── contracts/
│   └── CLAUDE.md.sample # Generic CLAUDE.md for template repo
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
# Files MODIFIED in Phase 1 (hardcoded reference fixes)
src/
├── family_config.py        # Remove _DEFAULT_CONFIG, add fail-fast validation
├── assistant.py            # Fix tool schema examples + sync routing strings
├── config.py               # Update comment (line 98)
├── context.py              # Update docstring (line 276)
├── drive_times.py          # Fix output string (line 91)
├── app.py                  # Update docstring (line 615)
└── tools/
    ├── outlook.py           # Fix 5 output strings + 2 docstrings
    ├── notion.py            # Fix 2 default parameters
    ├── calendar.py          # Update 2 docstrings
    ├── chores.py            # Update 1 docstring
    ├── nudges.py            # Update 2 comments/docstrings
    ├── amazon_sync.py       # Update 2 docstrings + 1 error message
    └── discovery.py         # Fix 2 example strings

# Files MODIFIED in Phase 2 (template genericization — applied to template repo copy only)
CLAUDE.md                    # Replaced with generic version
README.md                    # Rewritten as product README
ONBOARDING.md                # Remove "MomBot" refs
docker-compose.yml           # Rename n8n-mombot → n8n
.github/workflows/ci.yml     # Remove hardcoded health URL fallback
scripts/nuc.sh               # Make hostname configurable
docs/
├── ios-shortcut-setup.md    # Generic URLs and names
├── n8n-setup.md             # Generic service names
├── notion-setup.md          # Generic family examples
└── ynab-budget-rules.md     # Generic budget examples
```

**Structure Decision**: Existing single-project structure. No new directories or modules. Phase 1 modifies existing files in-place. Phase 2 creates a separate repo from a curated copy of the source tree.

## Phase 1: Fix Hardcoded References (Personal Instance)

Changes merged to `main` via PR. Benefits both personal instance and future template.

### 1.1 Remove `_DEFAULT_CONFIG` and Add Fail-Fast (FR-002)

**File**: `src/family_config.py`

- Delete `_DEFAULT_CONFIG` dict (lines 16-40)
- Modify `load_family_config()`:
  - If `config/family.yaml` not found → raise `FileNotFoundError` with message pointing to `config/family.yaml.example`
  - If required fields missing → raise `ValueError` listing each missing field
- Required fields: `family.name`, `family.members` (≥2 with names)
- Ensure `_build_placeholder_dict()` still works with yaml-only config (no merge with defaults)

### 1.2 Fix Runtime Output Strings (FR-001)

**`src/tools/outlook.py`** (~5 lines):
- Import or access `FAMILY_CONFIG` for `partner1_name`
- Replace all `"Jason"` string literals in return statements with config value

**`src/tools/notion.py`** (2 default params):
- Change `assignee: str = "Erin"` → compute default from `FAMILY_CONFIG["partner2_name"]`
- Both `get_backlog_for_nudge()` and the other function with this default

**`src/drive_times.py`** (1 line):
- Replace `"Erin can add them"` with `f"{FAMILY_CONFIG['partner2_name']} can add them"`

### 1.3 Fix Tool Schema Examples (FR-003)

**`src/assistant.py`** (~6 lines):
- Build tool schema descriptions dynamically at module level using `FAMILY_CONFIG`
- Replace hardcoded name examples in `input_schema` descriptions
- Replace `"Ask Jason to re-run..."` error message with generic operator reference

**`src/tools/discovery.py`** (2 lines):
- Replace `"remind Jason"` examples with config-driven partner name

### 1.4 Update All Comments & Docstrings (FR-011)

Across 11 files, ~15 instances. Replace specific names with role references:
- "Jason" → "Partner 1" or "the working partner"
- "Erin" → "Partner 2" or "the primary household manager"
- "Jason's work calendar" → "Partner 1's work calendar"
- "Erin's day" → "Partner 2's day"
- "Sandy" → "the caregiver"

### 1.5 Verify

- `pytest tests/` passes
- `grep -rn "Jason\|Erin\|Vienna\|Zoey\|Whole Foods" src/ --include="*.py"` returns zero results (excluding config examples)
- Manual startup test with existing `config/family.yaml` (no regression)

## Phase 2: Create Template Repository (Separate Repo)

### 2.1 Prepare Template Content

Create staging directory and copy from `family-meeting` repo:

**Include**:
- `src/` (all Python source — already cleaned in Phase 1)
- `config/family.yaml.example` (NOT `family.yaml`)
- `.env.example`
- `tests/`
- `Dockerfile`, `docker-compose.yml` (genericized)
- `railway.toml`
- `pyproject.toml`
- `requirements.txt`
- `.github/workflows/` (genericized)
- `scripts/` (genericized)
- `docs/` (genericized, excluding PRICING.md)
- `.specify/` (speckit framework)
- `.claude/commands/speckit.*.md` (speckit slash commands)
- `data/schedules.json` (template scheduler config)
- `.gitignore` (enhanced for template)

**Exclude**:
- `specs/` (historical feature artifacts)
- `memory/` (user-specific Claude memory)
- `data/conversation_archives/` (personal data)
- `data/conversations.json`, `data/user_preferences.json` (runtime data)
- `.claude/settings.local.json` (user-specific)
- `config/family.yaml` (instance-specific)
- `.env` (secrets)
- `PRICING.md`, `SERVICE_AGREEMENT.md` (business docs)
- `test_work_calendar_e2e.py` (ad-hoc test in root)
- `=6.0` (stray file in root)

### 2.2 Genericize Documentation (FR-006, FR-007, FR-012)

**CLAUDE.md**: Replace with `contracts/CLAUDE.md.sample` (already written — generic version with no personal refs, no feature history, generic deployment section).

**README.md**: Rewrite as product README:
- What it is (WhatsApp AI family assistant)
- Feature list (calendar, grocery, budget, meal planning, action items)
- Architecture diagram (text)
- Quick start (point to ONBOARDING.md)
- Available integrations table
- Development workflow (speckit)

**ONBOARDING.md**: Replace "MomBot" → "Family Assistant" (5 instances). Remove Sierra Story Co references.

**docs/ios-shortcut-setup.md**: Replace `mombot.sierrastoryco.com` → `<your-domain>`. Replace "Jason"/"Erin" → "Partner 1"/"Partner 2".

**docs/n8n-setup.md**: Replace `n8n-mombot` → `n8n`. Replace `192.168.4.152` → `<server-ip>`. Replace personal names → role references.

**docs/notion-setup.md**: Replace detailed family schedule (lines 124-236) with generic template instructions showing placeholder names.

**docs/ynab-budget-rules.md**: Replace personal subscription lists and partner-specific examples with generic categories.

### 2.3 Genericize Infrastructure (FR-008, FR-009)

**docker-compose.yml**: Rename `n8n-mombot` service → `n8n`. Update any internal references.

**.github/workflows/ci.yml**: Remove hardcoded `mombot.sierracodeco.com/health` fallback from health check. Use only `${{ vars.HEALTH_CHECK_URL }}` (fail if not set, which is expected for new repos without Railway).

**scripts/nuc.sh**: Change `NUC="warp-nuc"` to `NUC="${NUC_HOST:-your-server}"` (configurable via env var).

### 2.4 Enhanced `.gitignore` (FR-010)

Add to template's `.gitignore`:
```
config/family.yaml
.env
data/conversations.json
data/conversation_archives/
data/user_preferences.json
data/work_calendar.json
memory/
.claude/settings.local.json
```

### 2.5 Create GitHub Repo

```bash
# From staging directory with all cleaned content
gh repo create jabelk/family-assistant --public \
  --description "WhatsApp AI family assistant — configure for your household"
git init
git add -A
git commit -m "Initial template from family-meeting"
git remote add origin git@github.com:jabelk/family-assistant.git
git push -u origin main
gh repo edit jabelk/family-assistant --template
```

### 2.6 Verify Template

1. Create test repo from template: `gh repo create test-family --template jabelk/family-assistant --public`
2. Clone and search: `grep -rn "Jason\|Erin\|MomBot\|mombot\|sierrastoryco\|Belk\|warp-nuc" . --include="*.py" --include="*.md" --include="*.yml"` → zero results
3. Fill in test `family.yaml` and `.env`, run `python scripts/validate_setup.py`
4. Clean up test repo: `gh repo delete test-family --yes`

## Complexity Tracking

No constitution violations. No complexity justifications needed.
