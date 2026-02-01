# Roadmap

Ideas for future improvements (non-binding).

## Data analysis
- Detect best efforts (1k, 5k, 10k, HM, marathon) per activity and over history.
- Distributions: grade and pace histograms; optional zones for speed/cadence/HR/power.

## Pacing / theoretical
- Negative/positive split simulation and impact on ETA.
- Segment pacing plan: split the route into climbs/descents/flats.
- Condition adjustment: temperature, humidity, wind, altitude, surface.
- Hydration/nutrition timeline export.

## Visualization
- Cumulative time vs distance with target comparison.
- Map heatmaps (pace / heart rate) and annotated waypoints.

## Performance
- Cache expensive steps (parse, canonical DF build, derived series, aggregates) and avoid recompute on pure view changes.
- Share derived computations: compute slope/moving_mask/GAP once and reuse everywhere.
