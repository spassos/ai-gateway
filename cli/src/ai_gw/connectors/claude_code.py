"""Connector do Claude Code: merge não destrutivo em ~/.claude/settings.json."""

import json
import shutil
import time
from pathlib import Path

from ..store import Credentials

GATEWAY_ENV_KEYS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY",
)


def settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def connect(credentials: Credentials) -> Path:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    settings: dict = {}
    if path.exists():
        backup = path.with_suffix(f".json.bak-{int(time.time())}")
        shutil.copy2(path, backup)
        settings = json.loads(path.read_text() or "{}")

    env = settings.setdefault("env", {})
    env["ANTHROPIC_BASE_URL"] = credentials.base_url
    env["ANTHROPIC_AUTH_TOKEN"] = credentials.api_key
    env["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] = "1"

    path.write_text(json.dumps(settings, indent=2) + "\n")
    return path


def disconnect() -> bool:
    path = settings_path()
    if not path.exists():
        return False
    settings = json.loads(path.read_text() or "{}")
    env = settings.get("env", {})
    removed = False
    for key in GATEWAY_ENV_KEYS:
        if key in env:
            del env[key]
            removed = True
    if removed:
        path.write_text(json.dumps(settings, indent=2) + "\n")
    return removed
