import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.routes import router
from app.common.error_handlers import register_error_handlers
from app.config.settings import load_settings
from app.container import create_container

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    container = create_container(settings)
    app.state.container = container
    try:
        await container.broker.connect()
    except Exception:
        logger.exception("RabbitMQ unavailable during API startup; async events remain protected by the outbox")
    try:
        yield
    finally:
        await container.close()


def create_app() -> FastAPI:
    settings = load_settings()
    application = FastAPI(title=settings.application.name, lifespan=lifespan)
    application.include_router(router)
    register_error_handlers(application)

    def simplified_openapi() -> dict:
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            routes=application.routes,
        )
        for path in schema.get("paths", {}).values():
            for operation in path.values():
                if not isinstance(operation, dict):
                    continue
                responses = operation.get("responses", {})
                if responses.pop("422", None) is not None:
                    responses.setdefault("400", {"description": "Bad Request"})
        application.openapi_schema = schema
        return schema

    application.openapi = simplified_openapi
    return application


app = create_app()
