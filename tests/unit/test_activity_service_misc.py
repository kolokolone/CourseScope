from __future__ import annotations

import unittest

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestActivityServiceMisc(unittest.TestCase):
    def test_suggest_default_view(self) -> None:
        from services.activity_service import suggest_default_view
        from services.models import ActivityTypeDetection

        self.assertEqual(suggest_default_view(ActivityTypeDetection(type="real_run", confidence=1.0)), "real")
        self.assertEqual(
            suggest_default_view(ActivityTypeDetection(type="theoretical_route", confidence=1.0)),
            "theoretical",
        )


if __name__ == "__main__":
    unittest.main()
