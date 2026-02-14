from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill the Progression (analytics) SQLite index")
    parser.add_argument("--limit", type=int, default=0, help="Optional max number of activities to index")
    parser.add_argument("--commit-every", type=int, default=25, help="Commit every N activities")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    sys.path.append(str(root / "backend"))

    from config import get_activities_dir
    from db.session import init_db, make_engine, make_session_factory
    from progress.indexer import index_activity

    activities_dir = get_activities_dir().resolve()
    if not activities_dir.exists():
        print(f"No activities dir: {activities_dir}")
        return 0

    engine = make_engine()
    init_db(engine)
    session_factory = make_session_factory(engine)

    count = 0
    ok = 0
    failed = 0

    session = session_factory()
    try:
        for activity_dir in sorted([p for p in activities_dir.iterdir() if p.is_dir()], key=lambda p: p.name):
            activity_id = activity_dir.name
            meta_path = activity_dir / "meta.json"
            parquet_path = activity_dir / "df.parquet"
            if not meta_path.exists() or not parquet_path.exists():
                continue

            if args.limit and count >= int(args.limit):
                break

            count += 1
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                df = pd.read_parquet(parquet_path)
                index_activity(session, activity_id=activity_id, df=df, meta=meta, parquet_path=parquet_path)
                ok += 1
            except Exception as exc:
                failed += 1
                print(f"index_failed activity_id={activity_id} error={exc}")

            if args.commit_every and (count % int(args.commit_every) == 0):
                session.commit()

        session.commit()
    finally:
        session.close()

    print(f"indexed_total={count} ok={ok} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
