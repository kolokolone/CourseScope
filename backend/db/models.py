from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, Float, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    parquet_path: Mapped[str] = mapped_column(Text, nullable=False)

    # Progression index trace (computed artifacts).
    progress_indexed_at_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_rollup_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    sources: Mapped[list["ActivitySource"]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
    )


class ActivitySource(Base):
    __tablename__ = "activity_sources"
    __table_args__ = (
        UniqueConstraint("source", "source_activity_id", name="uq_activity_source_external"),
        Index("ix_activity_sources_activity_id", "activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(36), ForeignKey("activities.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_activity_id: Mapped[str] = mapped_column(Text, nullable=False)

    activity: Mapped[Activity] = relationship(back_populates="sources")


class Trace(Base):
    __tablename__ = "traces"
    __table_args__ = (
        Index("ix_traces_route_fingerprint", "route_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    route_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    elevation_gain_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    elevation_loss_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_min_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_max_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    parquet_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parquet_source_hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dataframe_schema_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parquet_generated_at_utc: Mapped[str | None] = mapped_column(Text, nullable=True)

    race_plans: Mapped[list["RacePlan"]] = relationship(
        back_populates="trace",
        cascade="all, delete-orphan",
    )


class RacePlan(Base):
    __tablename__ = "race_plans"
    __table_args__ = (Index("ix_race_plans_trace_id", "trace_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), ForeignKey("traces.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    goal_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("goals.id"), nullable=True)
    race_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Paris")
    active_scenario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    common_parameters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at_utc: Mapped[str] = mapped_column(Text, nullable=False)

    trace: Mapped[Trace] = relationship(back_populates="race_plans")
    scenarios: Mapped[list["RaceScenario"]] = relationship(
        back_populates="race_plan",
        cascade="all, delete-orphan",
    )
    equipment_items: Mapped[list["RaceEquipmentItem"]] = relationship(
        back_populates="race_plan",
        cascade="all, delete-orphan",
    )
    course_points: Mapped[list["RaceCoursePoint"]] = relationship(
        back_populates="race_plan",
        cascade="all, delete-orphan",
    )


class RaceScenario(Base):
    __tablename__ = "race_scenarios"
    __table_args__ = (Index("ix_race_scenarios_plan_id", "race_plan_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    race_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("race_plans.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    objective_type: Mapped[str] = mapped_column(String(16), nullable=False, default="pace")
    target_value: Mapped[float] = mapped_column(Float, nullable=False, default=300.0)
    slope_model: Mapped[str] = mapped_column(String(32), nullable=False, default="minetti")
    vma_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    personal_parameters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    calibration_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    calibration_parameters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    weather_assumptions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at_utc: Mapped[str] = mapped_column(Text, nullable=False)

    race_plan: Mapped[RacePlan] = relationship(back_populates="scenarios")
    stops: Mapped[list["RaceStop"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    strategy_segments: Mapped[list["RaceStrategySegment"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    nutrition_items: Mapped[list["RaceNutritionItem"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")


class RaceStop(Base):
    __tablename__ = "race_stops"
    __table_args__ = (Index("ix_race_stops_scenario_id", "scenario_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("race_scenarios.id"), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    stop_type: Mapped[str] = mapped_column(String(24), nullable=False)
    duration_s: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at_utc: Mapped[str] = mapped_column(Text, nullable=False)

    scenario: Mapped[RaceScenario] = relationship(back_populates="stops")


class RaceStrategySegment(Base):
    __tablename__ = "race_strategy_segments"
    __table_args__ = (Index("ix_race_strategy_scenario_id", "scenario_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("race_scenarios.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    start_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    end_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    target_pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    scenario: Mapped[RaceScenario] = relationship(back_populates="strategy_segments")


class RaceNutritionItem(Base):
    __tablename__ = "race_nutrition_items"
    __table_args__ = (Index("ix_race_nutrition_scenario_id", "scenario_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("race_scenarios.id"), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    item_type: Mapped[str] = mapped_column(String(24), nullable=False)
    amount: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    scenario: Mapped[RaceScenario] = relationship(back_populates="nutrition_items")


class RaceEquipmentItem(Base):
    __tablename__ = "race_equipment_items"
    __table_args__ = (Index("ix_race_equipment_plan_id", "race_plan_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    race_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("race_plans.id"), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    is_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    race_plan: Mapped[RacePlan] = relationship(back_populates="equipment_items")


class RaceCoursePoint(Base):
    __tablename__ = "race_course_points"
    __table_args__ = (Index("ix_race_course_points_plan_id", "race_plan_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    race_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("race_plans.id"), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    point_type: Mapped[str] = mapped_column(String(24), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    end_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    race_plan: Mapped[RacePlan] = relationship(back_populates="course_points")


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        Index("ix_goals_event_date", "event_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[str] = mapped_column(Text, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_city: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    race_type: Mapped[str] = mapped_column(String(16), nullable=False, default="road")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at_utc: Mapped[str] = mapped_column(Text, nullable=False)


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vma_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    vo2max_lastest: Mapped[float | None] = mapped_column(Float, nullable=True)
    hr_max_manual_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hr_max_source: Mapped[str] = mapped_column(String(16), nullable=False, default="detected")
    updated_at_utc: Mapped[str] = mapped_column(Text, nullable=False)


class SyncState(Base):
    __tablename__ = "sync_state"

    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    cursor_time_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at_utc: Mapped[str] = mapped_column(Text, nullable=False)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    finished_at_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ProgressActivityIndex(Base):
    __tablename__ = "progress_activity_index"

    activity_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    start_ts_utc: Mapped[str] = mapped_column(Text, nullable=False)
    local_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    tz: Mapped[str | None] = mapped_column(Text, nullable=True)

    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_version: Mapped[int] = mapped_column(Integer, nullable=False)
    indexed_at_ts: Mapped[str] = mapped_column(Text, nullable=False)
    fast_indexation_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    slow_indexation_date: Mapped[str | None] = mapped_column(Text, nullable=True)

    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    moving_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    elapsed_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    avg_pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    pace_threshold_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    avg_hr_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_hr_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)

    trimp: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_load_method: Mapped[str | None] = mapped_column(Text, nullable=True)

    decoupling_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability_cv: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability_iqr_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    aerobic_efficiency_m_s_per_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    vo2max: Mapped[float | None] = mapped_column(Float, nullable=True)

    has_hr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_power: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_cadence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # HR zone time columns (P1 — intensity distribution)
    z1_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    z2_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    z3_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    z4_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    z5_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    # New columns (P2 — audit SQLite)
    elevation_loss_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    pace_first_half_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    pace_second_half_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_normalized_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_intensity_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_tss: Mapped[float | None] = mapped_column(Float, nullable=True)
    cadence_mean_spm: Mapped[float | None] = mapped_column(Float, nullable=True)
    cadence_max_spm: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_progress_activity_start_ts", "start_ts_utc"),
        Index("ix_progress_activity_type_start_ts", "activity_type", "start_ts_utc"),
        Index("ix_progress_activity_type", "activity_type"),
    )


class ProgressBestEffortPoint(Base):
    __tablename__ = "progress_best_effort_points"
    __table_args__ = (
        UniqueConstraint("activity_id", "effort_kind", "duration_s", name="uq_progress_best_effort"),
        Index("ix_progress_best_effort_kind_duration", "effort_kind", "duration_s"),
        Index("ix_progress_best_effort_kind_duration_start", "effort_kind", "duration_s", "start_ts_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    activity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    start_ts_utc: Mapped[str] = mapped_column(Text, nullable=False)
    effort_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)


class ProgressPaceHrBin(Base):
    __tablename__ = "progress_pace_hr_bins"
    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "bin_step_s_per_km",
            "pace_bin_s_per_km",
            name="uq_progress_pace_hr_bin",
        ),
        Index("ix_progress_pace_hr_start", "start_ts_utc"),
        Index("ix_progress_pace_hr_type_start", "activity_type", "start_ts_utc"),
        Index("ix_progress_pace_hr_step_start", "bin_step_s_per_km", "start_ts_utc"),
        Index("ix_progress_pace_hr_pace", "bin_step_s_per_km", "pace_bin_s_per_km"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    activity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    start_ts_utc: Mapped[str] = mapped_column(Text, nullable=False)

    bin_step_s_per_km: Mapped[int] = mapped_column(Integer, nullable=False)
    pace_bin_s_per_km: Mapped[float] = mapped_column(Float, nullable=False)
    time_s_bin: Mapped[float] = mapped_column(Float, nullable=False)

    hr_mean_w_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    hr_q50_w_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)


class ProgressActivityTag(Base):
    __tablename__ = "progress_activity_tags"
    __table_args__ = (
        Index("ix_progress_tags_session", "session_tag"),
        Index("ix_progress_tags_terrain", "terrain_tag"),
        Index("ix_progress_tags_race", "race_marker"),
        Index("ix_progress_tags_source", "source"),
    )

    activity_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_tag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    terrain_tag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    race_marker: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")
    updated_at_ts: Mapped[str] = mapped_column(Text, nullable=False)


class ProgressIndexationRun(Base):
    __tablename__ = "progress_indexation_runs"
    __table_args__ = (
        Index("ix_progress_indexation_runs_started", "started_at_utc"),
        Index("ix_progress_indexation_runs_mode_status", "mode", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    strategy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    finished_at_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---- New tables (P1-P2 — audit SQLite) ----


class ProgressActivityZone(Base):
    __tablename__ = "progress_activity_zones"
    __table_args__ = (
        Index("ix_zones_activity_type", "activity_id", "zone_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'heart_rate', 'pace', 'power'
    zone_name: Mapped[str] = mapped_column(String(16), nullable=False)  # 'Z1', 'Z2', ...
    range_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    range_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_s: Mapped[float] = mapped_column(Float, nullable=False)
    time_pct: Mapped[float] = mapped_column(Float, nullable=False)


class ProgressActivitySplit(Base):
    __tablename__ = "progress_activity_splits"
    __table_args__ = (
        Index("ix_splits_activity", "activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    split_index: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    time_s: Mapped[float] = mapped_column(Float, nullable=False)
    pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, nullable=True)


class ProgressActivityClimb(Base):
    __tablename__ = "progress_activity_climbs"
    __table_args__ = (
        Index("ix_climbs_activity", "activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_gain_m: Mapped[float] = mapped_column(Float, nullable=False)
    avg_grade_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    vam_m_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)


class ProgressDailyAggregate(Base):
    __tablename__ = "progress_daily_aggregates"

    date_utc: Mapped[str] = mapped_column(String(16), primary_key=True)  # YYYY-MM-DD
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    moving_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    elapsed_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    trimp: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    z1_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    z2_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    z3_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    z4_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    z5_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
