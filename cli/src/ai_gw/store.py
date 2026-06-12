"""Credenciais locais: ~/.config/ai-gw/credentials.json com modo 0600."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Credentials:
    api_key: str
    base_url: str
    user_email: str
    broker_url: str


def config_dir() -> Path:
    return Path(os.environ.get("AI_GW_CONFIG_DIR", Path.home() / ".config" / "ai-gw"))


def credentials_path() -> Path:
    return config_dir() / "credentials.json"


def save(credentials: Credentials) -> Path:
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(credentials), indent=2))
    path.chmod(0o600)
    return path


def load() -> Credentials | None:
    path = credentials_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return Credentials(**data)


def clear() -> bool:
    path = credentials_path()
    if path.exists():
        path.unlink()
        return True
    return False
