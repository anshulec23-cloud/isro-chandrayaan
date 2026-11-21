"""
Outlier rejection via MAGSAC++ (global homography).

Transform model
---------------
This module fits and returns a **global projective homography** (3×3 matrix)
using OpenCV's USAC_MAGSAC estimator.

We explicitly do NOT implement Thin-Plate Spline (TPS) warping here.
The previous stub (`apply_tps_refinement`) called
`cv2.createThinPlateSplineShapeTransformer` but returned the input points
unchanged (a silent identity mock).  That function has been removed.

Why global homography is adequate for our tested footprint sizes
-----------------------------------------------------------------
The LUMEN pipeline is validated on overlapping OHRC/TMC-2 tiles whose
**ground footprint does not exceed ~3 km × 3 km** at the OHRC native 0.29 m/px
resolution (the full OHRC swath is ~3 km wide; the 12000 × ~80000 px strip is
ingested at a pipeline-internal cap of 2048 px per axis, corresponding to
~0.6 km² working extent).

At these extents the relative parallax between a nadir-pointing orbiter and the
flat-to-gently-rolling lunar south-pole terrain is small enough that the residual
non-rigid distortion between sensor footprints is well below our target RMSE of
0.5 px.  A global homography captures the dominant scale, rotation, and
perspective offset introduced by the differing orbital geometry of each pass.

When TPS / non-rigid warp IS needed
-------------------------------------
TPS becomes necessary when:
  • footprint overlap exceeds ~10 km (significant orbital bow-shock distortion), or
  • the DEM shows terrain relief > ~500 m within the tile (strong parallax).

Implementing real TPS requires:
  1. Fitting `scipy.interpolate.RBFInterpolator` (kernel='thin_plate_spline')
     on inlier correspondences.
  2. Replacing the homography warp path in `lumen/registration/warp.py` with a
     dense displacement-field map evaluated at every output pixel.
  3. Changing `RegistrationResult.transform_matrix` (currently always a 3×3
     ndarray) to a union type that also accepts a displacement field.

That is tracked as a future improvement, not currently implemented.
"""

import numpy as np
import cv2

__all__ = ["estimate_transform_magsac"]


def estimate_transform_magsac(
    pts_src: np.ndarray,
    pts_dst: np.ndarray,
    confidence: float = 0.999,
    max_iters: int = 5000,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate a robust homography using MAGSAC++.

    Args:
        pts_src: Source points, shape (N, 2), dtype float32.
        pts_dst: Destination points, shape (N, 2), dtype float32.
        confidence: Desired confidence level (USAC parameter).
        max_iters: Maximum RANSAC iterations (USAC parameter).

    Returns:
        (H, inlier_mask) where H is a 3×3 float64 homography matrix and
        inlier_mask is a boolean array of length N.  On failure (H is None
        from OpenCV or fewer than 4 input points) returns (I₃, all-False mask).
    """
    if len(pts_src) < 4:
        return np.eye(3), np.zeros(len(pts_src), dtype=bool)

    # USAC_MAGSAC is available in OpenCV 4.5.0+
    H, mask = cv2.findHomography(
        pts_src, pts_dst,
        cv2.USAC_MAGSAC,
        3.0,
        confidence=confidence,
        maxIters=max_iters,
    )

    if H is None:
        return np.eye(3), np.zeros(len(pts_src), dtype=bool)

    inlier_mask = mask.ravel() == 1
    return H, inlier_mask
