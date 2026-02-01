# Draft: Allure-vs-Grade Backend Move

## Requirements (confirmed)
- Move Allure-vs-Grade computation (binning + std + pro reference curve) from frontend to backend.
- Add a backend endpoint that returns binned pace-vs-grade (+ std) plus a pro reference curve.
- Update frontend chart to use the endpoint and avoid heavy computation in React.
- No new heavy dependencies.
- Do not change behavior of existing endpoints.
- Must account for existing backend functions around pace-vs-grade:
  - `backend/services/real_activity_service.py`
  - `backend/core/real_run_analysis.py`
- UI must use existing fetch patterns.

## Codebase Findings (confirmed)
- Frontend chart currently bins client-side:
  - `frontend/src/components/charts/AllureVsPenteChart.tsx`
  - It currently fetches series data via `useMultipleSeries(activityId, ['pace','grade'], { x_axis: 'time' })` and then:
    - clamps grade to +/- 20
    - bins by 1% (rounded)
    - computes mean + sample std (n-1)
    - overlays pro curve from `frontend/src/lib/proPaceVsGrade.ts`
- Frontend fetch pattern:
  - `frontend/src/lib/api.ts` provides `apiRequest()` and API modules (`analysisApi`, `seriesApi`, etc.)
  - `frontend/src/hooks/useActivity.ts` uses React Query for data fetching (`useQuery`, `useQueries`).
- Backend pace-vs-grade computation exists in core:
  - `backend/core/real_run_analysis.py:compute_pace_vs_grade_data()` returns columns `grade_center`, `pace_med`, `pace_std` (currently in min/km).
  - `backend/core/real_run_analysis.py:build_pace_vs_grade_plot()` uses that and overlays `get_pro_pace_vs_grade_df()`.
- Backend API is FastAPI:
  - `backend/api/main.py` defines the FastAPI app and includes routers under both `/` and `/api` prefixes.
  - `backend/api/routes/analysis.py` currently serves:
    - `GET /activity/{activity_id}/real`
    - `GET /activity/{activity_id}/theoretical`
  - Schemas live in `backend/api/schemas.py` (Pydantic models).
- Backend orchestration for real activity analysis:
  - `backend/services/real_activity_service.py:build_figures()` already calls `build_pace_vs_grade_plot(...)`.

## Open Questions
- Should the new backend bins match the current frontend chart semantics exactly (bin size 1%, mean pace + sample std), or is it acceptable to switch to the backend’s current semantics (0.5% bins, median pace + std computed in min/km)?
- Should the endpoint return pace in `s_per_km` (to match frontend formatting and existing series units) or `min_per_km` (to match current core output)?

## Scope Boundaries
- INCLUDE: new endpoint + schemas + service-level helper + frontend migration to fetch/render without client binning.
- EXCLUDE: changing existing endpoint behavior; adding new large dependencies; redesigning chart UI beyond wiring/data shape changes.
