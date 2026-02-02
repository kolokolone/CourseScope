# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [1.1.43] - 2026-02-02

### Changed
- Frontend: chart/metrics rendering tweaks and test adjustments.
- Backend: improve split computation robustness (moving-time behavior) and align related pytest expectations.

## [1.1.44] - 2026-02-02

### Changed
- Backend: pace-vs-grade now uses robust pause filtering (compute_moving_mask), fixed bin edges (include -20), and time-weighted per-bin aggregates.
- Backend/API: added optional pace-vs-grade fields (time_s_bin, weighted quantiles/mean, n_eff, outlier_clip_frac) without breaking existing response fields.
- Tests/Docs: added non-regression coverage + detailed metric documentation.

## [1.1.45] - 2026-02-02

### Changed
- UI (pace-vs-grade): force regular X-axis ticks every 2.5% and always show 0%.
- UI/Types: extend MetricTableColumn with optional `align` for table layouts.

## [1.1.46] - 2026-02-02

### Changed
- Backend (climbs): replaced point-grade thresholding with distance-windowed grade + hysteresis + gap-bridging; metrics computed on full segments.
- Backend (climbs): return all detected climbs (sorted by elevation gain) instead of truncating to top 3.
- Tests: added synthetic non-regression coverage for climb detection (noise, replats, descent split, stops).

## [1.1.47] - 2026-02-02

### Changed
- Climbs table: replace Start/End with "Début -> Fin (km)" and "Durée"; reorder columns.
- Climbs table: show D+ with 2 decimals; add backend-provided `start_end_km` and `duration_s`.

## [1.1.48] - 2026-02-02

### Changed
- Docs: updated metrics catalog/list with new climbs and pace-vs-grade fields; added documentation update runbook.

## [1.1.49] - 2026-02-02

### Fixed
- Docs tooling: include hidden climbs helper fields in metrics registry so `docs/metrics_list.txt` stays in sync with registry coverage tests.

## [1.1.41] - 2026-01-31

### Changed
- Docs/versioning: align README and package versions with the latest published tag history (v1.1.39 remains the code tag; this release publishes the docs/version bumps).

## [1.1.39] - 2026-01-31

### Fixed
- Charts: improve Y-axis auto-domain so each chart focuses on the real value range.
- Climbs: show the Climbs card even when no climbs are detected (so the pace-vs-grade chart can still render).

## [1.1.38] - 2026-01-31

### Added
- Backend: new endpoint `GET /activity/{id}/pace-vs-grade` returning binned pace-vs-grade (median + std + count) plus pro reference curve.

### Changed
- Climbs: "Allure vs Pente" now consumes backend-computed bins (frontend renders only; no heavy binning computation in UI).

### Fixed
- Tests: added smoke verification steps for `/pace-vs-grade` endpoint.

## [1.1.37] - 2026-01-31

### Fixed
- Map (Next.js dev/SSR): avoid Leaflet SSR crash ("window is not defined") by dynamically loading the Leaflet map client-side only.
- Map: "Points de pauses" now uses `pauses.items` as a fallback source (in addition to `/map` markers), so the toggle works even when map markers do not include pauses.

### Changed
- Charts: add shared smoothing control (Off/5/10/15), persisted across navigation.
- Charts: sync x-axis hover/cursor between all charts; distance axis ticks show whole kilometers.

## [1.1.36] - 2026-01-31

### Fixed
- Climbs: "Allure vs Pente" now reliably renders both curves (user + pro reference).

### Changed
- Climbs: show a shaded variability band (std) and dynamic Y domain on the "Allure vs Pente" chart.

## [1.1.35] - 2026-01-31

Based on v1.1.34.

### Added
- Climbs: add an interactive "Allure vs Pente" chart (binned mean pace + std error bars) with a dashed pro reference curve.

### Changed
- Metric grids: standardize MetricTile layouts to 6 columns on desktop (responsive 2/3/4).
- Charts: tooltip shows metric value first, then distance/time; axis selector selection matches the applied axis and is persisted.
- Charts: pace Y axis is inverted (faster = higher); heart rate uses a red curve with a transparent trend line and tighter Y domain.
- Charts: remove the "Moving" graph from the Charts section.
- Tables: Splits, Segment analysis, Personal records, and Efforts are collapsible (hidden by default, like Pauses).
- Page order: "Qualite / limites" is always rendered at the very bottom.
- UI only: hide "Series index".
- Map: toggles (pace-colored trace + pause points) now affect rendering and persist across navigation.

### Notes
- Pro curve source: `backend/core/resources/pro_pace_vs_grade.csv` mirrored to `frontend/src/lib/proPaceVsGrade.ts` for UI rendering.

## [1.1.33] - 2026-01-31

### Added
- **UI Grid Layout**: Optional 6-column grid layout for better metric organization
- **Cardio Drift Metrics**: Cardiac drift percentage and slope metrics moved to cardio section
- **Summary Reorganization**: Improved ordering of key metrics in summary section
- **Zones Redesign**: Tab-based zones display with Z6..Z1 ordering and visual bars
- **Power Duration Curve**: Interactive power duration curve chart moved below zones section
- **Collapsible Pauses**: Pauses table now collapsible for better space management
- **Climbs Enhancement**: Added pace column to climbs analysis
- **Charts Improvements**: 
  - Stacked chart layout for better readability
  - Improved chart ordering (pace, heart rate, elevation, grade, speed, power, cadence, moving)
  - Distance-based X-axis with kilometer formatting
  - Enhanced tooltips showing both X and Y axis values
- **Map Enhancements**:
  - Toggle for pace-colored trace display
  - Toggle for pause point visualization
  - Better legend and control placement

### Changed
- **Power Zones**: Moved power zones to hidden section (legacy compatibility)
- **Chart Grid**: Changed from 2-column to stacked single-column layout for mobile optimization
- **Pacing Section**: Removed pacing drift metrics (moved to cardio section)
- **Map Integration**: Enhanced map with activity ID for better data fetching

## [1.1.32] - 2026-01-31

### Fixed
- Windows launcher: avoid port-8000 zombie conflicts and disable uvicorn reload by default (set COURSESCOPE_RELOAD=1 to enable).
- Docs: add PowerShell-safe manual start commands.

## [1.1.31] - 2026-01-31

### Fixed
- Windows launcher: do not block frontend start if backend health check is slow; wait up to 60s then start with warning.

## [1.1.30] - 2026-01-31

### Fixed
- Windows startup: run_win.bat waits for backend /health before starting the frontend (prevents proxy ECONNREFUSED).
- Frontend logs: failed API responses are logged at warn-level to avoid dev overlay noise.

## [1.1.29] - 2026-01-31

### Fixed
- Upload networking (dev): frontend now ignores `NEXT_PUBLIC_API_URL` outside production and always uses the Next.js `/api/*` proxy to avoid CORS/host issues.

### Changed
- Docs: README changelog section now links to this file (no duplicated version blocks).

## [1.1.28] - 2026-01-31

### Fixed
- Upload networking: Next.js rewrite now proxies `/api/*` to `http://127.0.0.1:8000/*` (avoids Windows localhost edge cases).

### Changed
- Windows launcher: run_win.bat no longer forces direct backend URL for the frontend; dev defaults to proxy.

## [1.1.27] - 2026-01-31

### Fixed
- Windows launcher: skip reinstalling frontend deps when `frontend/node_modules/` exists (faster subsequent starts).

## [1.1.26] - 2026-01-31

### Fixed
- Windows launcher: start API + frontend in dedicated windows and keep the launcher open for diagnostics.

## [1.1.25] - 2026-01-31

### Fixed
- Windows launcher: simplified execution flow and added `--smoke` prereq check.

## [1.1.24] - 2026-01-31

### Changed
- CI: GitHub Actions workflow hardened and aligned with real repo commands.

## [1.1.23] - 2026-01-31

### Changed
- Docs: consolidated to a single source of truth; added root changelog and roadmap.
- Backend: series registry now reuses core computations for grade/moving.

### Fixed
- Series endpoint robustness: avoid NaN filtering crashes for non-numeric series.

## [1.1.22] - 2026-01-31

### Changed
- Legacy UI removed; FastAPI + Next.js is now the only supported runtime.

## [1.1.21] - 2026-01-31

### Fixed
- Upload + API routing hardened; `/api/*` compatibility preserved.
