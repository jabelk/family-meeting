#!/usr/bin/env python3
"""Pre-deployment validation script.

Validates family.yaml and .env configuration, checks integration completeness,
and reports deployment readiness.

Usage:
    python scripts/validate_setup.py [--env-file .env] [--config-file config/family.yaml]
"""

import argparse
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Add project root to path so we can import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations import INTEGRATION_REGISTRY, get_tools_for_integrations


def _mask_key(value: str) -> str:
    """Mask a secret value for display (show prefix + last 3 chars)."""
    if len(value) <= 8:
        return value[:2] + "***"
    return value[:6] + "***..." + value[-3:]


def validate_family_config(config_path: str) -> tuple[list[str], list[str], dict]:
    """Validate family.yaml structure and required fields.

    Returns (errors, warnings, parsed_config).
    """
    errors = []
    warnings = []
    config = {}
    path = Path(config_path)

    print(f"\nFamily Config: {config_path}")

    if not path.exists():
        errors.append(f"File not found: {config_path}")
        print(f"  \u2717 ERROR: File not found: {config_path}")
        return errors, warnings, config

    try:
        import yaml

        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        errors.append(f"Failed to parse YAML: {e}")
        print(f"  \u2717 ERROR: Failed to parse YAML: {e}")
        return errors, warnings, config

    print("  \u2713 File exists and parses correctly")

    # Required fields
    family_name = config.get("family", {}).get("name", "") or config.get("family_name", "")
    if family_name:
        print(f"  \u2713 Family name: {family_name}")
    else:
        errors.append("Missing required field: family name")
        print("  \u2717 ERROR: Missing required field 'family.name'")

    bot = config.get("bot", {})
    bot_name = bot.get("name", "")
    if bot_name:
        print(f"  \u2713 Bot name: {bot_name}")
    else:
        errors.append("Missing required field: bot name")
        print("  \u2717 ERROR: Missing required field 'bot.name'")

    # Timezone
    timezone = config.get("timezone", "") or config.get("family", {}).get("timezone", "")
    if timezone:
        try:
            ZoneInfo(timezone)
            print(f"  \u2713 Timezone: {timezone} (valid)")
        except (ZoneInfoNotFoundError, KeyError):
            errors.append(f"Invalid timezone: {timezone}")
            print(f"  \u2717 ERROR: Invalid timezone: {timezone}")
    else:
        warnings.append("No timezone set — will default to America/Los_Angeles")
        print("  \u26a0 WARNING: No timezone set (defaults to America/Los_Angeles)")

    # Partners
    partners = config.get("family", {}).get("partners", [])
    if not partners:
        # Check legacy format
        p1 = config.get("partner1_name", "")
        p2 = config.get("partner2_name", "")
        if p1 or p2:
            names = [n for n in [p1, p2] if n]
            print(f"  \u2713 Partners: {', '.join(names)}")
        else:
            errors.append("Missing required field: at least one partner")
            print("  \u2717 ERROR: Missing required field 'family.partners' (at least one partner required)")
    else:
        names = [p.get("name", "Unknown") for p in partners]
        print(f"  \u2713 Partners: {', '.join(names)}")

    return errors, warnings, config


def validate_env(env_path: str) -> tuple[list[str], list[str], dict[str, str]]:
    """Validate .env file — check required vars and formats.

    Returns (errors, warnings, env_vars).
    """
    errors = []
    warnings = []
    env_vars: dict[str, str] = {}
    path = Path(env_path)

    print(f"\nEnvironment: {env_path}")

    if not path.exists():
        errors.append(f"File not found: {env_path}")
        print(f"  \u2717 ERROR: File not found: {env_path}")
        return errors, warnings, env_vars

    # Parse .env file
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key:
                env_vars[key] = value

    # Required vars
    required_checks = [
        ("ANTHROPIC_API_KEY", "sk-ant-", "Get your API key at https://console.anthropic.com/"),
        ("WHATSAPP_PHONE_NUMBER_ID", None, "Get from Meta Business dashboard"),
        ("WHATSAPP_ACCESS_TOKEN", None, "Get from Meta Business dashboard"),
        ("WHATSAPP_VERIFY_TOKEN", None, "Set any random string for webhook verification"),
        ("WHATSAPP_APP_SECRET", None, "Get from Meta App Dashboard > Settings > Basic"),
        ("N8N_WEBHOOK_SECRET", None, "Set any random string for API auth"),
    ]

    required_passed = 0
    required_total = len(required_checks)

    for var_name, prefix, hint in required_checks:
        value = env_vars.get(var_name, "")
        if not value:
            errors.append(f"{var_name} not set")
            print(f"  \u2717 ERROR: {var_name} not set")
            print(f"    \u2192 {hint}")
        elif prefix and not value.startswith(prefix):
            warnings.append(f"{var_name} format unexpected (expected {prefix}* prefix)")
            print(f"  \u26a0 WARNING: {var_name} format unexpected (expected {prefix}* prefix)")
            required_passed += 1
        else:
            display = _mask_key(value) if "KEY" in var_name or "TOKEN" in var_name or "SECRET" in var_name else "set"
            print(f"  \u2713 {var_name}: {display}")
            required_passed += 1

    # Phone numbers
    phone_vars = [
        ("PARTNER1_PHONE", "JASON_PHONE"),
        ("PARTNER2_PHONE", "ERIN_PHONE"),
    ]
    for primary, legacy in phone_vars:
        value = env_vars.get(primary, "") or env_vars.get(legacy, "")
        var_used = primary if env_vars.get(primary) else legacy
        if not value:
            warnings.append(f"{primary} not set (proactive messages won't be sent)")
            print(f"  \u26a0 WARNING: {primary} not set (proactive messages won't be sent)")
        elif not re.match(r"^\d{10,15}$", value):
            warnings.append(f'{var_used} format invalid: "{value}" (use digits only, 10-15 chars, no + prefix)')
            print(f'  \u2717 WARNING: {var_used} format invalid: "{value}" (digits only, 10-15 chars, no + prefix)')
        else:
            print(f"  \u2713 {var_used}: {value} (valid format)")
            required_passed += 1
            required_total += 1

    return errors, warnings, env_vars


def validate_integrations(env_vars: dict[str, str]) -> tuple[list[str], list[str], int, int]:
    """Check integration group completeness.

    Returns (errors, warnings, enabled_count, disabled_count).
    """
    errors = []
    warnings = []
    enabled_count = 0
    disabled_count = 0
    enabled_names = set()

    print("\nIntegrations:")

    for name, integration in INTEGRATION_REGISTRY.items():
        if integration.always_enabled or integration.required:
            continue

        set_vars = [v for v in integration.env_vars if env_vars.get(v)]
        total_vars = len(integration.env_vars)

        if total_vars == 0:
            continue

        if len(set_vars) == total_vars:
            print(f"  \u2713 {integration.display_name}: enabled ({total_vars}/{total_vars} env vars set)")
            enabled_count += 1
            enabled_names.add(name)
        elif len(set_vars) == 0:
            print(f"  \u2717 {integration.display_name}: disabled (0/{total_vars} env vars set)")
            disabled_count += 1
        else:
            missing = [v for v in integration.env_vars if not env_vars.get(v)]
            warnings.append(f"{integration.display_name} partially configured ({len(set_vars)}/{total_vars})")
            print(
                f"  \u26a0 {integration.display_name}: partially configured ({len(set_vars)}/{total_vars} env vars set)"
            )
            print(f"    Missing: {', '.join(missing)}")
            disabled_count += 1

    # Calculate tool count
    total_tools = sum(len(i.tools) for i in INTEGRATION_REGISTRY.values())
    enabled_names.add("core")  # Core is always enabled
    available_tools = len(get_tools_for_integrations(enabled_names))

    return errors, warnings, enabled_count, disabled_count, available_tools, total_tools


def main():
    parser = argparse.ArgumentParser(description="Validate Family Meeting setup configuration")
    parser.add_argument("--env-file", default=".env", help="Path to .env file (default: .env)")
    parser.add_argument(
        "--config-file", default="config/family.yaml", help="Path to family.yaml (default: config/family.yaml)"
    )
    args = parser.parse_args()

    print("=== Family Meeting Setup Validation ===")

    # Validate family config
    config_errors, config_warnings, config = validate_family_config(args.config_file)

    # Validate environment
    env_errors, env_warnings, env_vars = validate_env(args.env_file)

    # Validate integrations
    int_errors, int_warnings, enabled, disabled, available_tools, total_tools = validate_integrations(env_vars)

    # Summary
    all_errors = config_errors + env_errors + int_errors
    all_warnings = config_warnings + env_warnings + int_warnings

    print(f"\nSummary: {'READY TO DEPLOY' if not all_errors else 'NOT READY'}")

    if all_errors:
        print(f"  Required: {len(all_errors)} error(s) found")
        print("  Fix the errors above before deploying.")
    else:
        print("  Required: all checks passed")

    print(f"  Integrations: {enabled} enabled, {disabled} disabled")
    print(f"  Tools available: {available_tools}/{total_tools}")

    if all_warnings:
        print(f"  Warnings: {len(all_warnings)}")

    sys.exit(1 if all_errors else 0)


if __name__ == "__main__":
    main()
