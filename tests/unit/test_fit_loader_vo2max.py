from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class _FakeField:
    def __init__(self, name: str, value, def_num: int | None = None):
        self.name = name
        self.value = value
        self.def_num = def_num


class _FakeMessage:
    def __init__(self, fields: list[_FakeField], *, name: str = "record", mesg_num: int | None = None):
        self.fields = fields
        self.name = name
        self.mesg_num = mesg_num


class _FakeFit:
    def __init__(self, mapping: dict[str, list[_FakeMessage]]):
        self._mapping = mapping

    def get_messages(self, name: str | None = None):
        if name is None:
            out: list[_FakeMessage] = []
            for messages in self._mapping.values():
                out.extend(messages)
            return out
        return self._mapping.get(name, [])


class TestFitLoaderVo2max(unittest.TestCase):
    def test_backfill_skips_fit_and_parquet_write_when_vo2max_is_valid(self) -> None:
        from progress._utils import _maybe_backfill_vo2max_from_fit

        df = pd.DataFrame({"vo2max": [None, 52.4]})

        with TemporaryDirectory() as tmp_dir:
            activity_dir = Path(tmp_dir)
            (activity_dir / "original.fit").write_bytes(b"fit")
            parquet_path = activity_dir / "df.parquet"

            with (
                patch("progress._utils.load_fit") as load_fit_mock,
                patch.object(pd.DataFrame, "to_parquet") as to_parquet_mock,
            ):
                result = _maybe_backfill_vo2max_from_fit(activity_dir, parquet_path, df)

        self.assertIs(result, df)
        load_fit_mock.assert_not_called()
        to_parquet_mock.assert_not_called()

    def test_backfill_still_reads_fit_when_existing_vo2max_is_invalid(self) -> None:
        from progress._utils import _maybe_backfill_vo2max_from_fit

        df = pd.DataFrame({"vo2max": [None, 120.0]})

        with TemporaryDirectory() as tmp_dir:
            activity_dir = Path(tmp_dir)
            (activity_dir / "original.fit").write_bytes(b"fit")
            parquet_path = activity_dir / "df.parquet"

            with (
                patch("progress._utils.load_fit", return_value=object()) as load_fit_mock,
                patch("progress._utils._extract_fit_vo2max", return_value=54.8),
                patch.object(pd.DataFrame, "to_parquet") as to_parquet_mock,
            ):
                result = _maybe_backfill_vo2max_from_fit(activity_dir, parquet_path, df)

        load_fit_mock.assert_called_once()
        to_parquet_mock.assert_called_once_with(parquet_path, engine="pyarrow")
        self.assertIsNot(result, df)
        self.assertTrue(bool((result["vo2max"] == 54.8).all()))

    def test_extracts_vo2max_from_user_metrics_first(self) -> None:
        from core.fit_loader import _extract_fit_vo2max

        fit = _FakeFit(
            {
                "user_metrics": [_FakeMessage([_FakeField("vo2_max", 52.4)])],
                "record": [_FakeMessage([_FakeField("vo2_max", 49.0)])],
            }
        )

        value = _extract_fit_vo2max(fit)  # type: ignore[arg-type]
        self.assertAlmostEqual(value, 52.4, places=4)

    def test_ignores_invalid_values_and_reads_string_numeric(self) -> None:
        from core.fit_loader import _extract_fit_vo2max

        fit = _FakeFit(
            {
                "user_profile": [
                    _FakeMessage([
                        _FakeField("vo2_max", "not-a-number"),
                        _FakeField("vo2_max", "54.8"),
                    ])
                ]
            }
        )

        value = _extract_fit_vo2max(fit)  # type: ignore[arg-type]
        self.assertAlmostEqual(value, 54.8, places=4)

    def test_extracts_vo2max_from_unknown_140_metmax_field(self) -> None:
        from core.fit_loader import _extract_fit_vo2max

        fit = _FakeFit(
            {
                "unknown_140": [
                    _FakeMessage(
                        [_FakeField("unknown_7", 1082223, def_num=7)],
                        name="unknown_140",
                        mesg_num=140,
                    )
                ]
            }
        )

        value = _extract_fit_vo2max(fit)  # type: ignore[arg-type]
        self.assertAlmostEqual(value, 57.79694366455078, places=6)

    def test_prefers_unknown_79_user_metrics_over_unknown_140_activity_metrics(self) -> None:
        from core.fit_loader import _extract_fit_vo2max

        fit = _FakeFit(
            {
                "unknown_79": [
                    _FakeMessage(
                        [_FakeField("unknown_17", 1080377, def_num=17)],
                        name="unknown_79",
                        mesg_num=79,
                    )
                ],
                "unknown_140": [
                    _FakeMessage(
                        [_FakeField("unknown_7", 1082223, def_num=7)],
                        name="unknown_140",
                        mesg_num=140,
                    )
                ],
            }
        )

        value = _extract_fit_vo2max(fit)  # type: ignore[arg-type]
        self.assertAlmostEqual(value, 57.69835662841797, places=6)


if __name__ == "__main__":
    unittest.main()
