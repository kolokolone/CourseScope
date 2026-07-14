from __future__ import annotations

import unittest
import hashlib
import json
from unittest.mock import Mock, patch

import pandas as pd
import numpy as np

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestTraceStoreHelpers(unittest.TestCase):
    def test_route_fingerprint_is_stable(self) -> None:
        from storage.trace_store import compute_route_fingerprint

        df = pd.DataFrame(
            {
                'lat': [48.1, 48.1002, 48.1004],
                'lon': [2.3, 2.3002, 2.3004],
            }
        )
        a = compute_route_fingerprint(df)
        b = compute_route_fingerprint(df.copy())
        self.assertIsNotNone(a)
        self.assertEqual(a, b)

    def test_trace_metrics_compute_distance_and_elevation(self) -> None:
        from storage.trace_store import compute_trace_metrics

        df = pd.DataFrame(
            {
                'distance_m': [0.0, 500.0, 1000.0, 1500.0],
                'elevation': [100.0, 120.0, 110.0, 130.0],
            }
        )
        out = compute_trace_metrics(df)
        self.assertAlmostEqual(float(out['distance_km'] or 0.0), 1.5, places=6)
        self.assertAlmostEqual(float(out['elevation_gain_m'] or 0.0), 40.0, places=6)
        self.assertAlmostEqual(float(out['elevation_loss_m'] or 0.0), 10.0, places=6)
        self.assertEqual(float(out['elevation_min_m'] or 0.0), 100.0)
        self.assertEqual(float(out['elevation_max_m'] or 0.0), 130.0)

    def test_valid_parquet_is_loaded_without_reading_or_rebuilding_original(self) -> None:
        from core.contracts.activity_df_contract import SCHEMA_VERSION, coerce_activity_df
        from storage.trace_store import TraceStore
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            store = TraceStore(directory)
            trace_id = 'trace-parquet'
            trace_dir = store._get_trace_dir(trace_id)
            trace_dir.mkdir()
            original = trace_dir / 'original.gpx'
            original.write_bytes(b'unchanged')
            (trace_dir / 'df.parquet').write_bytes(b'parquet-placeholder')
            source_hash = hashlib.sha256(b'unchanged').hexdigest()
            stat = original.stat()
            metadata = {'source_sha256': source_hash, 'source_size_bytes': stat.st_size, 'source_mtime_ns': stat.st_mtime_ns, 'dataframe_schema_version': SCHEMA_VERSION, 'generated_at_utc': '2026-07-14T10:00:00+00:00'}
            (trace_dir / 'meta.json').write_text(json.dumps(metadata), encoding='utf-8')
            dataframe = coerce_activity_df(pd.DataFrame({'distance_m': [0.0, 10.0], 'elevation': [100.0, 101.0], 'delta_distance_m': [np.nan, 10.0], 'delta_time_s': [np.nan, 1.0], 'elapsed_time_s': [0.0, 1.0], 'speed_m_s': [np.nan, 10.0], 'pace_s_per_km': [np.nan, 100.0]}))
            rebuild = Mock()
            with patch('pandas.read_parquet', return_value=dataframe), patch.object(type(original), 'read_bytes', side_effect=AssertionError('original bytes must not be read')):
                loaded = store.load_or_rebuild_dataframe(trace_id, expected_source_hash=source_hash, rebuild=rebuild)
            self.assertEqual(loaded.source, 'parquet')
            rebuild.assert_not_called()

    def test_missing_parquet_rebuilds_from_original(self) -> None:
        from core.contracts.activity_df_contract import coerce_activity_df
        from storage.trace_store import TraceStore
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            store = TraceStore(directory)
            trace_id = 'trace-rebuild'
            trace_dir = store._get_trace_dir(trace_id)
            trace_dir.mkdir()
            original = trace_dir / 'original.gpx'
            original.write_bytes(b'source')
            source_hash = hashlib.sha256(b'source').hexdigest()
            dataframe = coerce_activity_df(pd.DataFrame({'distance_m': [0.0, 10.0], 'elevation': [100.0, 101.0], 'delta_distance_m': [np.nan, 10.0], 'delta_time_s': [np.nan, 1.0], 'elapsed_time_s': [0.0, 1.0], 'speed_m_s': [np.nan, 10.0], 'pace_s_per_km': [np.nan, 100.0]}))
            rebuild = Mock(return_value=dataframe)
            with patch.object(store, '_write_dataframe'):
                loaded = store.load_or_rebuild_dataframe(trace_id, expected_source_hash=source_hash, rebuild=rebuild)
            self.assertEqual(loaded.source, 'rebuilt')
            self.assertEqual(loaded.rebuild_reason, 'parquet_missing')
            rebuild.assert_called_once()

    def test_incompatible_parquet_schema_is_rebuilt(self) -> None:
        from core.contracts.activity_df_contract import coerce_activity_df
        from storage.trace_store import TraceStore
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            store = TraceStore(directory)
            trace_id = 'trace-old-schema'
            trace_dir = store._get_trace_dir(trace_id)
            trace_dir.mkdir()
            original = trace_dir / 'original.gpx'
            original.write_bytes(b'source')
            source_hash = hashlib.sha256(b'source').hexdigest()
            stat = original.stat()
            (trace_dir / 'df.parquet').write_bytes(b'old')
            (trace_dir / 'meta.json').write_text(json.dumps({'source_sha256': source_hash, 'source_size_bytes': stat.st_size, 'source_mtime_ns': stat.st_mtime_ns, 'dataframe_schema_version': 'v0'}), encoding='utf-8')
            dataframe = coerce_activity_df(pd.DataFrame({'distance_m': [0.0, 10.0], 'elevation': [100.0, 101.0], 'delta_distance_m': [np.nan, 10.0], 'delta_time_s': [np.nan, 1.0], 'elapsed_time_s': [0.0, 1.0], 'speed_m_s': [np.nan, 10.0], 'pace_s_per_km': [np.nan, 100.0]}))
            rebuild = Mock(return_value=dataframe)
            with patch.object(store, '_write_dataframe'):
                loaded = store.load_or_rebuild_dataframe(trace_id, expected_source_hash=source_hash, rebuild=rebuild)
            self.assertEqual(loaded.rebuild_reason, 'dataframe_schema_incompatible')
            rebuild.assert_called_once()


if __name__ == '__main__':
    unittest.main()
