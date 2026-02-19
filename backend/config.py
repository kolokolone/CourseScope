from __future__ import annotations

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Return the base data directory.

    Layout:
    - <data_dir>/activities
    - <data_dir>/integrations/garmin
    - <data_dir>/coursescope.sqlite (default DB, override via COURSESCOPE_DATABASE_URL)
    """

    value = os.getenv("COURSESCOPE_DATA_DIR", "./data")
    return Path(value)


def get_garmin_tokens_dir() -> Path:
    return get_data_dir() / "integrations" / "garmin" / "tokens"


def get_activities_dir() -> Path:
    return get_data_dir() / "activities"


def get_traces_dir() -> Path:
    return get_data_dir() / "traces"
