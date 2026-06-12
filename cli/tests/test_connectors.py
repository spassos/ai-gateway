import json

import pytest
import tomlkit

from ai_gw.connectors import claude_code, codex
from ai_gw.store import Credentials


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AI_GW_CONFIG_DIR", str(tmp_path / ".config" / "ai-gw"))
    return tmp_path


@pytest.fixture
def credentials():
    return Credentials(
        api_key="sk-test-key",
        base_url="http://localhost:4000",
        user_email="dev@empresa.com",
        broker_url="http://localhost:8080",
    )


def test_claude_code_connect_creates_settings(fake_home, credentials):
    path = claude_code.connect(credentials)

    settings = json.loads(path.read_text())
    assert settings["env"]["ANTHROPIC_BASE_URL"] == "http://localhost:4000"
    assert settings["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-test-key"
    assert settings["env"]["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] == "1"


def test_claude_code_connect_preserves_existing_settings_and_backs_up(fake_home, credentials):
    path = claude_code.settings_path()
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"model": "opus", "env": {"FOO": "bar"}}))

    claude_code.connect(credentials)

    settings = json.loads(path.read_text())
    assert settings["model"] == "opus"
    assert settings["env"]["FOO"] == "bar"
    assert settings["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-test-key"
    backups = list(path.parent.glob("settings.json.bak-*"))
    assert len(backups) == 1


def test_claude_code_disconnect_removes_only_gateway_keys(fake_home, credentials):
    claude_code.connect(credentials)
    path = claude_code.settings_path()
    settings = json.loads(path.read_text())
    settings["env"]["FOO"] = "bar"
    path.write_text(json.dumps(settings))

    assert claude_code.disconnect() is True

    settings = json.loads(path.read_text())
    assert "ANTHROPIC_AUTH_TOKEN" not in settings["env"]
    assert settings["env"]["FOO"] == "bar"


def test_codex_connect_writes_valid_toml_and_env_file(fake_home, credentials):
    config_path, env_file = codex.connect(credentials)

    document = tomlkit.parse(config_path.read_text())
    assert document["model_provider"] == "ai-gw"
    provider = document["model_providers"]["ai-gw"]
    assert provider["base_url"] == "http://localhost:4000/v1"
    assert provider["env_key"] == "AI_GW_API_KEY"
    assert provider["wire_api"] == "chat"
    assert 'export AI_GW_API_KEY="sk-test-key"' in env_file.read_text()
    assert env_file.stat().st_mode & 0o777 == 0o600


def test_codex_connect_preserves_existing_config(fake_home, credentials):
    path = codex.config_path()
    path.parent.mkdir(parents=True)
    path.write_text('model = "gpt-5.4"\n# comentário do usuário\n')

    codex.connect(credentials)

    content = path.read_text()
    document = tomlkit.parse(content)
    assert document["model"] == "gpt-5.4"
    assert "# comentário do usuário" in content
    backups = list(path.parent.glob("config.toml.bak-*"))
    assert len(backups) == 1


def test_codex_disconnect_removes_provider(fake_home, credentials):
    codex.connect(credentials)

    assert codex.disconnect() is True

    document = tomlkit.parse(codex.config_path().read_text())
    assert "model_provider" not in document
    assert "ai-gw" not in document.get("model_providers", {})
    assert not codex.env_file_path().exists()
