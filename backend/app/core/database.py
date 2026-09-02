"""Database engine and session management."""
from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# SQLite (tests) and Postgres (prod) need different engine args. For Postgres
# we tune the connection pool so each API replica reuses connections instead of
# opening one per request; a real deployment also fronts Postgres with PgBouncer
# and points read traffic at replicas.
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    engine = create_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=1800,
    )


def init_db() -> None:
    """Create tables. In production this would be Alembic migrations."""
    # Import models so they register with SQLModel.metadata before create_all.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
