# LUMEN Retro Terminal Dashboard Design Document

This document outlines the UI/UX architecture and rationale for the LUMEN Mission Telemetry Terminal, explaining how the visual language balances high presentation impact for non-technical evaluators with rigorous scientific honesty.

---

## 1. Visual Language & Aesthetics

- **CRT Terminal / Mission Telemetry Aesthetic**: Pure black background (`#0a0a0a`), vibrant amber/orange accents (`#e8a33d`), and high-readability monospace typography throughout (IBM Plex Mono / Courier New / JetBrains Mono fallback). 
- **No Generic Gradients / Color Blocks**: Replaces generic modern dashboard widgets with high-density tabular telemetry displays, crisp borders, and subtle amber glowing borders.
- **Specification Tagging (`MOD-XX`)**: Every section is prefixed with a sequential technical spec identifier (e.g., `MOD-A0`, `MOD-A1`, `MOD-P0`, `MOD-E1`, `MOD-D1`) mirroring aerospace mission control displays.
- **Dashed Monospace Readout Tables**: Key-value telemetry pairs render with white/gray labels left-aligned and amber values right-aligned, separated by thin dashed horizontal lines (`border-b border-dashed border-[#222]`).

---

## 2. 4-Page Navigation Architecture

The left navigation sidebar presents 4 minimalist, numbered operational views with a dashed underline active indicator:

### `01. MAPPING/GEOMETRY`
- **Telemetry Readout Table**: Live XML-derived telemetry for all 4 primary sensor modes (TMC-2 NCA, TMC-2 NCN, OHRC NCP, IIRS NDI).
- **Interactive 3D Wireframe Scene (`@react-three/fiber`)**: Renders a physical ground grid (lunar surface datum), a satellite point orbiting overhead, an orientation footprint cone/pyramid, and an amber sun vector. **Crucially, the geometry is physically driven by real XML parameters** (incidence angle, solar azimuth, emission angle, and pixel resolution) rather than decorative animation.
- **Full Swath Viewer**: Out-of-core pan-and-zoom inspection of full orbital swaths.

### `02. PIPELINE`
- **7-Stage Sequential Stepper**: Interactive progression from RAW PDS4 Ingestion to Evaluation.
- **Preserved Scientific Disclosures**:
  - *Stage 2 (Orthorectification)*: Prominently identifies the ISRO GCP ground control grid (60,803 points) and discloses that a planar $z=0.0\text{ m}$ datum fallback is used because no raw SLDEM or GLD100 raster exists on disk.
  - *Stage 3 (Photometric Normalization)*: Explicitly discloses that while the Lommel-Seeliger model uses the real flat-plate incidence angle ($39.06^\circ$), pixel-level variation is driven by a synthetic relief approximation (`cv2.GaussianBlur * 500`).
  - *Stage 7 (Cross-Sensor Overlap)*: Clearly documents that OHRC is polar while TMC-2/IIRS are equatorial, demonstrating $0.00\%$ physical cross-sensor overlap in the local archive.

### `03. EVALUATION`
- **Interactive Alpha-Blend Slider (Primary View)**: Full-bleed canvas allowing seamless blending between Reference (TMC NCN) and Warped Source (TMC NCA) across $0\%$ to $100\%$.
- **Secondary Checkerboards**: High-resolution crater rim detail overlay and full-swath checkerboard modes.
- **Oversized Metric Callouts**: Large amber typography highlighting:
  - **Held-out RMSE** (5-fold cross-validation): $1.96\text{ px}$ ($\approx 10\text{ m}$ at 5.2 m/px).
  - **Fit residual** (points used for fitting): $1.85\text{ px}$.
  - **SSIM**: $0.535$.
  - **MAGSAC++ inlier ratio**: $24.8\%$ (92 / 371).
  - All values from `docs/results/benchmark.json` (TMC-2 aft → nadir, native window, SIFT).

### `04. DATASETS`
- **Physical Archive Inventory Table**: Direct scan of `data/raw/` reflecting all 8 products on disk with real file sizes computed directly from filesystem metadata (totaling $10.49\text{ GB}$).
- **Interactive `[INSPECT]` Trigger**: Deep-links any archive product back to the 3D Geometry inspector on Page 1.
- **MOD-D2 Geodetic Constraint**: Full geodetic footprint explanation clarifying why polar OHRC and equatorial TMC-2 cannot form cross-sensor registration pairs.

---

## 3. Resolution of the "Strip-Image" Bug
ISRO orbital swaths feature extreme aspect ratios (up to $13:1$ or higher). A conventional web image element compresses these into an unreadable thin line.

**Solution Maintained in Terminal Aesthetic**:
- Detail regions are cropped to standard square fields of view for instant telemetry comparison.
- Full swath previews integrate within an enclosed `react-zoom-pan-pinch` viewport that defaults to fit-to-width/fit-to-container while allowing infinite panning and mouse-wheel zooming. Images never collapse into unreadable strips.
