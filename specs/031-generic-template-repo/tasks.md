# Tasks: Generic Template Repository

**Input**: Design documents from `specs/031-generic-template-repo/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Verify current state and establish baseline

- [x] T001 Run existing test suite to establish green baseline: `pytest tests/` — 60 passed
- [x] T002 Run grep audit to confirm known hardcoded references: `grep -rn "Jason\|Erin\|Vienna\|Zoey\|Whole Foods" src/ --include="*.py"` — 59 refs found

**Checkpoint**: Baseline established — tests pass, hardcoded refs cataloged

---

## Phase 2: Foundational — US2: Remove Default Config Fallback (Priority: P1)

**Goal**: System fails fast on missing/invalid `config/family.yaml` instead of silently using the original developer's family details.

**Independent Test**: Start the system without `family.yaml` and verify it exits with an actionable error.

**⚠️ CRITICAL**: Must complete before US1 work begins — US1 depends on config-only values.

- [x] T003 [US2] Remove `_DEFAULT_CONFIG` dict from `src/family_config.py` (lines 16-40). Delete the entire fallback dictionary containing hardcoded Belk family data.

- [x] T004 [US2] Update `load_family_config()` in `src/family_config.py` to raise `FileNotFoundError` with message "Missing config/family.yaml — copy config/family.yaml.example and fill in your family's details." when config file is absent. Remove any merge/fallback logic that references `_DEFAULT_CONFIG`.

- [x] T005 [US2] Add required field validation in `load_family_config()` in `src/family_config.py`. After loading YAML, validate that `family.name`, `family.members` (list with ≥2 entries), and `family.members[0].name` / `family.members[1].name` exist. Raise `ValueError` listing all missing fields if validation fails.

- [x] T006 [US2] Verify `_build_placeholder_dict()` in `src/family_config.py` works correctly without `_DEFAULT_CONFIG` — ensure all placeholder keys (`partner1_name`, `partner2_name`, `bot_name`, `grocery_store`, etc.) are derived solely from the YAML config. Add sensible fallbacks for optional fields (e.g., `grocery_store` defaults to "the grocery store" if not in YAML).

- [x] T007 [US2] Run `pytest tests/` to verify tests still pass (tests use their own generic fixtures, not `_DEFAULT_CONFIG`). Verify the personal deployment's `config/family.yaml` still loads correctly.

**Checkpoint**: System fails fast on missing config. Existing deployment works. Tests pass.

---

## Phase 3: US1 — Eliminate Remaining Hardcoded Family References (Priority: P1) 🎯 MVP

**Goal**: All response messages, tool outputs, default values, and sync routing use config-driven values. Zero hardcoded family names in Python source.

**Independent Test**: Configure `family.yaml` with a different family ("The Smith Family", Partner1="Alex", Partner2="Jordan"). Trigger every tool with hardcoded refs and verify personalized output.

### Runtime Output Strings (FR-001)

- [x] T008 [P] [US1] Fix hardcoded "Jason" strings in `src/tools/outlook.py`. Import/access `FAMILY_CONFIG` and replace all `"Jason"` in return statements (lines ~110, 130, 164, 184, 189) with `FAMILY_CONFIG["partner1_name"]`. Update f-strings: `"Jason has no work meetings"` → `f"{partner1_name} has no work meetings"`, etc.

- [x] T009 [P] [US1] Fix default `assignee="Erin"` parameters in `src/tools/notion.py`. Change `get_backlog_for_nudge(assignee: str = "Erin")` (line ~555) and the other function with `assignee: str = "Erin"` default (line ~458) to compute defaults from `FAMILY_CONFIG["partner2_name"]`. Use `assignee: str = ""` with `if not assignee: assignee = FAMILY_CONFIG["partner2_name"]` pattern.

- [x] T010 [P] [US1] Fix hardcoded "Erin" string in `src/drive_times.py` (line ~91). Replace `"No drive times stored. Erin can add them by saying..."` with `f"No drive times stored. {FAMILY_CONFIG['partner2_name']} can add them by saying..."`.

- [x] T011 [P] [US1] Fix sync routing strings in `src/assistant.py`. Replace `"sent to Erin for review"` (line ~1396) with `f"sent to {FAMILY_CONFIG['partner2_name']} for review"`. Replace `"Sends the detailed suggestion message directly to Erin"` (line ~1363) and similar (line ~1383) with config-driven partner2 name. Replace `"Ask Jason to re-run setup_calendar.py on the NUC."` (line ~1374) with generic `"Ask the operator to re-run setup_calendar.py."`.

### Tool Schema Examples (FR-003)

- [x] T012 [US1] Fix tool schema example strings in `src/assistant.py`. Replace hardcoded names in `input_schema` descriptions: `"Who this is assigned to (Jason or Erin)."` (line ~129) → use config names. `"'Erin -> Jason: pick up dog'"` (line ~463) → config names. `"'Erin said: remind Jason to pick up the dog'"` (line ~488) → config names. `"'no Jason appointment reminders'"` (line ~1645) → config name. `"'jason', 'erin', 'family'"` calendar enum (line ~79) → config-driven calendar names. Build these strings at module level from `FAMILY_CONFIG`.

- [x] T013 [P] [US1] Fix example strings in `src/tools/discovery.py`. Replace `"remind Jason to pick up dog at 12:30"` (lines ~49, ~204) with `f"remind {FAMILY_CONFIG['partner1_name']} to pick up dog at 12:30"`.

### Comments & Docstrings (FR-011)

- [x] T014 [P] [US1] Update docstrings in `src/tools/outlook.py`. Change `"""Fetch Jason's work calendar events...` (line ~135) → `"""Fetch Partner 1's work calendar events...`. Change `"""Get Jason's busy windows...` (line ~193) → `"""Get Partner 1's busy windows...`.

- [x] T015 [P] [US1] Update docstring in `src/app.py`. Change `"""Receive Jason's work calendar events from iOS Shortcut."""` (line ~615) → `"""Receive Partner 1's work calendar events from iOS Shortcut."""`.

- [x] T016 [P] [US1] Update docstrings and comments in `src/tools/calendar.py`. Change `"both Jason and Erin can see it"` (line ~346) → `"both partners can see it"`. Change `"Erin → Jason: pick up dog"` (line ~350) → `"Partner 2 → Partner 1: pick up dog"`.

- [x] T017 [P] [US1] Update docstring in `src/tools/chores.py`. Change `"""Find free windows in Erin's day...` (line ~50) → `"""Find free windows in Partner 2's day...`.

- [x] T018 [P] [US1] Update docstrings and comments in `src/tools/nudges.py`. Change `"""Scan Erin's and family calendars...` (line ~97) → `"""Scan Partner 2's and family calendars...`. Change `# Check Erin's preferences` (line ~261) → `# Check Partner 2's preferences`.

- [x] T019 [P] [US1] Update docstrings and comments in `src/tools/amazon_sync.py`. Change `"""A record of Erin correcting...` (line ~36) → `"""A record of Partner 2 correcting...`. Change `# Erin's adjustment message` (line ~41) → `# Partner 2's adjustment message`. Change any `"Ask Jason to re-run..."` error messages → generic operator reference.

- [x] T020 [P] [US1] Update comment in `src/config.py`. Change `# Outlook (optional — Jason's work calendar ICS feed)` (line ~98) → `# Outlook (optional — Partner 1's work calendar ICS feed)`.

- [x] T021 [P] [US1] Update docstring in `src/context.py`. Change `Falls back to "With Erin..."` (line ~276) → `Falls back to "With Partner 2..."`.

### Verification

- [x] T022 [US1] Run `pytest tests/` and verify all tests pass after changes — 60 passed.

- [x] T023 [US1] Run hardcoded reference grep: `grep -rn "Jason\|Erin\|Vienna\|Zoey\|Whole Foods\|Belk\|Sandy" src/ --include="*.py"` and verify zero results outside of config example files, legacy env var alias comments in `src/config.py`, and keyword matching sets (e.g., `"whole foods"` in category detection is acceptable as a lowercase keyword).

- [x] T024 [US1] Verify personal deployment: restart with existing `config/family.yaml` and confirm no regression — system prompt, tool outputs, and sync routing all work correctly.

**Checkpoint**: Zero hardcoded family names in Python source. All tools use config-driven values. Tests pass. Personal deployment works.

---

## Phase 4: US3 — Create Separate GitHub Template Repository (Priority: P2)

**Goal**: A clean GitHub template repo exists with all source code but no personal data, ready for "Use this template".

**Independent Test**: Click "Use this template", clone, fill in config, deploy, exchange a WhatsApp message.

**Dependencies**: US1 and US2 must be complete (source code must be clean before copying to template).

### Prepare Template Content

- [x] T025 [US3] Create a staging directory for the template repo. Script the file copy process: include `src/`, `tests/`, `config/family.yaml.example`, `.env.example`, `Dockerfile`, `docker-compose.yml`, `railway.toml`, `pyproject.toml`, `requirements.txt`, `.github/`, `scripts/`, `docs/` (excluding PRICING.md), `.specify/`, `.claude/commands/speckit.*.md`, `data/schedules.json`. Exclude `specs/`, `memory/`, `data/conversation_archives/`, `data/conversations.json`, `data/user_preferences.json`, `data/work_calendar.json`, `.claude/settings.local.json`, `config/family.yaml`, `.env`, `PRICING.md`, `SERVICE_AGREEMENT.md`, `test_work_calendar_e2e.py`, `=6.0`.

### Genericize Infrastructure (FR-008, FR-009)

- [x] T026 [P] [US3] Rename `n8n-mombot` service to `n8n` in `docker-compose.yml` (in template staging directory). Update all internal references to the old service name.

- [x] T027 [P] [US3] Remove hardcoded `mombot.sierracodeco.com/health` fallback from `.github/workflows/ci.yml` (in template staging directory). Change health check line to use only `${{ vars.HEALTH_CHECK_URL }}` — if var not set, skip health check (expected for new repos).

- [x] T028 [P] [US3] Make `scripts/nuc.sh` hostname configurable (in template staging directory). Change `NUC="warp-nuc"` to `NUC="${NUC_HOST:-your-server}"`. Change hardcoded `~/family-meeting` path to `~/${REPO_NAME:-family-assistant}`.

### Enhanced .gitignore (FR-010)

- [x] T029 [US3] Create/update `.gitignore` in template staging directory to exclude: `config/family.yaml`, `.env`, `data/conversations.json`, `data/conversation_archives/`, `data/user_preferences.json`, `data/work_calendar.json`, `memory/`, `.claude/settings.local.json`.

### Template CLAUDE.md (FR-012)

- [x] T030 [US3] Copy `specs/031-generic-template-repo/contracts/CLAUDE.md.sample` to `CLAUDE.md` in template staging directory. This is the pre-written generic version with no personal references, no feature history, and generic deployment section.

### Create GitHub Repo (FR-005)

- [x] T031 [US3] Initialize git repo in staging directory, create initial commit, create GitHub repo with `gh repo create` (public, with description), push, and enable template flag with `gh repo edit --template`.

### Verify Template

- [x] T032 [US3] Search the entire template repo for personal references: `grep -rn "Jason\|Erin\|Vienna\|Zoey\|MomBot\|mombot\|sierrastoryco\|Belk\|warp-nuc\|192.168.4.152" . --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" --include="*.sh"`. Verify zero results.

**Checkpoint**: Template repo exists on GitHub with "Use this template" enabled. Zero personal references.

---

## Phase 5: US4 — Genericize Documentation (Priority: P2)

**Goal**: All documentation in the template repo uses generic placeholders instead of original family-specific details.

**Independent Test**: Read all docs and verify zero references to original family details.

**Dependencies**: T025 (staging directory) must be complete. Can run in parallel with US3 infra tasks (T026-T029).

### Documentation Updates (FR-006, FR-007)

- [x] T033 [P] [US4] Write new `README.md` for template repo (in staging directory). Include: product description ("WhatsApp AI family assistant"), feature list (calendar, grocery, budget, meal planning, action items, recipes, chores), architecture overview (text diagram), available integrations table (9 integrations with optional/required labels), quick start (point to ONBOARDING.md), development workflow (speckit overview). No references to original family.

- [x] T034 [P] [US4] Genericize `ONBOARDING.md` in template staging directory. Replace 5 "MomBot" references with "Family Assistant" or `{bot_name}`. Replace any "Sierra Story Co" references. Replace any hardcoded domain examples with `<your-domain>`.

- [x] T035 [P] [US4] Genericize `docs/ios-shortcut-setup.md` in template staging directory. Replace `mombot.sierrastoryco.com` → `<your-domain>`. Replace "Jason" → "Partner 1" / "the working partner". Replace "Erin" → "Partner 2".

- [x] T036 [P] [US4] Genericize `docs/n8n-setup.md` in template staging directory. Replace `n8n-mombot` → `n8n`. Replace `192.168.4.152` → `<server-ip>`. Replace "Erin" → "Partner 2". Replace "Sandy" → "the caregiver".

- [x] T037 [P] [US4] Genericize `docs/notion-setup.md` in template staging directory. Replace detailed family schedule section (lines ~124-236) with generic placeholder instructions using "Partner 1", "Partner 2", "Child 1", "Child 2", "Caregiver". Replace `"Jason"` / `"Erin"` in Assignee options → `"Partner 1"` / `"Partner 2"`. Keep the structural instructions (database setup steps) intact.

- [x] T038 [P] [US4] Genericize `docs/ynab-budget-rules.md` in template staging directory. Replace personal subscription examples with generic categories ("Partner 1 Subscriptions", "Partner 2 Subscriptions"). Replace "Jason" / "Erin" references with role-based names. Keep the budget rule structure intact.

### Final Verification

- [x] T039 [US4] Run full personal reference search across all files in template staging directory: `grep -rn "Jason\|Erin\|Vienna\|Zoey\|MomBot\|mombot\|sierrastoryco\|Belk\|Sandy\|warp-nuc\|Sierra Story\|Sierra Code\|192.168.4.152\|jabelk" . --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" --include="*.sh" --include="*.json"`. Fix any remaining references. Verify zero results.

- [x] T040 [US4] Push updated docs to template repo: `git add -A && git commit -m "Genericize documentation" && git push`.

**Checkpoint**: All template docs are generic. Zero personal references across entire template repo.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all user stories

- [x] T041 Run full test suite on personal instance: `pytest tests/`
- [x] T042 Run `python scripts/validate_setup.py` on personal instance to verify validation script works with fail-fast config
- [x] T043 Run quickstart.md verification commands (grep audit, fail-fast test, template search)
- [x] T044 Create PR for Phase 1 changes (US1 + US2) in `family-meeting` repo on branch `031-generic-template-repo`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **US2 (Phase 2)**: Depends on Setup — BLOCKS US1 (config loading changes must land first)
- **US1 (Phase 3)**: Depends on US2 — BLOCKS US3/US4 (source must be clean before template)
- **US3 (Phase 4)**: Depends on US1 + US2 merged to main
- **US4 (Phase 5)**: Depends on T025 (staging dir). Can overlap with US3 infra tasks.
- **Polish (Phase 6)**: Depends on all phases complete

### User Story Dependencies

```
US2 (fail-fast config) → US1 (fix hardcoded refs) → US3 (create template) + US4 (genericize docs)
```

- **US2 → US1**: US2 changes config loading; US1 relies on config for replacement values
- **US1 → US3/US4**: Source code must be clean before copying to template repo
- **US3 ↔ US4**: Can overlap — US4 docs work starts after staging dir exists (T025)

### Within Each User Story

- Runtime fixes before schema fixes before comment fixes (US1)
- Staging directory before infrastructure changes before repo creation (US3)
- All doc tasks are parallel within US4

### Parallel Opportunities

**Within US1** (Phase 3):
```
T008 (outlook.py) || T009 (notion.py) || T010 (drive_times.py) || T011 (assistant.py sync)
T014 (outlook docs) || T015 (app.py docs) || T016 (calendar docs) || T017 (chores docs) || T018 (nudges docs) || T019 (amazon docs) || T020 (config docs) || T021 (context docs)
```

**Within US3** (Phase 4):
```
T026 (docker) || T027 (ci.yml) || T028 (nuc.sh)
```

**Within US4** (Phase 5):
```
T033 (README) || T034 (ONBOARDING) || T035 (ios-shortcut) || T036 (n8n) || T037 (notion) || T038 (ynab)
```

---

## Implementation Strategy

### MVP First (US2 + US1)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: US2 — Remove default config, add fail-fast (T003-T007)
3. Complete Phase 3: US1 — Fix all hardcoded refs (T008-T024)
4. **STOP and VALIDATE**: Grep audit returns zero results. Tests pass. Personal deployment works.
5. Merge PR to main.

### Incremental Delivery

1. US2 + US1 merged → Personal instance is template-ready
2. US3 complete → Template repo exists on GitHub
3. US4 complete → Template docs are fully generic
4. Polish → Final validation, PR

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US2 are both P1 priority but US2 is foundational (must complete first)
- Phase 4 and 5 (template repo) operate on a staging directory, not the personal repo
- The `contracts/CLAUDE.md.sample` is already written — T030 just copies it
- Legacy env var aliases in `src/config.py` (JASON_PHONE, ERIN_PHONE) are kept for backward compatibility — they are not "hardcoded references" per se, just legacy naming in fallback comments
- Lowercase keyword matches (e.g., `"whole foods"` in category detection sets) are acceptable — these are data patterns, not family-specific references
