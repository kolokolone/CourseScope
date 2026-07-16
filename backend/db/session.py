from __future__ import annotations

import os
import importlib

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_data_dir

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

    # Explicit, idempotent migrations for existing local databases.
    importlib.import_module("db.migrations.20260714_race_planning").upgrade(engine)
    importlib.import_module("db.migrations.20260716_pace_hr_resolutions").upgrade(engine)
    importlib.import_module("db.migrations.20260716_race_stop_label").upgrade(engine)

    # Lightweight migrations for SQLite (local default): add new nullable columns
    # without requiring users to delete their DB.
    try:
        if engine.dialect.name == "sqlite":
            with engine.begin() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA busy_timeout=5000"))

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
                if "fast_indexation_date" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN fast_indexation_date TEXT"))
                if "slow_indexation_date" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN slow_indexation_date TEXT"))
                # P2: new columns (audit SQLite)
                if "elevation_loss_m" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN elevation_loss_m REAL"))
                if "pace_first_half_s_per_km" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN pace_first_half_s_per_km REAL"))
                if "pace_second_half_s_per_km" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN pace_second_half_s_per_km REAL"))
                if "power_normalized_w" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN power_normalized_w REAL"))
                if "power_intensity_factor" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN power_intensity_factor REAL"))
                if "power_tss" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN power_tss REAL"))
                if "cadence_mean_spm" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN cadence_mean_spm REAL"))
                if "cadence_max_spm" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN cadence_max_spm REAL"))
                # P1: HR zone time columns for intensity distribution
                if "z1_time_s" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN z1_time_s REAL"))
                if "z2_time_s" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN z2_time_s REAL"))
                if "z3_time_s" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN z3_time_s REAL"))
                if "z4_time_s" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN z4_time_s REAL"))
                if "z5_time_s" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN z5_time_s REAL"))
                if "hr_max_used_bpm" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN hr_max_used_bpm REAL"))
                if "hr_max_source" not in progress_cols:
                    conn.execute(text("ALTER TABLE progress_activity_index ADD COLUMN hr_max_source TEXT"))
                # P1: drop redundant column cardiac_drift_pct
                try:
                    conn.execute(text("ALTER TABLE progress_activity_index DROP COLUMN cardiac_drift_pct"))
                except Exception:
                    pass  # SQLite < 3.35, column will persist physically

                # P2-P3: new indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_activity_sources_activity_id ON activity_sources(activity_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_progress_activity_type ON progress_activity_index(activity_type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_progress_tags_source ON progress_activity_tags(source)"))

                # P1: HR zone time columns in daily aggregates
                daily_cols = [
                    str(row[1])
                    for row in conn.execute(text("PRAGMA table_info(progress_daily_aggregates)"))
                ]
                if "z1_time_s" not in daily_cols:
                    conn.execute(text("ALTER TABLE progress_daily_aggregates ADD COLUMN z1_time_s REAL"))
                if "z2_time_s" not in daily_cols:
                    conn.execute(text("ALTER TABLE progress_daily_aggregates ADD COLUMN z2_time_s REAL"))
                if "z3_time_s" not in daily_cols:
                    conn.execute(text("ALTER TABLE progress_daily_aggregates ADD COLUMN z3_time_s REAL"))
                if "z4_time_s" not in daily_cols:
                    conn.execute(text("ALTER TABLE progress_daily_aggregates ADD COLUMN z4_time_s REAL"))
                if "z5_time_s" not in daily_cols:
                    conn.execute(text("ALTER TABLE progress_daily_aggregates ADD COLUMN z5_time_s REAL"))
    except Exception:
        # Best-effort: app should stay usable even if migrations fail.
        pass
