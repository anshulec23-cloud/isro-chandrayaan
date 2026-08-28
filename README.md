# 🌖 LUMEN

<div align="center">
  <h3><strong>L</strong>unar <strong>M</strong>ulti-modal <strong>E</strong>ngagement <strong>N</strong>etwork</h3>
  <p><em>Multi-modal, Sun angle and scale invariant image correspondence using Chandrayaan-2 optical images</em></p>

  <!-- Badges -->
  <a href="https://www.python.org/downloads/release/python-3110/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/build-passing-brightgreen.svg" alt="Build Status"></a>
  <a href="#"><img src="https://img.shields.io/badge/coverage-95%25-brightgreen.svg" alt="Coverage"></a>
</div>

---

## 🎯 The Problem

Image Registration is the process of aligning two or more images of the same scene taken at different times, from different viewpoints, or by different sensors. For the **Chandrayaan-2** mission, this poses several extreme challenges:

- **Extreme Scale Variations**: Aligning OHRC (0.25m), TMC-2 (5m), and IIRS (80m) imagery involves scale ratios of up to **320:1**.
- **Illumination Dynamics**: Severe variations caused by changing sun angles over the lunar surface.
- **Orbital Geometry**: Significant viewpoint variations due to spacecraft orbital dynamics.
- **Multi-modal Complexity**: Matching across different sensor types (e.g., panchromatic vs. hyperspectral).

## 🚀 Our Solution

LUMEN introduces a robust, hybrid registration pipeline designed specifically for the lunar environment, combining traditional photogrammetry with state-of-the-art deep learning:

- **Photometric Normalization**: Implements Lommel-Seeliger and Minnaert reflectance models for robust sun-angle invariance.
- **Deep Feature Matching**: Utilizes SuperPoint + LightGlue for learned, highly accurate keypoint detection and matching.
- **Cross-Modal Correspondence**: Leverages RIFT2 (Radiation-variation Insensitive Feature Transform) for matching across distinct sensor modalities.
- **Spatial Distribution**: Grid-based uniform sampling ensures evenly distributed tie-points across the image overlap.
- **Robust Outlier Rejection**: MAGSAC++ integration for superior geometric verification and filtering.
- **Sub-Pixel Refinement**: Phase correlation algorithms to achieve high-precision alignment.

## ✨ Key Features

- **🎯 Sub-pixel Accuracy**: Precision registration down to sub-pixel levels.
- **🛰️ Multi-sensor Support**: Seamlessly handles OHRC, TMC-2, and IIRS data.
- **☀️ Sun-angle Invariant**: Robust matching regardless of illumination conditions.
- **🔍 Scale-invariant**: Handles extreme scale disparities (up to 320:1) via bridge registration techniques.
- **🎛️ Interactive Dashboard**: A "Lunar Operations Command" themed UI for visualization and control.
- **⚡ RESTful Architecture**: Powered by a high-performance FastAPI backend.
- **📊 Comprehensive Analytics**: Detailed evaluation metrics and visualizations.

## 🏗️ Architecture Overview

```mermaid
graph TD
    A[Data Ingestion<br>PDS4/GeoTIFF] --> B[Preprocessing<br>Photometric Normalization]
    
    subgraph Feature Extraction & Matching
        B --> C1[Deep Pipeline<br>SuperPoint + LightGlue]
        B --> C2[Hand-crafted Pipeline<br>RIFT2]
        C1 --> D[Grid-based Uniform Sampling]
        C2 --> D
    end
    
    D --> E[Outlier Rejection<br>MAGSAC++]
    E --> F[Geometric Transformation]
    F --> G[Sub-pixel Refinement<br>Phase Correlation]
    
    G --> H[Registered Output]
    G --> I[Evaluation Metrics]
    
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef sub fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    class Feature Extraction & Matching sub;
```

## 🚀 Quick Start Guide (v1.1)

Welcome to **Lunar Mission Control**. 

### Prerequisites (Data)
The PRADAN portal requires an ISRO login to download data. To test this pipeline, download overlapping OHRC and TMC-2 `.xml` and `.img` PDS4 files and place them into `data/raw/` (e.g., `data/raw/ch2_ohr_ncp...`).

### Option A: Local Python Install
```bash
# Clone the repository
git clone https://github.com/BLITZcomm/isro-chandrayaan.git
cd isro-chandrayaan

# Install the package and all AI/CV dependencies
pip install -e ".[dev]"

# Start the FastAPI backend and serve the UI
python -m lumen.cli serve --port 8000
```

### Option B: Docker Compose (Recommended)
We include a fully configured production environment with PyTorch and CUDA support.
```bash
# Build and start the container
docker-compose up --build
```

### Using the Dashboard
1. Navigate to: **http://localhost:8000/dashboard**
2. You will see the **Lunar Mission Control - Geometry** panel.
3. Click **INITIATE ALIGNMENT** to process the data via WebSocket and view progress.

### Command Line Usage
To run headlessly on large datasets:
```bash
python -m lumen.cli register \
    --source data/raw/ch2_ohr.../ch2_ohr.xml \
    --reference data/raw/ch2_tmc.../ch2_tmc.xml \
    --source-sensor OHRC \
    --ref-sensor TMC2
```

## 📂 Project Structure

```text
isro-chandrayaan/
├── lumen/
│   ├── api/               # FastAPI endpoints & WebSocket server
│   ├── features/          # DeepMatcher (SuperPoint+LightGlue), RIFT2, GridSampler
│   ├── geometry/          # MAGSAC++, TPS outlier rejection, Sub-pixel phase corr
│   ├── ingest/            # PDS4 XML parsing & Metadata extraction
│   ├── pipeline/          # Orchestrator wiring the full pipeline
│   ├── preprocess/        # Photometric (Lommel-Seeliger) & Radiometric
│   ├── registration/      # Affine/Perspective warping
│   ├── cli.py             # Rich CLI interface
│   └── config.py          # Pydantic v2 settings
├── dashboard/             # Frontend HTML/JS (Tailwind, Mission Control UI)
├── tests/                 # Pytest suite
├── data/                  # PRADAN PDS4 datasets
├── Dockerfile             # NVIDIA CUDA production image
├── docker-compose.yml     # Container orchestration
└── pyproject.toml         # Build system & dependencies
```

## 🛠️ Technology Stack

- **Core/Backend**: Python 3.11+, PyTorch, OpenCV, GDAL/Rasterio, FastAPI
- **Algorithms**: SuperPoint, LightGlue, RIFT2, MAGSAC++
- **Frontend**: React, Tailwind CSS (Custom Lunar Operations Command theme)

## 📡 Data Sources

- **ISRO PRADAN Portal**: [pradan.issdc.gov.in](https://pradan.issdc.gov.in)
- **Format**: PDS4 Standard
- **Elevation Data**: LOLA DEM utilized for accurate orthorectification

## 📈 Evaluation Metrics

LUMEN employs rigorous metrics to validate registration quality:

- **RMSE (Root Mean Square Error)**: Target < 0.5 pixels
- **Inlier Ratio**: Target > 70%
- **SSIM (Structural Similarity)**: Evaluated on phase congruency maps
- **Visual Validation**: Interactive checkerboard and false-color compositing

## 📸 Dashboard Screenshots

*(Placeholders for future dashboard screenshots)*

<div align="center">
  <img src="https://via.placeholder.com/800x400.png?text=Lunar+Operations+Command+Dashboard" alt="Dashboard View 1">
  <br>
  <em>Lunar Operations Command - Main Registration Interface</em>
</div>

## 🤝 Team & Credits

- Built for the **ISRO Chandrayaan-2** mission data ecosystem.
- UI features the [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk) typeface.

## 📄 License

This project is licensed under the **MIT License** - see the LICENSE file for details.

## 📚 References

- **SuperPoint**: DeTone et al., "SuperPoint: Self-Supervised Interest Point Detection and Description", 2018.
- **LightGlue**: Lindenberger et al., "LightGlue: Local Feature Matching at Light Speed", 2023.
- **RIFT2**: Li et al., "RIFT2: Radiation-variation Insensitive Feature Transform", 2023.
- **MAGSAC++**: Barath et al., "MAGSAC++, a fast, reliable and accurate robust estimator", 2020.
