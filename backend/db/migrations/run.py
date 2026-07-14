from __future__ import annotations

import importlib

from db.session import make_engine
from db.models import Base


def main() -> None:
    engine = make_engine()
    Base.metadata.create_all(engine)
    migration = importlib.import_module("db.migrations.20260714_race_planning")
    migration.upgrade(engine)
    print(f"Applied {migration.MIGRATION_ID}")


if __name__ == "__main__":
    main()
