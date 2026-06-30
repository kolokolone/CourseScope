from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestSettingsRepository(unittest.TestCase):
    def test_detected_hr_max_reads_progress_index(self) -> None:
        from db.models import Base, ProgressActivityIndex
        from db.settings_repository import SettingsRepository

        engine = create_engine('sqlite:///:memory:', future=True)
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

        session = Session()
        try:
            session.add(
                ProgressActivityIndex(
                    activity_id='a1',
                    activity_type='real',
                    start_ts_utc='2026-01-01T00:00:00Z',
                    local_date='2026-01-01',
                    tz='UTC',
                    fingerprint='fp-1',
                    metrics_version=1,
                    indexed_at_ts='2026-01-01T00:00:00Z',
                    distance_m=10000.0,
                    moving_time_s=3000.0,
                    elapsed_time_s=3100.0,
                    elevation_gain_m=100.0,
                    avg_pace_s_per_km=300.0,
                    best_pace_s_per_km=250.0,
                    pace_threshold_s_per_km=290.0,
                    avg_hr_bpm=150.0,
                    max_hr_bpm=188.0,
                    trimp=50.0,
                    training_load_method='edwards',
                    decoupling_pct=2.0,
                    stability_cv=0.1,
                    stability_iqr_ratio=0.1,
                    aerobic_efficiency_m_s_per_bpm=0.02,
                    has_hr=1,
                    has_power=0,
                    has_cadence=1,
                    data_points=100,
                )
            )
            session.commit()

            repo = SettingsRepository()
            self.assertEqual(repo.get_detected_hr_max(session), 188)
        finally:
            session.close()


if __name__ == '__main__':
    unittest.main()
