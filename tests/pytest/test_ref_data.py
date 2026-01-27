from __future__ import annotations

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_pro_pace_vs_grade_provider_schema_and_info() -> None:
    from core.ref_data import get_pro_pace_vs_grade_df, get_pro_pace_vs_grade_info

    df = get_pro_pace_vs_grade_df()
    assert {"grade_percent", "pace_s_per_km_pro"}.issubset(set(df.columns))

    info = get_pro_pace_vs_grade_info()
    assert info.rows == int(len(df))
    assert info.source in {"file", "package", "missing"}
    if len(df) > 0:
        assert isinstance(info.sha256, str)
        assert len(info.sha256) == 64
