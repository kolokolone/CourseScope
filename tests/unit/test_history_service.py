from __future__ import annotations

import unittest

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestHistoryService(unittest.TestCase):
    def test_upsert_history_dedup_and_trim(self) -> None:
        from services.history_service import upsert_history

        history: list[dict] = [
            {"name": "a", "x": 1},
            {"name": "b", "x": 2},
        ]
        upsert_history(history, {"name": "b", "x": 99}, max_items=2)
        self.assertEqual([h["name"] for h in history], ["b", "a"])
        self.assertEqual(history[0]["x"], 99)


if __name__ == "__main__":
    unittest.main()
