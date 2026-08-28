# LUMEN Project Constraints

## 1. Introduction
This document outlines the constraints for the LUMEN (Lunar Multi-modal Engagement Network) project, which focuses on multi-modal, sun angle, and scale invariant image correspondence using Chandrayaan-2 optical images. The constraints are categorized into Data, Algorithmic, Accuracy, Computational, Environmental, Regulatory/IP, UI/UX, and Integration.

## 2. Constraints Log

### 2.1. Data Constraints

| Constraint | Description | Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Format** | PDS4 (Planetary Data System 4) with XML labels and binary data arrays. | LOW | Utilize `pds4_tools` library for robust parsing. |
| **Sensors** | OHRC (0.25m), TMC-2 (5m), IIRS (80m) — vastly different resolutions. | HIGH | Implement multi-resolution pyramid schemes and scale-space matching. |
| **Scale Ratios** | Up to 320:1 between OHRC and IIRS. | HIGH | Pre-scale images using spatial metadata before feature extraction. |
| **Data Volume** | Individual OHRC strips can be ~3km × ~12km at 0.25m = ~576 million pixels per strip. | MEDIUM | Process images in overlapping tiles to manage memory. |
| **Band Count** | IIRS has 256 spectral bands (0.8-5.0 µm). | MEDIUM | Perform band selection or PCA to reduce dimensionality before matching. |
| **Coordinate System** | Lunar body-fixed, selenographic coordinates. | LOW | Use standard planetary SPICE kernels and PROJ strings for transformations. |
| **DEM Dependency** | Requires LOLA/SELENE DEM for orthorectification (typically 59m resolution). | MEDIUM | Automate DEM fetching and alignment based on image footprint. |
| **Data Access** | Requires PRADAN portal access, manual download may be needed. | HIGH | Provide clear instructions and semi-automated scraper if permitted. |
| **Artifacts** | No cloud cover, but DO have thermal noise, cosmic ray artifacts. | MEDIUM | Implement pre-processing filters (e.g., median filtering) for artifact removal. |

### 2.2. Algorithmic Constraints

| Constraint | Description | Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **SuperPoint+LightGlue** | Requires GPU (CUDA), model weights ~50MB, inference on 1024×1024 takes ~100ms on RTX 3060. | MEDIUM | Provide CPU fallback (though slower); optimize batch sizes. |
| **RIFT2** | CPU-based, computationally intensive for large images, O(N²) descriptor matching. | HIGH | Use parallel processing (multiprocessing) and limit search windows. |
| **MAGSAC++** | Requires minimum 4 point correspondences for homography, 7 for fundamental matrix. | MEDIUM | Ensure robust feature extraction; fallback to affine if points are sparse. |
| **Phase Correlation** | Works best for translations, less robust for large rotations (>15°). | LOW | Use spatial metadata to pre-rotate images before applying phase correlation. |
| **Scale Handling** | Images must be resampled to common GSD before matching. | HIGH | Implement accurate resampling pipelines using GDAL. |
| **Minimum Matches** | Need ≥20 well-distributed matches for reliable affine transformation. | MEDIUM | Implement grid-based feature detection to ensure spatial distribution. |
| **Memory** | Loading full OHRC strips requires >4GB RAM per image. | HIGH | Utilize memory-mapped files and chunked processing. |

### 2.3. Accuracy Constraints

| Constraint | Description | Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Target** | Sub-pixel accuracy of the SOURCE image. | HIGH | Employ sub-pixel refinement techniques (e.g., phase correlation refinement). |
| **RMSE Threshold** | < 1.0 pixel for same-sensor, < 2.0 pixels for cross-sensor. | HIGH | Rigorous outlier rejection and non-linear optimization of transformations. |
| **Inlier Ratio** | Target > 70% after MAGSAC++ filtering. | MEDIUM | Tune feature descriptor thresholds and matching criteria. |
| **Spatial Uniformity** | Matches must be uniformly distributed (grid-based constraint). | MEDIUM | Enforce grid-based non-maximum suppression during feature detection. |
| **Photometric Normalization**| Must handle sun elevation from 5° to 85°. | HIGH | Utilize illumination-invariant descriptors (like RIFT) and pre-processing normalization. |

### 2.4. Computational Constraints

| Constraint | Description | Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **GPU** | NVIDIA GPU with CUDA 11.8+ recommended for deep learning features. | MEDIUM | Clear documentation of requirements; CPU-only pipeline option. |
| **RAM** | Minimum 16GB, recommended 32GB for large OHRC images. | HIGH | Enforce memory limits; use out-of-core processing for large datasets. |
| **Storage** | Each processed pair may require 2-5GB temporary storage. | MEDIUM | Implement automatic cleanup of temporary files; use compressed formats. |
| **Processing Time** | Target < 5 minutes per image pair on GPU, < 30 minutes on CPU. | MEDIUM | Profile code and optimize bottlenecks; provide progress indicators. |

### 2.5. Environmental Constraints

| Constraint | Description | Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10-3.12 (PyTorch compatibility). | LOW | Specify explicit version ranges in `pyproject.toml`/`requirements.txt`. |
| **OS** | Cross-platform (Linux primary, Windows/macOS supported). | MEDIUM | Set up CI/CD pipelines across all target OS platforms. |
| **Docker** | Must be containerizable for reproducibility. | LOW | Provide optimized Dockerfiles with multi-stage builds. |
| **GDAL** | System dependency required for geospatial I/O. | MEDIUM | Use conda environments or pre-built wheels to simplify GDAL installation. |

### 2.6. Regulatory/IP Constraints

| Constraint | Description | Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Data License** | ISRO data is freely available for research under ISRO's data policy. | LOW | Include license attributions and adherence guidelines in docs. |
| **Open Source** | All algorithmic components use permissive licenses (MIT, Apache 2.0, BSD). | LOW | Automated license scanning in CI pipeline. |
| **ITAR** | No ITAR restrictions on lunar surface data. | LOW | Verify regularly if integrating new external datasets. |

### 2.7. UI/UX Constraints

| Constraint | Description | Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Accessibility** | WCAG 2.1 AA minimum (challenging with dark theme). | MEDIUM | Use automated accessibility linters and perform manual contrast checks. |
| **Browser** | Chrome 100+, Firefox 100+, Safari 15+. | LOW | Use Babel/Autoprefixer and cross-browser testing tools. |
| **Image Rendering** | WebGL for 3D geometry visualization, Canvas for 2D image overlays. | MEDIUM | Use established libraries (e.g., Three.js, OpenLayers) for robust rendering. |
| **Maximum File Upload**| 500MB per image through web interface. | HIGH | Implement chunked uploads and client-side format validation. |

### 2.8. Integration Constraints

| Constraint | Description | Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **PDS4 Schema Versions**| Must handle both PDS4 1.15.x and 1.16.x schemas. | MEDIUM | Use flexible XML parsing and version-agnostic metadata extractors. |
| **DEM Formats** | Support GeoTIFF and IMG (PDS) formats. | LOW | Standardize reading through GDAL/rasterio abstractions. |
| **Output Formats** | GeoTIFF (registered image), JSON (match points), CSV (metrics). | LOW | Implement well-defined output writer classes with strict schemas. |

## 3. Constraint Dependency Matrix

The following table illustrates how different constraints interact with and depend on one another.

| Constraint | Depends On / Influences | Description of Interaction |
| :--- | :--- | :--- |
| **Scale Ratios (320:1)** | Scale Handling, RAM | Extreme scale differences necessitate robust resampling (Scale Handling), which dramatically increases memory usage (RAM). |
| **Data Volume** | RAM, Processing Time | Large image sizes dictate the memory requirements (RAM) and directly impact the ability to meet the <5 min / <30 min Processing Time limits. |
| **RAM (16GB/32GB)** | Memory (Algorithmic), Data Volume | The available system RAM limits how much of a large image (e.g., OHRC) can be loaded at once, enforcing chunking or tiling strategies. |
| **SuperPoint+LightGlue** | GPU (CUDA), Python | State-of-the-art matching relies on deep learning, which necessitates specific hardware (GPU) and software environments (Python 3.10-3.12, PyTorch). |
| **Photometric Normalization**| RMSE Threshold, Inlier Ratio | Dealing with extreme sun elevation angles (5°-85°) is crucial to extracting robust features, which in turn determines the Inlier Ratio and RMSE. |
| **GDAL Dependency** | OS, Docker | Relying on GDAL for robust geospatial processing introduces complexity in cross-platform installation (OS) and requires careful Dockerfile construction. |
| **Maximum File Upload** | Data Volume, RAM | The 500MB web upload limit must be reconciled with the fact that full OHRC strips can easily exceed this, requiring client-side tiling or server-side streaming logic. |
