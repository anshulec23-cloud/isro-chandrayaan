# LUMEN: Lunar Multi-Sensor Registration Pipeline

LUMEN is an automated computer vision pipeline developed to rigorously align multi-sensor orbital imagery of the Moon (ISRO Chandrayaan-2/3 TMC, OHRC, and IIRS data). 

## Project Documentation

The repository has been fully audited and documented. Please refer to the `/docs` directory for detailed information:

- 🏗️ **[Architecture & Data Flow](docs/ARCHITECTURE.md)**: Detailed explanation of the 7-stage pipeline.
- 📜 **[Progress Log](docs/PROGRESS.md)**: A chronological history of the project's development.
- ⚖️ **[Rules & Constraints](docs/RULES.md)**: Hardware RAM limits and strict data limitations.
- 🎨 **[Dashboard UI Design](docs/DESIGN.md)**: The rationale behind the stage-tracker and image viewer.
- 🎯 **[PRD & Gap Analysis](docs/PRD.md)**: Original requirements vs actual deliverables.
- 🔍 **[Self-Audit Report](docs/AUDIT.md)**: Handoff notes and what works end-to-end.

## Getting Started

### 1. Requirements
- **Python 3.10+**
- **Node.js 18+**
- **OS**: Windows / Linux
- **RAM**: Minimum 16GB required.

### 2. Setup
1. Clone the repository.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Prepare the data: Ensure ISRO PDS4 archives are extracted into `data/raw/` and `data/calibrated/`. 

### 3. Running the Demo Dashboard
To view the validated results, the interactive pipeline stage tracker, and the out-of-core image viewers, run the automated demo script from the root of the repository:

```bash
.\START_DEMO.bat
```
This script will build the React dashboard, launch the FastAPI server, and automatically open the interactive demonstration in your default web browser.

## Current Validated Results

The pipeline has been thoroughly tested and validated on an overlapping TMC-to-TMC stereo pair situated in the Lunar Equatorial region (Latitude: -29.51° to -3.62°S, Longitude: 140.78° to 142.71°E). Note: OHRC products are located at the Lunar South Pole (-84.66° to -89.95°S), resulting in 0.00% physical cross-sensor overlap in the current archive.

- **Independent Validation RMSE**: 1.932 px (~10.59 meters on ground) cross-validated against 20 unseen SIFT tie points to prevent matcher bias.
- **Matcher-Based RMSE**: 1.447 px (~7.93 meters on ground) MAGSAC++ internal residual error.
- **Structural Similarity (SSIM)**: 0.623 photometric structural correlation across the shared 92.34% ground footprint.
- **RANSAC Inlier Ratio**: 57.9% (62 inliers / 107 match candidates).

*Interactive alpha-blend comparison (0–100%), checkerboard overlays, and visual proofs can be viewed directly in the Retro Terminal Dashboard.*

## Dashboard Architecture

The frontend has been rebuilt with a retro CRT terminal telemetry aesthetic (`#0a0a0a` pure black, `#e8a33d` amber accents, monospace typography, and `MOD-XX` technical spec tags):

1. **`01. MAPPING/GEOMETRY`**: XML-derived telemetry readout table, animated 3D Three.js wireframe acquisition geometry (satellite position, sensor orientation cone, rotating ground grid, and sun illumination vector driven by real incidence/emission angles), and full-bleed swath viewer.
2. **`02. PIPELINE`**: Interactive 7-stage tracker (PDS4 Ingestion through Evaluation) with prominent honesty disclosures (Stage 2 ISRO GCP grid with z=0.0m datum fallback; Stage 3 Lommel-Seeliger synthetic relief demo; Stage 7 physical non-overlap disclosure).
3. **`03. EVALUATION`**: Full-bleed interactive horizontal alpha-blend slider (0% Reference to 100% Aligned Source), secondary crater rim and full-swath checkerboards, and oversized numeric metric cards distinguishing independent vs matcher-based RMSE.
4. **`04. DATASETS`**: Live physical archive inventory table listing all 8 Chandrayaan-2 products on disk (10.49 GB total volume) with real file sizes computed from disk, `[INSPECT]` cross-linking to Page 1, and geodetic coverage constraint analysis.

## Directory Map

- `lumen/`: Core Python package containing the pipeline architecture.
- `scripts/`: Standalone scripts for inventory, preview generation, and manual validation.
- `dashboard/`: Single-page React application with retro CRT telemetry design.
- `tests/`: Extensive pytest suite verifying pipeline integrity.
- `data/`: 
  - `raw/`: Raw ISRO zip archives and extracted PDS4 data (10.49 GB across 8 products).
  - `derived/`: IIRS hyperspectral radiance and reflectance cubes (`.qub`).
  - `processed/real_ortho_outputs/`: Generated GeoTIFF projections.
  - `processed/FINAL_DEMO/`: Validated TMC-TMC output images and checkerboards.
- `docs/`: Full project documentation.
