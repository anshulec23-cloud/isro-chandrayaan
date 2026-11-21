# scripts/

Run from the repository root. Scripts that read imagery need the PRADAN products in
`data/raw/` (see the main README for product IDs).

| Script | What it does |
|---|---|
| `benchmark.py` | Measures accuracy on real pairs; writes `docs/results/benchmark.json` and the overlays in `docs/images/`. Source of every number in the README. |
| `generate_match_previews.py` | Regenerates the dashboard's Stage 4 match images from the same run as the benchmark. |
| `run_real_ortho_outputs.py` | Orthorectifies the products to GeoTIFFs in `data/processed/real_ortho_outputs/` (the pipeline reuses these for windowed reads). |
| `generate_previews.py`, `generate_stage_assets.py` | Build the remaining dashboard preview images. |
| `run_real_demo.py`, `generate_checkpoints.py` | Older end-to-end demo run with fixed checkpoints (superseded by `benchmark.py` for accuracy numbers). |
| `check_footprint_overlap.py`, `inventory_footprints.py`, `diagnose_footprints.py` | Inspect product footprints and which pairs overlap. |
| `download_selene.py` | Downloads the public JAXA SELENE TC ortho-mosaic used as the cross-mission reference. |
| `cross_mission_technique{1,2,3}_*.py` | The three TMC-2 vs SELENE experiments shown on the Evaluation page (photometric + SIFT, mutual information, crater matching). |
