# Panoramic-image-based GLP and SCR

Code for **A panoramic-image-based method for recognizing street shade conditions under direct and reflected solar radiation: Validation in central Tokyo**, Shanshan Liu and Takashi Asawa, *Building and Environment*, article 115388.
[https://doi.org/10.1016/j.buildenv.2026.115388](https://doi.org/10.1016/j.buildenv.2026.115388)

GLP predicts glass locations from annotated reference panoramas and facade geometry. SCR uses glass, building and tree masks with solar geometry to recognize shade conditions. The standard example evaluates the panorama observation position at **1.2 m**.

## Installation

Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the real example

From the repository root:

```bash
python run_block2_example.py
```

This runs three reference panoramas through GLP for **2C-5, 2E-5 and 2W-11**, merges predictions for each point, then runs SCR for their morning, noon and afternoon timestamps on 12 August 2024 (Japan time). Source and target heights are both 1.2 m; no ground-view conversion is applied.

Outputs are saved under `outputs/block2/`: `glass/` contains the three predicted glass masks; `scr/predictions.csv` contains nine classifications; `scr/reflection_debug.json` contains the reflection calculation details. Precomputed example results are in `examples/block2/results/`.

## Inputs and files

| File | Purpose |
|---|---|
| `examples/block2/references/` | Three annotated reference panoramas |
| `examples/block2/jobs.json` | GLP geometry and reference-to-target mapping |
| `examples/block2/masks/` | Building and tree masks for the three target points |
| `examples/block2/scr_config.json` | Target geometry, mask paths and SCR settings |
| `examples/block2/samples.csv` | Selected point IDs and original observation times |
| `run_glp.py`, `glp/` | GLP projection and merging |
| `run_scr.py`, `scr/` | Direct/reflected classification and final merging |

Full panoramas are equirectangular, with south at the horizontal center. Glass is pink for the left facade and green for the right facade relative to the street axis. Tree masks use green foreground; building masks use black foreground. See [METHOD_NOTES.md](METHOD_NOTES.md) for color rules, parameter definitions and coordinate conventions.

SCR outputs `Su` (sunlit), `TS` (tree shade), `BS` (building shade), `TS-BR`, `BS-BR`, or `BR-TS`. `BR` denotes building reflection; `BR-TS` denotes a potential reflection obstructed by trees. Input timestamps retain their original precision. For solar-position calculations, timestamps are truncated to the minute.

## Other commands

```bash
python run_glp.py                     # Real GLP example -> outputs/glp/
python run_scr.py                     # SCR with bundled glass masks -> outputs/scr/
python examples/block2/review_glp.py   # Regenerate review figures -> outputs/block2_review/
```

For your own inputs, use `python run_glp.py --config PATH --output DIR` and `python run_scr.py --config PATH --input CSV --output DIR`. Mask paths in a configuration are relative to that configuration. `run_block2_example.py` is the complete example that passes freshly generated glass masks to SCR.

## Multiple references and tower setbacks

Predictions from multiple reference images are combined by union **within the same target and facade group**. The paper separated podium and tower regions when the setback was at least **0.5 m**. For setbacks such as Block 3, prepare separate masks and geometry for podium and tower planes. Give each plane its own GLP `group` and SCR reflection entry; run reflection calculations separately and then merge statuses (`BR-TS > BR > None`). Do not flatten distinct planes into one glass mask with a single distance. The included Block 2 example uses one facade group.

## Example data

This repository includes selected reference images, masks, geometric parameters and timestamps for the Block 2 example, together with example outputs. The complete study dataset is not included. The example demonstrates the GLP–SCR workflow and is not intended to reproduce the full validation results reported in the paper.

See [the example guide](examples/block2/README.md) for the example inputs and outputs, and [METHOD_NOTES.md](METHOD_NOTES.md) for calculation details and assumptions.

## Citation

If you use this code or the GLP–SCR method in your research, please cite:

Liu, S., & Asawa, T. *A panoramic-image-based method for recognizing street shade conditions under direct and reflected solar radiation: Validation in central Tokyo*. Building and Environment, Article 115388. https://doi.org/10.1016/j.buildenv.2026.115388

## License

Original code, documentation and bundled example assets: **CC BY-NC 4.0**. See [LICENSE](LICENSE). Please credit Shanshan Liu and Takashi Asawa. Third-party dependencies retain their own licenses; the linked article is not relicensed here.

