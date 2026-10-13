# Block 2 example

Three supplied references (2C-1, 2C-6, 2C-12) predict glass at 2C-5, 2E-5 and 2W-11. Each target combines three predictions by union within one facade group. Source and target heights are 1.2 m. Street azimuth is 195 degrees; source facade distances are 10.44 m left and 10.76 m right.

From the repository root, run `python run_block2_example.py`. The runner regenerates glass before SCR. Results are written to `outputs/block2/`.

## Selected inputs

| Target | Walk from 2C-1 / 2C-6 / 2C-12 (m) | Lateral (m) | Target left / right (m) |
|---|---|---:|---|
| 2C-5 | -27.7 / 9.2 / 63.2 | 0 | 10.44 / 10.76 |
| 2E-5 | -27.9 / 9.0 / 63.0 | -7.25 | 3.19 / 18.01 |
| 2W-11 | -83.1 / -46.2 / 7.8 | 7.35 | 17.79 / 3.41 |

A uniform building depth b=50 m and observer height 1.2 m are used. Latitude/longitude are 35.6794/139.7625.

The standard input mask size is **2048 × 1024 pixels (width × height)**. The building masks in this example already have this size. The supplied tree masks are 3584 × 1792 pixels and are automatically resized to 2048 × 1024 during SCR processing; tree masks prepared directly at 2048 × 1024 can also be used. The nine timestamps are selected from the original workbook's morning, noon and afternoon sheets on 2024-08-12, localized to Asia/Tokyo. The supplied seconds are retained in `samples.csv`; solar calculations use minutes.

The positive longitudinal direction is the street azimuth (195 degrees) for both GLP and SCR. With 2C-1 as the longitudinal origin, SCR positions are -27.7 m (2C-5), -27.9 m (2E-5) and -83.1 m (2W-11). Building interval endpoints use the same origin and direction. These signed positions describe locations; negative values do not denote negative physical lengths.

## Included results

`results/glp/merged/` contains three glass masks. Each `results/glp/review_*.png` shows the 2C-1, 2C-6 and 2C-12 predictions and their union from top to bottom. `results/scr/predictions.csv` contains the nine SCR predictions.

| Target | Morning | Noon | Afternoon |
|---|---|---|---|
| 2C-5 | BS | TS | BR-TS |
| 2E-5 | BS | Su | BS |
| 2W-11 | TS | TS | BS-BR |

To regenerate individual GLP masks, review sheets and union checks, run `python examples/block2/review_glp.py`; outputs go to `outputs/block2_review/`.
