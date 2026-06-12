import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import audit
from .config import get_settings
from .litellm_client import LiteLLMClient
from .routes import router

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.litellm = LiteLLMClient(settings)
        app.state.engine = audit.make_engine(settings.database_url)
        await audit.ensure_schema(app.state.engine)
        yield
        await app.state.litellm.aclose()
        await app.state.engine.dispose()

    app = FastAPI(title="ai-gateway-broker", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
