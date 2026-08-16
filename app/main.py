from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.ready import router as ready_router
from app.config import get_settings
from app.infrastructure.logging.setup import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)
    logger.info("app_startup", environment=settings.environment)
    yield
    logger.info("app_shutdown")


app = FastAPI(title="Compliment Bot", lifespan=lifespan)
app.include_router(health_router)
app.include_router(ready_router)
