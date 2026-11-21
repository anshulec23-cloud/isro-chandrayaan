# LUMEN Architecture

The LUMEN (Lunar Multi-Sensor Registration) pipeline is designed to automate the ingestion, standardization, and geometric alignment of disparate orbital datasets from ISRO's Chandrayaan-2/3 missions (TMC-2, OHRC, IIRS).

## Data Flow Diagram

```mermaid
graph TD
    subgraph Data Sources
        RawZip[ISRO ZIP Archives] --> Extractor[PDS4 Extractor]
        Extractor --> XML[PDS4 XML Metadata]
        Extractor --> IMG[Raw Pixel Data .img]
    end

    subgraph Pipeline Orchestrator
        S1[Stage 1: Ingestion & Metadata Parsing]
        S2[Stage 2: Orthorectification]
        S3[Stage 3: Overlap Cropping]
        S4[Stage 4: Photometric Normalization]
        S5[Stage 5: Multi-modal Matching]
        S6[Stage 6: Homography Alignment]
        S7[Stage 7: Evaluation]
    end

    XML --> S1
    IMG --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5
    S5 --> S6
    S6 --> S7

    subgraph Output
        S7 --> GeoTIFF[Registered GeoTIFF]
        S7 --> Metrics[RMSE & SSIM Metrics]
        S7 --> Visual[Checkerboard Overlays]
    end
```

## The 7-Stage Pipeline

LUMEN employs a modular, 7-stage architecture that processes PDS4 archives into registered GeoTIFFs. Measured accuracy is ≈ 2 px (≈ 10 m) at native TMC-2 resolution; see the README.

### 1. Ingestion & Metadata Parsing
- **Rationale**: ISRO delivers data in the planetary standard PDS4 format (.img with .xml sidecars), while external missions like JAXA SELENE use PDS3 (.img with .lbl headers).
- **Action**: The `PDS4Ingester` and `SeleneAdapter` automatically detect the format, extracting critical metadata such as native resolution (GSD), solar incidence/emission angles, and the bounding footprint coordinates. For SELENE products, memory-mapped raster slicing enables zero-RAM overhead ingestion.

### 2. Orthorectification
- **Rationale**: Spacecraft capture distorted images due to camera angle and planetary curvature. Raw pixels cannot be compared directly.
- **Action**: Uses `rasterio` and GDAL to warp the raw `.img` pixels onto a flat Geographic Coordinate System (EPSG:4326). It utilizes Ground Control Point (GCP) CSVs or pixel-level location images (IIRS) to perform the reprojection with cosine-latitude polar anisotropy correction. Reference products already orthorectified (e.g. SELENE TCORT) are cleanly ingested and georeferenced directly.
- **Tech Stack**: Python `rasterio.warp.reproject` using `Resampling.lanczos`.

### 3. Overlap Cropping
- **Rationale**: Lunar strips are massive (often 100,000+ pixels tall). Processing the entire strip when only a tiny fraction overlaps with the reference image causes Out-of-Memory (OOM) crashes.
- **Action**: Uses `shapely` to calculate the exact geographic intersection polygon between the source and reference images. Both images are then cropped to this exact bounding box.

### 4. Photometric Normalization
- **Rationale**: Images captured on different orbits have drastically different lighting, shadows, and contrast, confusing AI feature matchers.
- **Action**: Applies Contrast Limited Adaptive Histogram Equalization (CLAHE) and performs solar angle compensation based on the XML metadata to standardize the visual appearance of craters.

### 5. Multi-modal Matching
- **Rationale**: To align the images, we must find identical physical features (like crater rims) across same-sensor stereo pairs or disparate cross-mission optical sensors.
- **Action**: Uses feature detectors (SIFT, ORB, or SuperPoint) to extract keypoints. It then utilizes advanced matching algorithms (like MAGSAC++) to find correspondences that are invariant to scale and rotation. For cross-sensor optical data (e.g., TMC vs SELENE TC), multi-scale feature pyramids and phase-congruency descriptors (RIFT2) are evaluated.

### 6. Homography Alignment
- **Rationale**: Keypoint matches always contain false positives (outliers). 
- **Action**: Uses RANSAC (or MAGSAC++) to filter out bad matches and calculate a robust Transformation Matrix (Affine or Homography). This matrix defines how to geometrically stretch, rotate, and translate the source image to perfectly overlay the reference image.

### 7. Evaluation
- **Rationale**: We must mathematically prove the accuracy of the alignment.
- **Action**: The pipeline reports the fit residual of the inliers, SSIM, and (when held-out checkpoints are supplied) a separate checkpoint RMSE. `scripts/benchmark.py` adds a 5-fold cross-validated RMSE and converts it to ground metres. Checkerboard and false-colour overlays are generated for visual verification.
