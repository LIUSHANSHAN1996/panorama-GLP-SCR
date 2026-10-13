# Method and configuration notes

## Settings

| Setting | Meaning |
|---|---|
| `latitude`, `longitude`, `timezone` | Solar-position coordinates and local time zone |
| `image_width`, `image_height` | Equirectangular mask dimensions |
| `reflection_axis_deg` | Facade-parallel azimuth; equal to street azimuth for the parallel canyon |
| `observer_height_m` | Camera height hc above the building-height ground datum; default 1.2 m |
| `building_depth_m` | Uniform blocking-building depth b; 50 m in the real study example |

The reflected viewing azimuth is `(2 * reflection_axis_deg - solar_azimuth) % 360`; its altitude equals solar altitude. This is the assumed parallel-canyon geometry, not arbitrary-facade ray tracing.

## Geometry inputs

Each point has tree/building masks and a `reflections` mapping. Each facade group has a glass mask and:

| Field | Meaning |
|---|---|
| `street_azimuth_deg` | Street direction, clockwise from north |
| `street_width_m` | W for the modeled facade group |
| `distance_left_m`, `distance_right_m` | Perpendicular target-to-facade distances; the selected distance is a |
| `observer_s_m` | Target position on the common longitudinal s axis |
| `left_buildings`, `right_buildings` | Lists of `[start_s_m, end_s_m, height_m]` for the modeled buildings |

The global Cartesian axes follow the paper: x points west, y south and z upward. The longitudinal coordinate s is measured along the street direction, positive along `street_azimuth_deg`, matching GLP's positive `walk_distance_m`. Observer positions and building intervals share one origin. For a street azimuth A and origin (x0, y0), `s = -(x-x0)*sin(A) - (y-y0)*cos(A)`. GLP uses the relative displacement `s_target - s_source`. In the Block 2 example the longitudinal origin is 2C-1; positions opposite the positive street direction have negative s values. All distances are in meters. Separate podium/tower planes require separate masks and geometry; the paper uses a setback threshold of at least 0.5 m for this separation.

## Building-depth calculation: Eqs. (14)-(19)

`reflection_block_geometry` computes the paper's path segments explicitly. Let delta be the signed sun angle relative to the street direction. For the selected illuminated facade, `normal_cos` is the positive cosine of the angle between the sun and that facade's outward normal. The signed longitudinal tangent along the street axis is:

```python
q = cos(delta) / normal_cos
Lr = a * q
Ld = (W + b) * q
s_hit = observer_s_m + Ld + Lr
hr = hypot(a, Lr) * tan(solar_altitude)
hd = hypot(W + b, Ld) * tan(solar_altitude)
h = observer_height_m + hd + hr
```

This implements the distance relationships of Eqs. (14)-(19), with the left/right case mirrored and signed on the input table's axis. The square-root lengths are positive; Ld and Lr retain direction for locating the hit. Solar directions behind the selected facade or effectively parallel to it have no valid finite path.

The original, unexpanded building intervals are queried at `s_hit`. If several intervals include that position (including a shared boundary within 1e-6 m), the greatest height is used, so a zero-height interval cannot hide a taller overlapping candidate because it appears first. Uncovered positions produce no reflection prediction and are marked `outside_building_table` in debug output. Zero-height intervals explicitly model open space.

A reflection is allowed when h is strictly above the matched height. The tree mask then distinguishes BR from BR-TS. Debug output includes b, a, W+b, Ld, Lr, hd, hr, s_hit, h, candidate segment indices and the selected height.

## GLP inputs

`jobs.json` contains `defaults` and `jobs`. Each job has `job_id`, `source_mask`, `target_id`, `group` and geometry overrides. `distance_left_m` and `distance_right_m` are source-to-facade distances. `walk_distance_m` is positive along the street axis, and `lateral_offset_m` is positive toward its right. `source_height_m` and `target_height_m` share a ground datum; an omitted target height equals source height. The example specifies both as 1.2 m. SCR uses target-to-facade distances instead.

RGB glass colors are pink (255,105,180) for the left facade and green (0,255,0) for the right. GLP uses tolerance 10; full panoramas must have width twice height and south at the horizontal center. White is background and fully transparent input pixels are ignored. Source/target orientations must agree.

## SCR inputs

`samples.csv` requires unique `sample_id`, `point_id` matching the config, and full-date `timestamp`. Times use an explicit UTC offset or the configured time zone. Solar positions use pvlib apparent elevation with timestamps truncated to minutes.

Mask foreground tests in RGB: trees G>150, R<100, B<100; buildings all channels<50; green glass G>200, R<100, B<100; pink glass R>150, B>130, G<180. Masks are resized to configured dimensions by linear interpolation. Missing files are rejected in ordinary runs.

The example includes nine predictions for three observation points at morning, noon and afternoon timestamps.
