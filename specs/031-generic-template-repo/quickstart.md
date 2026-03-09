# Quickstart: Generic Template Repository

**Feature**: 031-generic-template-repo
**Date**: 2026-03-09

## Prerequisites

- Python 3.12+
- Git
- GitHub CLI (`gh`) installed and authenticated
- Access to the `family-meeting` repo (source)

## Implementation Order

### Phase 1: Fix Hardcoded References in Source (US1 + US2)

These changes go into the `family-meeting` repo on branch `031-generic-template-repo` and get merged to main. Both the personal instance and future template benefit.

1. **Remove `_DEFAULT_CONFIG`** in `src/family_config.py`
   - Delete the fallback dict (lines 16-40)
   - Update `load_family_config()` to raise `FileNotFoundError` if `config/family.yaml` missing
   - Add required field validation with specific error messages

2. **Fix runtime output strings** (3 files, ~10 lines)
   - `src/tools/outlook.py` — Replace `"Jason"` with `FAMILY_CONFIG["partner1_name"]`
   - `src/tools/notion.py` — Replace `assignee="Erin"` defaults with config lookup
   - `src/drive_times.py` — Replace `"Erin"` with `FAMILY_CONFIG["partner2_name"]`

3. **Fix tool schema examples** in `src/assistant.py` (~6 lines)
   - Build example strings using family config at startup

4. **Fix sync routing strings** in `src/assistant.py` (~3 lines)
   - Replace hardcoded name strings with config lookups

5. **Update all comments/docstrings** (~15 instances across 11 files)
   - Replace specific names with role-based references

6. **Run tests**: `pytest tests/` — should pass with no changes to test fixtures

### Phase 2: Create Template Repo (US3 + US4)

1. **Prepare template content**
   - Create a staging directory
   - Copy source code, configs, CI/CD, Docker, docs, `.specify/`, `.claude/commands/speckit.*`
   - Exclude: `specs/`, `memory/`, `data/conversation_archives/`, `.claude/settings.local.json`, `config/family.yaml`, `.env`, `PRICING.md`, `SERVICE_AGREEMENT.md`

2. **Genericize documentation**
   - Replace CLAUDE.md with generic version (from `contracts/CLAUDE.md.sample`)
   - Update ONBOARDING.md (remove "MomBot" references)
   - Update docs/*.md (remove family names, use placeholders)
   - Write new README.md (product description, not personal project)

3. **Genericize infrastructure**
   - Rename `n8n-mombot` → `n8n` in docker-compose.yml
   - Remove hardcoded health check URL fallback in ci.yml
   - Make `scripts/nuc.sh` hostname configurable

4. **Create GitHub template repo**
   ```bash
   gh repo create family-assistant --public --description "WhatsApp AI family assistant — template repo"
   cd /tmp/family-assistant
   git init && git add -A && git commit -m "Initial template from family-meeting"
   git remote add origin <repo-url>
   git push -u origin main
   gh repo edit --template
   ```

5. **Verify template**
   - Clone via "Use this template"
   - Search for original family names (expect zero results)
   - Fill in test config, run validation script, verify startup

## Verification Commands

```bash
# After Phase 1 — verify no hardcoded names in Python source
grep -rn "Jason\|Erin\|Vienna\|Zoey\|Whole Foods" src/ --include="*.py" | grep -v "family.yaml.example"

# After Phase 1 — verify tests pass
pytest tests/

# After Phase 1 — verify fail-fast behavior
mv config/family.yaml config/family.yaml.bak
python -c "from src.family_config import load_family_config; load_family_config()"
# Should raise FileNotFoundError
mv config/family.yaml.bak config/family.yaml

# After Phase 2 — verify template repo is clean
cd /tmp/template-test
grep -rn "Jason\|Erin\|Vienna\|Zoey\|MomBot\|mombot\|sierrastoryco\|Belk\|warp-nuc" . --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml"
# Should return zero results
```
