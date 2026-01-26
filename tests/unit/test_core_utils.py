from __future__ import annotations

import unittest

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestCoreUtils(unittest.TestCase):
    def test_mmss_to_seconds(self) -> None:
        from core.utils import mmss_to_seconds

        self.assertEqual(mmss_to_seconds("0:00"), 0)
        self.assertEqual(mmss_to_seconds("1:05"), 65)
        self.assertEqual(mmss_to_seconds("12:34"), 754)

    def test_seconds_to_mmss(self) -> None:
        from core.utils import seconds_to_mmss

        self.assertEqual(seconds_to_mmss(0), "0:00")
        self.assertEqual(seconds_to_mmss(65), "1:05")
        self.assertEqual(seconds_to_mmss(754), "12:34")


if __name__ == "__main__":
    unittest.main()
