"""Tests for the integration registry (src/integrations.py)."""

import os
from unittest.mock import patch

from src.integrations import (
    INTEGRATION_REGISTRY,
    get_enabled_integrations,
    get_integration_status,
    get_tools_for_integrations,
    is_integration_enabled,
)


class TestIntegrationRegistry:
    """Test INTEGRATION_REGISTRY structure and completeness."""

    def test_all_integrations_have_required_fields(self):
        for name, integration in INTEGRATION_REGISTRY.items():
            assert integration.name == name, f"{name}: name mismatch"
            assert integration.display_name, f"{name}: missing display_name"
            assert isinstance(integration.required, bool), f"{name}: required must be bool"
            assert isinstance(integration.env_vars, tuple), f"{name}: env_vars must be tuple"
            assert isinstance(integration.tools, tuple), f"{name}: tools must be tuple"
            assert integration.prompt_tag, f"{name}: missing prompt_tag"

    def test_core_is_always_enabled(self):
        core = INTEGRATION_REGISTRY["core"]
        assert core.always_enabled is True
        assert len(core.env_vars) == 0

    def test_required_integrations(self):
        required = {n for n, i in INTEGRATION_REGISTRY.items() if i.required}
        assert "whatsapp" in required
        assert "ai_api" in required
        assert "notion" not in required

    def test_no_duplicate_tools_across_integrations(self):
        seen = {}
        for name, integration in INTEGRATION_REGISTRY.items():
            for tool in integration.tools:
                assert tool not in seen, f"Tool '{tool}' in both '{seen[tool]}' and '{name}'"
                seen[tool] = name


class TestGetEnabledIntegrations:
    """Test get_enabled_integrations() with various env configurations."""

    def test_minimal_config(self):
        """Only required vars set — core + whatsapp + ai_api should be enabled."""
        minimal_env = {
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "WHATSAPP_PHONE_NUMBER_ID": "123",
            "WHATSAPP_ACCESS_TOKEN": "token",
            "WHATSAPP_VERIFY_TOKEN": "verify",
            "WHATSAPP_APP_SECRET": "secret",
        }
        with patch.dict(os.environ, minimal_env, clear=True):
            enabled = get_enabled_integrations()
        assert "core" in enabled
        assert "whatsapp" in enabled
        assert "ai_api" in enabled
        assert "notion" not in enabled
        assert "google_calendar" not in enabled
        assert "ynab" not in enabled

    def test_full_config(self):
        """All env vars set — all integrations enabled."""
        full_env = {
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "WHATSAPP_PHONE_NUMBER_ID": "123",
            "WHATSAPP_ACCESS_TOKEN": "token",
            "WHATSAPP_VERIFY_TOKEN": "verify",
            "WHATSAPP_APP_SECRET": "secret",
            "NOTION_TOKEN": "ntn_test",
            "NOTION_ACTION_ITEMS_DB": "db1",
            "NOTION_MEAL_PLANS_DB": "db2",
            "NOTION_MEETINGS_DB": "db3",
            "NOTION_FAMILY_PROFILE_PAGE": "page1",
            "GOOGLE_CALENDAR_FAMILY_ID": "cal@group",
            "OUTLOOK_CALENDAR_ICS_URL": "https://outlook.example.com",
            "YNAB_ACCESS_TOKEN": "ynab_token",
            "YNAB_BUDGET_ID": "budget_id",
            "ANYLIST_SIDECAR_URL": "http://localhost:3000",
            "NOTION_RECIPES_DB": "rdb1",
            "NOTION_COOKBOOKS_DB": "rdb2",
            "R2_ACCOUNT_ID": "r2_id",
        }
        with patch.dict(os.environ, full_env, clear=True):
            enabled = get_enabled_integrations()
        assert "notion" in enabled
        assert "google_calendar" in enabled
        assert "ynab" in enabled
        assert "anylist" in enabled
        assert "recipes" in enabled

    def test_partial_notion_not_enabled(self):
        """Partial Notion config — should not be enabled."""
        partial_env = {
            "NOTION_TOKEN": "ntn_test",
            "NOTION_ACTION_ITEMS_DB": "db1",
            # Missing: NOTION_MEAL_PLANS_DB, NOTION_MEETINGS_DB, NOTION_FAMILY_PROFILE_PAGE
        }
        with patch.dict(os.environ, partial_env, clear=True):
            enabled = get_enabled_integrations()
        assert "notion" not in enabled


class TestGetToolsForIntegrations:
    """Test get_tools_for_integrations()."""

    def test_core_only(self):
        tools = get_tools_for_integrations({"core"})
        assert "get_daily_context" in tools
        assert "save_preference" in tools
        assert "get_help" in tools
        assert "get_action_items" not in tools

    def test_core_plus_notion(self):
        tools = get_tools_for_integrations({"core", "notion"})
        assert "get_daily_context" in tools
        assert "get_action_items" in tools
        assert "get_budget_summary" not in tools

    def test_empty_returns_nothing(self):
        tools = get_tools_for_integrations(set())
        assert len(tools) == 0


class TestIntegrationStatus:
    """Test get_integration_status() and is_integration_enabled()."""

    def test_core_always_enabled(self):
        assert is_integration_enabled("core") is True
        assert get_integration_status("core") == "enabled"

    def test_unknown_integration(self):
        assert is_integration_enabled("nonexistent") is False
        assert get_integration_status("nonexistent") == "disabled"

    def test_partial_status(self):
        partial_env = {"NOTION_TOKEN": "test"}
        with patch.dict(os.environ, partial_env, clear=True):
            assert get_integration_status("notion") == "partial"
            assert is_integration_enabled("notion") is False
