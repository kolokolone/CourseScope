from __future__ import annotations

import importlib

from db.session import make_engine
from db.models import Base


def main() -> None:
    engine = make_engine()
    Base.metadata.create_all(engine)
    migration_names = (
        "db.migrations.20260714_race_planning",
        "db.migrations.20260716_pace_hr_resolutions",
        "db.migrations.20260716_race_stop_label",
    )
    for migration_name in migration_names:
        migration = importlib.import_module(migration_name)
        migration.upgrade(engine)
        print(f"Applied {migration.MIGRATION_ID}")


if __name__ == "__main__":
    main()
