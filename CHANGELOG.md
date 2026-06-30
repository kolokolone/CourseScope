# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [1.1.93] - 2026-06-30

### Changed
- **Refactor** : extraction des fonctions dupliquées frontend (`lib/dateUtils.ts`, `lib/chartUtils.ts`, `lib/paceUtils.ts`) — 12 doublons éliminés dans 10 fichiers consommateurs
- **Suppression** : composants inutilisés `HeroKpi.tsx`, `MetricTile.tsx` (activity-beta), `SidebarStats.tsx`, `store/activityStore.ts`
- **Correction** : `isValidNumber` dans `insights.ts` importe désormais depuis `formatters.ts`

## [1.1.92] - 2026-06-30

### Changed
- **Refactor** : extraction des fonctions dupliquées backend (`core/_shared.py`, `progress/_utils.py`, `api/_helpers.py`) — 16 doublons éliminés
- **Refactor** : unification du pattern `temp_storage` fallback → `resolve_activity_df()` dans 10+ endpoints
- **Suppression** : `api/compat.py`, `services/history_service.py`, `MemoryCache`/`DiskCache` (code mort), `pace_to_mmss` (grade_table.py)
- **Suppression** : endpoints `/health`, `/progress/verify`, `/progress/verify-status`
- **Suppression** : `progress/verify_index.py`, `progress/verify_runner.py`

## [1.1.91] - 2026-06-30

### Added
- **Persistance analytique** : nouvelles tables `progress_activity_zones`, `progress_activity_splits`, `progress_activity_climbs` — les zones, splits et montées ne sont plus recalculés à chaque consultation
- **Best efforts** : support des efforts FC (`hr_bpm`) et puissance (`power_w`) dans `progress_best_effort_points`
- **Agrégats journaliers** : table `progress_daily_aggregates` pour accélérer `/progress/series` et `/progress/training-load`
- **Cache** : `InMemoryCache` TTL 60s pour `GET /activity/{id}/real`
- **Nouvelles métriques** : pacing, puissance avancée (NP/IF/TSS), cadence, dénivelé négatif dans `progress_activity_index`
- **Extraction FIT** : `extract_fit_laps()` pour parser les messages `lap` Garmin
- **Documentation** : ~30 endpoints ajoutés dans `metrics_catalog.md` ; `base-sqlite.md` mis à jour avec le nouveau schéma

### Changed
- `METRICS_VERSION` : 6 → 7 (force indexation lente complète au prochain passage)
- **Suppression** : colonne `cardiac_drift_pct` (redondante avec `decoupling_pct`)

### Fixed
- **Index** : ajout d'index sur `activity_sources.activity_id`, `progress_activity_index.activity_type`, `progress_activity_tags.source`

## [1.1.90] - 2026-06-30

### Changed
- **Documentation** : fusion de `metrics_list.txt` dans `metrics_catalog.md` (catalogue unique enrichi avec compatibilité GPX/FIT)
- **Documentation** : suppression des fichiers obsolètes (`ROADMAP.md`, `cahier_des_charges.txt`, `implementations-a-faire.txt`)
- **Documentation** : déplacement de `docs/modifications.txt` → `agents/modifications.txt` (33+ références mises à jour)
- **Documentation** : adaptation de `agent-workflow.md` à l'architecture agentique réelle de CourseScope
- **Documentation** : mise à jour du README.md (structure complète, endpoints, métriques, architecture)
- **Documentation** : harmonisation de tous les fichiers `/docs` (titres, en-têtes standardisés, rôles clarifiés)
- **Documentation** : création de `docs/documentation-style-guide.md` (guide de rédaction)
- **Documentation** : création de `docs/audit_application.md` (rapport d'audit complet)

### Removed
- `.sisyphus/` (artefacts de planification obsolètes)
- `docs/ROADMAP.md`, `docs/implementations-a-faire.txt`, `docs/cahier_des_charges.txt`

## [1.1.88] - 2026-06-25

### Fixed
- **AllureVsPenteChart** : bande de variabilité utilise désormais `pace_std_w_s_per_km` (écart-type pondéré) au lieu de `pace_std_s_per_km` (non pondéré) — correction M-1 de l'audit.
- Renommage `paceMean` → `paceMedian` dans `BinPoint` pour refléter la sémantique réelle (médiane, pas moyenne).
- Description du graphique corrigée : « La barre verticale » → « La zone grise ».
- Tooltip enrichi avec le nombre d'échantillons par bin.
- Types TypeScript `PaceVsGradeBin` complétés (`pace_std_w_s_per_km`, `time_s_bin`).

## [1.1.87] - 2026-06-22

### Added
- Nouvelle page bêta `/activities-beta/[id]` avec hero éditable, sub-nav sticky par ancres françaises, insights interprétatifs, carte sans footer technique, splits, zones, relief et accordéons repliables. Frontend-only, zéro modification backend.

### Fixed
- `params.id` Promise error Next.js 16 → passage à `useParams()` hook.
- Superposition chart/contrôles dans `MainAnalysisCard` → retrait du `h-[420px]` fixe et des doublons de contrôles.
- Sub-nav masquée par la carte Leaflet → z-index passé à `z-[1001]`.
- Scroll saccadé → `IntersectionObserver` déplacé dans `ActivityBetaSubNav` pour isoler les re-rendus.
- Colonnes D+/D- et KM vides dans `SplitsCard` → champs corrigés (`elev_delta_m`, `split_index`).
- Barres d'allure compressées dans `SplitsCard` → normalisation entre 10 %–90 % de la largeur.

## [1.1.86] - 2026-02-23

### Changed
- Progress indexation API: propagate `reason` payload on `POST /progress/index/fast` instead of forcing `api_fast`.
- Garmin sync: trigger fast indexation automatically after `/integrations/garmin/sync` (best-effort, non-blocking).
- Indexation runner observability: emit explicit `finalize` phase before run completion.

### Added
- Tests: `slow` endpoint returns `202` when run already active, fast reason payload propagation, and fast trigger idempotence while running.
- Frontend test for `/settings` full indexation click flow (`indexFast` + forced `indexSlow backfill_full`).
- Operational migration/deployment runbook: `docs/indexation_operational_runbook.md`.

## [1.1.85] - 2026-02-23

### Changed
- Progress indexation: stabilize CLI tooling with `scripts/index_progress.py` and keep `scripts/reindex_progress.py` as a compatibility alias.

## [1.1.83] - 2026-02-23

### Changed
- Progression (`/progress`): switch to the new fast/slow indexation status flow (auto-trigger fast indexation on page load and poll unified status).
- Settings (`/settings`): replace legacy progression verify button with explicit `Indexation rapide` and `Indexation complete` actions + progress/status display.

## [1.1.81] - 2026-02-22

### Changed
- Activity details (`/activities/[id]`): detail metric tiles now expose explanatory hover notes and removed the requested helper subtitles/text blocks from the details card.
- Progression (`/progress`): removed `Taxonomie des seances` and `Comparaisons like-for-like` cards, and added a VO2max line chart (3 last months only, y-axis 0 to max + 15%, same curve color as weekly volume).
- VO2max indexing: added `vo2max` storage in `progress_activity_index`, `vo2max_lastest` in `user_settings`, and indexer updates so FIT-derived VO2max is persisted and refreshed during progression indexing.
- Home (`/`): history card is now alone on its own row, removed action buttons from that card, aligned upload card title sizing with history title, moved `Prochain objectif` below history, and added `VO2 max actuelle` circular gauge card with hover-only category note.

## [1.1.80] - 2026-02-22

### Changed
- Goals (`/goals`): removed the `Globe 3D des objectifs` card entirely and keep a single map-based objective visualization.
- Goals frontend cleanup: deleted `GoalsGlobe3D` component and removed all active references/imports tied to the globe feature.

## [1.1.79] - 2026-02-22

### Changed
- Goals (`/goals`): added a new `Map des objectifs` card above the 3D globe, using OpenStreetMap with marker display for all tracked goals.
- Goals map interactions: marker hover now shows the same goal mini-card overlay style as the globe, and map auto-zoom focuses on the 3 next upcoming goals.

## [1.1.78] - 2026-02-22

### Changed
- Activity details (`/activities/[id]`): power duration curve is no longer capped to the fixed 1h window set; backend now expands duration windows up to the actual available activity duration.
- Activity charts (`/activities/[id]`): unsupported zone series (`hr_zones`, `power_zones`) are no longer requested by the frontend chart panel, preventing repeated `400 Bad Request` logs.
- Power duration chart (`/activities/[id]` details): frontend trims the displayed curve at the first point where computed power reaches `0W`.

## [1.1.77] - 2026-02-22

### Changed
- Activity map tab (`/activities/[id]`): removed the separate pauses card and promoted the map card to full width with the same large height as trace map view.
- Activity details tab (`/activities/[id]`): replaced the multi-card metrics layout with a single full-width card (`Metriques de l activite`) structured into sections A->G (Essentiel, Allure/Vitesse, Denivele/Terrain, Cardio, Cadence/Dynamique, Puissance, Charge), while keeping the three bottom analysis cards below.
- Pace/grade filters (`/activities/[id]`, `/traces/[id]`): minimum `time_s` threshold for pace and grade bins increased from 60s to 90s.

## [1.1.76] - 2026-02-22

### Changed
- Goals (`/goals`): replaced synthetic globe texture with a real Earth map texture + bump map, keeping objective markers on top; timeline mini-cards now use content-based width and reduced spacing between goals.
- Activities (`/activities/[id]`): secondary KPIs are always visible in Apercu (no hide toggle), KPI hover help is now also available on essential KPI tiles, and chart smoothing includes 20 with auto-reset to 15 when opening the page.
- Splits UI (`/activities/[id]`): split card now uses full chart height and removes the collapsed split table; split description text is updated for clarity.
- Charts (`/activities/[id]`): grade-time bars now reuse filtered bins (`time_s >= 60`) for consistency with trace behavior, and partial series reload issues no longer trigger a full red error state.
- Details tab (`/activities/[id]`): reorganized into clearer groups and removed cards `Personal records`, `Qualite / limites`, `Efforts`, and `Segment analysis (time best efforts)`.
- Traces (`/traces/[id]`): removed `Points de pauses` toggle from map controls and improved color-by-pace route computation with better pace-to-polyline alignment + smoothing.
- Backend real analysis response: stopped returning payloads for removed activity-detail cards (`best_efforts`, `personal_records`, `segment_analysis`, `limits`) to reduce unnecessary response work.

## [1.1.75] - 2026-02-22

### Changed
- Goals (`/goals`): timeline arrows are now dynamic (distance varies by gap between objective dates), J-X badges align with countdown values from today, mini-cards are auto-sized/centered, the objective form appears above the objectives list while editing/creating, and the objectives list is placed directly under the timeline.
- Goals globe (`/goals`): globe now uses a visible world-map texture layer, blue markers are slightly smaller and keep a stable apparent size while zooming, rotation is disabled, focus remains on the next three objectives, canvas uses full card width, and star background depth effect is enhanced.
- Activity detail (`/activities/[id]`): removed duplicate race date chip in top KPI row, moved secondary KPI tiles into the main "Apercu" card (same representation), expanded KPI help texts, and improved "Distributions" card text consistency + chart height behavior.
- Pace bins (`/traces/[id]` and `/activities/[id]`): pace-time histogram cap changed from 200% to 175% of reference pace, bins under 60s are filtered out, and x-axis ticks are synchronized to 30s cadence.

## [1.1.74] - 2026-02-22

### Changed
- Goals: replaced timeline with a horizontal card flow (today card + arrows + J-X labels), compacted calendar rows/cells, and added city autocomplete (`Ville, Pays`) backed by a new backend geocoding proxy.
- Activities: header now shows inline activity ID and race date, merged Splits + Temps intermédiaires into one tab, cleaned Distributions card, moved predictions/power/training-load cards into Détails, and added new Charts cards (`Allure vs distance`, `Temps par allure`, `Temps par % de pente`) computed from backend real-activity bins.
- Traces: pace/elevation smoothing moved to 20 points, pace-time bins are capped at 200% of target pace, and grade-time bins now filter segments under 60s with centered numeric slope axis.
- Settings/Goals backend: added `DELETE /goals` cleanup endpoint and maintenance action `Nettoyer objectifs`; maintenance actions are now fully in French and maintenance card is placed below Garmin.

## [1.1.67] - 2026-02-19

### Changed
- Settings: added a "Mentions personnelles" card under Garmin with author note, GitHub link, and a placeholder for a future "buy me a coffee" link.
- Docker: install Python dependencies inside a virtual environment during image build (avoids PEP 668 externally-managed pip error on Debian/Ubuntu).
- Docs: refreshed README (quickstart + docker-compose example).

## [1.1.66] - 2026-02-19

### Changed
- Docker deployment: add single-image stack artifacts (`Dockerfile`, `.dockerignore`, GHCR workflow) and launcher support for `run_linux.sh --docker`.
- Theoretical trace UI: target pace input now accepts minute-only values (example `6` -> `6:00`), charts layout updated, and denivele chart added.
- Theoretical analytics: pace bins switched to 15s and grade-time bins are clipped to `[-20%, 20%]`.

## [1.1.65] - 2026-02-18

### Changed
- Settings/Garmin: formatte les timestamps (date+heure lisibles) et affiche un delta sync plus user-friendly.
- Activites: ajoute un tri via l'en-tete du tableau (Date/Km/D+).
- Backend: `/integrations/garmin/status` expose `cursor_updated_at_utc`, `last_run.processed_count` et `last_run.duration_s` (champs optionnels).

## [1.1.64] - 2026-02-14

### Changed
- Progression: Phase 3 adds session taxonomy (easy/tempo/interval/long_run), terrain tags (flat/rolling/hilly), and optional race/test markers (auto + manual override).
- Progression: added Pace-HR Waterfall 3D (WebGL) with like-for-like filters and server-side binned curves for efficient rendering.
- Progression charts: adjusted smoothing and robust axis domains (Best effort now uses P10-P90 +/-10%).
- Docs: updated metrics catalog/list with progression endpoints and computed artifacts.

## [1.1.63] - 2026-02-14

### Changed
- Progression charts: dynamic Y-axis domains (+/-5% padding) for Best effort, EF, Decoupling, HR@pace and Pace@HR to keep each chart focused on relevant ranges.
- Progression charts: added thin black trend lines on EF and Decoupling scatter charts.
- Progression charts: added legends on HR@pace and Pace@HR charts.
- Best effort chart: switched area fill to render below the pace curve (with reversed pace axis) and applied robust Y-domain strategy (P5-P95 + 5% padding) to limit extreme-value distortion.

## [1.1.62] - 2026-02-14

### Changed
- Progression: opening `/progress` now auto-runs verify/reindex for stale indexes (including new pace-HR bins) and refreshes charts automatically when background indexing completes.
- Progression UI: clarified empty-state messaging to reflect automatic background indexing (no manual `scripts/reindex_progress.py` required in normal flow).

## [1.1.54] - 2026-02-09

### Changed
- Backend: added Garmin Connect integration endpoints (`/integrations/garmin/connect`, `/integrations/garmin/sync`, `/integrations/garmin/status`) with incremental sync and dedupe (external activity id + FIT SHA-256).
- Backend: added an internal activity index (SQLAlchemy, PostgreSQL-ready) while keeping the source-of-truth `.fit` + `df.parquet` on disk.

### Fixed
- Backend serialization: `df_to_records` now preserves `None` for missing datetime values (avoids `NaN` in JSON payloads).

## [1.1.55] - 2026-02-09

### Changed
- Frontend: updated home page sections (Upload + last 10 stored activities) with links to Settings and full Activities history.
- Frontend: added Settings page for upload persistence (default OFF) and Garmin connection/status.
- Frontend: added Activities history page with weekly km bar chart + sortable table (date/name/km/D+/duration).

### Changed (Backend)
- Upload: added optional `persist_to_disk` form field (default false). If disabled, activity is stored in-memory only.
- Analysis endpoints: fallback to in-memory activities for analysis/series/map.
- Garmin: added credentials store (`data/integrations/garmin/credentials.json`) + endpoints to save/check credentials.

## [1.1.56] - 2026-02-09

### Changed
- Home: split upload into two explicit flows (Real activity vs Theoretical track); removed automatic type selection.
- Activities: sort newest→oldest by activity date; show activity date (started_at) instead of ingestion date.
- Activities: weekly km chart now supports range selection (3m/6m/1y/all) and adds a rolling average line.
- Activities: added "Sync Garmin" button to fetch new activities.

### Changed (Backend)
- Upload: added optional `activity_type` form field to force `real` vs `theoretical` (bypass auto-detection) and included it in the load cache key.
- Storage metadata: added `started_at` (derived from file timestamps) and list endpoint now returns activities sorted by started_at.

## [1.1.57] - 2026-02-09

### Changed
- Settings/Garmin: OTP entry is now handled in-browser via a two-step connect flow (Connect -> OTP -> Confirm).
- Settings/Garmin: status panel no longer displays token path.
- Garmin sync: only imports Running and Trail Running activities.
- Garmin sync: sync work runs in a worker thread so the backend stays responsive.
- Settings: moved "Cleanup activites" from Home to Settings.

## [1.1.58] - 2026-02-09

### Changed
- Settings/Garmin: removed duplicate action buttons and kept a single connect flow (plus OTP confirm when needed) and a single Sync button.

## [1.1.59] - 2026-02-09

### Changed
- Garmin: added `POST /integrations/garmin/reset` to reset cursor + mappings for a full resync.
- Settings: added "Sync complet" (reset + sync) to re-download Garmin activities after cleanup.
- Cleanup: `DELETE /activities` now also clears the DB activity index and Garmin cursor so a re-sync can restore activities.

## [1.1.60] - 2026-02-09

### Fixed
- UI: removed redundant Home shortcuts panel and duplicate "Afficher toutes" button; uploads now display side-by-side.
- UI: fixed TheoreticalActivityPage hooks order error (no conditional hooks).

## [1.1.61] - 2026-02-09

### Changed
- Activities chart: switched weekly km bars to an area line with custom dots and current-week highlight; removed average line.

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

## [1.1.50] - 2026-02-02

### Fixed
- Charts (hover sync): series endpoint preserves full x sampling and returns null for invalid y, so all charts can share the same x base and keep the synced cursor stable.

### Changed
- Charts: connect across missing y values (`connectNulls`) to keep lines continuous; tooltip shows `—` when a value is missing.

## [1.1.51] - 2026-02-03

### Changed
- Charts: default X axis is now Distance (persisted prefs migrated); compacted axis/smoothing controls into a single row.
- Charts (heart rate): added an extra, slower trend line (more smoothed) in grey.

## [1.1.52] - 2026-02-03

### Changed
- Real activity page: new sticky header + tabbed navigation (Aperçu/Splits/Temps/Climbs/Charts/Map/Détails) to reduce scroll.
- Real activity page: compact density mode for sections and internal scroll for long tables; lazy-mount heavy tabs.

## [1.1.53] - 2026-02-03

### Changed
- Home: dashboard layout with sticky header + tabs (Upload/Activites) and scrollable activity list.
- Theoretical activity page: aligned UI with Real (sticky header + tabs, compact sections).

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
