from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ObjectiveType = Literal["pace", "time", "effort"]
StopType = Literal["water", "nutrition", "assistance", "other"]


class RaceStopInput(BaseModel):
    distance_km: float = Field(ge=0)
    stop_type: StopType
    duration_s: float = Field(default=0, ge=0, le=86_400)
    notes: str | None = None
    sort_order: int = 0


class RaceStopPatch(BaseModel):
    distance_km: float | None = Field(default=None, ge=0)
    stop_type: StopType | None = None
    duration_s: float | None = Field(default=None, ge=0, le=86_400)
    notes: str | None = None
    sort_order: int | None = None


class RaceScenarioInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    objective_type: ObjectiveType = "pace"
    target_value: float = Field(default=300, gt=0)
    slope_model: Literal["minetti"] = "minetti"
    vma_kmh: float | None = Field(default=None, gt=0, le=35)
    personal_parameters: dict[str, Any] | None = None
    calibration_factor: float = Field(default=1, ge=0.5, le=2)
    calibration_parameters: dict[str, Any] | None = None
    weather_assumptions: dict[str, Any] | None = None
    is_active: bool = False
    stops: list[RaceStopInput] = Field(default_factory=list)


class RaceScenarioPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    objective_type: ObjectiveType | None = None
    target_value: float | None = Field(default=None, gt=0)
    slope_model: Literal["minetti"] | None = None
    vma_kmh: float | None = Field(default=None, gt=0, le=35)
    personal_parameters: dict[str, Any] | None = None
    calibration_factor: float | None = Field(default=None, ge=0.5, le=2)
    calibration_parameters: dict[str, Any] | None = None
    weather_assumptions: dict[str, Any] | None = None
    is_active: bool | None = None
    strategy_segments: list[dict[str, Any]] | None = None
    nutrition: list[dict[str, Any]] | None = None


class StrategySegmentInput(BaseModel):
    name: str
    start_distance_km: float = Field(ge=0)
    end_distance_km: float = Field(gt=0)
    target_pace_s_per_km: float | None = Field(default=None, gt=0)
    notes: str | None = None
    sort_order: int = 0


class NutritionItemInput(BaseModel):
    distance_km: float = Field(ge=0)
    item_type: Literal["nutrition", "hydration"]
    amount: str | None = None
    notes: str | None = None
    sort_order: int = 0


class EquipmentItemInput(BaseModel):
    label: str
    is_checked: bool = False
    notes: str | None = None
    sort_order: int = 0


class CoursePointInput(BaseModel):
    distance_km: float = Field(ge=0)
    point_type: Literal["landmark", "custom_segment"]
    label: str
    end_distance_km: float | None = Field(default=None, gt=0)
    notes: str | None = None
    sort_order: int = 0


class RacePlanInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    goal_id: str | None = None
    race_date: str | None = None
    start_time: str | None = None
    timezone: str = "Europe/Paris"
    common_parameters: dict[str, Any] | None = None
    notes: str | None = None
    scenarios: list[RaceScenarioInput] = Field(default_factory=list)
    equipment: list[EquipmentItemInput] = Field(default_factory=list)
    course_points: list[CoursePointInput] = Field(default_factory=list)


class RacePlanPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    goal_id: str | None = None
    race_date: str | None = None
    start_time: str | None = None
    timezone: str | None = None
    active_scenario_id: str | None = None
    common_parameters: dict[str, Any] | None = None
    notes: str | None = None
    equipment: list[EquipmentItemInput] | None = None
    course_points: list[CoursePointInput] | None = None


class PlanPreviewRequest(BaseModel):
    plan_id: str | None = None
    scenario_id: str | None = None
    plan: dict[str, Any] | None = None
    scenario: RaceScenarioInput | None = None
    stops: list[RaceStopInput] | None = None
    custom_points: list[CoursePointInput] | None = None
    custom_segments: list[StrategySegmentInput] | None = None


class ScenarioComparisonRequest(BaseModel):
    scenario_ids: list[str] = Field(min_length=2)
