from __future__ import annotations

import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_df_to_records_does_not_mutate_input_and_converts_types() -> None:
    from services.serialization import df_to_records

    df = pd.DataFrame(
        {
            "a": [1.0, np.nan],
            "t": [pd.Timestamp("2026-01-01 00:00:00"), pd.NaT],
        }
    )
    before = df.copy(deep=True)

    records = df_to_records(df)
    pd.testing.assert_frame_equal(df, before)

    assert records[0]["a"] == 1.0
    assert records[1]["a"] is None

    assert isinstance(records[0]["t"], str)
    assert records[0]["t"].startswith("2026-01-01")
    assert records[1]["t"] is None


def test_df_to_records_limit_does_not_mutate_input() -> None:
    from services.serialization import df_to_records

    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    before = df.copy(deep=True)
    records = df_to_records(df, limit=1)
    pd.testing.assert_frame_equal(df, before)
    assert len(records) == 1
