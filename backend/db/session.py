from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_data_dir

from .models import Base


def get_database_url() -> str:
    url = os.getenv("COURSESCOPE_DATABASE_URL")
    if url:
        return url

    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = (data_dir / "coursescope.sqlite").resolve()
    # SQLAlchemy expects 3 slashes for absolute paths.
    return f"sqlite:///{db_path.as_posix()}"


def make_engine() -> Engine:
    url = get_database_url()
    connect_args = {}
    if url.startswith("sqlite:"):
        # Needed for FastAPI TestClient (multi-threaded) + sqlite.
        connect_args = {"check_same_thread": False}
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
