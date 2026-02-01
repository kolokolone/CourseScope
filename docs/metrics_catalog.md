# Metrics Catalog

Compiled from API schemas and backend metric builders (`backend/api/schemas.py`, `backend/core/real_run_analysis.py`, `backend/core/metrics.py`).
See `docs/metrics_list.txt` for a categorized list of all file-only metrics.

## Activity Load (POST /activity/load)

### Sidebar stats

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `stats_sidebar.distance_km` | float | km | distance km |
| `stats_sidebar.elapsed_time_s` | float | s | elapsed time s |
| `stats_sidebar.moving_time_s` | float | s | moving time s |
| `stats_sidebar.elevation_gain_m` | float | m | elevation gain m |

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

### Climbs

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `climbs.items[]` | array<object> | - | items |
| `climbs.items[].distance_km` | unknown | km | climb distance km |
| `climbs.items[].elevation_gain_m` | unknown | m | climb elevation gain m |
| `climbs.items[].avg_grade_percent` | unknown | % | average grade percent |
| `climbs.items[].vam_m_h` | unknown | m/h | vertical ascent rate |
| `climbs.items[].start_idx` | unknown | - | start index |
| `climbs.items[].end_idx` | unknown | - | end index |

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

## Theoretical Activity Metrics (GET /activity/{id}/theoretical)

### Infos de course

| Path | Type | Unit | Description |
| --- | --- | --- | --- |
| `summary.total_time_s` | float | s | total time s |
| `summary.total_distance_km` | float | km | total distance km |
| `summary.average_pace_s_per_km` | float | s/km | average pace s per km |
| `summary.elevation_gain_m` | float | m | elevation gain m |

### Series index

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
| `limits.note` | string | - | note |
