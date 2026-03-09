"""Tests for the prompt loader module (src/prompts/)."""

import pytest

from src.prompts import load_system_prompt, load_tool_descriptions, render_template


def test_load_system_prompt_returns_nonempty():
    """System prompt loads from section files and contains expected markers."""
    prompt = load_system_prompt()
    assert len(prompt) > 0
    # Check for expected section content (identity and response rules)
    assert "Mom Bot" in prompt or "family" in prompt.lower()


def test_load_tool_descriptions_returns_77():
    """All 77 tool descriptions load from external Markdown files."""
    descs = load_tool_descriptions()
    assert isinstance(descs, dict)
    assert len(descs) == 77, f"Expected 77 tool descriptions, got {len(descs)}"


def test_load_tool_descriptions_has_key_tools():
    """Spot-check that critical tools are present."""
    descs = load_tool_descriptions()
    for tool in ["get_calendar_events", "get_action_items", "push_grocery_list", "get_daily_context"]:
        assert tool in descs, f"Missing tool description: {tool}"
        assert len(descs[tool]) > 0, f"Empty description for: {tool}"


def test_all_templates_loadable():
    """Every .md file in src/prompts/templates/ is loadable and non-empty."""
    from pathlib import Path

    templates_dir = Path("src/prompts/templates")
    template_files = sorted(templates_dir.glob("*.md"))
    assert len(template_files) > 0, "No template files found"

    for f in template_files:
        name = f.stem
        from src.prompts import load_template

        content = load_template(name)
        assert len(content) > 0, f"Template {name} is empty"


def test_render_template_missing_placeholder():
    """render_template raises KeyError when a required placeholder is missing."""
    with pytest.raises(KeyError):
        render_template("amazon_order_parsing")  # missing clean_text
