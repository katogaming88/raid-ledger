"""SQLAlchemy engine and session factory.

Supports SQLite (local dev) and PostgreSQL (Supabase prod) via DATABASE_URL.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from raid_ledger.db.schema import Base


def get_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine from a database URL.

    For SQLite, enables check_same_thread=False (needed for Streamlit's
    threaded model) and WAL journal mode for better concurrent reads.
    """
    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(database_url, connect_args=connect_args)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory bound to the given engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """Create all tables and indexes from the ORM schema."""
    Base.metadata.create_all(engine)
