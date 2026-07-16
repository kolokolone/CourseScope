# Metrics Catalog

Compiled from API schemas and backend metric builders (`backend/api/schemas.py`, `backend/core/real_run_analysis.py`, `backend/core/metrics.py`).

## Data Source Compatibility

| Label | Meaning |
|---|---|
| `[Both]` | Available from both GPX and FIT files |
| `[FIT]` | Requires FIT file with heart rate / power / running dynamics fields present |
| `[Cond cadence]` | Conditional on cadence data being present in the file |
| `[Cond …]` | Conditional on the specified sensor data being present |

## Activity Load (POST /activity/load)

### Request fields

Requête multipart persistée dans le domaine des activités réelles.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `file` | GPX/FIT | requis | fichier d'une activité réellement enregistrée |
| `name` | string | nom du fichier | nom affiché |
| `activity_type` | `real` | `real` | seule valeur acceptée ; une trace théorique utilise `POST /traces/upload` |

### Sidebar stats

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `stats_sidebar.distance_km` | float | km | distance km |
| `stats_sidebar.elapsed_time_s` | float | s | elapsed time s |
| `stats_sidebar.moving_time_s` | float | s | moving time s |
| `stats_sidebar.elevation_gain_m` | float | m | elevation gain m |

## Activities List (GET /activities)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `activities[].started_at` | datetime | - | activity start datetime (derived from file timestamps) |
| `activities[].created_at` | datetime | - | ingestion datetime (storage time) |

### Limits

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `limits.downsampled` | bool | - | downsampled |
| `limits.dataframe_limit` | int | - | dataframe limit |
| `limits.note` | string | - | note |

## Real Activity Metrics (GET /activity/{id}/real)

### Infos de course

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `summary.distance_km` | float | km | distance km |
| `summary.total_time_s` | float | s | total time s |
| `summary.moving_time_s` | float | s | moving time s |
| `summary.average_pace_s_per_km` | float | s/km | average pace s per km |
| `summary.average_speed_kmh` | float | km/h | average speed kmh |
| `summary.elevation_gain_m` | float | m | elevation gain m |

### Cardio

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `summary.cardio.hr_avg_bpm` | float | bpm | average heart rate (time-weighted, moving points) |
| `summary.cardio.hr_max_bpm` | float | bpm | max heart rate (moving points) |
| `summary.cardio.hr_min_bpm` | float | bpm | min heart rate (moving points) |

### Summary

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `garmin_summary.total_time_s` | float | s | total time s |
| `garmin_summary.moving_time_s` | float | s | moving time s |
| `garmin_summary.pause_time_s` | float | s | pause time s |
| `garmin_summary.distance_km` | float | km | distance km |
| `garmin_summary.moving_distance_km` | float | km | moving distance km |
| `garmin_summary.average_pace_s_per_km` | float | s/km | average pace s per km |
| `garmin_summary.average_speed_kmh` | float | km/h | average speed kmh |
| `garmin_summary.max_speed_kmh` | float | km/h | max speed kmh |
| `garmin_summary.best_pace_s_per_km` | float | s/km | best pace s per km |
| `garmin_summary.gap_mean_s_per_km` | float | s/km | gap mean s per km |
| `garmin_summary.pace_median` | float | - | pace median |
| `garmin_summary.pace_p10` | float | - | pace p10 |
| `garmin_summary.pace_p90` | float | - | pace p90 |
| `garmin_summary.pace_median_s_per_km` | float | s/km | pace median s per km |
| `garmin_summary.pace_p10_s_per_km` | float | s/km | pace p10 s per km |
| `garmin_summary.pace_p90_s_per_km` | float | s/km | pace p90 s per km |
| `garmin_summary.elevation_gain_m` | float | m | elevation gain m |
| `garmin_summary.elevation_loss_m` | float | m | elevation loss m |
| `garmin_summary.elevation_gain_filtered_m` | float | m | elevation gain filtered m |
| `garmin_summary.elevation_loss_filtered_m` | float | m | elevation loss filtered m |
| `garmin_summary.elevation_min_m` | float | m | elevation min m |
| `garmin_summary.elevation_max_m` | float | m | elevation max m |
| `garmin_summary.grade_mean_pct` | float | % | grade mean pct |
| `garmin_summary.grade_min_pct` | float | % | grade min pct |
| `garmin_summary.grade_max_pct` | float | % | grade max pct |
| `garmin_summary.vam_m_h` | float | m/h | vam m h |
| `garmin_summary.steps_total` | float | - | steps total |
| `garmin_summary.step_length_est_m` | float | m | step length est m |
| `garmin_summary.longest_pause_s` | float | s | longest pause s |

### Highlights

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `highlights.items[]` | array | - | items |

### Zones

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `zones.heart_rate.type` | string | - | dataframe type |
| `zones.heart_rate.shape[]` | array | - | dataframe shape |
| `zones.heart_rate.columns[]` | array | - | dataframe columns |
| `zones.heart_rate.records[]` | array<object> | - | records |
| `zones.heart_rate.records[].zone` | unknown | - | zone |
| `zones.heart_rate.records[].range` | unknown | - | range |
| `zones.heart_rate.records[].time_s` | unknown | s | time s |
| `zones.heart_rate.records[].time_pct` | unknown | % | time pct |
| `zones.pace.type` | string | - | dataframe type |
| `zones.pace.shape[]` | array | - | dataframe shape |
| `zones.pace.columns[]` | array | - | dataframe columns |
| `zones.pace.records[]` | array<object> | - | records |
| `zones.pace.records[].zone` | unknown | - | zone |
| `zones.pace.records[].range` | unknown | - | range |
| `zones.pace.records[].time_s` | unknown | s | time s |
| `zones.pace.records[].time_pct` | unknown | % | time pct |
| `zones.power.type` | string | - | dataframe type |
| `zones.power.shape[]` | array | - | dataframe shape |
| `zones.power.columns[]` | array | - | dataframe columns |
| `zones.power.records[]` | array<object> | - | records |
| `zones.power.records[].zone` | unknown | - | zone |
| `zones.power.records[].range` | unknown | - | range |
| `zones.power.records[].time_s` | unknown | s | time s |
| `zones.power.records[].time_pct` | unknown | % | time pct |

### Best efforts

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `best_efforts.rows[]` | array<object> | - | rows |
| `best_efforts.rows[].distance_km` | unknown | km | distance km |
| `best_efforts.rows[].time_s` | unknown | s | time s |
| `best_efforts.rows[].pace_s_per_km` | unknown | s/km | pace s per km |

### Personal records

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `personal_records.rows[]` | array<object> | - | rows |
| `personal_records.rows[].distance_km` | unknown | km | distance km |
| `personal_records.rows[].time_s` | unknown | s | time s |
| `personal_records.rows[].pace_s_per_km` | unknown | s/km | pace s per km |

### Segment analysis (time best efforts)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `segment_analysis.rows[]` | array<object> | - | rows |
| `segment_analysis.rows[].duration_s` | unknown | s | duration s |
| `segment_analysis.rows[].distance_km` | unknown | km | distance km |
| `segment_analysis.rows[].time_s` | unknown | s | time s |
| `segment_analysis.rows[].pace_s_per_km` | unknown | s/km | pace s per km |

### Performance predictions

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `performance_predictions.items[]` | array<object> | - | predictions |
| `performance_predictions.items[].target_distance_km` | unknown | km | target distance km |
| `performance_predictions.items[].predicted_time_s` | unknown | s | predicted time s |
| `performance_predictions.items[].base_distance_km` | unknown | km | base distance km |
| `performance_predictions.items[].base_time_s` | unknown | s | base time s |
| `performance_predictions.items[].exponent` | unknown | - | Riegel exponent |

### Pauses

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `pauses.items[]` | array<object> | - | items |
| `pauses.items[].lat` | unknown | - | lat |
| `pauses.items[].lon` | unknown | - | lon |
| `pauses.items[].label` | unknown | - | label |

### Map data (GET /activity/{id}/map)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `bbox` | [number,number,number,number] | deg | Bounding box [south,west,north,east] |
| `polyline` | array<[number,number]> | deg | GPX polyline points |
| `markers[].lat` | float | deg | Marker latitude |
| `markers[].lon` | float | deg | Marker longitude |
| `markers[].label` | string | - | Marker label |
| `markers[].type` | string | - | Marker type |

### Climbs

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `climbs.items[]` | array<object> | - | items |
| `climbs.items[].distance_km` | unknown | km | climb distance km |
| `climbs.items[].elevation_gain_m` | unknown | m | climb elevation gain m |
| `climbs.items[].avg_grade_percent` | unknown | % | average grade percent |
| `climbs.items[].pace_s_per_km` | unknown | s/km | median pace on climb |
| `climbs.items[].vam_m_h` | unknown | m/h | vertical ascent rate |
| `climbs.items[].start_idx` | unknown | - | start index |
| `climbs.items[].end_idx` | unknown | - | end index |
| `climbs.items[].distance_m_end` | unknown | m | end distance (meters) |
| `climbs.items[].start_km` | unknown | km | start distance (km) |
| `climbs.items[].end_km` | unknown | km | end distance (km) |
| `climbs.items[].start_end_km` | string | km | formatted range ("xx.xx -> yy.yy") |
| `climbs.items[].duration_s` | unknown | s | moving time spent on segment |

## Pace vs grade (GET /activity/{id}/pace-vs-grade)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `bins[]` | array<object> | - | binned pace-vs-grade points |
| `bins[].grade_center` | float | % | bin center (median grade) |
| `bins[].pace_med_s_per_km` | float | s/km | weighted median pace |
| `bins[].pace_std_s_per_km` | float | s/km | unweighted std (after winsorization) |
| `bins[].pace_n` | int | - | number of samples in bin |
| `bins[].pro_pace_s_per_km` | float | s/km | pro reference pace at grade |
| `bins[].time_s_bin` | float | s | total moving time in bin |
| `bins[].pace_mean_w_s_per_km` | float | s/km | time-weighted mean pace |
| `bins[].pace_q25_w_s_per_km` | float | s/km | time-weighted P25 |
| `bins[].pace_q50_w_s_per_km` | float | s/km | time-weighted P50 |
| `bins[].pace_q75_w_s_per_km` | float | s/km | time-weighted P75 |
| `bins[].pace_iqr_w_s_per_km` | float | s/km | time-weighted IQR |
| `bins[].pace_std_w_s_per_km` | float | s/km | time-weighted std |
| `bins[].pace_n_eff` | float | - | effective sample size (weights) |
| `bins[].outlier_clip_frac` | float | - | fraction of time clipped by winsorization |
| `pro_ref[]` | array<object> | - | pro reference curve points |
| `pro_ref[].grade_percent` | float | % | grade percent |
| `pro_ref[].pace_s_per_km_pro` | float | s/km | pro pace |

### Splits

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `splits.rows[]` | array<object> | - | rows |
| `splits.rows[].split_index` | unknown | - | split index |
| `splits.rows[].distance_km` | unknown | km | distance km |
| `splits.rows[].time_s` | unknown | s | time s |
| `splits.rows[].pace_s_per_km` | unknown | s/km | pace s per km |
| `splits.rows[].elevation_gain_m` | unknown | m | elevation gain m |

### Pacing

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `pacing.pace_first_half_s_per_km` | float | s/km | pace first half s per km |
| `pacing.pace_second_half_s_per_km` | float | s/km | pace second half s per km |
| `pacing.pace_delta_s_per_km` | float | s/km | pace delta s per km |
| `pacing.drift_s_per_km_per_km` | float | s/km/km | drift s per km per km |
| `pacing.cardiac_drift_pct` | float | % | cardiac drift pct |
| `pacing.cardiac_drift_slope_pct` | float | % | cardiac drift slope pct |
| `pacing.stability_cv` | float | - | stability cv |
| `pacing.stability_iqr_ratio` | float | - | stability iqr ratio |
| `pacing.gap_residual_median_s` | float | s | gap residual median s |
| `pacing.pace_threshold_s_per_km` | float | s/km | pace threshold s per km |

### Cadence

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `cadence.mean_spm` | float | spm | mean spm |
| `cadence.max_spm` | float | spm | max spm |
| `cadence.target_spm` | float | spm | target spm |
| `cadence.above_target_pct` | float | % | above target pct |

### Power

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `power.mean_w` | float | W | mean w |
| `power.max_w` | float | W | max w |
| `power.ftp_w` | float | W | ftp w |
| `power.ftp_estimated` | bool | - | ftp estimated |
| `power.zones.type` | string | - | dataframe type |
| `power.zones.shape[]` | array | - | dataframe shape |
| `power.zones.columns[]` | array | - | dataframe columns |
| `power.zones.records[]` | array<object> | - | records |
| `power.zones.records[].zone` | unknown | - | zone |
| `power.zones.records[].range` | unknown | - | range |
| `power.zones.records[].time_s` | unknown | s | time s |
| `power.zones.records[].time_pct` | unknown | % | time pct |

### Running dynamics

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `running_dynamics.stride_length_mean_m` | float | m | stride length mean m |
| `running_dynamics.vertical_oscillation_mean_cm` | float | cm | vertical oscillation mean cm |
| `running_dynamics.vertical_ratio_mean_pct` | float | % | vertical ratio mean pct |
| `running_dynamics.ground_contact_time_mean_ms` | float | ms | ground contact time mean ms |
| `running_dynamics.gct_balance_mean_pct` | float | % | gct balance mean pct |

### Power advanced

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `power_advanced.normalized_power_w` | float | W | normalized power w |
| `power_advanced.intensity_factor` | float | - | intensity factor |
| `power_advanced.tss` | float | - | tss |
| `power_advanced.power_duration_curve[]` | array<object> | - | peak power by duration |
| `power_advanced.power_duration_curve[].duration_s` | unknown | s | duration s |
| `power_advanced.power_duration_curve[].power_w` | unknown | W | peak average power w |

### Training load

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `training_load.trimp` | float | - | TRIMP (Edwards) |
| `training_load.method` | string | - | method name |

### Series index

Available series (names used in `GET /activity/{id}/series/{name}`):

| Series name | Source | Description |
| --- | --- | --- |
| `speed` | [Both] | Speed (m/s) |
| `pace` | [Both] | Pace (s/km) |
| `elevation` | [Both] | Elevation (m) |
| `heart_rate` | [FIT] | Heart rate (bpm) |
| `cadence` | [Cond cadence] | Cadence (spm) |
| `power` | [FIT] | Power (watts) |
| `grade` | [Both] | Grade (%) |
| `moving` | [Both] | Moving mask (boolean) |
| `hr_zones` | [FIT] | HR zone at each point |
| `power_zones` | [FIT] | Power zone at each point |

Series metadata:

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `series_index.available[]` | array<object> | - | available series |
| `series_index.available[].name` | string | - | series name |
| `series_index.available[].unit` | string | - | unit |
| `series_index.available[].x_axes[]` | array | - | allowed x axes |
| `series_index.available[].default` | bool | - | default series |

### Limits

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `limits.downsampled` | bool | - | downsampled |
| `limits.original_points` | int | - | original points |
| `limits.returned_points` | int | - | returned points |
| `limits.note` | string | - | note |

## Activité théorique historique

`GET /activity/{activity_id}/theoretical` est déprécié et répond HTTP 410. Une préparation théorique est identifiée exclusivement par `trace_id` et calculée avec `POST /traces/{trace_id}/plan-preview`.

## Progression API (GET /progress/*)

Progression endpoints are backed by the SQLite progression index (computed artifacts). They are designed for dashboard queries and support optional filtering.

### Index verification (POST /progress/verify, GET /progress/verify-status)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `running` | bool | - | background indexing/verification is running |
| `last_started_at_utc` | string\|null | - | ISO UTC timestamp |
| `last_finished_at_utc` | string\|null | - | ISO UTC timestamp |
| `last_error` | string\|null | - | last error message |
| `last_result.scanned` | int | - | activities scanned |
| `last_result.indexed` | int | - | activities reindexed |
| `last_result.up_to_date` | int | - | activities already up-to-date |
| `last_result.errors` | int | - | errors encountered |

### Indexed activities list (GET /progress/activities)

Query params:
- `from`, `to` (date or ISO datetime)
- `type` (`real` pour les nouveaux imports ; `theoretical` uniquement pour d'anciens index)
- `limit` (max rows)
- `session_tag`, `terrain_tag`, `race_marker` (optional filters)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `activities[].activity_id` | string | - | UUID |
| `activities[].start_ts_utc` | string | - | ISO UTC timestamp |
| `activities[].distance_m` | float\|null | m | distance |
| `activities[].moving_time_s` | float\|null | s | moving time |
| `activities[].elapsed_time_s` | float\|null | s | elapsed time |
| `activities[].elevation_gain_m` | float\|null | m | elevation gain |
| `activities[].avg_pace_s_per_km` | float\|null | s/km | average pace |
| `activities[].best_pace_s_per_km` | float\|null | s/km | best pace |
| `activities[].pace_threshold_s_per_km` | float\|null | s/km | threshold proxy |
| `activities[].avg_hr_bpm` | float\|null | bpm | average HR |
| `activities[].max_hr_bpm` | float\|null | bpm | max HR |
| `activities[].trimp` | float\|null | - | TRIMP |
| `activities[].aerobic_efficiency_m_s_per_bpm` | float\|null | m/s/bpm | aerobic efficiency |
| `activities[].decoupling_pct` | float\|null | % | cardiac drift (alias) |
| `activities[].stability_cv` | float\|null | - | pacing stability CV |
| `activities[].stability_iqr_ratio` | float\|null | - | pacing stability IQR ratio |
| `activities[].has_hr` | bool | - | HR sensor present |
| `activities[].has_power` | bool | - | power sensor present |
| `activities[].has_cadence` | bool | - | cadence present |
| `activities[].data_points` | int\|null | - | stored points count |
| `activities[].session_tag` | string\|null | - | session taxonomy tag |
| `activities[].terrain_tag` | string\|null | - | terrain taxonomy tag |
| `activities[].race_marker` | bool | - | race/test day marker |
| `activities[].tag_source` | string\|null | - | `auto` or `manual` |

### Series aggregation (GET /progress/series)

Returns: `[ { bucket_start: 'YYYY-MM-DD', value: number } ]`.

### Best efforts timeline (GET /progress/best-efforts)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `points[].start_ts_utc` | string | - | ISO UTC timestamp |
| `points[].value` | float | s/km | best-effort pace |
| `points[].is_pr` | bool | - | running PR flag |

### HR at fixed pace / Pace at fixed HR (GET /progress/hr-at-pace, GET /progress/pace-at-hr)

Optional like-for-like filters: `session_tag`, `terrain_tag`, `endurance_only`.

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `series[].pace_s_per_km` | float | s/km | reference pace |
| `series[].hr_bpm` | float | bpm | reference HR |
| `series[].points[].value` | float | bpm or s/km | interpolated value |

### Session taxonomy (GET /progress/session-taxonomy)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `session_counts[].tag` | string | - | session tag |
| `session_counts[].count` | int | - | count |
| `terrain_counts[].tag` | string | - | terrain tag |
| `terrain_counts[].count` | int | - | count |
| `race_markers` | int | - | activities marked as race |
| `total_tagged` | int | - | total activities with a tag row |

### Manual tag upsert (POST /progress/tags)

Request: `{ activity_id, session_tag?, terrain_tag?, race_marker? }`.
Response: `{ ok, activity_id }`.

### Pace-HR Waterfall (GET /progress/pace-hr-waterfall)

Returns definitive Pace↔HR bins per activity for 3D rendering. The requested resolution must be one of the native indexes `5`, `10`, `20` or `30 s/km`; the endpoint never re-aggregates stored bins. The simplified preprocessing computes pace over a continuous 30-second window, applies Hampel and median HR filters, and removes the first 10 minutes with positive distance. It does not use the shared moving mask, gap segmentation, HR slew rejection or pace-transition exclusion. Full algorithm: [pace_hr_waterfall.md](pace_hr_waterfall.md).

Query parameters specific to this endpoint: `bin_step_s_per_km=5|10|20|30` (default `10`) and `limit=1..120` (default `60`). Session, terrain and endurance filters are not part of the Waterfall contract.

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `activities[].start_ts_utc` | string | - | ISO UTC timestamp |
| `activities[].points[].pace_bin_s_per_km` | float | s/km | pace bin |
| `activities[].points[].hr_bpm` | float | bpm | aggregated HR |
| `activities[].points[].time_s_bin` | float | s | time weight |

## Activities CRUD (DELETE /activity/{id}, DELETE /activities, PATCH /activities/{id})

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `id` | string | - | UUID de l'activité |
| `name` | string\|null | - | nom mis à jour (PATCH) |
| `message` | string | - | message de confirmation (DELETE) |

## Traces et préparation de course

Contrat détaillé, pipeline et exemples : [race-planning.md](race-planning.md).

### Liste (GET /traces)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `traces[]` | array<object> | - | liste des traces sauvegardées |
| `traces[].id` | string | - | UUID de la trace |
| `traces[].name` | string\|null | - | nom de la trace |
| `traces[].created_at_utc` | string | - | ISO UTC timestamp |
| `traces[].distance_km` | float | km | distance |
| `traces[].elevation_gain_m` | float | m | dénivelé positif |
| `traces[].elevation_loss_m` | float\|null | m | dénivelé négatif |
| `traces[].elevation_min_m` | float\|null | m | altitude min |
| `traces[].elevation_max_m` | float\|null | m | altitude max |
| `traces[].original_filename` | string\|null | - | nom du fichier original |
| `sync.scanned` | int | - | traces parcourues |
| `sync.indexed` | int | - | traces indexées |
| `sync.up_to_date` | int | - | traces déjà à jour |
| `sync.deleted` | int | - | traces supprimées |
| `sync.errors` | int | - | erreurs |

### Upload (POST /traces/upload)

Requête multipart: `file` (GPX/FIT), `name` (optionnel).

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `trace` | object | - | TraceItem (memes champs que ci-dessus) |
La réponse contient `trace`, sans `activity_id`. L'import crée aussi un plan et un scénario par défaut.

### Rename (PATCH /traces/{id})

Requête: `{ "name": "nouveau nom" }`. Retourne un `TraceItem`.

### Delete single (DELETE /traces/{id})

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `deleted` | bool | - | true si supprime |

### Cleanup all (DELETE /traces)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `deleted` | int | - | nombre de traces supprimees |

### Détail (GET /traces/{trace_id})

| Path | Type | Unit | Description |
|---|---|---|---|
| `trace.id` | string | - | `trace_id`, jamais un identifiant d'activité |
| `file.parquet_source` | `parquet`\|`rebuilt` | - | source effectivement chargée |
| `file.parquet_rebuild_reason` | string\|null | - | raison d'une reconstruction |
| `file.dataframe_schema_version` | string | - | version du DataFrame canonique |
| `file.parquet_generated_at_utc` | string\|null | - | date ISO de génération |
| `static_metrics.distance_km` | float | km | distance du profil normalisé |
| `quality` | object | - | densité, interpolation, trous et avertissements |
| `active_plan` | object\|null | - | référence du plan actif |
| `plans[]` | array<object> | - | plans et scénarios minimaux |

### Fichier original (GET /traces/{trace_id}/download)

Renvoie le GPX/FIT source exact avec `Content-Disposition: attachment` et le nom original assaini. Réponse `404` si la trace ou le fichier manque. Aucun chemin local n'est exposé. La route compatible `/api/traces/{trace_id}/download` a le même comportement.

### Prévisualisation (POST /traces/{trace_id}/plan-preview)

Le corps accepte soit `plan_id`/`scenario_id`, soit un plan et un scénario structurés. `target_value` est exprimé en `s/km` pour `pace`, en secondes pour `time`, et en ratio pour `effort`.

| Path | Type | Unit | Description |
|---|---|---|---|
| `units` | object | - | unités explicites de la réponse |
| `totals.running_time_s` | float | s | temps de course |
| `totals.stop_time_s` | float | s | somme des pauses |
| `totals.elapsed_time_s` | float | s | course et pauses |
| `totals.arrival_time_iso` | string\|null | - | arrivée dans le fuseau du plan |
| `profile[].distance_km` | float | km | distance d'affichage |
| `profile[].pace_s_per_km` | float | s/km | allure issue du coût Minetti, gain descendant régularisé et lissage métrique backend |
| `profile[].grade_robust_pct` | float | % | pente du calcul métier |
| `passages[]` | array<object> | - | départ, passages kilométriques/personnalisés et arrivée |
| `passages[].kind` | string | - | `start`, `kilometer`, `landmark`, `custom_segment` ou `arrival` |
| `passages[].label` | string | - | libellé utilisateur ou libellé calculé |
| `splits[]` | array<object> | - | vrais splits kilométriques, indépendants des points personnalisés |
| `splits[].cumulative_running_time_s` | float | s | cumul de course à la fin du split |
| `splits[].cumulative_stop_time_s` | float | s | cumul des pauses à la fin du split |
| `splits[].cumulative_elapsed_time_s` | float | s | cumul course et pauses |
| `splits[].passage_time_iso` | string\|null | - | ETA dans le fuseau du plan |
| `splits[].is_partial` | bool | - | dernier split inférieur à 1 km |
| `climbs[]` | array<object> | - | ascensions détectées |
| `histograms.pace` | object | - | classes complètes/affichées et temps masqué |
| `histograms.grade` | object | - | temps/distance par pente et temps masqué |
| `alerts[]` | array<object> | - | diagnostics exploitables |
| `quality` | object | - | qualité du profil source |

### Persistance et comparaison

| Méthode | Route |
|---|---|
| `GET`, `POST` | `/traces/{trace_id}/plans` |
| `GET`, `PATCH`, `DELETE` | `/traces/{trace_id}/plans/{plan_id}` |
| `POST` | `/traces/{trace_id}/plans/{plan_id}/scenarios` |
| `PATCH`, `DELETE` | `/traces/{trace_id}/plans/{plan_id}/scenarios/{scenario_id}` |
| `POST` | `/traces/{trace_id}/plans/{plan_id}/scenarios/{scenario_id}/stops` |
| `PATCH`, `DELETE` | `/traces/{trace_id}/plans/{plan_id}/scenarios/{scenario_id}/stops/{stop_id}` |
| `POST` | `/traces/{trace_id}/plans/{plan_id}/compare` |
| `GET` | `/traces/{trace_id}/calibration` |

Les mutations retournent l'objet modifié et `preview_required: true` lorsqu'un nouveau calcul est nécessaire.

### Routes dépréciées

`POST /traces/{trace_id}/open`, `GET /activity/{activity_id}/trace-status` et `POST /activity/{activity_id}/trace-save` répondent HTTP 410 et ne créent aucune activité temporaire.

## Goals (GET /goals, POST /goals, PATCH /goals/{id}, DELETE /goals/{id}, DELETE /goals)

### Liste (GET /goals)

Avant de construire la réponse, le backend supprime les objectifs tels que `event_date < date_courante` dans le fuseau `Europe/Paris`. Les objectifs du jour et futurs sont conservés. Si un plan de course référence un objectif expiré, son `goal_id` facultatif est détaché avant la suppression.

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `goals[]` | array<object> | - | liste des objectifs |
| `goals[].id` | string | - | UUID |
| `goals[].name` | string | - | nom de la course |
| `goals[].event_date` | string | - | date au format YYYY-MM-DD |
| `goals[].distance_km` | float | km | distance |
| `goals[].location` | string\|null | - | lieu |
| `goals[].location_city` | string\|null | - | ville |
| `goals[].location_country` | string\|null | - | pays |
| `goals[].location_country_code` | string\|null | - | code pays (ISO) |
| `goals[].location_lat` | float\|null | deg | latitude |
| `goals[].location_lon` | float\|null | deg | longitude |
| `goals[].target_time_s` | float\|null | s | temps cible |
| `goals[].target_pace_s_per_km` | float\|null | s/km | allure cible |
| `goals[].race_type` | string | - | `road` ou `trail` |
| `goals[].notes` | string\|null | - | notes |
| `goals[].created_at_utc` | string | - | ISO UTC timestamp |
| `goals[].updated_at_utc` | string | - | ISO UTC timestamp |

### Create (POST /goals)

Requete: `GoalCreateRequest`. Un seul de `target_time_s` / `target_pace_s_per_km` requis.

### Update (PATCH /goals/{id})

Requete: `GoalUpdateRequest` (tous les champs optionnels). Retourne le `GoalItem` mis a jour.

### Delete single / all (DELETE /goals/{id}, DELETE /goals)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `deleted` | bool\|int | - | true ou nombre supprime |

## Personal Settings (GET /settings/personal, PATCH /settings/personal, GET /settings/personal/hr-max-detected)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `vma_kmh` | float\|null | km/h | VMA |
| `vo2max_lastest` | float\|null | - | derniere estimation VO2max detectee |
| `hr_max_manual_bpm` | int\|null | bpm | FC max manuelle |
| `hr_max_source` | string | - | `detected` ou `manual` |
| `hr_max_detected_bpm` | int\|null | bpm | FC max detectee automatiquement |
| `hr_max_effective_bpm` | int\|null | bpm | FC max effective utilisee |
| `updated_at_utc` | string | - | ISO UTC timestamp |

### PATCH /settings/personal

Requete: `{ vma_kmh?, hr_max_manual_bpm?, hr_max_source? }`.

### GET /settings/personal/hr-max-detected

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `hr_max_detected_bpm` | int\|null | bpm | FC max detectee |

## Garmin Integration (POST /integrations/garmin/*, GET /integrations/garmin/*)

### Connect (POST /integrations/garmin/connect)

Requete: `{ email?, password?, otp?, mfa_session_id? }`.

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `status` | string | - | `ok` ou `otp_required` |
| `mfa_session_id` | string\|null | - | session MFA a fournir avec l'OTP |

### Sync (POST /integrations/garmin/sync)

Le backend reprend d'abord les jetons OAuth du répertoire configuré. Si cette reprise échoue et que des identifiants Garmin sont déjà enregistrés, il tente une seule reconnexion automatique, persiste les nouveaux jetons puis reprend la synchronisation. Une reconnexion exigeant un MFA reste un `401 reauth_required` et doit être finalisée depuis les paramètres. Le chemin valide avec jetons fonctionnels, notamment dans Docker, n'est pas modifié.

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `run_id` | string | - | UUID du run de synchro |
| `status` | string | - | `ok` ou `error` |
| `imported_count` | int | - | activites importees |
| `skipped_count` | int | - | activites ignorees (deja presentes) |
| `cursor_time_utc` | string\|null | - | curseur apres synchro |
| `error` | string\|null | - | message d'erreur |

### Reset (POST /integrations/garmin/reset)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `status` | string | - | `ok` |
| `deleted_sources` | int | - | mappings source supprimes |
| `deleted_cursor` | int | - | curseurs supprimes |

### Status (GET /integrations/garmin/status)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `tokens_present` | bool | - | tokens d'authentification presents |
| `tokens_dir` | string | - | repertoire des tokens |
| `cursor_time_utc` | string\|null | - | curseur de synchro |
| `cursor_updated_at_utc` | string\|null | - | date maj curseur |
| `last_run.id` | string\|null | - | UUID du dernier run |
| `last_run.status` | string\|null | - | statut du dernier run |
| `last_run.imported_count` | int\|null | - | importees |
| `last_run.skipped_count` | int\|null | - | ignorees |
| `last_run.duration_s` | int\|null | s | duree du run |

### Credentials (POST /integrations/garmin/credentials, GET /integrations/garmin/credentials/status)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `configured` | bool | - | credentials sauvegardes |
| `email` | string\|null | - | email Garmin |
| `path` | string | - | chemin du fichier credentials |

## Progress Indexation (POST /progress/index/fast, POST /progress/index/slow, GET /progress/index/status)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `running` | bool | - | indexation en cours |
| `mode` | string | - | `fast` ou `slow` |
| `phase` | string | - | phase actuelle |
| `current_run_duration_ms` | int\|null | ms | duree du run courant |
| `progress_current` | int | - | progression actuelle |
| `progress_total` | int | - | progression totale |
| `percent` | float | % | pourcentage |
| `last_result.scanned` | int\|null | - | activites parcourues |
| `last_result.indexed` | int\|null | - | activites indexees |
| `last_result.up_to_date` | int\|null | - | deja a jour |
| `last_result.errors` | int\|null | - | erreurs |
| `last_error` | string\|null | - | derniere erreur |
| `last_started_at_utc` | string\|null | - | ISO UTC |
| `last_finished_at_utc` | string\|null | - | ISO UTC |
| `last_duration_ms` | int\|null | ms | duree du dernier run |

POST /progress/index/fast accepte `{ "reason": "..." }`.
POST /progress/index/slow accepte `{ "strategy": "incremental|backfill_missing|backfill_full", "reason": "...", "force": bool }`.

## Training Load (GET /progress/training-load)

Query params: `from`, `to` (date ou ISO datetime).

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `points[]` | array<object> | - | serie temporelle |
| `points[].bucket_start` | string | - | date YYYY-MM-DD |
| `points[].acute_load_7d` | float | - | charge aigue (7 jours) |
| `points[].chronic_load_42d` | float\|null | - | charge chronique (42 jours) |
| `points[].acwr` | float\|null | - | ratio charge aigue/chronique |
| `points[].monotony_7d` | float\|null | - | monotonie (7 jours) |
| `points[].strain_7d` | float\|null | - | strain (charge x monotonie) |
| `current_acwr` | float\|null | - | ACWR actuel |
| `current_monotony` | float\|null | - | monotonie actuelle |
| `current_strain` | float\|null | - | strain actuel |
| `risk_zone` | string\|null | - | `low`, `moderate`, `high` |

## Calendar (GET /progress/calendar)

Query params: `year` (obligatoire, 2000-2100).

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `days[]` | array<object> | - | jours avec activite |
| `days[].date` | string | - | `local_date` YYYY-MM-DD, repli UTC pour les anciennes lignes |
| `days[].has_activity` | bool | - | activite ce jour |
| `days[].distance_km` | float | km | distance cumulee |
| `days[].moving_time_s` | float | s | temps de mouvement cumule |
| `days[].activity_count` | int | - | nombre d'activites |
| `year` | int | - | annee |
| `total_active_days` | int | - | jours actifs dans l'annee |
| `longest_streak` | int | jours | plus longue série consécutive dans l'année affichée |
| `current_streak` | int | jours | série globale terminant aujourd'hui ou hier, sinon zéro |

## Intensity Distribution (GET /progress/intensity-distribution)

Query params: `from`, `to` (dates YYYY-MM-DD), `type` (optionnel, `real` par défaut).

Temps passé dans chaque zone de fréquence cardiaque (Z1-Z5) agrégé par semaine.
Les activités sans données HR sont silencieusement exclues.
Les temps et les seuils reposent sur le même snapshot de FC max effective. Une modification de valeur/source invalide les bins, déclenche une indexation lente complète et empêche l'affichage des anciens temps pendant le recalcul.

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `points[]` | array<object> | - | serie hebdomadaire |
| `points[].bucket_start` | string | - | date debut semaine YYYY-MM-DD |
| `points[].z1_time_min` | float | min | temps en zone 1 (50-60% FC max) |
| `points[].z2_time_min` | float | min | temps en zone 2 (60-70% FC max) |
| `points[].z3_time_min` | float | min | temps en zone 3 (70-80% FC max) |
| `points[].z4_time_min` | float | min | temps en zone 4 (80-90% FC max) |
| `points[].z5_time_min` | float | min | temps en zone 5 (≥90% FC max) |
| `points[].total_time_min` | float | min | temps total avec HR |
| `zone_thresholds_bpm` | object\|null | bpm | seuils de zones en bpm (null si FC max non configurée) |
| `zone_thresholds_bpm.z1` | float | bpm | seuil Z1 |
| `zone_thresholds_bpm.z2` | float | bpm | seuil Z2 |
| `zone_thresholds_bpm.z3` | float | bpm | seuil Z3 |
| `zone_thresholds_bpm.z4` | float | bpm | seuil Z4 |
| `zone_thresholds_bpm.z5` | float | bpm | seuil Z5 |
| `zone_ranges_bpm[]` | array<object>\|null | bpm/% | bornes min inclusives et max exclusives de Z1 à Z5 |
| `hr_max_used_bpm` | float\|null | bpm | FC max utilisée par les bins |
| `hr_max_source` | `manual`\|`detected` | - | provenance de la FC max |
| `zones_stale` | bool | - | les lignes indexées ne correspondent pas au réglage courant |
| `reindexation_running` | bool | - | un recalcul lent des zones est en cours |

## Long Run Dose (GET /progress/long-run-dose)

Query params: `from`, `to` (dates YYYY-MM-DD).

Distance et temps des sorties longues (tag `long_run` : distance ≥ 18 km ou temps ≥ 90 min) agrégés par semaine.

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `[].bucket_start` | string | - | date debut semaine YYYY-MM-DD |
| `[].distance_km` | float | km | distance totale en sortie longue |
| `[].moving_time_h` | float | h | temps total en sortie longue |
| `[].activity_count` | int | - | nombre de sorties longues |
| `[].max_distance_km` | float | km | plus longue sortie de la semaine |

## VAM Trend (GET /progress/vam-trend)

Query params: `from`, `to` (dates YYYY-MM-DD).

Meilleur VAM (vitesse ascensionnelle) par activité contenant au moins une montée.
Les activités sans montée sont silencieusement exclues.

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `[].activity_id` | string | - | ID de l'activité |
| `[].start_ts_utc` | string | - | date/heure UTC de l'activité |
| `[].vam_max_m_h` | float | m/h | VAM max parmi les montées de l'activité |

## Geo Cities (GET /geo/cities)

Query params: `query` (min 2 car.), `limit` (1-10, defaut 8), `language` (defaut `fr`).

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `query` | string | - | terme recherche |
| `results[]` | array<object> | - | resultats |
| `results[].label` | string | - | "Ville, Pays" |
| `results[].city` | string | - | ville |
| `results[].country` | string | - | pays |
| `results[].country_code` | string\|null | - | code pays ISO |
| `results[].lat` | float | deg | latitude |
| `results[].lon` | float | deg | longitude |

## Root & Health (GET /, GET /health)

### Root (GET /)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `message` | string | - | "CourseScope API" |
| `version` | string | - | version de l'API |
| `docs` | string | - | URL de la doc Swagger |
| `status` | string | - | "operational" |

### Health (GET /health)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `status` | string | - | "healthy" |
| `storage` | string | - | statut du storage |
| `registry` | string | - | statut du registry |

## Real Bins (GET /activity/{id}/real-bins)

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `pace_elevation_series[]` | array<object> | - | points pace x elevation |
| `pace_elevation_series[].distance_km` | float | km | distance |
| `pace_elevation_series[].pace_s_per_km` | float | s/km | allure |
| `pace_elevation_series[].elevation_m` | float\|null | m | altitude |
| `pace_time_bins[]` | array<object> | - | distribution temps par allure |
| `pace_time_bins[].pace_bin_floor_s_per_km` | float | s/km | plancher du bin |
| `pace_time_bins[].label` | string | - | label format (ex: "5:00-5:15/km") |
| `pace_time_bins[].time_s` | float | s | temps passe dans le bin |
| `grade_time_bins[]` | array<object> | - | distribution temps par pente |
| `grade_time_bins[].grade_bin_center_pct` | float | % | centre du bin de pente |
| `grade_time_bins[].label` | string | - | label format (ex: "2.0%") |
| `grade_time_bins[].time_s` | float | s | temps passe dans le bin |
| `pace_histogram.complete_classes[]` | array<object> | - | toutes les classes d'allure servant au contrôle d'intégrité |
| `pace_histogram.display_classes[]` | array<object> | - | classes après seuil de 90 s et limite de 1,75 × l'allure moyenne |
| `pace_histogram.total_time_s` | float | s | somme exacte des classes complètes |
| `pace_histogram.displayed_time_s` | float | s | temps visible dans le graphique |
| `pace_histogram.hidden_time_s` | float | s | temps masqué par les règles d'affichage |
| `grade_histogram.complete_classes[]` | array<object> | - | toutes les classes calculées avec la pente robuste commune |
| `grade_histogram.display_classes[]` | array<object> | - | toutes les classes de pente non vides, identiques à `complete_classes` |
| `grade_histogram.total_time_s` | float | s | somme exacte des classes complètes |
| `grade_histogram.displayed_time_s` | float | s | temps visible dans le graphique |
| `grade_histogram.hidden_time_s` | float | s | toujours `0`, aucun masque temporel n'est appliqué à la pente |

Les champs `pace_time_bins` et `grade_time_bins` sont des alias de compatibilité des `display_classes`. Les nouvelles vues utilisent les deux objets `*_histogram`. La pente n'est plus calculée point à point et les dépassements de ±20 % sont conservés dans des classes extrêmes explicites. Le composant partagé activité/trace sort ces overflows de l'échelle numérique principale et affiche séparément leur durée et leur part du temps total.

## Series (GET /activity/{id}/series/{series_name})

`x_unit` rend l'unité de l'abscisse explicite : `s` pour `x_axis=time`, `km` pour `x_axis=distance`. Les bornes `from` et `to` utilisent la même unité. Le DataFrame canonique reste stocké en mètres en interne.
