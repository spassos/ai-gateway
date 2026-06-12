import httpx
import pytest
from fastapi import FastAPI

from broker import audit
from broker.config import Settings
from broker.routes import router


class FakeLiteLLM:
    def __init__(self, existing_keys: list[str] | None = None, user_exists: bool = False):
        self.existing_keys = existing_keys or []
        self.user_exists = user_exists
        self.deleted: list[str] = []

    async def upsert_user(self, email: str) -> bool:
        return not self.user_exists

    async def list_user_keys(self, email: str) -> list[str]:
        return self.existing_keys

    async def delete_keys(self, tokens: list[str]) -> None:
        self.deleted = tokens

    async def generate_key(self, email: str) -> str:
        return "sk-new-key"

    async def user_info(self, email: str) -> dict:
        return {"user_info": {"max_budget": 50.0, "spend": 1.25, "budget_reset_at": None}}

    async def key_info(self, virtual_key: str) -> dict:
        if virtual_key != "sk-new-key":
            raise RuntimeError("key not found")
        return {"info": {"user_id": "dev@empresa.com"}}


def make_settings(**overrides) -> Settings:
    defaults = dict(
        litellm_master_key="sk-master",
        database_url="postgresql://x:y@localhost/db",
        broker_allowed_domain="empresa.com",
        broker_dev_fake_auth=True,
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture
def audit_events(monkeypatch):
    events: list[dict] = []

    async def fake_record(engine, actor_email, action, details=None, source_ip=None):
        events.append({"actor_email": actor_email, "action": action, "details": details or {}})

    monkeypatch.setattr(audit, "record", fake_record)
    return events


def make_client(litellm: FakeLiteLLM, settings: Settings) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(router)
    app.state.settings = settings
    app.state.litellm = litellm
    app.state.engine = None  # audit.record é mockado nos testes
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_provision_creates_user_and_returns_key(audit_events):
    litellm = FakeLiteLLM()
    async with make_client(litellm, make_settings()) as client:
        response = await client.post("/v1/provision", headers={"X-Dev-Email": "dev@empresa.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["api_key"] == "sk-new-key"
    assert body["user_email"] == "dev@empresa.com"
    assert body["budget"]["max"] == 50.0
    assert audit_events[-1]["action"] == audit.AuditAction.USER_CREATED


async def test_provision_rotates_existing_keys(audit_events):
    litellm = FakeLiteLLM(existing_keys=["sk-old-1", "sk-old-2"], user_exists=True)
    async with make_client(litellm, make_settings()) as client:
        response = await client.post("/v1/provision", headers={"X-Dev-Email": "dev@empresa.com"})

    assert response.status_code == 200
    assert litellm.deleted == ["sk-old-1", "sk-old-2"]
    assert audit_events[-1]["action"] == audit.AuditAction.KEY_ROTATED
    assert audit_events[-1]["details"]["rotated_keys"] == 2


async def test_provision_denied_without_credentials_is_audited(audit_events):
    settings = make_settings(broker_dev_fake_auth=False)
    async with make_client(FakeLiteLLM(), settings) as client:
        response = await client.post("/v1/provision")

    assert response.status_code == 401
    assert audit_events[-1]["action"] == audit.AuditAction.PROVISION_DENIED


async def test_provision_denied_for_wrong_domain(audit_events, monkeypatch):
    settings = make_settings(broker_dev_fake_auth=False)

    monkeypatch.setattr(
        "broker.auth.google_id_token.verify_oauth2_token",
        lambda token, request, audience=None: {
            "iss": "https://accounts.google.com",
            "email": "intruso@gmail.com",
            "email_verified": True,
        },
    )
    async with make_client(FakeLiteLLM(), settings) as client:
        response = await client.post(
            "/v1/provision", headers={"Authorization": "Bearer fake-token"}
        )

    assert response.status_code == 403
    assert audit_events[-1]["action"] == audit.AuditAction.PROVISION_DENIED


async def test_provision_allows_email_in_allowlist_without_domain(audit_events, monkeypatch):
    # Cenário sem Google Workspace: domínio vazio, autorização por allowlist.
    settings = make_settings(
        broker_dev_fake_auth=False,
        broker_allowed_domain="",
        broker_allowed_emails="sergio.passos88@gmail.com, outra@gmail.com",
    )
    monkeypatch.setattr(
        "broker.auth.google_id_token.verify_oauth2_token",
        lambda token, request, audience=None: {
            "iss": "https://accounts.google.com",
            "email": "Sergio.Passos88@gmail.com",
            "email_verified": True,
        },
    )
    async with make_client(FakeLiteLLM(), settings) as client:
        response = await client.post(
            "/v1/provision", headers={"Authorization": "Bearer fake-token"}
        )

    assert response.status_code == 200
    assert response.json()["user_email"] == "sergio.passos88@gmail.com"


async def test_provision_denies_everything_when_nothing_configured(audit_events, monkeypatch):
    # Fail closed: sem domínio e sem allowlist, nenhuma conta passa.
    settings = make_settings(
        broker_dev_fake_auth=False, broker_allowed_domain="", broker_allowed_emails=""
    )
    monkeypatch.setattr(
        "broker.auth.google_id_token.verify_oauth2_token",
        lambda token, request, audience=None: {
            "iss": "https://accounts.google.com",
            "email": "qualquer@gmail.com",
            "email_verified": True,
        },
    )
    async with make_client(FakeLiteLLM(), settings) as client:
        response = await client.post(
            "/v1/provision", headers={"Authorization": "Bearer fake-token"}
        )

    assert response.status_code == 403


async def test_me_returns_budget_for_valid_key():
    async with make_client(FakeLiteLLM(), make_settings()) as client:
        response = await client.get("/v1/me", headers={"Authorization": "Bearer sk-new-key"})

    assert response.status_code == 200
    body = response.json()
    assert body["user_email"] == "dev@empresa.com"
    assert body["budget"]["spent"] == 1.25


async def test_me_rejects_unknown_key():
    async with make_client(FakeLiteLLM(), make_settings()) as client:
        response = await client.get("/v1/me", headers={"Authorization": "Bearer sk-revoked"})

    assert response.status_code == 401
