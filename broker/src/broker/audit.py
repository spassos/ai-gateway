"""Auditoria de identidade (Princípio 4 da constituição).

Schema `broker` separado para não colidir com as migrações do LiteLLM.
A auditoria de USO (por request) é do LiteLLM em LiteLLM_SpendLogs.
"""

import json
from enum import StrEnum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class AuditAction(StrEnum):
    LOGIN = "login"
    USER_CREATED = "user_created"
    KEY_ROTATED = "key_rotated"
    KEY_REVOKED = "key_revoked"
    PROVISION_DENIED = "provision_denied"


_DDL = """
CREATE SCHEMA IF NOT EXISTS broker;
CREATE TABLE IF NOT EXISTS broker.audit_events (
  id          BIGSERIAL PRIMARY KEY,
  ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_email TEXT NOT NULL,
  action      TEXT NOT NULL,
  details     JSONB NOT NULL DEFAULT '{}',
  source_ip   TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor ON broker.audit_events (actor_email, ts);
"""


def make_engine(database_url: str) -> AsyncEngine:
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_async_engine(async_url, pool_size=2, max_overflow=2)


async def ensure_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for statement in _DDL.strip().split(";"):
            if statement.strip():
                await conn.execute(text(statement))


async def record(
    engine: AsyncEngine,
    actor_email: str,
    action: AuditAction,
    details: dict | None = None,
    source_ip: str | None = None,
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO broker.audit_events (actor_email, action, details, source_ip) "
                "VALUES (:actor_email, :action, CAST(:details AS jsonb), :source_ip)"
            ),
            {
                "actor_email": actor_email,
                "action": action.value,
                "details": json.dumps(details or {}),
                "source_ip": source_ip,
            },
        )
