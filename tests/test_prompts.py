"""Tests for the prompt loader module (src/prompts/)."""

import pytest

from src.prompts import (
    _parse_frontmatter,
    _should_include_section,
    load_system_prompt,
    load_tool_descriptions,
    render_system_prompt,
    render_template,
)


def test_load_system_prompt_returns_nonempty():
    """System prompt loads from section files and contains expected markers."""
    prompt = load_system_prompt()
    assert len(prompt) > 0
    # Raw template has placeholders
    assert "{bot_name}" in prompt or "family" in prompt.lower()


def test_render_system_prompt_with_config():
    """Rendered system prompt replaces family config placeholders."""
    test_config = {
        "bot_name": "TestBot",
        "partner1_name": "Alice",
        "partner2_name": "Bob",
        "family_name": "The Test Family",
    }
    rendered = render_system_prompt(test_config)
    assert "TestBot" in rendered
    assert "{bot_name}" not in rendered


def test_load_tool_descriptions_returns_78():
    """All 78 tool descriptions load from external Markdown files."""
    descs = load_tool_descriptions()
    assert isinstance(descs, dict)
    assert len(descs) == 78, f"Expected 78 tool descriptions, got {len(descs)}"


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


class TestParseFrontmatter:
    """Test _parse_frontmatter() helper."""

    def test_no_frontmatter(self):
        metadata, body = _parse_frontmatter("# Just a heading\nSome content")
        assert metadata == {}
        assert body == "# Just a heading\nSome content"

    def test_requires_tag(self):
        content = "---\nrequires: [core]\n---\n# Identity\nYou are a bot."
        metadata, body = _parse_frontmatter(content)
        assert metadata["requires"] == ["core"]
        assert body == "# Identity\nYou are a bot."

    def test_requires_any_tag(self):
        content = "---\nrequires_any: [notion, google_calendar, outlook]\n---\nContent"
        metadata, body = _parse_frontmatter(content)
        assert metadata["requires_any"] == ["notion", "google_calendar", "outlook"]

    def test_malformed_no_closing(self):
        content = "---\nrequires: [core]\nNo closing delimiter"
        metadata, body = _parse_frontmatter(content)
        assert metadata == {}  # No closing --- → treated as no frontmatter


class TestShouldIncludeSection:
    """Test _should_include_section() filtering logic."""

    def test_no_metadata_always_included(self):
        assert _should_include_section({}, {"core"}) is True

    def test_requires_all_present(self):
        assert _should_include_section({"requires": ["core"]}, {"core", "notion"}) is True

    def test_requires_missing(self):
        assert _should_include_section({"requires": ["notion"]}, {"core"}) is False

    def test_requires_any_one_present(self):
        meta = {"requires_any": ["notion", "google_calendar"]}
        assert _should_include_section(meta, {"core", "notion"}) is True

    def test_requires_any_none_present(self):
        meta = {"requires_any": ["notion", "google_calendar"]}
        assert _should_include_section(meta, {"core"}) is False


class TestFilteredSystemPrompt:
    """Test load_system_prompt() with integration filtering."""

    def test_core_only_excludes_budget(self):
        """With only core enabled, budget section should be excluded."""
        full = load_system_prompt()
        core_only = load_system_prompt(enabled_integrations=frozenset({"core"}))
        assert len(core_only) < len(full)

    def test_all_integrations_matches_unfiltered(self):
        """With all integrations enabled, output should match unfiltered."""
        all_integrations = frozenset(
            {"core", "whatsapp", "ai_api", "notion", "google_calendar", "outlook", "ynab", "anylist", "recipes"}
        )
        filtered = load_system_prompt(enabled_integrations=all_integrations)
        unfiltered = load_system_prompt()
        assert filtered == unfiltered


class TestFilteredToolDescriptions:
    """Test load_tool_descriptions() with tool filtering."""

    def test_filter_to_subset(self):
        subset = frozenset({"get_daily_context", "save_preference"})
        descs = load_tool_descriptions(enabled_tools=subset)
        assert set(descs.keys()) == subset

    def test_none_returns_all(self):
        descs = load_tool_descriptions()
        assert len(descs) == 78
