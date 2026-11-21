# Product Requirements Document (PRD)

## Original Problem Statement
**Problem Code**: SIH1666 (ISRO)
**Title**: Automated Registration of Multi-Sensor Lunar Imagery

**Objective**: Develop a software pipeline capable of automatically ingesting, preprocessing, and aligning optical imagery of the Moon captured by multiple sensors (specifically the Terrain Mapping Camera-2, Orbiter High Resolution Camera, and Imaging Infra-Red Spectrometer) aboard ISRO's Chandrayaan missions. The alignment must be robust against variations in scale, rotation, illumination, and viewing geometry, achieving sub-pixel accuracy to enable multi-spectral scientific analysis.

## Gap Analysis: Delivered vs. Required

| Requirement | Delivered Status | Notes |
| :--- | :--- | :--- |
| **PDS4 Ingestion** | ✅ Complete | Fully parses XML to extract bounding coordinates, angles, and geometry paths. |
| **Orthorectification** | ✅ Complete | Successfully warps raw pixels to EPSG:4326 using Ground Control Points (GCP) or IIRS location images. Implemented anisotropic projection to prevent polar memory explosion. |
| **Photometric Normalization** | ⚠️ Partial | CLAHE standardises contrast and is used in every run. Lommel-Seeliger/Minnaert are implemented but have no effect without a DEM: the angles are one value per scene, so the correction is a uniform gain that CLAHE removes (identical results with it disabled). |
| **Multi-Sensor Alignment** | ⚠️ Partially Blocked | The codebase logic supports OHRC, TMC, and IIRS. However, the provided dataset in `data/raw/` contains zero physical overlaps between these three sensors. Cross-sensor alignment is strictly blocked by the lack of overlapping data. |
| **Same-Sensor Stereo Alignment** | ✅ Complete | Measured on the overlapping TMC-2 aft/nadir stereo pair (lat [-29.51°, -3.62°], lon [140.78°, 142.71°]); see the README results table. |
| **Sub-pixel Accuracy** | ❌ Not met | Held-out (5-fold cross-validated) RMSE at native resolution is **1.96 px ≈ 10 m** (TMC-2 aft → nadir) and **1.86 px ≈ 10 m** (TMC-2 → SELENE TC); `docs/results/benchmark.json`. Terrain parallax between the ±26° stereo looks cannot be absorbed by a single homography without a DEM. The earlier "1.932 px ≈ 10.59 m" was measured on a ~332 m/px grid (≈ 550 m on the ground). |

## Conclusion
The LUMEN pipeline successfully delivers a fully automated, 7-stage registration architecture. It exceeds requirements regarding modularity, memory management (running entirely within 16GB RAM), and UI visualization. Two requirements are not met. Cross-sensor (OHRC/IIRS) alignment is untested because the local archive has no overlapping products. Sub-pixel accuracy is not reached at native resolution (≈ 2 px, ≈ 10 m); a DEM-based orthorectification or a non-rigid warp is needed to remove stereo parallax.
