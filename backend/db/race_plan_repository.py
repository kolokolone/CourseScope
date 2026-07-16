from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import (
    RaceCoursePoint,
    RaceEquipmentItem,
    RaceNutritionItem,
    RacePlan,
    RaceScenario,
    RaceStop,
    RaceStrategySegment,
    utc_now_iso,
)


def _json(value: object | None) -> str | None:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if value is not None else None


def _from_json(value: str | None) -> object | None:
    return json.loads(value) if value else None


def _optional_text(value: object | None) -> str | None:
    normalized = str(value).strip() if value is not None else ""
    return normalized or None


class RacePlanRepository:
    def list_for_trace(self, session: Session, trace_id: str) -> list[RacePlan]:
        statement = select(RacePlan).where(RacePlan.trace_id == trace_id).order_by(RacePlan.updated_at_utc.desc())
        return list(session.execute(statement).scalars().unique().all())

    def get(self, session: Session, trace_id: str, plan_id: str) -> RacePlan | None:
        statement = select(RacePlan).where(RacePlan.id == plan_id, RacePlan.trace_id == trace_id)
        return session.execute(statement).scalars().first()

    def ensure_default(self, session: Session, trace_id: str) -> RacePlan:
        """Return an existing plan or create the legacy trace default once."""

        plans = self.list_for_trace(session, trace_id)
        if plans:
            return plans[0]
        plan = self.create(session, trace_id, {"name": "Plan principal"})
        session.flush()
        return plan

    def create(self, session: Session, trace_id: str, data: dict[str, object]) -> RacePlan:
        now = utc_now_iso()
        plan = RacePlan(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            name=str(data.get("name") or "Plan de course"),
            goal_id=data.get("goal_id") or None,
            race_date=data.get("race_date") or None,
            start_time=data.get("start_time") or None,
            timezone=str(data.get("timezone") or "Europe/Paris"),
            common_parameters_json=_json(data.get("common_parameters")),
            notes=data.get("notes") or None,
            created_at_utc=now,
            updated_at_utc=now,
        )
        session.add(plan)
        session.flush()
        for item in data.get("equipment", []) or []:
            self._add_equipment(plan, dict(item))
        for item in data.get("course_points", []) or []:
            self._add_course_point(plan, dict(item))
        scenarios = list(data.get("scenarios", []) or [])
        if not scenarios:
            scenarios = [{"name": "Scenario principal", "objective_type": "pace", "target_value": 300.0, "slope_model": "minetti", "is_active": True}]
        for index, item in enumerate(scenarios):
            scenario_data = dict(item)
            scenario_data["is_active"] = bool(scenario_data.get("is_active", index == 0))
            scenario = self.create_scenario(session, plan, scenario_data)
            if plan.active_scenario_id is None or scenario.is_active:
                plan.active_scenario_id = scenario.id
        return plan

    def update(self, session: Session, plan: RacePlan, data: dict[str, object]) -> RacePlan:
        direct = {"name", "goal_id", "race_date", "start_time", "timezone", "active_scenario_id", "notes"}
        for key in direct:
            if key in data:
                setattr(plan, key, data[key])
        if "common_parameters" in data:
            plan.common_parameters_json = _json(data["common_parameters"])
        if "equipment" in data and data["equipment"] is not None:
            plan.equipment_items.clear()
            for item in data["equipment"] or []:
                self._add_equipment(plan, dict(item))
        if "course_points" in data and data["course_points"] is not None:
            plan.course_points.clear()
            for item in data["course_points"] or []:
                self._add_course_point(plan, dict(item))
        plan.updated_at_utc = utc_now_iso()
        return plan

    def delete(self, session: Session, plan: RacePlan) -> None:
        session.delete(plan)

    def create_scenario(self, session: Session, plan: RacePlan, data: dict[str, object]) -> RaceScenario:
        now = utc_now_iso()
        scenario = RaceScenario(
            id=str(uuid.uuid4()),
            race_plan_id=plan.id,
            name=str(data.get("name") or "Scenario"),
            objective_type=str(data.get("objective_type") or "pace"),
            target_value=float(data.get("target_value") or 300.0),
            slope_model=str(data.get("slope_model") or "minetti"),
            vma_kmh=float(data["vma_kmh"]) if data.get("vma_kmh") is not None else None,
            personal_parameters_json=_json(data.get("personal_parameters")),
            calibration_factor=float(data.get("calibration_factor") or 1.0),
            calibration_parameters_json=_json(data.get("calibration_parameters")),
            weather_assumptions_json=_json(data.get("weather_assumptions")),
            is_active=bool(data.get("is_active", False)),
            created_at_utc=now,
            updated_at_utc=now,
        )
        plan.scenarios.append(scenario)
        for item in data.get("stops", []) or []:
            self.create_stop(session, scenario, dict(item))
        return scenario

    def get_scenario(self, session: Session, plan: RacePlan, scenario_id: str) -> RaceScenario | None:
        return next((item for item in plan.scenarios if item.id == scenario_id), None)

    def update_scenario(self, plan: RacePlan, scenario: RaceScenario, data: dict[str, object]) -> RaceScenario:
        direct = {"name", "objective_type", "target_value", "slope_model", "vma_kmh", "calibration_factor", "is_active"}
        for key in direct:
            if key in data:
                setattr(scenario, key, data[key])
        mapping = {
            "personal_parameters": "personal_parameters_json",
            "calibration_parameters": "calibration_parameters_json",
            "weather_assumptions": "weather_assumptions_json",
        }
        for source, target in mapping.items():
            if source in data:
                setattr(scenario, target, _json(data[source]))
        if "strategy_segments" in data and data["strategy_segments"] is not None:
            scenario.strategy_segments.clear()
            for item in data["strategy_segments"] or []:
                value = dict(item)
                scenario.strategy_segments.append(RaceStrategySegment(id=str(uuid.uuid4()), name=str(value.get("name") or "Portion"), start_distance_km=float(value.get("start_distance_km") or 0), end_distance_km=float(value.get("end_distance_km") or 0), target_pace_s_per_km=float(value["target_pace_s_per_km"]) if value.get("target_pace_s_per_km") is not None else None, notes=value.get("notes") or None, sort_order=int(value.get("sort_order") or 0)))
        if "nutrition" in data and data["nutrition"] is not None:
            scenario.nutrition_items.clear()
            for item in data["nutrition"] or []:
                value = dict(item)
                scenario.nutrition_items.append(RaceNutritionItem(id=str(uuid.uuid4()), distance_km=float(value.get("distance_km") or 0), item_type=str(value.get("item_type") or "nutrition"), amount=value.get("amount") or None, notes=value.get("notes") or None, sort_order=int(value.get("sort_order") or 0)))
        if scenario.is_active:
            for other in plan.scenarios:
                other.is_active = other.id == scenario.id
            plan.active_scenario_id = scenario.id
        scenario.updated_at_utc = utc_now_iso()
        plan.updated_at_utc = scenario.updated_at_utc
        return scenario

    def delete_scenario(self, session: Session, plan: RacePlan, scenario: RaceScenario) -> None:
        session.delete(scenario)
        if plan.active_scenario_id == scenario.id:
            remaining = next((item for item in plan.scenarios if item.id != scenario.id), None)
            plan.active_scenario_id = remaining.id if remaining else None
            if remaining:
                remaining.is_active = True

    def create_stop(self, session: Session, scenario: RaceScenario, data: dict[str, object]) -> RaceStop:
        now = utc_now_iso()
        stop = RaceStop(
            id=str(uuid.uuid4()),
            scenario_id=scenario.id,
            label=_optional_text(data.get("label")),
            distance_km=float(data.get("distance_km") or 0),
            stop_type=str(data.get("stop_type") or "other"),
            duration_s=float(data.get("duration_s") or 0),
            notes=data.get("notes") or None,
            sort_order=int(data.get("sort_order") or 0),
            created_at_utc=now,
            updated_at_utc=now,
        )
        scenario.stops.append(stop)
        return stop

    def get_stop(self, scenario: RaceScenario, stop_id: str) -> RaceStop | None:
        return next((item for item in scenario.stops if item.id == stop_id), None)

    def update_stop(self, stop: RaceStop, data: dict[str, object]) -> RaceStop:
        if "label" in data:
            stop.label = _optional_text(data["label"])
        for key in {"distance_km", "stop_type", "duration_s", "notes", "sort_order"}:
            if key in data:
                setattr(stop, key, data[key])
        stop.updated_at_utc = utc_now_iso()
        return stop

    def _add_equipment(self, plan: RacePlan, data: dict[str, object]) -> None:
        plan.equipment_items.append(RaceEquipmentItem(id=str(uuid.uuid4()), label=str(data.get("label") or ""), is_checked=bool(data.get("is_checked", False)), notes=data.get("notes") or None, sort_order=int(data.get("sort_order") or 0)))

    def _add_course_point(self, plan: RacePlan, data: dict[str, object]) -> None:
        plan.course_points.append(RaceCoursePoint(id=str(uuid.uuid4()), distance_km=float(data.get("distance_km") or 0), point_type=str(data.get("point_type") or "landmark"), label=str(data.get("label") or ""), end_distance_km=float(data["end_distance_km"]) if data.get("end_distance_km") is not None else None, notes=data.get("notes") or None, sort_order=int(data.get("sort_order") or 0)))


def stop_to_dict(stop: RaceStop) -> dict[str, object]:
    return {"id": stop.id, "label": stop.label, "distance_km": stop.distance_km, "stop_type": stop.stop_type, "duration_s": stop.duration_s, "notes": stop.notes, "sort_order": stop.sort_order, "created_at_utc": stop.created_at_utc, "updated_at_utc": stop.updated_at_utc}


def scenario_to_dict(scenario: RaceScenario, *, full: bool = True) -> dict[str, object]:
    result = {"id": scenario.id, "race_plan_id": scenario.race_plan_id, "name": scenario.name, "objective_type": scenario.objective_type, "target_value": scenario.target_value, "slope_model": scenario.slope_model, "vma_kmh": scenario.vma_kmh, "calibration_factor": scenario.calibration_factor, "is_active": scenario.is_active, "created_at_utc": scenario.created_at_utc, "updated_at_utc": scenario.updated_at_utc}
    if full:
        result.update({"personal_parameters": _from_json(scenario.personal_parameters_json), "calibration_parameters": _from_json(scenario.calibration_parameters_json), "weather_assumptions": _from_json(scenario.weather_assumptions_json), "stops": [stop_to_dict(item) for item in sorted(scenario.stops, key=lambda value: (value.distance_km, value.sort_order))], "strategy_segments": [{"id": item.id, "name": item.name, "start_distance_km": item.start_distance_km, "end_distance_km": item.end_distance_km, "target_pace_s_per_km": item.target_pace_s_per_km, "notes": item.notes, "sort_order": item.sort_order} for item in scenario.strategy_segments], "nutrition": [{"id": item.id, "distance_km": item.distance_km, "item_type": item.item_type, "amount": item.amount, "notes": item.notes, "sort_order": item.sort_order} for item in scenario.nutrition_items]})
    return result


def plan_to_dict(plan: RacePlan, *, full: bool = True) -> dict[str, object]:
    result = {"id": plan.id, "trace_id": plan.trace_id, "name": plan.name, "goal_id": plan.goal_id, "race_date": plan.race_date, "start_time": plan.start_time, "timezone": plan.timezone, "active_scenario_id": plan.active_scenario_id, "notes": plan.notes, "created_at_utc": plan.created_at_utc, "updated_at_utc": plan.updated_at_utc, "scenarios": [scenario_to_dict(item, full=full) for item in plan.scenarios]}
    if full:
        result.update({"common_parameters": _from_json(plan.common_parameters_json), "equipment": [{"id": item.id, "label": item.label, "is_checked": item.is_checked, "notes": item.notes, "sort_order": item.sort_order} for item in plan.equipment_items], "course_points": [{"id": item.id, "distance_km": item.distance_km, "point_type": item.point_type, "label": item.label, "end_distance_km": item.end_distance_km, "notes": item.notes, "sort_order": item.sort_order} for item in plan.course_points]})
    return result
