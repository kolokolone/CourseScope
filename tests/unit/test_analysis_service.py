from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestAnalysisService(unittest.TestCase):
    def test_load_activity_cache_roundtrip(self) -> None:
        from services.analysis_service import load_activity
        from services.cache import InMemoryCache
        from services.serialization import to_jsonable

        project_dir = Path(__file__).resolve().parents[2]
        fit_path = project_dir / "tests" / "course.fit"
        cache = InMemoryCache(max_items=8)

        loaded1 = load_activity(data=fit_path.read_bytes(), name=fit_path.name, cache=cache)
        loaded2 = load_activity(data=fit_path.read_bytes(), name=fit_path.name, cache=cache)
        self.assertEqual(loaded1.name, loaded2.name)
        payload = to_jsonable(loaded2, dataframe_limit=10)
        json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
