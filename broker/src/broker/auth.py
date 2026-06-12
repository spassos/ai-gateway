"""Autenticação: extrai a identidade corporativa da requisição.

A AUTORIZAÇÃO primária é do IAM do GCP (Cloud Run --no-allow-unauthenticated +
roles/run.invoker no grupo de devs). Esta validação é defesa em profundidade:
rejeita contas fora do domínio corporativo mesmo se o IAM estiver mal
configurado. O token nunca é logado.
"""

import logging

from fastapi import HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from .config import Settings

logger = logging.getLogger(__name__)

_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def authenticate(request: Request, settings: Settings) -> str:
    """Retorna o e-mail corporativo verificado ou levanta 401/403."""
    if settings.broker_dev_fake_auth:
        dev_email = request.headers.get("X-Dev-Email")
        if dev_email:
            return dev_email.lower()

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer <google_id_token> ausente")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        # audience=None: o ID token do `gcloud auth print-identity-token` de
        # contas de usuário tem aud fixo do client do gcloud; o IAM do Cloud Run
        # já fez a autorização. Assinatura (JWKS) e exp são verificados aqui.
        claims = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), audience=None
        )
    except Exception as exc:  # token inválido/expirado/assinatura errada
        raise HTTPException(status_code=401, detail="Google ID token inválido") from exc

    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise HTTPException(status_code=401, detail="Issuer inválido")
    if not claims.get("email_verified"):
        raise HTTPException(status_code=403, detail="E-mail não verificado")

    email = (claims.get("email") or "").lower()
    domain = settings.broker_allowed_domain.lower().strip()
    allowed_emails = {
        e.strip().lower() for e in settings.broker_allowed_emails.split(",") if e.strip()
    }
    # `hd` só existe em contas Workspace; o fallback de sufixo cobre tokens sem o claim.
    hosted_domain = (claims.get("hd") or "").lower()
    domain_ok = bool(domain) and (hosted_domain == domain or email.endswith(f"@{domain}"))
    # Sem Workspace (sem domínio), a autorização fina é por allowlist de e-mails.
    # Nada configurado = nega tudo (fail closed), mesmo que o IAM deixe passar.
    if not domain_ok and email not in allowed_emails:
        raise HTTPException(status_code=403, detail="Conta não autorizada para o gateway")

    return email
