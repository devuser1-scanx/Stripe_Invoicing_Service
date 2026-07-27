from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.billing import router as billing_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import close_database_resources


@asynccontextmanager
async def lifespan(
    _: FastAPI,
) -> AsyncIterator[None]:
    configure_logging()

    yield

    close_database_resources()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url=(
        "/docs"
        if settings.environment != "production"
        else None
    ),
    redoc_url=None,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(billing_router)