"""Tests for the family config loader (src/family_config.py)."""

import pytest

from src.family_config import _build_placeholder_dict, _validate_config


def _valid_raw():
    """Return a minimal valid config dict."""
    return {
        "bot": {"name": "TestBot"},
        "family": {
            "name": "The Test Family",
            "timezone": "America/New_York",
            "partners": [{"name": "Alice", "work": "engineer"}],
            "children": [{"name": "Charlie", "age": 4, "details": "preschool"}],
            "caregivers": [],
        },
        "preferences": {"grocery_store": "Trader Joe's"},
    }


def test_validate_config_valid():
    """Valid config passes validation without error."""
    _validate_config(_valid_raw())


def test_validate_config_missing_bot_name():
    raw = _valid_raw()
    raw["bot"]["name"] = ""
    with pytest.raises(ValueError, match="bot.name"):
        _validate_config(raw)


def test_validate_config_missing_family_name():
    raw = _valid_raw()
    raw["family"]["name"] = ""
    with pytest.raises(ValueError, match="family.name"):
        _validate_config(raw)


def test_validate_config_invalid_timezone():
    raw = _valid_raw()
    raw["family"]["timezone"] = "Fake/Zone"
    with pytest.raises(ValueError, match="invalid timezone"):
        _validate_config(raw)


def test_validate_config_no_partners():
    raw = _valid_raw()
    raw["family"]["partners"] = []
    with pytest.raises(ValueError, match="partners"):
        _validate_config(raw)


def test_build_placeholder_dict_basic():
    """Placeholder dict contains expected keys with correct values."""
    raw = _valid_raw()
    d = _build_placeholder_dict(raw)
    assert d["bot_name"] == "TestBot"
    assert d["family_name"] == "The Test Family"
    assert d["partner1_name"] == "Alice"
    assert d["partner2_name"] == ""  # Only one partner
    assert d["child1_name"] == "Charlie"
    assert d["grocery_store"] == "Trader Joe's"
    assert "Charlie (age 4)" in d["children_summary"]


def test_build_placeholder_dict_two_partners():
    raw = _valid_raw()
    raw["family"]["partners"].append({"name": "Bob", "work": "teacher"})
    d = _build_placeholder_dict(raw)
    assert d["partner1_name"] == "Alice"
    assert d["partner2_name"] == "Bob"
    assert d["partner1_work"] == "engineer"
    assert d["partner2_work"] == "teacher"


def test_build_placeholder_dict_no_children():
    raw = _valid_raw()
    raw["family"]["children"] = []
    d = _build_placeholder_dict(raw)
    assert d["children_summary"] == ""
    assert d["child1_name"] == ""


def test_build_placeholder_dict_welcome_message_default():
    """Welcome message auto-generates when not provided."""
    raw = _valid_raw()
    d = _build_placeholder_dict(raw)
    assert "TestBot" in d["welcome_message"]
    assert "help" in d["welcome_message"].lower()


def test_build_placeholder_dict_welcome_message_custom():
    raw = _valid_raw()
    raw["bot"]["welcome_message"] = "Hi there!"
    d = _build_placeholder_dict(raw)
    assert d["welcome_message"] == "Hi there!"
