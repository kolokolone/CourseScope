# Audit Backend - CourseScope (agent-review)

Timestamp: 2026-02-13 21:16 (local)

## Top 10 improvements (prioritized)

1) Fix or remove the broken adapter in `backend/api/compat.py`.
   - Risk: runtime crash if imported/used (references `ActivityType.REAL_RUN` even though `ActivityType` is a `Literal`).
   - Safe path: make it consistent with `services.models` literals ("real_run" / "theoretical_route") and align dataclass fields.

2) Align cache interface semantics in `backend/services/cache.py`.
   - Risk: `KeyValueCache.get()` is used as a nullable-return API in `backend/services/analysis_service.py`, but `MemoryCache.get()` raises `KeyError` (mismatch with `KeyValueCache` protocol).
   - Suggested: either change `MemoryCache.get()` to return `None` on miss, or keep it separate (do not claim it implements `KeyValueCache`).

3) Normalize error handling so 500s always include `request_id`.
   - Current: middleware in `backend/api/main.py` adds `request_id` only for uncaught exceptions.
   - Routes often catch `Exception` and raise `HTTPException(500, detail=...)` without `request_id`, bypassing middleware’s 500 envelope.
   - Suggested: avoid broad `except Exception` in routes (let middleware wrap), or include `request_id` in those 500 payloads.

4) Add negative-path API tests (4xx/5xx) and headers.
   - Tests mostly cover happy paths.
   - Add coverage for: invalid file extension, file too large (413), missing activity (404), invalid series name (400), Garmin reauth-required (401), and verify `X-Request-ID` header and 500 JSON shape.

5) Consolidate `_model_to_dict` usage.
   - Duplicated in `backend/api/routes/activities.py`, `backend/api/routes/series.py`, and `backend/storage/activity_store.py`.
   - Suggested: a single helper that consistently returns JSON-compatible types (Pydantic v2 `mode="json"`).

6) Clarify or implement downsampling for `/series` endpoint.
   - `backend/registry/series_registry.py` accepts `downsample` but currently always returns full sampling; downsampling code exists but is unused/placeholder.
   - Risk: UI performance issues on large activities and confusing API parameter semantics.

7) Tighten typing / contracts for API response models.
   - `backend/api/schemas.py` uses many `dict`/`Optional[dict]` fields (loose contracts).
   - Suggested: progressively type the nested payloads (even shallowly) to reduce regressions.

8) Reduce import-path fragility.
   - Mixed import styles (`from config import ...` vs `from backend.config import ...`) plus path-hacking patterns make packaging/test execution brittle.
   - Suggested: standardize absolute imports under the `backend` package and remove `sys.path` hacks once imports are clean.

9) Storage/index consistency improvements.
   - `backend/storage/activity_store.py` deletes filesystem dirs but does not update the DB index on per-activity delete.
   - Mitigation exists (`_get_db_activity_id_by_hash` checks dir exists), but DB can accumulate stale rows.

10) Security hygiene for Garmin credentials.
   - `backend/integrations/garmin/credentials_store.py` stores plaintext email/password in `data/.../credentials.json`.
   - Even if kept (no feature change), document risk and ensure the data dir is excluded/secured (permissions, `.gitignore`, user guidance).

## Backend mindmap (files)

```
backend/
  __init__.py                      - package marker (empty)
  config.py                        - env-based paths (data dir, activities dir, garmin tokens dir)
  data/                            - local runtime data (non-code)
    activities/                    - activity storage directory (runtime)
  api/
    __init__.py                    - package marker (empty)
    main.py                        - FastAPI app entrypoint, lifespan init, middleware, router mounting, CORS
    schemas.py                     - Pydantic models for API request/response payloads
    compat.py                      - adapter between API layer and service models (currently inconsistent/buggy)
    routes/
      __init__.py                  - package marker (empty)
      activities.py                - upload/load/list/delete/cleanup activity endpoints
      analysis.py                  - real/theoretical analysis endpoints + pace-vs-grade endpoint
      series.py                    - per-series and series-index endpoints
      maps.py                      - map payload endpoint (bbox/polyline/markers)
      garmin_integration.py        - Garmin connect/sync/status/reset endpoints
  services/
    __init__.py                    - service layer contract (UI-free)
    models.py                      - dataclasses for service-level domain payloads
    activity_service.py            - bytes->DF loading, contract validation, sidebar stats, view suggestion
    analysis_service.py            - orchestration entrypoints + caching (load/analyze)
    real_activity_service.py       - orchestration for real activity outputs (garmin stats, figures, map payload)
    theoretical_service.py         - orchestration for theoretical activity outputs
    serialization.py               - JSON-safe serialization for pandas/numpy/plotly/dataclasses
    cache.py                       - cache abstractions + in-memory/disk implementations
    history_service.py             - pure helper for history list updates
  core/
    __init__.py                    - core layer contract (UI-free)
    constants.py                   - shared numeric defaults/thresholds
    derived.py                     - DerivedSeries dataclass (grade/moving/gap)
    parsing.py                     - parse helpers (km list)
    formatting.py                  - formatting helpers (durations, HH:MM:SS)
    utils.py                       - misc conversion helpers (pace, mm:ss)
    grade_table.py                 - grade->pace factor table + helpers
    gpx_loader.py                  - GPX parsing + DF building + type detection
    fit_loader.py                  - FIT parsing + DF building + datetime patch + type detection
    stats/
      __init__.py                  - package marker
      basic_stats.py               - distance/time/elevation basic stats
    contracts/
      __init__.py                  - package marker
      activity_df_contract.py      - canonical DF schema + coercion + validation
    resources/
      __init__.py                  - package marker
      pro_pace_vs_grade.csv        - packaged reference data
    ref_data.py                    - loading/caching pro pace-vs-grade reference table
    theoretical_model.py           - theoretical timing/splits/summary + plotly figure
    transform_report.py            - TransformReport to track data-shaping steps
    real_run_analysis.py           - core real-run computations (moving mask, splits, efforts, climbs, plots)
    metrics.py                     - Garmin-like metrics computation + zone tables
  storage/
    __init__.py                    - package marker (empty)
    activity_store.py              - activity persistence (parquet/meta.json) + in-memory storage
  registry/
    __init__.py                    - package marker (empty)
    series_registry.py             - series definitions + extraction/slicing/cleaning for API
  db/
    __init__.py                    - DB layer description
    models.py                      - SQLAlchemy ORM models
    session.py                     - engine/session factory + schema init
    repository.py                  - repository methods for dedupe/source mapping/cursor/sync runs
  integrations/
    __init__.py                    - integrations package
    garmin/
      __init__.py                  - garmin integration package
      client.py                    - login/token resume + MFA state
      credentials_store.py         - save/load plaintext credentials (data dir)
      sync_service.py              - backfill/incremental sync, dedupe by hash, DB cursor/state
```

## Inventory of backend functions/classes (module-level)

Source: AST scan across `backend/**/*.py` (module-level defs + class methods). Line numbers omitted here; see code for exact locations.

API
- `backend/api/main.py`: `_DefaultRequestIdFilter.filter`, `_configure_logging`, `lifespan`, `request_logging_middleware`, `get_activity_storage`, `get_series_registry`, `root`, `health_check`.
- `backend/api/routes/activities.py`: `_get_logger`, `_get_request_id`, `get_activity_storage`, `_model_to_dict`, `check_dataframe_limits`, `load_activity_endpoint`, `list_activities`, `delete_activity`, `cleanup_all_activities`.
- `backend/api/routes/analysis.py`: `_interp_pro_pace_s_per_km`, `_is_finite_number`, `_build_cardio_summary`, `get_series_registry`, `_build_limits`, `prepare_real_response`, `prepare_theoretical_response`, `get_real_activity`, `get_theoretical_activity`, `get_pace_vs_grade`.
- `backend/api/routes/series.py`: `_model_to_dict`, `get_series_registry`, `get_series`, `list_available_series`.
- `backend/api/routes/maps.py`: `calculate_bounds`, `extract_polyline`, `extract_markers`, `get_activity_map`.
- `backend/api/routes/garmin_integration.py`: request/response models + `_tokens_present`, `garmin_connect`, `garmin_sync`, `garmin_reset`, `garmin_status`, `garmin_credentials_status`, `garmin_save_credentials`.

Config
- `backend/config.py`: `get_data_dir`, `get_garmin_tokens_dir`, `get_activities_dir`.

Core contracts/stats/loaders
- `backend/core/contracts/activity_df_contract.py`: `ValidationReport.raise_for_issues`, `coerce_activity_df`, `validate_activity_df`, `assert_activity_df_contract`.
- `backend/core/stats/basic_stats.py`: `_time_range_from_time_column`, `_total_time_fallback_seconds`, `_distance_m`, `_elevation_gain_loss`, `compute_basic_stats`.
- `backend/core/gpx_loader.py`: `_decode_gpx_bytes`, `_local_tag`, `_extract_extension_value`, `_extract_extension_values`, `load_gpx`, `gpx_to_dataframe`, `detect_gpx_type`.
- `backend/core/fit_loader.py`: `_patch_fitparse_datetime`, `_build_field_lookup`, `_get_value`, `_field_value_and_units`, conversions helpers, `load_fit`, `fit_to_dataframe`, `detect_fit_type`.

Core analytics
- `backend/core/real_run_analysis.py`: statistical helpers, `compute_moving_mask`, `compute_derived_series`, `compute_summary_stats`, `compute_pace_series`, `compute_splits`, `compute_best_efforts`, `compute_best_efforts_by_duration`, `compute_race_predictions`, `build_distribution_plots`, `compute_pace_vs_grade_data`, `build_pace_vs_grade_plot*`, grade/gap helpers, scatter/heatmap, residuals, `compute_climbs`, `compute_pause_markers`, `build_pace_elevation_plot`.
- `backend/core/metrics.py`: zone/pace/power helpers, `estimate_zone_inputs`, `compute_garmin_like_stats`, `format_zone_table`.
- `backend/core/theoretical_model.py`: `compute_theoretical_timing`, `compute_theoretical_splits`, `compute_theoretical_summary`, `compute_passage_at_distances`, `build_theoretical_plot`.
- `backend/core/ref_data.py`: pro table loader helpers + `load_pro_pace_vs_grade`, `get_pro_pace_vs_grade_df`, `get_pro_pace_vs_grade_info`.

Services
- `backend/services/activity_service.py`: `load_activity_from_bytes`, `compute_sidebar_stats`, `suggest_default_view`.
- `backend/services/analysis_service.py`: `load_activity`, `analyze_real`, `analyze_theoretical`.
- `backend/services/real_activity_service.py`: `prepare_base`, `compute_map_df`, `compute_pace_series`, `compute_garmin_stats`, `build_figures`, `analyze_real_activity`.
- `backend/services/theoretical_service.py`: `prepare_base`, `compute_display_df`, `compute_passages`, `build_base_figure`, `compute_splits`, `compute_weather_factor`, `compute_advanced`, `compute_adv_cap_default`, `analyze_theoretical_activity`.
- `backend/services/serialization.py`: `_is_nan`, `_dt_to_iso`, `df_to_records`, `series_to_list`, `to_jsonable`.
- `backend/services/cache.py`: `KeyValueCache`, `MemoryCache`, `DiskCache`, `NullCache`, `InMemoryCache`, `make_cache_key`.
- `backend/services/history_service.py`: `upsert_history`.

Storage / DB / Integrations
- `backend/storage/activity_store.py`: helpers + `ActivityStorage` interface + `LocalTempStorage` + `InMemoryStorage`.
- `backend/db/session.py`: `get_database_url`, `make_engine`, `make_session_factory`, `init_db`.
- `backend/db/repository.py`: `ActivityIndexRepository` methods (hash/source mapping, cursor, sync runs, deletes).
- `backend/integrations/garmin/client.py`: `start_login`, `resume_login_with_otp`, `connect_with_tokens` (+ helpers).
- `backend/integrations/garmin/credentials_store.py`: `load_credentials`, `save_credentials`, `credentials_status` (+ helper).
- `backend/integrations/garmin/sync_service.py`: `GarminSyncService.sync` (+ helpers).

## Detailed audit (by file)

### `backend/api/main.py`

Purpose: FastAPI app creation, lifespan initialization (logger/DB/storage/registry), request logging middleware, router mounting.

Findings
- `_configure_logging`:
  - Good: clears handlers to avoid duplicates; adds request_id filter; writes both file and stream.
  - Risk: file handler encoding is UTF-8 (good), but log file path is time-based; frequent restarts generate many files.
- `lifespan`:
  - Good: initializes DB + storage + registry and puts into `app.state`.
  - Risk: no explicit teardown/close for DB engine; acceptable for process lifetime.
- `request_logging_middleware`:
  - Good: generates UUID request id; adds `X-Request-ID` header; logs request duration.
  - Gap: route-level `except Exception` handlers prevent this middleware from returning the canonical 500 payload shape.
- Router mounting:
  - Good: mounts both direct and `/api/*` mirrors for compatibility.
  - Risk: version string duplicated in `FastAPI(version=...)` and `root()` response.

Tests
- Covered by `tests/pytest/test_api_smoke.py` for `/health` and general request flow.
- Missing: explicit assertion on `X-Request-ID` presence, and on JSON 500 envelope including `request_id`.

### `backend/api/routes/activities.py`

Purpose: activity upload (GPX/FIT), list, delete, and cleanup.

Function audits
- `_get_logger` / `_get_request_id`:
  - OK; request_id fallback to "-".
- `check_dataframe_limits`:
  - Behavior: only returns flags; does not downsample.
  - Risk: suggests downsampling without providing it; might be fine as a UI hint.
- `load_activity_endpoint`:
  - Good: validates filename/ext; size guard; logs structured events; uses contract validation via `services.analysis_service.load_activity`.
  - Risk: reads full upload into memory; acceptable with `max_size` guard.
  - Risk: uses private method `storage._compute_sidebar_stats` (ties endpoint to `LocalTempStorage`).
  - Edge cases: missing content_type; FIT uploads can use octet-stream (test covers).
- `list_activities`:
  - Risk: returns dicts (via `_model_to_dict`) rather than `response_model`; typing/serialization depends on helper.
- `delete_activity`:
  - Risk: DB index entries are not removed (filesystem deletion only).
- `cleanup_all_activities`:
  - Good: clears both filesystem and DB index/cursor.

Tests
- Happy-path upload/list/map/series via `tests/pytest/test_api_smoke.py`.
- Missing: invalid extension/413 cases, delete path (404/500), and list payload shape assertions.

### `backend/api/routes/analysis.py`

Purpose: build API response payloads for real/theoretical analysis and pace-vs-grade.

Function audits
- `_interp_pro_pace_s_per_km`:
  - OK linear interpolation; protects against missing/parse errors.
  - Improvement: input rows assumed sorted; caller sorts (good).
- `_build_cardio_summary`:
  - Good: guards types and finiteness; enriches summary with cardio values.
- `prepare_real_response`:
  - Good: isolates API payload shaping from core computations.
  - Risk: `personal_records_payload` duplicates `best_efforts_rows` (likely placeholder or semantic bug).
  - Risk: multiple `to_jsonable` conversions; could be centralized.
- `prepare_theoretical_response`:
  - Note: returns `TheoreticalActivityResponse` inheriting `RealActivityResponse` but sets many fields to `None`/empty.
- `get_real_activity`/`get_theoretical_activity`:
  - Pattern: load df from persistent storage, fallback to temp storage.
  - Risk: broad `except Exception` returns 500 without request_id.
- `get_pace_vs_grade`:
  - Good: reuses core `compute_pace_vs_grade_data` + adds pro reference curve points.
  - Edge cases: pro reference CSV missing -> returns empty pro_ref (good).

Tests
- `tests/pytest/test_api_smoke.py`, `tests/pytest/test_api_cardio.py` cover successful real analysis.
- Missing: 404 on missing activity, 500 envelope shape, and correctness tests for pace-vs-grade schema.

### `backend/api/routes/series.py`

Purpose: provide series extraction endpoint via `SeriesRegistry`.

Findings
- Duplicates `_model_to_dict`.
- Pattern: route-level try/except maps ValueError to 400, FileNotFoundError to 404.
- Risk: broad 500 without request_id.

### `backend/api/routes/maps.py`

Purpose: compute bbox/polyline/markers from activity df.

Function audits
- `calculate_bounds`:
  - OK; returns [minLon,minLat,maxLon,maxLat]; returns zeros when missing.
- `extract_polyline`:
  - Note: returns list of [lat, lon] (not [lon,lat]). Ensure frontend expects this.
  - Performance: uses `iterrows()`; may be slow on large df.
- `extract_markers`:
  - Heuristics: pauses based on speed<0.1; max elevation marker.
  - Risk: iterating all pauses can be many points.

### `backend/api/routes/garmin_integration.py`

Purpose: Garmin auth + MFA resume + sync + status/reset.

Findings
- `_tokens_present`: safe; catches errors.
- `garmin_connect`: supports MFA via in-memory dict `app.state.garmin_mfa_states`.
  - Risk: store is in-memory; process restart invalidates sessions (expected).
  - Risk: broad exception returns 500 without request_id.
- `garmin_sync`: runs sync in thread via `anyio.to_thread.run_sync` (good for blocking IO).
- `garmin_reset`/`garmin_status`: directly manipulates repository + closes session (good).
- Credentials endpoints:
  - Uses plaintext credentials store (document security implications).

Tests
- `tests/pytest/test_garmin_integration_sync.py` covers idempotency and dedupe-by-hash.
- Missing: auth error mapping, MFA path, reset/status payload assertions.

### `backend/config.py`

Purpose: stable env-driven paths.

Findings
- OK minimal.
- Suggested: consider `.resolve()` consistently at boundary (some callers resolve).

### `backend/services/analysis_service.py`

Purpose: UI-free entrypoints with caching.

Function audits
- `load_activity`:
  - Good: stable cache key includes schema version + sha256 + activity_type.
  - Risk: assumes `cache.get()` returns `None` on miss.
- `analyze_real`:
  - Good: stable key includes params/view; returns cached `RealRunResult`.
  - Risk: passes `loaded.df` which can be `None` if caller uses storage.load() not load_dataframe(); ensure call sites pass a fully-loaded activity.
- `analyze_theoretical`:
  - Good orchestration; returns `TheoreticalResult` with figures.

Tests
- `tests/unit/test_analysis_service.py` covers `load_activity` caching and JSON serialization.

### `backend/services/activity_service.py`

Purpose: bytes -> parsed activity df + contract validation.

Findings
- `load_activity_from_bytes`:
  - Good: chooses loader by extension; coercion + single validation at service boundary.
  - Edge case: non-.fit treated as GPX; if random extension slips through upstream, parsing will fail (API already checks extensions).
- `compute_sidebar_stats`:
  - Uses `compute_basic_stats`; output uses `None` for non-positive values.
  - Note: differs from API `SidebarStats` fields naming (`elapsed_time_s` vs `duration_s` in service model); keep an eye on mapping.
- `suggest_default_view`: OK.

### `backend/services/real_activity_service.py`

Purpose: compose core computations into API-friendly payloads for real activities.

Findings
- `prepare_base`:
  - Good: centralizes derived series, summary, zones defaults, best efforts, climbs, pauses, splits.
- `compute_map_df`:
  - Good: dropna lat/lon/distance; returns map-ready df with color/label.
  - Risk: map_df index subset; assignments rely on index alignment (works), but ensure derived series indices match df.
- `compute_garmin_stats`: delegates to `core.metrics.compute_garmin_like_stats`.
- `build_figures`: fetches pro ref once.
- `analyze_real_activity`: OK composition.

### `backend/services/theoretical_service.py`

Purpose: compose theoretical timing computations into API-friendly payloads.

Notes
- `compute_weather_factor`: deterministic clamp; OK.
- `_compute_adjusted_pace_base`: shared helper; good dedupe.

### `backend/services/serialization.py`

Purpose: convert pandas/numpy/dataclasses/plotly figures to JSON-serializable primitives.

Findings
- Good: handles NaN/NaT, datetime, numpy scalars, plotly figures.
- Risk: fallback `str(obj)` can hide type regressions; acceptable as last resort but should be used consciously.

Tests
- `tests/unit/test_serialization.py`, `tests/pytest/test_serialization_df_to_records.py`, `tests/unit/test_serialization_plotly.py`.

### `backend/services/cache.py`

Purpose: caching helpers.

Findings
- `KeyValueCache` protocol says `get` returns `Any|None`.
- `MemoryCache.get` raises `KeyError` -> mismatch.
- `InMemoryCache` matches protocol and is used in tests.
- `DiskCache` uses pickle; security risk if enabled on untrusted data (document).

### `backend/storage/activity_store.py`

Purpose: persist activities to disk (original file + parquet + meta) and optionally index in DB.

Findings
- `LocalTempStorage.store`:
  - Good: dedupe by sha256 when DB enabled.
  - Good: normalizes tz-aware datetime columns to UTC naive before parquet.
  - Risk: writes `meta.json` without explicit encoding; prefer `encoding="utf-8"` for portability.
  - Risk: broad exception wraps and deletes directory; OK but can hide root exception type.
- `LocalTempStorage.list_activities`:
  - Good: robust to legacy metadata by backfilling `started_at` from parquet time column.
  - Performance: reading parquet `time` column per activity can be expensive if many items.
- `delete`/`cleanup_all`:
  - DB index rows may remain unless route explicitly clears them.
- `InMemoryStorage`:
  - `list_activities` returns empty list (feature gap, but likely acceptable for temp storage).

### `backend/db/session.py`, `backend/db/models.py`, `backend/db/repository.py`

Purpose: DB index for activity dedupe and integration state.

Findings
- Uses SQLite by default (file under data dir) with env override.
- `check_same_thread=False` helps FastAPI TestClient.
- Repository methods are minimal and mostly safe.
- Missing tests for repository/session behaviors.

### `backend/integrations/garmin/*`

Findings
- `client.py`:
  - Good: handles MFA by returning in-memory client state; persists tokens.
  - Error handling: wraps requests HTTP errors with body snippet.
- `credentials_store.py`:
  - Stores plaintext credentials; returns status payload for UI.
- `sync_service.py`:
  - Good: backfill/incremental logic with env tunables; chunking; dedupe by source mapping and sha256 of extracted fit bytes.
  - Error path: returns `GarminSyncResult(status="error", error=str(exc))` and records DB sync run status.

## Tests audit (backend)

Current
- `pytest.ini` sets `tests/unit` + `tests/pytest`.
- Mixed styles: many `unittest.TestCase` + some pytest function tests.

Gaps
- Negative-path coverage for API routes (4xx/5xx) and request-id headers.
- DB layer untested.
- Garmin auth/MFA untested.

## External best-practice references (FastAPI)

- Handling errors / exception handlers: https://fastapi.tiangolo.com/tutorial/handling-errors/
- App structure (`APIRouter`, larger apps): https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Testing dependencies / overrides: https://fastapi.tiangolo.com/advanced/testing-dependencies/
