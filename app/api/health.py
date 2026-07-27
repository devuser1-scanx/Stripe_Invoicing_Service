import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["Health"])
logger = logging.getLogger("scanx.database")


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/ready")
def readiness() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "database": "connected",
        }

    except Exception as exc:
        logger.exception(
            "DATABASE CONNECTION FAILED: %s: %s",
            type(exc).__name__,
            str(exc),
        )

        # Temporary diagnostic output.
        # Remove this print after the connection problem is fixed.
        print(
            f"DATABASE CONNECTION FAILED | "
            f"{type(exc).__name__} | {exc}",
            flush=True,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc