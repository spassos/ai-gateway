from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    litellm_base_url: str = "http://litellm:4000"
    litellm_master_key: str
    database_url: str
    gateway_public_url: str = "http://localhost:4000"

    broker_allowed_domain: str = "empresa.com"
    broker_user_max_budget: float = 50.0
    broker_user_budget_duration: str = "30d"
    # SOMENTE DEV: aceita X-Dev-Email no lugar do Google ID token.
    broker_dev_fake_auth: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
