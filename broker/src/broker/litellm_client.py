"""Cliente da API admin do LiteLLM. Único lugar que usa o master key."""

from typing import Any

import httpx

from .config import Settings


class LiteLLMClient:
    def __init__(self, settings: Settings):
        self._base_url = settings.litellm_base_url.rstrip("/")
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
            timeout=30.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def upsert_user(self, email: str) -> bool:
        """Garante o usuário com a policy de budget vigente. True se foi criado agora."""
        payload = {
            "user_id": email,
            "user_email": email,
            "max_budget": self._settings.broker_user_max_budget,
            "budget_duration": self._settings.broker_user_budget_duration,
        }
        response = await self._client.post("/user/new", json=payload)
        if response.status_code == 200:
            return True
        # Usuário já existe → reaplica a policy (mudanças de budget valem no próximo login).
        update = await self._client.post("/user/update", json=payload)
        update.raise_for_status()
        return False

    async def list_user_keys(self, email: str) -> list[str]:
        response = await self._client.get("/user/info", params={"user_id": email})
        response.raise_for_status()
        keys = response.json().get("keys") or []
        return [k["token"] for k in keys if k.get("token")]

    async def delete_keys(self, tokens: list[str]) -> None:
        if not tokens:
            return
        response = await self._client.post("/key/delete", json={"keys": tokens})
        response.raise_for_status()

    async def generate_key(self, email: str) -> str:
        response = await self._client.post(
            "/key/generate",
            json={
                "user_id": email,
                "key_alias": f"ai-gw:{email}",
                "metadata": {"provisioned_by": "broker"},
            },
        )
        response.raise_for_status()
        return response.json()["key"]

    async def user_info(self, email: str) -> dict[str, Any]:
        response = await self._client.get("/user/info", params={"user_id": email})
        response.raise_for_status()
        return response.json()

    async def key_info(self, virtual_key: str) -> dict[str, Any]:
        """Resolve a virtual key do dev (sem master key) para user/gasto via /key/info."""
        response = await self._client.get("/key/info", params={"key": virtual_key})
        response.raise_for_status()
        return response.json()
