"""DB engine/session management (D-18): SQLite now, Postgres for pilot — same ORM
models, switched purely by DATABASE_URL."""

from collections.abc import Iterator
from contextlib import contextmanager

from config.settings import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# SQLite's default driver only allows the connection to be used from the thread that
# created it; FastAPI can hand a request to a different thread, so this is required
# for SQLite specifically. Postgres doesn't need it.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
