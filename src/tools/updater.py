"""Upstream update detection, notification, and rollback management."""

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from src.config import ADMIN_PHONE, ANTHROPIC_API_KEY, TIMEZONE, UPSTREAM_REMOTE

logger = logging.getLogger(__name__)

_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("data")
_STATE_PATH = _DATA_DIR / "update_state.json"
_BACKUP_DIR = _DATA_DIR / "backups"
_MAX_BACKUPS = 3
_ROLLBACK_GRACE_DAYS = 7

_DEFAULT_STATE = {
    "deployed_sha": "",
    "last_checked_sha": "",
    "last_notified_sha": "",
    "last_update_time": None,
    "pre_update_sha": None,
    "pre_update_backup_path": None,
    "skipped_sha": None,
}


# ---------------------------------------------------------------------------
# State persistence (atomic JSON — same pattern as drive_times.py)
# ---------------------------------------------------------------------------


def _load_state() -> dict:
    if _STATE_PATH.exists():
        try:
            return json.loads(_STATE_PATH.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load update state: %s", e)
    return dict(_DEFAULT_STATE)


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    os.rename(str(tmp), str(_STATE_PATH))


def get_update_state() -> dict:
    return _load_state()


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(*args: str) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# US1: Update checking and notification
# ---------------------------------------------------------------------------


def check_for_updates() -> dict:
    """Check if upstream has new commits beyond local HEAD."""
    try:
        fetch = _git("fetch", UPSTREAM_REMOTE)
        if fetch.returncode != 0:
            logger.warning("git fetch %s failed: %s", UPSTREAM_REMOTE, fetch.stderr.strip())
            return {"update_available": False, "error": f"git fetch failed: {fetch.stderr.strip()}"}
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("git fetch failed: %s", e)
        return {"update_available": False, "error": str(e)}

    try:
        local_sha = _git("rev-parse", "HEAD").stdout.strip()
        upstream_sha = _git("rev-parse", f"{UPSTREAM_REMOTE}/main").stdout.strip()
    except Exception as e:
        return {"update_available": False, "error": str(e)}

    if local_sha == upstream_sha:
        return {"update_available": False}

    state = _load_state()
    if state.get("last_notified_sha") == upstream_sha or state.get("skipped_sha") == upstream_sha:
        return {"update_available": False, "already_notified": True}

    log_result = _git("log", f"HEAD..{UPSTREAM_REMOTE}/main", "--oneline", "--no-merges")
    raw_log = log_result.stdout.strip() if log_result.returncode == 0 else ""
    commit_count = len(raw_log.splitlines()) if raw_log else 0

    return {
        "update_available": True,
        "local_sha": local_sha,
        "upstream_sha": upstream_sha,
        "commit_count": commit_count,
        "raw_log": raw_log,
    }


def generate_changelog_summary(raw_log: str, commit_count: int) -> str:
    """Use Claude Haiku to summarize git commits into user-friendly bullet points."""
    if not ANTHROPIC_API_KEY:
        return raw_log  # Fallback to raw log if no API key

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Summarize these {commit_count} git commits into 2-4 plain-language bullet points "
                        "describing what changed for a non-technical user. Focus on new features, bug fixes, "
                        "and improvements. Ignore refactoring or CI changes. Use bullet points (- ). "
                        f"Commits:\n{raw_log}"
                    ),
                }
            ],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning("Changelog summary failed, using raw log: %s", e)
        return raw_log


async def notify_update_available(upstream_sha: str, summary: str, commit_count: int) -> None:
    """Send update notification via WhatsApp to admin."""
    from src.whatsapp import send_message

    message = (
        "\U0001f504 *Update Available*\n\n"
        f"{commit_count} improvement(s) since your last update:\n\n"
        f"{summary}\n\n"
        "Reply *update* to apply, or *skip* to ignore this update."
    )
    await send_message(ADMIN_PHONE, message)

    state = _load_state()
    state["last_notified_sha"] = upstream_sha
    _save_state(state)
    logger.info("Update notification sent (upstream: %s)", upstream_sha[:7])


# ---------------------------------------------------------------------------
# US2: Apply update
# ---------------------------------------------------------------------------


def backup_data() -> str:
    """Create a timestamped backup of the data directory."""
    now = datetime.now(TIMEZONE)
    backup_name = f"pre-update-{now.strftime('%Y%m%d-%H%M%S')}"
    backup_path = _BACKUP_DIR / backup_name

    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        _DATA_DIR,
        backup_path,
        ignore=shutil.ignore_patterns("backups", "__pycache__"),
    )
    logger.info("Data backed up to %s", backup_path)

    # Keep only the most recent backups
    existing = sorted(_BACKUP_DIR.iterdir(), key=lambda p: p.name, reverse=True)
    for old_backup in existing[_MAX_BACKUPS:]:
        if old_backup.is_dir():
            shutil.rmtree(old_backup)
            logger.info("Removed old backup: %s", old_backup.name)

    return str(backup_path)


async def apply_update() -> dict:
    """Pull upstream changes and trigger redeploy."""
    result = check_for_updates()
    if not result.get("update_available"):
        return {"success": False, "reason": "already_up_to_date"}

    old_sha = result["local_sha"]

    # Backup data
    backup_path = backup_data()

    # Attempt merge
    merge = _git("merge", f"{UPSTREAM_REMOTE}/main", "--no-edit")
    if merge.returncode != 0:
        logger.error("Merge failed: %s", merge.stderr.strip())
        _git("merge", "--abort")
        return {"success": False, "reason": "merge_conflict", "backup_path": backup_path}

    new_sha = _git("rev-parse", "HEAD").stdout.strip()

    # Update state
    state = _load_state()
    state["pre_update_sha"] = old_sha
    state["deployed_sha"] = new_sha
    state["last_update_time"] = datetime.now(TIMEZONE).isoformat()
    state["pre_update_backup_path"] = backup_path
    state["skipped_sha"] = None
    _save_state(state)

    # Trigger redeploy (Railway CLI if available)
    try:
        deploy = subprocess.run(
            ["railway", "up", "--detach", "--service", "fastapi"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if deploy.returncode != 0:
            logger.warning("Railway deploy command failed: %s", deploy.stderr.strip())
    except FileNotFoundError:
        logger.info("Railway CLI not available — redeploy must be triggered externally")
    except subprocess.TimeoutExpired:
        logger.warning("Railway deploy timed out")

    return {"success": True, "old_sha": old_sha, "new_sha": new_sha, "backup_path": backup_path}


async def handle_update_command(sender_phone: str) -> str:
    """Handle 'update' command from WhatsApp."""
    if sender_phone != ADMIN_PHONE:
        return "Only the admin can apply updates."

    from src.whatsapp import send_message

    await send_message(ADMIN_PHONE, "\u2699\ufe0f Applying update... this may take a moment.")

    result = await apply_update()

    if result.get("success"):
        msg = (
            "\u2705 *Update Applied*\n\n"
            f"Updated from {result['old_sha'][:7]} to {result['new_sha'][:7]}. "
            "Data backed up. The app will restart shortly.\n\n"
            "Reply *undo update* within 7 days to rollback."
        )
    elif result.get("reason") == "already_up_to_date":
        msg = "\u2705 Already up to date — no update needed."
    elif result.get("reason") == "merge_conflict":
        msg = (
            "\u274c *Update Failed*\n\n"
            "The update has merge conflicts that need manual resolution. "
            "Your data has been backed up and no changes were applied."
        )
    else:
        msg = f"\u274c Update failed: {result.get('reason', 'unknown error')}"

    await send_message(ADMIN_PHONE, msg)
    return msg


async def handle_skip_command(sender_phone: str) -> str:
    """Handle 'skip' command — suppress notification for this update."""
    if sender_phone != ADMIN_PHONE:
        return "Only the admin can manage updates."

    state = _load_state()
    state["skipped_sha"] = state.get("last_notified_sha")
    _save_state(state)

    msg = "Got it \u2014 I'll skip this update. I'll notify you when the next one is available."
    from src.whatsapp import send_message

    await send_message(ADMIN_PHONE, msg)
    return msg


# ---------------------------------------------------------------------------
# US3: Rollback
# ---------------------------------------------------------------------------


async def rollback_update() -> dict:
    """Revert to pre-update version and restore data backup."""
    state = _load_state()

    if not state.get("pre_update_sha"):
        return {"success": False, "reason": "no_recent_update"}

    if state.get("last_update_time"):
        update_time = datetime.fromisoformat(state["last_update_time"])
        now = datetime.now(TIMEZONE)
        if now - update_time > timedelta(days=_ROLLBACK_GRACE_DAYS):
            return {"success": False, "reason": "grace_period_expired"}

    pre_sha = state["pre_update_sha"]

    # Revert code
    reset = _git("reset", "--hard", pre_sha)
    if reset.returncode != 0:
        return {"success": False, "reason": f"git reset failed: {reset.stderr.strip()}"}

    # Restore data backup if available
    backup_path = state.get("pre_update_backup_path")
    if backup_path and Path(backup_path).exists():
        # Remove current data files (except backups/ and update_state.json)
        for item in _DATA_DIR.iterdir():
            if item.name in ("backups", "update_state.json"):
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # Copy backup contents back
        backup_dir = Path(backup_path)
        for item in backup_dir.iterdir():
            dest = _DATA_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        logger.info("Data restored from backup: %s", backup_path)

    # Update state
    state["deployed_sha"] = pre_sha
    state["pre_update_sha"] = None
    state["pre_update_backup_path"] = None
    state["last_update_time"] = None
    _save_state(state)

    # Trigger redeploy
    try:
        subprocess.run(
            ["railway", "up", "--detach", "--service", "fastapi"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.info("Railway CLI not available for redeploy")

    return {"success": True, "reverted_to": pre_sha}


async def handle_undo_command(sender_phone: str) -> str:
    """Handle 'undo update' command from WhatsApp."""
    if sender_phone != ADMIN_PHONE:
        return "Only the admin can rollback updates."

    from src.whatsapp import send_message

    result = await rollback_update()

    if result.get("success"):
        sha = result["reverted_to"][:7]
        msg = (
            "\u23ea *Update Rolled Back*\n\n"
            f"Reverted to previous version ({sha}). Data restored from backup. "
            "The app will restart shortly."
        )
    elif result.get("reason") == "no_recent_update":
        msg = "No recent update to undo."
    elif result.get("reason") == "grace_period_expired":
        msg = (
            f"The rollback window ({_ROLLBACK_GRACE_DAYS} days) has passed. "
            "Manual rollback may be needed — check the deployment docs."
        )
    else:
        msg = f"\u274c Rollback failed: {result.get('reason', 'unknown error')}"

    await send_message(ADMIN_PHONE, msg)
    return msg
