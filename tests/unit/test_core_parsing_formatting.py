from __future__ import annotations

import json
import unittest
from datetime import datetime

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestCoreParsingFormatting(unittest.TestCase):
    def test_parse_km_list(self) -> None:
        from core.parsing import parse_km_list

        self.assertEqual(parse_km_list(""), [])
        self.assertEqual(parse_km_list("5"), [5.0])
        self.assertEqual(parse_km_list("5km, 10 km,21.1"), [5.0, 10.0, 21.1])
        self.assertEqual(parse_km_list("-1, 2"), [2.0])

    def test_formatting(self) -> None:
        from core.formatting import format_duration_clock, format_duration_compact, format_time_of_day

        self.assertEqual(format_duration_clock(None), "-")
        self.assertEqual(format_duration_clock(65), "1:05")
        self.assertEqual(format_duration_compact(65), "1m05s")

        self.assertEqual(format_time_of_day(None), "-")
        self.assertEqual(format_time_of_day(datetime(2026, 1, 1, 12, 34, 56)), "12:34:56")

        # Les sorties doivent etre JSON-serialisables.
        json.dumps({
            "clock": format_duration_clock(65),
            "compact": format_duration_compact(65),
            "tod": format_time_of_day(datetime(2026, 1, 1, 12, 34, 56)),
        })


if __name__ == "__main__":
    unittest.main()
