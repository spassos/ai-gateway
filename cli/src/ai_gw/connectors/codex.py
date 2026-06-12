"""Connector do Codex CLI: provider em ~/.codex/config.toml + key via env.

O Codex só lê a API key de variável de ambiente (env_key), nunca do config —
por isso gravamos também ~/.config/ai-gw/env.sh para o usuário dar source.
"""

import shutil
import time
from pathlib import Path

import tomlkit

from ..store import Credentials, config_dir

PROVIDER_ID = "ai-gw"
ENV_KEY = "AI_GW_API_KEY"


def config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def env_file_path() -> Path:
    return config_dir() / "env.sh"


def connect(credentials: Credentials) -> tuple[Path, Path]:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    document = tomlkit.document()
    if path.exists():
        backup = path.with_suffix(f".toml.bak-{int(time.time())}")
        shutil.copy2(path, backup)
        document = tomlkit.parse(path.read_text())

    document["model_provider"] = PROVIDER_ID

    providers = document.setdefault("model_providers", tomlkit.table())
    provider = tomlkit.table()
    provider["name"] = "AI Gateway"
    provider["base_url"] = f"{credentials.base_url.rstrip('/')}/v1"
    provider["env_key"] = ENV_KEY
    provider["wire_api"] = "chat"
    providers[PROVIDER_ID] = provider

    path.write_text(tomlkit.dumps(document))

    env_file = env_file_path()
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(f'export {ENV_KEY}="{credentials.api_key}"\n')
    env_file.chmod(0o600)

    return path, env_file


def disconnect() -> bool:
    path = config_path()
    removed = False
    if path.exists():
        document = tomlkit.parse(path.read_text())
        providers = document.get("model_providers")
        if providers is not None and PROVIDER_ID in providers:
            del providers[PROVIDER_ID]
            removed = True
        if document.get("model_provider") == PROVIDER_ID:
            del document["model_provider"]
            removed = True
        if removed:
            path.write_text(tomlkit.dumps(document))
    env_file = env_file_path()
    if env_file.exists():
        env_file.unlink()
        removed = True
    return removed
