from collections.abc import Generator
from typing import Any

import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_connector: Connector | None = None


def _get_connector() -> Connector:
    global _connector
    if _connector is None:
        _connector = Connector(refresh_strategy="LAZY")
    return _connector


def _cloud_sql_connection() -> Any:
    ip_type = IPTypes.PRIVATE if settings.db_ip_type == "PRIVATE" else IPTypes.PUBLIC
    return _get_connector().connect(
        settings.instance_connection_name,
        "pg8000",
        user=settings.db_user,
        password=settings.db_password.get_secret_value(),
        db=settings.db_name,
        ip_type=ip_type,
    )


def _create_engine() -> Engine:
    options = {
        "pool_pre_ping": True,
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_recycle": settings.db_pool_recycle_seconds,
        "future": True,
    }

    if settings.use_tcp_database:
        url = sqlalchemy.engine.URL.create(
            drivername="postgresql+pg8000",
            username=settings.db_user,
            password=settings.db_password.get_secret_value(),
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
        )
        return sqlalchemy.create_engine(url, **options)

    return sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=_cloud_sql_connection,
        **options,
    )


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def close_database_resources() -> None:
    engine.dispose()
    global _connector
    if _connector is not None:
        _connector.close()
        _connector = None
