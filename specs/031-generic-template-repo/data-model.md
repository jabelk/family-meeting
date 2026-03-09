# Data Model: Generic Template Repository

**Feature**: 031-generic-template-repo
**Date**: 2026-03-09

## Overview

This feature does not introduce new data entities. It modifies how existing entities are referenced — replacing hardcoded family-specific values with configuration-driven lookups.

## Modified Entities

### Family Config (existing — `src/family_config.py`)

**Change**: Remove `_DEFAULT_CONFIG` fallback dict. `load_family_config()` now raises on missing/invalid config instead of silently using defaults.

**Before**:
```
load_family_config()
  → if family.yaml missing → return _DEFAULT_CONFIG (hardcoded Belk family)
  → if family.yaml exists → merge with _DEFAULT_CONFIG as base
```

**After**:
```
load_family_config()
  → if family.yaml missing → raise FileNotFoundError with actionable message
  → if family.yaml exists but missing required fields → raise ValueError listing missing fields
  → if family.yaml valid → return parsed config (no fallback merge)
```

**Required fields** (validation enforced):
- `family.name` (string)
- `family.members` (list with at least 2 partners)
- `family.members[0].name` and `family.members[1].name` (partner names)

**Optional fields** (absent = feature disabled, not error):
- `family.members[].children` (list)
- `preferences.grocery_store` (string)
- `preferences.recipe_source` (string)
- `caregivers` (list)
- `calendar.event_mappings` (dict)
- `calendar.childcare_keywords` (list)

### Placeholder Dict (existing — `_build_placeholder_dict()`)

No schema change. Same placeholder keys (`partner1_name`, `partner2_name`, `bot_name`, `grocery_store`, etc.) are produced. The only difference is they come exclusively from `family.yaml` rather than potentially from `_DEFAULT_CONFIG`.

## No New Entities

The template repository, personal instance repository, and hardcoded reference concepts from the spec are organizational/process entities, not data model entities. They don't require database schemas or config structures.
