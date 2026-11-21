"""Subpixel refinement of tie-points using local phase correlation.

Each matched point pair is refined by extracting a small patch around the
*exact* (floating-point) location in both images, Hann-windowing both
patches, and measuring their residual offset with upsampled phase
correlation.  The reference point is kept fixed and the source point is
moved by the measured residual.

Earlier versions truncated both coordinates to integers before extracting
patches and then kept the truncated reference coordinate, which threw away
up to 1 px of precision and made the "refined" points slightly *worse* than
the matcher output.  ``tests/test_subpixel.py`` guards against that.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from skimage.registration import phase_cross_correlation

__all__ = ["phase_correlate_subpixel", "refine_subpixel"]

logger = logging.getLogger(__name__)


def phase_correlate_subpixel(
    patch_src: np.ndarray, patch_ref: np.ndarray, upsample_factor: int = 100
) -> tuple[float, float]:
    """Return the (dx, dy) offset of ``patch_src`` relative to ``patch_ref``.

    A positive ``dx`` means the content of ``patch_src`` sits ``dx`` pixels to
    the right of where it sits in ``patch_ref``.
    """
    shift = phase_cross_correlation(patch_ref, patch_src, upsample_factor=upsample_factor)
    # skimage < 0.20 returned (shift, error, diffphase); newer returns the array.
    if isinstance(shift, tuple):
        shift = shift[0]
    return float(shift[1]), float(shift[0])


def refine_subpixel(
    image_src: np.ndarray,
    image_ref: np.ndarray,
    pts_src: np.ndarray,
    pts_ref: np.ndarray,
    patch_size: int = 64,
    upsample_factor: int = 100,
    max_correction: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Refine matched points to subpixel precision.

    Args:
        image_src: Source image (the one that will be warped).
        image_ref: Reference image.
        pts_src: (N, 2) source points as (x, y).
        pts_ref: (N, 2) reference points as (x, y).
        patch_size: Side of the square correlation window in pixels.
        upsample_factor: Phase-correlation upsampling (100 → 0.01 px steps).
        max_correction: Corrections larger than this (px) are treated as
            unreliable (repetitive texture, occlusion) and the original
            point is kept.

    Returns:
        ``(refined_src, refined_ref)`` as float64 arrays.  ``refined_ref`` is
        ``pts_ref`` unchanged; it is returned for call-site symmetry.
    """
    pts_src = np.asarray(pts_src, dtype=np.float64).reshape(-1, 2)
    pts_ref = np.asarray(pts_ref, dtype=np.float64).reshape(-1, 2)
    if len(pts_src) == 0:
        return pts_src.copy(), pts_ref.copy()

    src = np.asarray(image_src, dtype=np.float32)
    ref = np.asarray(image_ref, dtype=np.float32)
    half = patch_size / 2.0
    window = np.outer(np.hanning(patch_size), np.hanning(patch_size)).astype(np.float32)

    def inside(img: np.ndarray, x: float, y: float) -> bool:
        return half <= x < img.shape[1] - half and half <= y < img.shape[0] - half

    refined = pts_src.copy()
    n_refined = 0
    for i, ((xs, ys), (xr, yr)) in enumerate(zip(pts_src, pts_ref)):
        if not (inside(src, xs, ys) and inside(ref, xr, yr)):
            continue
        p_src = cv2.getRectSubPix(src, (patch_size, patch_size), (float(xs), float(ys)))
        p_ref = cv2.getRectSubPix(ref, (patch_size, patch_size), (float(xr), float(yr)))
        if p_src.std() < 1e-6 or p_ref.std() < 1e-6:
            continue  # flat patch (shadow / no-data): nothing to correlate
        p_src = (p_src - p_src.mean()) * window
        p_ref = (p_ref - p_ref.mean()) * window
        dx, dy = phase_correlate_subpixel(p_src, p_ref, upsample_factor)
        if np.hypot(dx, dy) > max_correction:
            continue
        refined[i] = (xs - dx, ys - dy)
        n_refined += 1

    logger.debug(f"Subpixel refinement adjusted {n_refined}/{len(pts_src)} points")
    return refined, pts_ref.copy()
