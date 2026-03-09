"""Prompt loader — reads system prompt sections, tool descriptions, and templates from external files."""

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent
SYSTEM_DIR = PROMPTS_DIR / "system"
TOOLS_DIR = PROMPTS_DIR / "tools"
TEMPLATES_DIR = PROMPTS_DIR / "templates"


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """Load and concatenate all system prompt section files in sorted filename order.

    Files in src/prompts/system/ are numbered (01-identity.md, 02-response-rules.md, etc.)
    and joined with double newlines to form the complete system prompt.

    Raises FileNotFoundError if the system directory is empty or missing.
    """
    files = sorted(SYSTEM_DIR.glob("*.md"))
    if not files:
        raise FileNotFoundError(
            f"No system prompt files found in {SYSTEM_DIR}. "
            "Expected numbered .md files (e.g., 01-identity.md)."
        )
    sections = []
    for f in files:
        content = f.read_text(encoding="utf-8").strip()
        if not content:
            logger.warning("Empty system prompt section: %s", f.name)
            continue
        sections.append(content)
    return "\n\n".join(sections)


@lru_cache(maxsize=1)
def load_tool_descriptions() -> dict[str, str]:
    """Parse tool description files into a dict mapping tool_name -> description.

    Each file in src/prompts/tools/ uses ## headers to delimit individual tool descriptions:

        ## get_calendar_events
        Fetch upcoming events from Google Calendar...

        ## get_outlook_events
        Returns Jason's work calendar events...

    Returns a dict like {"get_calendar_events": "Fetch upcoming...", ...}.
    Logs warnings for files with no parseable headers.
    """
    descriptions: dict[str, str] = {}
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
                if current_tool:
                    descriptions[current_tool] = "\n".join(current_lines).strip()
                current_tool = line[3:].strip()
                current_lines = []
            elif current_tool is not None:
                current_lines.append(line)

        # Save last tool in file
        if current_tool:
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
