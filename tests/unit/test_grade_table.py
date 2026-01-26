from __future__ import annotations

import unittest

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestGradeTable(unittest.TestCase):
    def test_grade_factor_basics(self) -> None:
        from core.grade_table import grade_factor

        self.assertAlmostEqual(grade_factor(0.0), 1.0, places=6)
        self.assertGreater(grade_factor(5.0), 1.0)
        self.assertLess(grade_factor(-5.0), 1.0)


if __name__ == "__main__":
    unittest.main()
