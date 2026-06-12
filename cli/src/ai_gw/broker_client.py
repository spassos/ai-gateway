from typing import Any

import httpx


class BrokerError(RuntimeError):
    pass


def provision(
    broker_url: str, *, id_token: str | None = None, dev_email: str | None = None
) -> dict[str, Any]:
    headers: dict[str, str] = {}
    if dev_email:
        headers["X-Dev-Email"] = dev_email
    elif id_token:
        headers["Authorization"] = f"Bearer {id_token}"
    else:
        raise BrokerError("É preciso um identity token ou --dev-email")

    response = httpx.post(f"{broker_url.rstrip('/')}/v1/provision", headers=headers, timeout=30)
    if response.status_code == 403:
        raise BrokerError(
            "Acesso negado (403). Verifique se sua conta está no grupo de acesso "
            "do gateway e se é a conta corporativa."
        )
    if response.status_code != 200:
        raise BrokerError(f"Broker retornou {response.status_code}: {response.text}")
    return response.json()


def me(broker_url: str, api_key: str) -> dict[str, Any]:
    response = httpx.get(
        f"{broker_url.rstrip('/')}/v1/me",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    if response.status_code == 401:
        raise BrokerError("Sua key foi revogada ou expirou. Rode `ai-gw login` novamente.")
    if response.status_code != 200:
        raise BrokerError(f"Broker retornou {response.status_code}: {response.text}")
    return response.json()


def list_models(base_url: str, api_key: str) -> list[dict[str, Any]]:
    response = httpx.get(
        f"{base_url.rstrip('/')}/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    if response.status_code != 200:
        raise BrokerError(f"Gateway retornou {response.status_code}: {response.text}")
    return response.json().get("data", [])
