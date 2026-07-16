"""Rebuild the derived Pace-HR table for native multi-resolution bins."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from db.models import ProgressPaceHrBin


MIGRATION_ID = "20260716_pace_hr_resolutions"


def upgrade(engine: Engine) -> None:
    inspector = inspect(engine)
    if "progress_pace_hr_bins" not in inspector.get_table_names():
        ProgressPaceHrBin.__table__.create(bind=engine, checkfirst=True)
        return

    columns = {
        str(column["name"])
        for column in inspector.get_columns("progress_pace_hr_bins")
    }
    if "bin_step_s_per_km" in columns:
        return

    # Cette table est un cache analytique entierement reconstruit par
    # l'indexation lente. La recreer evite de convertir des medianes 10 s/km en
    # pseudo-resolutions et permet d'installer la nouvelle contrainte unique.
    with engine.begin() as connection:
        ProgressPaceHrBin.__table__.drop(bind=connection, checkfirst=True)
        ProgressPaceHrBin.__table__.create(bind=connection)
