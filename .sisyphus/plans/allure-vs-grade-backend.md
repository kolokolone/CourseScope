# Allure-vs-Grade: Move Binning From Frontend To Backend

## TL;DR

> **Quick Summary**: Add a new FastAPI endpoint that returns pre-binned pace-vs-grade data (+ std) plus the pro reference curve, then switch `AllureVsPenteChart` to fetch that payload and only render.
>
> **Deliverables**:
> - New endpoint: `GET /activity/{activity_id}/pace_vs_grade` (also available as `/api/activity/{activity_id}/pace_vs_grade`)
> - New API schema + tests for the endpoint response
> - Frontend chart migrated off `useMultipleSeries(['pace','grade'])`
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES (2 waves)
> **Critical Path**: Backend contract + endpoint  Frontend client + chart migration  Verification

---

## Context

### Original Request
- Move Allure-vs-Grade computation from frontend to backend.
- Backend returns binned pace-vs-grade (+ std) + pro reference curve.
- Frontend renders using endpoint; no heavy computation.

### Current Implementation (verified)
- Frontend bins client-side in `frontend/src/components/charts/AllureVsPenteChart.tsx` using series from `frontend/src/hooks/useActivity.ts:useMultipleSeries()`.
- Pro reference curve is duplicated in frontend: `frontend/src/lib/proPaceVsGrade.ts`.
- Backend already contains pace-vs-grade logic:
  - `backend/core/real_run_analysis.py:compute_pace_vs_grade_data()` (currently returns `grade_center`, `pace_med`, `pace_std` in min/km)
  - `backend/core/real_run_analysis.py:build_pace_vs_grade_plot()` overlays `get_pro_pace_vs_grade_df()`.
- Backend API is FastAPI and uses routers:
  - App: `backend/api/main.py`
  - Analysis router: `backend/api/routes/analysis.py`
  - Schemas: `backend/api/schemas.py`
- Frontend API calls follow `frontend/src/lib/api.ts` (`apiRequest` + `analysisApi.*`).

### Metis Review
- Not available in this environment (tooling restriction). This plan includes an explicit self gap-check section.

---

## Work Objectives

### Core Objective
Expose a stable, backend-computed pace-vs-grade dataset for the chart (bins + std + pro ref), and remove client-side binning and pro-curve duplication from the frontend.

### Definition of Done
- Frontend `AllureVsPenteChart` renders exclusively from the new endpoint (no `useMultipleSeries(['pace','grade'])` usage).
- New endpoint returns a stable, versioned response with documented units.
- Existing endpoints remain behaviorally unchanged.
- Backend + frontend verification commands pass.

### Must NOT Do (guardrails)
- Do not add new heavy dependencies.
- Do not change behavior of existing endpoints (`/activity/*/real`, `/series/*`, `/map`, etc.).

---

## Key Design Decisions (with placeholders)

1) **Binning semantics** (affects chart appearance)
- [DECISION NEEDED]
  - Option A (preserve current UI): 1% bins by rounding grade, pace mean + sample std (s/km), minimal filtering.
  - Option B (reuse current backend behavior): 0.5% bins using `pd.cut`, pace median + std (min/km), includes backend filtering (moving mask + slow outlier filter).

2) **Units in API response**
- Default recommendation: **pace in `s_per_km`** to match frontend formatters (`formatPaceSecondsPerKm`) and existing series semantics.

3) **Pro reference curve**
- Include raw points from backend source (`backend/core/resources/pro_pace_vs_grade.csv`) via `backend/core/ref_data.py:get_pro_pace_vs_grade_df()`.

---

## API Contract Proposal

### Endpoint
- `GET /activity/{activity_id}/pace_vs_grade`

### Query params (keep minimal; defaults stable)
- `bin_size_pct` (float, optional; default depends on Decision #1)
- `grade_clamp_pct` (float, optional; default 20)
- `method` (enum: `ui_round_mean` | `core_cut_median`, optional; default depends on Decision #1)

### Response (Pydantic)
- `version`: string (e.g. `"1"`)
- `bins`: list of bin rows
  - `grade_pct`: float
  - `pace_s_per_km`: float
  - `pace_std_s_per_km`: float
  - `n`: int
- `pro_ref`: list of reference points
  - `grade_pct`: float
  - `pace_s_per_km`: float
- `meta`: includes `bin_size_pct`, `grade_clamp_pct`, `method`

---

## Verification Strategy

### Backend
- Add/extend pytest coverage for the new endpoint using `fastapi.testclient.TestClient`.
- Reuse existing test patterns from `tests/pytest/test_api_smoke.py` and `tests/pytest/test_api_cardio.py`.

### Frontend
- Typecheck/build to ensure API types and chart compile.

---

## Execution Strategy (Parallel Waves)

Wave 1 (Backend contract + endpoint):
- Task 1: Define Pydantic schema for response
- Task 2: Implement endpoint in analysis router
- Task 3: Implement/adjust computation helper (reuse core + ref_data)
- Task 4: Add backend tests

Wave 2 (Frontend migration):
- Task 5: Add frontend API client method + TS types
- Task 6: Refactor `AllureVsPenteChart` to fetch and render payload
- Task 7: Remove/stop using client-side pro curve + binning helpers

Critical Path: 1  2  5  6  Verification

---

## TODOs (implementation-ready)

- [ ] 1. Define backend response schema for pace-vs-grade

  **What to do**:
  - Add new Pydantic models to `backend/api/schemas.py` for:
    - `PaceVsGradeBin`
    - `ProPaceVsGradePoint`
    - `PaceVsGradeResponse` (including `version` + `meta`)

  **Must NOT do**:
  - Do not modify existing schema fields used by current endpoints.

  **References**:
  - `backend/api/schemas.py`  existing schema style and conventions.
  - `frontend/src/types/api.ts`  TS-side contract mirror style.

  **Acceptance Criteria**:
  - `python -m compileall backend` exits 0.

- [ ] 2. Implement backend endpoint `GET /activity/{activity_id}/pace_vs_grade`

  **What to do**:
  - Add a new route handler in `backend/api/routes/analysis.py`.
  - Load the activity DataFrame via `request.app.state.storage.load_dataframe(activity_id)` (same as existing endpoints).
  - Compute bins + pro curve and return `PaceVsGradeResponse`.
  - Ensure endpoint is included under both `/` and `/api` prefixes (already handled by `backend/api/main.py` router include).

  **References**:
  - `backend/api/routes/analysis.py`  patterns for storage loading, error handling, and response construction.
  - `backend/api/main.py`  router inclusion and `/api` compatibility.

  **Acceptance Criteria**:
  - `python -m pytest tests/pytest/test_api_smoke.py` passes.
  - `curl -s http://127.0.0.1:8000/activity/<activity_id>/pace_vs_grade | python -m json.tool` returns valid JSON (manual with a real id).

- [ ] 3. Implement computation helper (reuse existing core)

  **What to do**:
  - Add a service-level function (preferred location: `backend/services/real_activity_service.py`) that:
    - accepts a DataFrame
    - returns bins (pace + std) in **seconds per km**
    - attaches pro reference points from `backend/core/ref_data.py:get_pro_pace_vs_grade_df()`
  - Reuse `backend/core/real_run_analysis.py:compute_pace_vs_grade_data()` where possible.
  - If Decision #1 requires UI-accurate binning, either:
    - extend `compute_pace_vs_grade_data()` with optional parameters (keeping existing defaults to preserve plot behavior), or
    - create a small additional helper in `backend/core/real_run_analysis.py` dedicated to API output.

  **References**:
  - `backend/services/real_activity_service.py:build_figures()`  existing pro_ref wiring.
  - `backend/core/real_run_analysis.py:compute_pace_vs_grade_data()`  existing filtering/binning approach.
  - `backend/core/ref_data.py:get_pro_pace_vs_grade_df()`  authoritative pro curve source.

  **Acceptance Criteria**:
  - For a non-empty activity, endpoint returns:
    - `bins.length > 0`
    - `pro_ref.length > 0`
    - all `pace_s_per_km > 0`, `pace_std_s_per_km >= 0`

- [ ] 4. Add backend API test for the new endpoint

  **What to do**:
  - Add a pytest test (new file recommended): `tests/pytest/test_api_pace_vs_grade.py`.
  - Follow the pattern in `tests/pytest/test_api_cardio.py`:
    - start `TestClient(app)` using `backend/api/main.py:app`
    - upload a small activity (reuse existing helper in test suite if present)
    - call `GET /activity/{activity_id}/pace_vs_grade`
    - assert response schema (keys + types + non-empty arrays)

  **References**:
  - `tests/pytest/test_api_cardio.py`  upload + fetch pattern.
  - `tests/pytest/test_api_smoke.py`  basic API expectations.

  **Acceptance Criteria**:
  - `python -m pytest tests/pytest/test_api_pace_vs_grade.py` passes.

- [ ] 5. Add frontend API client + TS types for the new endpoint

  **What to do**:
  - Extend `frontend/src/types/api.ts` with:
    - `PaceVsGradeBin`, `ProPaceVsGradePoint`, `PaceVsGradeResponse`
  - Extend `frontend/src/lib/api.ts`:
    - add `analysisApi.getPaceVsGrade(activityId, params?)`
  - Extend `frontend/src/hooks/useActivity.ts`:
    - add `usePaceVsGrade(activityId, params?)` using React Query (same patterns as `useRealActivity`).

  **References**:
  - `frontend/src/lib/api.ts`  existing API base URL + `apiRequest()` usage.
  - `frontend/src/hooks/useActivity.ts`  React Query keying patterns.
  - `frontend/src/types/api.ts`  API type conventions.

  **Acceptance Criteria**:
  - `cd frontend && npm run build` succeeds.

- [ ] 6. Refactor `AllureVsPenteChart` to render from backend payload

  **What to do**:
  - Replace `useMultipleSeries(activityId, ['pace','grade'])` usage with `usePaceVsGrade(activityId, ...)`.
  - Remove client-side binning functions (`mean`, `std`, the `Map<number, number[]>` binning loop).
  - Keep only lightweight transformations needed for Recharts:
    - compute `paceLower/paceUpper` from returned `paceStd`
    - compute `proPace` by interpolating `pro_ref` (optional)
  - Ensure empty/loading/error states do not render the chart.

  **References**:
  - `frontend/src/components/charts/AllureVsPenteChart.tsx`  current chart rendering and tooltip.
  - `frontend/src/lib/proPaceVsGrade.ts`  current pro interpolation logic (may be removed or kept as fallback).

  **Acceptance Criteria**:
  - UI renders the chart for a loaded activity.
  - No additional series endpoint calls happen for this chart (verify via dev console: only one request for pace_vs_grade).

- [ ] 7. Remove/retire frontend pro curve duplication (optional cleanup)

  **What to do**:
  - If the endpoint always provides `pro_ref`, stop importing `PRO_PACE_VS_GRADE` from `frontend/src/lib/proPaceVsGrade.ts`.
  - Decide whether to keep the file as fallback/offline mode or remove it.

  **Guardrail**:
  - If removed, ensure no other components rely on it.

  **Acceptance Criteria**:
  - `cd frontend && npm run build` succeeds.

---

## Success Criteria (end-to-end)

### Backend verification commands
```bash
python -m compileall backend
python -m pytest tests/pytest/
```

### Frontend verification commands
```bash
cd frontend
npm run build
```

### Manual API spot-check (optional)
```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/activity/<activity_id>/pace_vs_grade | python -m json.tool
```
