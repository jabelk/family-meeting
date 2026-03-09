# Research: Prompt Externalization

## Decision 1: File Format for Prompt Content

**Decision**: Markdown (`.md`) files for all prompt content.

**Rationale**: Anthropic recommends structuring prompts with XML tags and Markdown headers — formats Claude is specifically trained to parse. Markdown requires zero new dependencies (read with `pathlib`), produces clean git diffs, and is readable by non-developers. The system prompt already uses Markdown-style formatting (bold, bullets, numbered rules).

**Alternatives considered**:
- **YAML**: Better for structured data (tool schemas), but adds `pyyaml` dependency and is less readable for long-form prompt text. Tool schemas stay in Python per clarification, so YAML's structured-data advantage isn't needed.
- **Jinja2**: Overkill for 11 dynamic prompts with simple variable injection. Adds dependency and learning curve. Python's built-in `.format()` handles all current placeholder patterns.
- **JSON**: Not human-readable for long text. Would require escaping newlines and special characters.

## Decision 2: System Prompt Composition Strategy

**Decision**: Split into ~8 numbered section files in `src/prompts/system/`, loaded and concatenated in filename sort order.

**Rationale**: The current 376-line system prompt has 12 logical sections. Grouping related sections into ~8 files keeps each file focused (30-100 lines) while avoiding excessive fragmentation. Numbered prefixes (01-, 02-) guarantee assembly order without an explicit manifest file.

**Alternatives considered**:
- **Single monolithic file**: Simpler but defeats the purpose — a daily-planner rule change still diffs against 375 other lines.
- **Manifest file listing sections**: Adds indirection without clear benefit. Filename ordering is sufficient and self-documenting.

## Decision 3: Tool Description Storage

**Decision**: One Markdown file per tool module (12 files), with `## tool_name` headers delimiting individual tool descriptions. Parameter schemas stay in Python code.

**Rationale**: Grouping by module (calendar, notion, ynab, etc.) matches the existing `src/tools/` organization. Using `## tool_name` Markdown headers enables simple parsing — split on headers, build a dict of name→description. Schemas remain as Python dicts where they benefit from type checking and IDE support.

**Alternatives considered**:
- **One file per tool**: 71 files is excessive for descriptions that are 1-5 lines each.
- **One giant file**: Too large, loses the organizational benefit.
- **YAML with both description and schema**: Adds dependency and duplicates schema definitions that need to stay in sync with Python function signatures.

## Decision 4: Template Placeholder Syntax

**Decision**: Python `.format()` style placeholders (e.g., `{item_title}`, `{category_list}`).

**Rationale**: All 11 existing dynamic prompts use f-strings with simple variable names. Converting to `.format()` style is a 1:1 mapping with no behavioral change. No new dependency needed — it's stdlib.

**Alternatives considered**:
- **Jinja2 `{{ var }}`**: Overkill, adds dependency.
- **Custom `$var` syntax**: Non-standard, requires custom parser.

## Decision 5: Loader Architecture

**Decision**: Single `src/prompts.py` module with `@lru_cache` for startup-time loading. Three functions: `load_system_prompt()`, `load_tool_descriptions()`, `render_template(name, **kwargs)`.

**Rationale**: Matches the existing codebase pattern of utility modules in `src/` (e.g., `src/config.py`, `src/context.py`). `@lru_cache` ensures files are read once and cached for the process lifetime, satisfying FR-007. No class hierarchy or registry pattern needed — three functions cover all use cases.

**Alternatives considered**:
- **PromptRegistry class**: Over-engineered for 3 access patterns.
- **Banks/Mirascope library**: Adds dependency for what 30 lines of stdlib code handles.
- **Per-request file reads**: Unnecessary I/O overhead for static content.
