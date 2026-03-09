"""Tests for the validation script (scripts/validate_setup.py)."""

import sys
from pathlib import Path

# Add project root so we can import the validation module
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scripts.validate_setup import validate_env, validate_family_config, validate_integrations


class TestValidateFamilyConfig:
    """Test validate_family_config()."""

    def test_missing_file(self, tmp_path, capsys):
        errors, warnings, config = validate_family_config(str(tmp_path / "nonexistent.yaml"))
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_valid_config(self, tmp_path, capsys):
        config_file = tmp_path / "family.yaml"
        config_file.write_text(
            """
family:
  name: The Smiths
  timezone: America/New_York
  partners:
    - name: Alice
    - name: Bob
bot:
  name: FamilyBot
"""
        )
        errors, warnings, config = validate_family_config(str(config_file))
        assert len(errors) == 0
        assert config["family"]["name"] == "The Smiths"

    def test_missing_family_name(self, tmp_path, capsys):
        config_file = tmp_path / "family.yaml"
        config_file.write_text(
            """
bot:
  name: TestBot
"""
        )
        errors, warnings, config = validate_family_config(str(config_file))
        assert any("family name" in e.lower() for e in errors)

    def test_missing_bot_name(self, tmp_path, capsys):
        config_file = tmp_path / "family.yaml"
        config_file.write_text(
            """
family:
  name: TestFamily
  partners:
    - name: Alice
"""
        )
        errors, warnings, config = validate_family_config(str(config_file))
        assert any("bot name" in e.lower() for e in errors)

    def test_invalid_timezone(self, tmp_path, capsys):
        config_file = tmp_path / "family.yaml"
        config_file.write_text(
            """
family:
  name: TestFamily
  timezone: Invalid/Timezone
  partners:
    - name: Alice
bot:
  name: TestBot
"""
        )
        errors, warnings, config = validate_family_config(str(config_file))
        assert any("timezone" in e.lower() for e in errors)

    def test_no_timezone_warns(self, tmp_path, capsys):
        config_file = tmp_path / "family.yaml"
        config_file.write_text(
            """
family:
  name: TestFamily
  partners:
    - name: Alice
bot:
  name: TestBot
"""
        )
        errors, warnings, config = validate_family_config(str(config_file))
        assert len(errors) == 0
        assert any("timezone" in w.lower() for w in warnings)

    def test_invalid_yaml(self, tmp_path, capsys):
        config_file = tmp_path / "family.yaml"
        config_file.write_text("{{invalid yaml: [")
        errors, warnings, config = validate_family_config(str(config_file))
        assert any("parse" in e.lower() or "yaml" in e.lower() for e in errors)


class TestValidateEnv:
    """Test validate_env()."""

    def test_missing_file(self, tmp_path, capsys):
        errors, warnings, env_vars = validate_env(str(tmp_path / ".env"))
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_valid_env(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
ANTHROPIC_API_KEY=sk-ant-test-key-12345
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_ACCESS_TOKEN=token123
WHATSAPP_VERIFY_TOKEN=verify123
WHATSAPP_APP_SECRET=secret123
N8N_WEBHOOK_SECRET=webhook123
"""
        )
        errors, warnings, env_vars = validate_env(str(env_file))
        assert len(errors) == 0
        assert env_vars["ANTHROPIC_API_KEY"] == "sk-ant-test-key-12345"

    def test_missing_required_vars(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text("SOME_OTHER_VAR=value\n")
        errors, warnings, env_vars = validate_env(str(env_file))
        # Should have errors for all 6 required vars
        assert len(errors) >= 5

    def test_bad_api_key_prefix(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
ANTHROPIC_API_KEY=bad-prefix-key
WHATSAPP_PHONE_NUMBER_ID=123
WHATSAPP_ACCESS_TOKEN=token
WHATSAPP_VERIFY_TOKEN=verify
WHATSAPP_APP_SECRET=secret
N8N_WEBHOOK_SECRET=webhook
"""
        )
        errors, warnings, env_vars = validate_env(str(env_file))
        assert any("ANTHROPIC_API_KEY" in w and "prefix" in w for w in warnings)

    def test_invalid_phone_number(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
ANTHROPIC_API_KEY=sk-ant-test
WHATSAPP_PHONE_NUMBER_ID=123
WHATSAPP_ACCESS_TOKEN=token
WHATSAPP_VERIFY_TOKEN=verify
WHATSAPP_APP_SECRET=secret
N8N_WEBHOOK_SECRET=webhook
PARTNER1_PHONE=+1-555-1234
"""
        )
        errors, warnings, env_vars = validate_env(str(env_file))
        assert any("format" in w.lower() and "phone" in w.lower() for w in warnings)

    def test_valid_phone_number(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
ANTHROPIC_API_KEY=sk-ant-test
WHATSAPP_PHONE_NUMBER_ID=123
WHATSAPP_ACCESS_TOKEN=token
WHATSAPP_VERIFY_TOKEN=verify
WHATSAPP_APP_SECRET=secret
N8N_WEBHOOK_SECRET=webhook
PARTNER1_PHONE=15551234567
PARTNER2_PHONE=15559876543
"""
        )
        errors, warnings, env_vars = validate_env(str(env_file))
        # No phone-related warnings when both are valid
        assert not any("phone" in w.lower() for w in warnings)


class TestValidateIntegrations:
    """Test validate_integrations()."""

    def test_no_optional_integrations(self, capsys):
        env_vars = {}
        errors, warnings, enabled, disabled, avail, total = validate_integrations(env_vars)
        assert enabled == 0
        assert disabled > 0

    def test_partial_integration_warns(self, capsys):
        env_vars = {"NOTION_TOKEN": "test_token"}
        errors, warnings, enabled, disabled, avail, total = validate_integrations(env_vars)
        assert any("partially" in w.lower() for w in warnings)

    def test_full_notion_integration(self, capsys):
        env_vars = {
            "NOTION_TOKEN": "ntn_test",
            "NOTION_ACTION_ITEMS_DB": "db1",
            "NOTION_MEAL_PLANS_DB": "db2",
            "NOTION_MEETINGS_DB": "db3",
            "NOTION_FAMILY_PROFILE_PAGE": "page1",
        }
        errors, warnings, enabled, disabled, avail, total = validate_integrations(env_vars)
        assert enabled >= 1
        assert total > 0
