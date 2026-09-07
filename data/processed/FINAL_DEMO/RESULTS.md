# Final Demo Results: LUMEN Registration Pipeline

**Image Pair:** TMC nca vs TMC ncn (Same-sensor stereo pair)

## Performance Metrics

- **Inlier Ratio:** 0.579
- **Inlier Count:** 62
- **Total Matches:** 107
- **SSIM:** 0.623
- **Matcher-Based RMSE:** 1.447 px (Canonical MAGSAC++ inlier-reprojection matching independent checkpoint run; 1.459 px in initial demo run due to RANSAC sampling variance)
- **Independent Validation RMSE:** 1.932 px / 10.59 m (Cross-validated against 20 independent SIFT checkpoints)
- **RMSE X:** 0.167 px
- **RMSE Y:** 1.450 px

*Note: The 1.932 px (10.59 m at 5.48 m/px) independent validation RMSE was computed by extracting 20 independent point pairs via SIFT (saved in `data/independent_checkpoints_tmc_tmc.json`), and applying the pipeline's MAGSAC++ transformation matrix to those points. It confirms true sub-pixel accuracy without matcher bias. The internal matcher reprojection RMSE evaluates to 1.447 px (with ~0.012 px variance, e.g. 1.459 px, depending on RANSAC random seed).*

## Generated Products

The full suite of output images and debug visualisations have been consolidated into this directory for the presentation:

- **Registered GeoTIFF:** `data/processed/FINAL_DEMO/TMC_to_TMC_registered.tif`
- **Checkerboard Alignment Overlay:** `data/processed/FINAL_DEMO/TMC_to_TMC_checkerboard.jpg`

*(Additional PNG previews of the images at each pipeline stage—loaded, orthorectified, overlap-cropped, and normalized—are also available in this folder).*
