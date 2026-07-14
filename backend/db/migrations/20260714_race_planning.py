"""Add trace parquet metadata and relational race-planning tables.

Run through ``python -m db.migrations.run`` or automatically at backend start.
The migration is idempotent for the default SQLite database.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from db.models import RaceCoursePoint, RaceEquipmentItem, RaceNutritionItem, RacePlan, RaceScenario, RaceStop, RaceStrategySegment


MIGRATION_ID = "20260714_race_planning"


def upgrade(engine: Engine) -> None:
    for table in (RacePlan.__table__, RaceScenario.__table__, RaceStop.__table__, RaceStrategySegment.__table__, RaceNutritionItem.__table__, RaceEquipmentItem.__table__, RaceCoursePoint.__table__):
        table.create(bind=engine, checkfirst=True)
    additions = {
        "parquet_path": "TEXT",
        "parquet_source_hash_sha256": "VARCHAR(64)",
        "dataframe_schema_version": "VARCHAR(32)",
        "parquet_generated_at_utc": "TEXT",
    }
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            columns = {str(row[1]) for row in connection.execute(text("PRAGMA table_info(traces)"))}
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE traces ADD COLUMN {name} {sql_type}"))
            connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (id TEXT PRIMARY KEY, applied_at_utc TEXT NOT NULL)"))
            connection.execute(text("INSERT OR IGNORE INTO schema_migrations(id, applied_at_utc) VALUES (:id, CURRENT_TIMESTAMP)"), {"id": MIGRATION_ID})
        elif engine.dialect.name == "postgresql":
            for name, sql_type in additions.items():
                connection.execute(text(f"ALTER TABLE traces ADD COLUMN IF NOT EXISTS {name} {sql_type}"))
            connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (id TEXT PRIMARY KEY, applied_at_utc TEXT NOT NULL)"))
            connection.execute(text("INSERT INTO schema_migrations(id, applied_at_utc) VALUES (:id, CURRENT_TIMESTAMP) ON CONFLICT (id) DO NOTHING"), {"id": MIGRATION_ID})
