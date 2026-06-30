"""Service layer for progress/analytics business logic."""

import math
from datetime import datetime, timezone, timedelta

from core.progress_math import aggregate_curve, interp_linear, compute_streaks
from core.utils import bucket_start


class ProgressService:
    """Stateless service for progress endpoint computations."""

    # ------------------------------------------------------------------
    # (a) Training Load — ACWR, monotony, strain, risk zones
    # ------------------------------------------------------------------
    @staticmethod
    def compute_training_load(rows) -> dict:
        """Compute ACWR, monotony, strain from TRIMP rows.

        Each row must expose ``.value`` (float | None) and ``.start_ts_utc`` (str).
        Returns a dict with points, current_acwr, current_monotony,
        current_strain, and risk_zone.
        """
        # Bucket TRIMP per day
        daily_trimp: dict[str, float] = {}
        for r in rows:
            if r.value is None or not math.isfinite(r.value):
                continue
            day = r.start_ts_utc[:10]
            daily_trimp[day] = daily_trimp.get(day, 0.0) + r.value

        if not daily_trimp:
            return {
                "points": [],
                "current_acwr": None,
                "current_monotony": None,
                "current_strain": None,
                "risk_zone": None,
            }

        sorted_days = sorted(daily_trimp.keys())

        points: list[dict] = []
        for i, day in enumerate(sorted_days):
            # Acute load: 7-day rolling
            acute_sum = 0.0
            acute_count = 0
            for j in range(max(0, i - 6), i + 1):
                acute_sum += daily_trimp[sorted_days[j]]
                acute_count += 1
            acute_load = acute_sum / 7.0

            # Chronic load: 42-day rolling
            chronic_sum = 0.0
            chronic_count = 0
            for j in range(max(0, i - 41), i + 1):
                chronic_sum += daily_trimp[sorted_days[j]]
                chronic_count += 1
            chronic_load = chronic_sum / 42.0 if chronic_count >= 7 else None

            # ACWR
            acwr = acute_load / chronic_load if (chronic_load is not None and chronic_load > 0) else None

            # Monotony (on acute window)
            monotony = None
            if acute_count >= 3:
                mean_val = acute_sum / acute_count
                variance = 0.0
                for j in range(max(0, i - 6), i + 1):
                    v = daily_trimp[sorted_days[j]]
                    variance += (v - mean_val) ** 2
                variance /= acute_count
                std_val = math.sqrt(variance)
                if std_val > 0:
                    monotony = mean_val / std_val

            # Strain
            strain = acute_sum * monotony if monotony is not None else None

            points.append({
                "bucket_start": day,
                "acute_load_7d": round(acute_load, 1),
                "chronic_load_42d": round(chronic_load, 1) if chronic_load is not None else None,
                "acwr": round(acwr, 2) if acwr is not None else None,
                "monotony_7d": round(monotony, 2) if monotony is not None else None,
                "strain_7d": round(strain, 1) if strain is not None else None,
            })

        last = points[-1] if points else None
        risk_zone = None
        current_acwr = None
        current_monotony = None
        current_strain = None

        if last is not None:
            current_acwr = last["acwr"]
            current_monotony = last["monotony_7d"]
            current_strain = last["strain_7d"]

            if current_acwr is not None:
                if current_acwr < 0.8:
                    risk_zone = "low"
                elif current_acwr < 1.3:
                    risk_zone = "moderate"
                else:
                    risk_zone = "high"

        return {
            "points": points,
            "current_acwr": current_acwr,
            "current_monotony": current_monotony,
            "current_strain": current_strain,
            "risk_zone": risk_zone,
        }

    # ------------------------------------------------------------------
    # (b) Time Series — aggregation by bucket (day/week/month)
    # ------------------------------------------------------------------
    @staticmethod
    def compute_time_series(rows, group_by: str, agg: str) -> list[dict]:
        """Aggregate value rows into day/week/month buckets.

        Each row must expose ``.value`` (float | None) and ``.start_ts_utc`` (str).
        """
        buckets: dict[str, list[float]] = {}
        for r in rows:
            if r.value is None:
                continue
            if not isinstance(r.value, (int, float)):
                continue
            v = float(r.value)
            if not math.isfinite(v):
                continue

            try:
                dt = datetime.fromisoformat(str(r.start_ts_utc).replace("Z", "+00:00"))
            except Exception:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            b = bucket_start(dt, group_by)
            key = b.date().isoformat()
            buckets.setdefault(key, []).append(v)

        out = []
        for key in sorted(buckets.keys()):
            values = buckets[key]
            if not values:
                continue
            if agg == "avg":
                value = float(sum(values) / len(values))
            else:
                value = float(sum(values))
            out.append({"bucket_start": key, "value": value})

        return out

    # ------------------------------------------------------------------
    # (c) HR@Pace / Pace@HR — interpolation series
    # ------------------------------------------------------------------
    @staticmethod
    def compute_hr_pace_series(rows, refs, mode: str) -> dict:
        """Build HR-at-pace or pace-at-HR interpolation series.

        Each row must expose ``.hr_q50_w_bpm``, ``.hr_mean_w_bpm``,
        ``.pace_bin_s_per_km``, ``.activity_id``, ``.start_ts_utc``.

        ``mode`` must be ``"hr_at_pace"`` or ``"pace_at_hr"``.
        """
        per_activity: dict[str, dict] = {}
        for r in rows:
            hr_value = r.hr_q50_w_bpm if r.hr_q50_w_bpm is not None else r.hr_mean_w_bpm
            if hr_value is None:
                continue
            if not math.isfinite(hr_value):
                continue
            if not math.isfinite(r.pace_bin_s_per_km):
                continue
            data = per_activity.setdefault(r.activity_id, {"start_ts_utc": r.start_ts_utc, "pairs": []})

            if mode == "pace_at_hr":
                # Interpolate pace from HR: pairs are (hr, pace)
                data["pairs"].append((float(hr_value), float(r.pace_bin_s_per_km)))
            else:
                # hr_at_pace: interpolate HR from pace
                data["pairs"].append((float(r.pace_bin_s_per_km), float(hr_value)))

        out_key = "hr_bpm" if mode == "pace_at_hr" else "pace_s_per_km"

        out_series = []
        for ref in refs:
            pts = []
            for activity_id, data in per_activity.items():
                value = interp_linear(list(data["pairs"]), float(ref))
                if value is None:
                    continue
                pts.append(
                    {
                        "activity_id": activity_id,
                        "start_ts_utc": data["start_ts_utc"],
                        "value": float(value),
                    }
                )
            pts.sort(key=lambda x: str(x["start_ts_utc"]))
            out_series.append({out_key: float(ref), "points": pts})

        return {"series": out_series}

    # ------------------------------------------------------------------
    # (d) 3D Waterfall — pace/HR/time aggregation per activity
    # ------------------------------------------------------------------
    @staticmethod
    def compute_waterfall(rows, tags_map: dict, bin_step_s_per_km: float) -> list[dict]:
        """Build pace/HR waterfall data from pace-hr rows.

        Each row must expose ``.hr_q50_w_bpm``, ``.hr_mean_w_bpm``,
        ``.pace_bin_s_per_km``, ``.time_s_bin``, ``.activity_id``,
        ``.start_ts_utc``.

        ``tags_map`` is a dict of activity_id → tag object with
        ``.session_tag``, ``.terrain_tag``, ``.race_marker`` attributes.
        """
        by_activity: dict[str, dict] = {}
        for r in rows:
            hr_value = r.hr_q50_w_bpm if r.hr_q50_w_bpm is not None else r.hr_mean_w_bpm
            if hr_value is None:
                continue
            if not (math.isfinite(hr_value) and math.isfinite(r.pace_bin_s_per_km) and math.isfinite(r.time_s_bin)):
                continue
            item = by_activity.setdefault(
                r.activity_id,
                {
                    "activity_id": r.activity_id,
                    "start_ts_utc": r.start_ts_utc,
                    "points_raw": [],
                },
            )
            item["points_raw"].append((float(r.pace_bin_s_per_km), float(hr_value), float(r.time_s_bin)))

        activities = []
        for activity_id, item in by_activity.items():
            points = aggregate_curve(list(item["points_raw"]), float(bin_step_s_per_km))
            if len(points) < 1:
                continue
            tag = tags_map.get(activity_id)
            activities.append(
                {
                    "activity_id": activity_id,
                    "start_ts_utc": item["start_ts_utc"],
                    "session_tag": tag.session_tag if tag is not None else "unknown",
                    "terrain_tag": tag.terrain_tag if tag is not None else "unknown",
                    "race_marker": bool(tag.race_marker) if tag is not None else False,
                    "points": points,
                }
            )

        activities.sort(key=lambda x: str(x["start_ts_utc"]))
        return activities

    # ------------------------------------------------------------------
    # (e) Activity List — filtering + mapping
    # ------------------------------------------------------------------
    @staticmethod
    def build_activity_list(rows, tags_map: dict, filters: dict | None = None) -> list[dict]:
        """Filter and map activity rows into API response dicts.

        ``filters`` is an optional dict with optional keys ``session_tag``,
        ``terrain_tag``, ``race_marker``.
        """
        filters = filters or {}

        session_tag_filter = filters.get("session_tag")
        terrain_tag_filter = filters.get("terrain_tag")
        race_marker_filter = filters.get("race_marker")

        # Apply filters
        if session_tag_filter is not None or terrain_tag_filter is not None or race_marker_filter is not None:
            filtered_rows = []
            for r in rows:
                tag = tags_map.get(str(r.activity_id))
                if session_tag_filter is not None and (tag is None or tag.session_tag != session_tag_filter):
                    continue
                if terrain_tag_filter is not None and (tag is None or tag.terrain_tag != terrain_tag_filter):
                    continue
                if race_marker_filter is not None and (tag is None or bool(tag.race_marker) != bool(race_marker_filter)):
                    continue
                filtered_rows.append(r)
            rows = filtered_rows

        payload = []
        for r in rows:
            tag = tags_map.get(str(r.activity_id))
            payload.append(
                {
                    "activity_id": r.activity_id,
                    "activity_type": r.activity_type,
                    "start_ts_utc": r.start_ts_utc,
                    "distance_m": r.distance_m,
                    "moving_time_s": r.moving_time_s,
                    "elapsed_time_s": r.elapsed_time_s,
                    "elevation_gain_m": r.elevation_gain_m,
                    "avg_pace_s_per_km": r.avg_pace_s_per_km,
                    "best_pace_s_per_km": r.best_pace_s_per_km,
                    "pace_threshold_s_per_km": r.pace_threshold_s_per_km,
                    "avg_hr_bpm": r.avg_hr_bpm,
                    "max_hr_bpm": r.max_hr_bpm,
                    "trimp": r.trimp,
                    "training_load_method": r.training_load_method,
                    "aerobic_efficiency_m_s_per_bpm": r.aerobic_efficiency_m_s_per_bpm,
                    "vo2max": r.vo2max,
                    "decoupling_pct": r.decoupling_pct,
                    "stability_cv": r.stability_cv,
                    "stability_iqr_ratio": r.stability_iqr_ratio,
                    "has_hr": bool(r.has_hr),
                    "has_power": bool(r.has_power),
                    "has_cadence": bool(r.has_cadence),
                    "data_points": r.data_points,
                    "session_tag": (tag.session_tag if tag is not None else None),
                    "terrain_tag": (tag.terrain_tag if tag is not None else None),
                    "race_marker": (bool(tag.race_marker) if tag is not None else False),
                    "tag_source": (tag.source if tag is not None else None),
                }
            )

        return payload

    # ------------------------------------------------------------------
    # (f) Session Taxonomy — counting sessions by type / terrain
    # ------------------------------------------------------------------
    @staticmethod
    def compute_session_taxonomy(rows) -> dict:
        """Count sessions by session tag, terrain tag, and race marker.

        Each row must expose ``.session_tag``, ``.terrain_tag``, ``.race_marker``.
        """
        session_counts: dict[str, int] = {}
        terrain_counts: dict[str, int] = {}
        race_markers = 0
        for r in rows:
            s = r.session_tag or "unknown"
            t = r.terrain_tag or "unknown"
            session_counts[s] = session_counts.get(s, 0) + 1
            terrain_counts[t] = terrain_counts.get(t, 0) + 1
            if r.race_marker:
                race_markers += 1

        return {
            "session_counts": [{"tag": k, "count": session_counts[k]} for k in sorted(session_counts.keys())],
            "terrain_counts": [{"tag": k, "count": terrain_counts[k]} for k in sorted(terrain_counts.keys())],
            "race_markers": int(race_markers),
            "total_tagged": int(len(rows)),
        }

    # ------------------------------------------------------------------
    # (g) Tag Merge — partial merging of tag values
    # ------------------------------------------------------------------
    @staticmethod
    def merge_tag(previous, new: dict) -> dict:
        """Merge new tag values with previous, falling back to previous.

        ``previous`` is a tag object with ``.session_tag``, ``.terrain_tag``,
        ``.race_marker`` attributes, or None.

        ``new`` is a dict with optional keys ``session_tag``, ``terrain_tag``,
        ``race_marker``. Returns a dict with the merged values.
        """
        return {
            "session_tag": (
                new.get("session_tag")
                if new.get("session_tag") is not None
                else (previous.session_tag if previous is not None else None)
            ),
            "terrain_tag": (
                new.get("terrain_tag")
                if new.get("terrain_tag") is not None
                else (previous.terrain_tag if previous is not None else None)
            ),
            "race_marker": (
                int(bool(new.get("race_marker")))
                if new.get("race_marker") is not None
                else (1 if (previous is not None and previous.race_marker) else 0)
            ),
        }

    # ------------------------------------------------------------------
    # (h) Calendar — day-level heatmap aggregation
    # ------------------------------------------------------------------
    @staticmethod
    def compute_calendar(rows, year: int) -> dict:
        """Aggregate activity rows into a calendar heatmap for a given year.

        Each row must expose ``.start_ts_utc``, ``.distance_m``, ``.moving_time_s``.
        """
        by_day: dict[str, dict] = {}
        active_dates: set[str] = set()

        for r in rows:
            if r.start_ts_utc is None:
                continue
            day_key = str(r.start_ts_utc)[:10]
            active_dates.add(day_key)

            if day_key not in by_day:
                by_day[day_key] = {"distance_km": 0.0, "moving_time_s": 0.0, "activity_count": 0}

            entry = by_day[day_key]
            entry["activity_count"] += 1

            if r.distance_m is not None and math.isfinite(r.distance_m):
                entry["distance_km"] += r.distance_m / 1000.0

            if r.moving_time_s is not None and math.isfinite(r.moving_time_s):
                entry["moving_time_s"] += r.moving_time_s

        days = []
        for day_key in sorted(by_day.keys()):
            entry = by_day[day_key]
            days.append({
                "date": day_key,
                "has_activity": True,
                "distance_km": round(entry["distance_km"], 3),
                "moving_time_s": round(entry["moving_time_s"], 1),
                "activity_count": entry["activity_count"],
            })

        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        longest_streak, current_streak = compute_streaks(active_dates, today_iso)

        return {
            "days": days,
            "year": year,
            "total_active_days": len(active_dates),
            "longest_streak": longest_streak,
            "current_streak": current_streak,
        }

    # ------------------------------------------------------------------
    # (i) PR Annotation — mark best efforts that set a new PR
    # ------------------------------------------------------------------
    @staticmethod
    def annotate_prs(points) -> list[dict]:
        """Annotate best-effort points with is_pr flag.

        Each point must expose ``.value``, ``.activity_id``, ``.start_ts_utc``.
        """
        best = math.inf
        out = []
        for p in points:
            v = float(p.value)
            is_pr = False
            if math.isfinite(v) and v < best:
                best = v
                is_pr = True
            out.append(
                {
                    "activity_id": p.activity_id,
                    "start_ts_utc": p.start_ts_utc,
                    "value": v,
                    "is_pr": is_pr,
                }
            )
        return out

    # ------------------------------------------------------------------
    # (j) Intensity Distribution — HR zone time by week
    # ------------------------------------------------------------------
    @staticmethod
    def compute_intensity_distribution(rows) -> list[dict]:
        """Aggregate HR zone time (Z1-Z5) by week.

        Each row must expose ``.start_ts_utc``, ``.z1_time_s`` … ``.z5_time_s``.
        Rows with no HR zone data (all z columns NULL) are silently excluded.
        Returns a list of dicts with bucket_start and z1_time_min … z5_time_min.
        """
        from core.utils import bucket_start as _bucket_start

        weeks: dict[str, dict[str, float]] = {}
        for r in rows:
            z_vals = [
                getattr(r, 'z1_time_s', None),
                getattr(r, 'z2_time_s', None),
                getattr(r, 'z3_time_s', None),
                getattr(r, 'z4_time_s', None),
                getattr(r, 'z5_time_s', None),
            ]
            if all(z is None or not math.isfinite(float(z)) for z in z_vals):
                continue

            try:
                dt = datetime.fromisoformat(str(r.start_ts_utc).replace("Z", "+00:00"))
            except Exception:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            b = _bucket_start(dt, "week")
            key = b.date().isoformat()

            if key not in weeks:
                weeks[key] = {"z1": 0.0, "z2": 0.0, "z3": 0.0, "z4": 0.0, "z5": 0.0, "total": 0.0}
            for i, zone_key in enumerate(["z1", "z2", "z3", "z4", "z5"]):
                v = z_vals[i]
                if v is not None and math.isfinite(float(v)):
                    weeks[key][zone_key] += float(v)
                    weeks[key]["total"] += float(v)

        out = []
        for key in sorted(weeks.keys()):
            w = weeks[key]
            out.append({
                "bucket_start": key,
                "z1_time_min": round(w["z1"] / 60.0, 1),
                "z2_time_min": round(w["z2"] / 60.0, 1),
                "z3_time_min": round(w["z3"] / 60.0, 1),
                "z4_time_min": round(w["z4"] / 60.0, 1),
                "z5_time_min": round(w["z5"] / 60.0, 1),
                "total_time_min": round(w["total"] / 60.0, 1),
            })
        return out

    # ------------------------------------------------------------------
    # (k) Long Run Dose — distance/time of long runs by week
    # ------------------------------------------------------------------
    @staticmethod
    def compute_long_run_dose(rows) -> list[dict]:
        """Aggregate distance and time of long-run activities by week.

        Each row must expose ``.start_ts_utc``, ``.distance_m``,
        ``.moving_time_s``, ``.activity_id``.
        Rows are assumed to be pre-filtered to session_tag == 'long_run'.
        """
        from core.utils import bucket_start as _bucket_start

        weeks: dict[str, dict] = {}
        for r in rows:
            try:
                dt = datetime.fromisoformat(str(r.start_ts_utc).replace("Z", "+00:00"))
            except Exception:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            b = _bucket_start(dt, "week")
            key = b.date().isoformat()

            dist = float(r.distance_m or 0)
            time_s = float(r.moving_time_s or 0)
            if key not in weeks:
                weeks[key] = {"distance_m": 0.0, "moving_time_s": 0.0, "count": 0, "max_distance_m": 0.0}
            weeks[key]["distance_m"] += dist
            weeks[key]["moving_time_s"] += time_s
            weeks[key]["count"] += 1
            if dist > weeks[key]["max_distance_m"]:
                weeks[key]["max_distance_m"] = dist

        out = []
        for key in sorted(weeks.keys()):
            w = weeks[key]
            out.append({
                "bucket_start": key,
                "distance_km": round(w["distance_m"] / 1000.0, 1),
                "moving_time_h": round(w["moving_time_s"] / 3600.0, 1),
                "activity_count": w["count"],
                "max_distance_km": round(w["max_distance_m"] / 1000.0, 1),
            })
        return out

    # ------------------------------------------------------------------
    # (l) VAM Trend — best VAM per activity over time
    # ------------------------------------------------------------------
    @staticmethod
    def compute_vam_trend(rows) -> list[dict]:
        """Format VAM trend rows into API response.

        Each row must expose ``.activity_id``, ``.start_ts_utc``,
        ``.vam_max_m_h``.
        Rows with NULL vam_max_m_h are silently excluded.
        """
        out = []
        for r in rows:
            vam = getattr(r, 'vam_max_m_h', None)
            if vam is None or not math.isfinite(float(vam)):
                continue
            out.append({
                "activity_id": r.activity_id,
                "start_ts_utc": r.start_ts_utc,
                "vam_max_m_h": round(float(vam), 0),
            })
        return out
