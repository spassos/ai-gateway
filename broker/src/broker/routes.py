from typing import Any

from fastapi import APIRouter, HTTPException, Request

from . import audit
from .audit import AuditAction
from .auth import authenticate

router = APIRouter()


def _budget_payload(user_info: dict[str, Any], max_budget_default: float) -> dict[str, Any]:
    info = user_info.get("user_info") or {}
    return {
        "max": info.get("max_budget", max_budget_default),
        "spent": info.get("spend", 0.0),
        "period_end": info.get("budget_reset_at"),
    }


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/provision")
async def provision(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    litellm = request.app.state.litellm
    engine = request.app.state.engine
    source_ip = request.client.host if request.client else None

    try:
        email = authenticate(request, settings)
    except HTTPException as exc:
        await audit.record(
            engine,
            actor_email="unknown",
            action=AuditAction.PROVISION_DENIED,
            details={"status": exc.status_code, "reason": exc.detail},
            source_ip=source_ip,
        )
        raise

    created = await litellm.upsert_user(email)
    old_keys = await litellm.list_user_keys(email)
    await litellm.delete_keys(old_keys)
    api_key = await litellm.generate_key(email)

    action = AuditAction.USER_CREATED if created else AuditAction.KEY_ROTATED
    await audit.record(
        engine,
        actor_email=email,
        action=action,
        details={"rotated_keys": len(old_keys)},
        source_ip=source_ip,
    )

    user_info = await litellm.user_info(email)
    return {
        "api_key": api_key,
        "base_url": settings.gateway_public_url,
        "user_email": email,
        "budget": _budget_payload(user_info, settings.broker_user_max_budget),
    }


@router.get("/v1/me")
async def me(request: Request) -> dict[str, Any]:
    """Status de gasto. Bearer = a virtual key do dev (não o token Google)."""
    settings = request.app.state.settings
    litellm = request.app.state.litellm

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization: Bearer <virtual_key> ausente")
    virtual_key = authorization.removeprefix("Bearer ").strip()

    try:
        key_info = await litellm.key_info(virtual_key)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Virtual key inválida ou revogada") from exc

    email = (key_info.get("info") or {}).get("user_id")
    if not email:
        raise HTTPException(status_code=401, detail="Key sem usuário associado")

    user_info = await litellm.user_info(email)
    return {
        "user_email": email,
        "budget": _budget_payload(user_info, settings.broker_user_max_budget),
    }
