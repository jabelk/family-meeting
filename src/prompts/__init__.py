"""Prompt loader — reads system prompt sections, tool descriptions, and templates from external files."""

import logging
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent
SYSTEM_DIR = PROMPTS_DIR / "system"
TOOLS_DIR = PROMPTS_DIR / "tools"
TEMPLATES_DIR = PROMPTS_DIR / "templates"


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Returns (metadata_dict, content_without_frontmatter).
    If no frontmatter found, returns ({}, content).
    """
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    frontmatter_text = content[3:end].strip()
    metadata: dict = {}
    for line in frontmatter_text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                metadata[key] = [v.strip() for v in value[1:-1].split(",")]
            else:
                metadata[key] = value
    body = content[end + 3 :].strip()
    return metadata, body


def _should_include_section(metadata: dict, enabled: set[str]) -> bool:
    """Check if a prompt section should be included based on enabled integrations."""
    requires = metadata.get("requires")
    requires_any = metadata.get("requires_any")
    if requires:
        return all(tag in enabled for tag in requires)
    if requires_any:
        return any(tag in enabled for tag in requires_any)
    # No frontmatter requirements → always include
    return True


@lru_cache(maxsize=4)
def load_system_prompt(enabled_integrations: frozenset[str] | None = None) -> str:
    """Load and concatenate system prompt sections, filtered by enabled integrations.

    Files in src/prompts/system/ are numbered (01-identity.md, 02-response-rules.md, etc.)
    and joined with double newlines. YAML frontmatter tags (requires/requires_any)
    control which sections are included based on configured integrations.

    Args:
        enabled_integrations: Frozenset of enabled integration names. If None, all
            sections are included (backward compatible).

    Raises FileNotFoundError if the system directory is empty or missing.
    """
    files = sorted(SYSTEM_DIR.glob("*.md"))
    if not files:
        raise FileNotFoundError(
            f"No system prompt files found in {SYSTEM_DIR}. Expected numbered .md files (e.g., 01-identity.md)."
        )
    enabled = set(enabled_integrations) if enabled_integrations is not None else None
    sections = []
    for f in files:
        raw = f.read_text(encoding="utf-8").strip()
        if not raw:
            logger.warning("Empty system prompt section: %s", f.name)
            continue
        metadata, content = _parse_frontmatter(raw)
        if enabled is not None and not _should_include_section(metadata, enabled):
            logger.debug("Skipping prompt section %s (integration not enabled)", f.name)
            continue
        sections.append(content)
    return "\n\n".join(sections)


@lru_cache(maxsize=4)
def load_tool_descriptions(enabled_tools: frozenset[str] | None = None) -> dict[str, str]:
    """Parse tool description files into a dict mapping tool_name -> description.

    Each file in src/prompts/tools/ uses ## headers to delimit individual tool descriptions:

        ## get_calendar_events
        Fetch upcoming events from Google Calendar...

        ## get_outlook_events
        Returns Partner 1's work calendar events...

    Args:
        enabled_tools: Frozenset of tool names to include. If None, all tools
            are included (backward compatible).

    Returns a dict like {"get_calendar_events": "Fetch upcoming...", ...}.
    Logs warnings for files with no parseable headers.
    """
    descriptions: dict[str, str] = {}
    allowed = set(enabled_tools) if enabled_tools is not None else None
    files = sorted(TOOLS_DIR.glob("*.md"))
    if not files:
        logger.warning("No tool description files found in %s", TOOLS_DIR)
        return descriptions

    for f in files:
        content = f.read_text(encoding="utf-8")
        current_tool = None
        current_lines: list[str] = []

        for line in content.splitlines():
            if line.startswith("## "):
                # Save previous tool
                if current_tool and (allowed is None or current_tool in allowed):
                    descriptions[current_tool] = "\n".join(current_lines).strip()
                current_tool = line[3:].strip()
                current_lines = []
            elif current_tool is not None:
                current_lines.append(line)

        # Save last tool in file
        if current_tool and (allowed is None or current_tool in allowed):
            descriptions[current_tool] = "\n".join(current_lines).strip()

    logger.info("Loaded %d tool descriptions from %d files", len(descriptions), len(files))
    return descriptions


@lru_cache(maxsize=None)
def load_template(name: str) -> str:
    """Load a prompt template file by name (without .md extension).

    Args:
        name: Template name, e.g., "amazon_classification"

    Returns the raw template text with {placeholder} markers.
    Raises FileNotFoundError if the template file doesn't exist.
    """
    path = TEMPLATES_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Prompt template is empty: {path}")
    return content


class _PassthroughDict(defaultdict):
    """Dict that returns '{key}' for missing keys — prevents KeyError during format_map."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_system_prompt(family_config: dict, enabled_integrations: frozenset[str] | None = None) -> str:
    """Load system prompt template and substitute family config placeholders.

    Uses format_map with a passthrough dict so unknown {placeholders} (e.g., from
    template files) pass through unchanged.

    Args:
        family_config: Family config placeholder dict.
        enabled_integrations: Frozenset of enabled integration names for filtering.
            If None, all sections are included.
    """
    template = load_system_prompt(enabled_integrations=enabled_integrations)
    mapping = _PassthroughDict(str, family_config)
    return template.format_map(mapping)


def render_tool_descriptions(family_config: dict, enabled_tools: frozenset[str] | None = None) -> dict[str, str]:
    """Load tool descriptions and substitute family config placeholders in each.

    Args:
        family_config: Family config placeholder dict.
        enabled_tools: Frozenset of tool names to include. If None, all tools included.
    """
    raw = load_tool_descriptions(enabled_tools=enabled_tools)
    mapping = _PassthroughDict(str, family_config)
    return {name: desc.format_map(mapping) for name, desc in raw.items()}


def render_template(name: str, **kwargs: object) -> str:
    """Load a prompt template and substitute placeholders with provided values.

    Args:
        name: Template name (e.g., "amazon_classification")
        **kwargs: Values for {placeholder} substitution

    Returns the rendered prompt string.
    Raises KeyError if a required placeholder is missing from kwargs.
    """
    template = load_template(name)
    return template.format(**kwargs)
