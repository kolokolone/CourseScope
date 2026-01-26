from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestSerialization(unittest.TestCase):
    def test_to_jsonable_loaded_activity(self) -> None:
        from services import activity_service
        from services.serialization import to_jsonable

        project_dir = Path(__file__).resolve().parents[2]
        fit_path = project_dir / "course.fit"
        loaded = activity_service.load_activity_from_bytes(fit_path.read_bytes(), fit_path.name)
        payload = to_jsonable(loaded, dataframe_limit=50)
        json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
