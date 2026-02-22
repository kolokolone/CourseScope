from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
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

    # Lightweight migrations for SQLite (local default): add new nullable columns
    # without requiring users to delete their DB.
    try:
        if engine.dialect.name == "sqlite":
            with engine.begin() as conn:
                cols = [
                    str(row[1])
                    for row in conn.execute(text("PRAGMA table_info(activities)"))
                ]
                if "progress_indexed_at_utc" not in cols:
                    conn.execute(text("ALTER TABLE activities ADD COLUMN progress_indexed_at_utc TEXT"))
                if "progress_rollup_path" not in cols:
                    conn.execute(text("ALTER TABLE activities ADD COLUMN progress_rollup_path TEXT"))

                goal_cols = [
                    str(row[1])
                    for row in conn.execute(text("PRAGMA table_info(goals)"))
                ]
                if "location_city" not in goal_cols:
                    conn.execute(text("ALTER TABLE goals ADD COLUMN location_city TEXT"))
                if "location_country" not in goal_cols:
                    conn.execute(text("ALTER TABLE goals ADD COLUMN location_country TEXT"))
                if "location_country_code" not in goal_cols:
                    conn.execute(text("ALTER TABLE goals ADD COLUMN location_country_code TEXT"))
                if "location_lat" not in goal_cols:
                    conn.execute(text("ALTER TABLE goals ADD COLUMN location_lat REAL"))
                if "location_lon" not in goal_cols:
                    conn.execute(text("ALTER TABLE goals ADD COLUMN location_lon REAL"))

                settings_cols = [
                    str(row[1])
                    for row in conn.execute(text("PRAGMA table_info(user_settings)"))
                ]
                if "vo2max_lastest" not in settings_cols:
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN vo2max_lastest REAL"))

                progress_cols = [
                    str(row[1])
                    for row in conn.execute(text("PRAGMA table_info(progress_activity_index)"))
                ]
                if "vo2max" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN vo2max REAL"))
    except Exception:
        # Best-effort: app should stay usable even if migrations fail.
        pass
