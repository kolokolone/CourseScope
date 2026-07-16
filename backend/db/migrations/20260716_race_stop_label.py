"""Add an optional user-facing label to persisted race stops."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from db.models import RaceStop


MIGRATION_ID = "20260716_race_stop_label"


def _record_migration(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(id TEXT PRIMARY KEY, applied_at_utc TEXT NOT NULL)"
            )
        )
        if engine.dialect.name == "sqlite":
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO schema_migrations(id, applied_at_utc) "
                    "VALUES (:id, CURRENT_TIMESTAMP)"
                ),
                {"id": MIGRATION_ID},
            )
        elif engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    "INSERT INTO schema_migrations(id, applied_at_utc) "
                    "VALUES (:id, CURRENT_TIMESTAMP) ON CONFLICT (id) DO NOTHING"
                ),
                {"id": MIGRATION_ID},
            )


def upgrade(engine: Engine) -> None:
    if "race_stops" not in inspect(engine).get_table_names():
        RaceStop.__table__.create(bind=engine, checkfirst=True)

    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            columns = {
                str(row[1])
                for row in connection.execute(text("PRAGMA table_info(race_stops)"))
            }
            if "label" not in columns:
                connection.execute(text("ALTER TABLE race_stops ADD COLUMN label TEXT"))
        elif engine.dialect.name == "postgresql":
            connection.execute(
                text("ALTER TABLE race_stops ADD COLUMN IF NOT EXISTS label TEXT")
            )

    _record_migration(engine)
