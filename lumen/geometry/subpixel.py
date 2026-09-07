"""Subpixel refinement using Phase Correlation."""

import numpy as np
from skimage.registration import phase_cross_correlation
import cv2

__all__ = ['phase_correlate_subpixel', 'refine_matches_subpixel', 'refine_subpixel']


def phase_correlate_subpixel(patch0: np.ndarray, patch1: np.ndarray,
                              upsample_factor: int = 100) -> tuple[float, float, float]:
    """Perform phase correlation to find subpixel shifts between patches.

    Args:
        patch0: Source image patch.
        patch1: Reference image patch.
        upsample_factor: Upsampling factor for subpixel accuracy.

    Returns:
        Tuple of (dx, dy, confidence).
        ``dx`` and ``dy`` are subpixel shifts in x (column) and y (row).
        ``confidence`` is a proxy value in [0, 1]: 1.0 = zero shift detected.

    scikit-image API note
    ---------------------
    scikit-image ≥ 0.20 removed the ``return_error`` kwarg and changed
    ``phase_cross_correlation`` to return only the shift array (no longer a
    3-tuple).  This function handles both the old and new signatures.
    """
    result = phase_cross_correlation(patch0, patch1, upsample_factor=upsample_factor)

    # Old API (skimage < 0.20): returns (shift, error, diffphase)
    if isinstance(result, tuple) and len(result) == 3:
        shift, error, _ = result
        return float(shift[1]), float(shift[0]), float(error)

    # New API (skimage >= 0.20): returns shift array directly
    shift = result
    max_shift = max(patch0.shape) / 2.0
    magnitude = float(np.linalg.norm(shift))
    confidence = max(0.0, 1.0 - magnitude / max_shift)
    return float(shift[1]), float(shift[0]), confidence


def refine_matches_subpixel(image0: np.ndarray, image1: np.ndarray,
                             matches0: np.ndarray, matches1: np.ndarray,
                             keypoints0: np.ndarray, keypoints1: np.ndarray,
                             patch_size: int = 64, upsample_factor: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Refine match coordinates using phase correlation on local patches.

    Args:
        image0: Source image.
        image1: Reference image.
        matches0: Indices of matched keypoints in image0.
        matches1: Indices of matched keypoints in image1.
        keypoints0: Coordinates of keypoints in image0.
        keypoints1: Coordinates of keypoints in image1.
        patch_size: Size of local patch to extract around keypoints.
        upsample_factor: Factor for subpixel accuracy.

    Returns:
        Refined coordinates (refined_kp0, refined_kp1).
    """
    half_patch = patch_size // 2
    refined_kp0 = []
    refined_kp1 = []

    kp0_matched = keypoints0[matches0]
    kp1_matched = keypoints1[matches1]

    for i in range(len(kp0_matched)):
        x0, y0 = map(int, kp0_matched[i])
        x1, y1 = map(int, kp1_matched[i])

        # Ensure patches are within bounds
        if (x0 - half_patch < 0 or y0 - half_patch < 0 or
                x1 - half_patch < 0 or y1 - half_patch < 0 or
                x0 + half_patch >= image0.shape[1] or y0 + half_patch >= image0.shape[0] or
                x1 + half_patch >= image1.shape[1] or y1 + half_patch >= image1.shape[0]):
            refined_kp0.append(kp0_matched[i])
            refined_kp1.append(kp1_matched[i])
            continue

        patch0 = image0[y0 - half_patch:y0 + half_patch, x0 - half_patch:x0 + half_patch]
        patch1 = image1[y1 - half_patch:y1 + half_patch, x1 - half_patch:x1 + half_patch]

        dx, dy, _ = phase_correlate_subpixel(patch0, patch1, upsample_factor)

        refined_kp0.append([x0 + dx, y0 + dy])
        refined_kp1.append([x1, y1])  # Keep reference stationary

    return np.array(refined_kp0, dtype=np.float64), np.array(refined_kp1, dtype=np.float64)


def refine_subpixel(image0: np.ndarray, image1: np.ndarray,
                    pts0: np.ndarray, pts1: np.ndarray,
                    patch_size: int = 64, upsample_factor: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Refine inlier keypoints using phase correlation on local patches.

    Args:
        image0: Source image.
        image1: Reference image.
        pts0: Inlier match coordinates in image0 (N, 2).
        pts1: Inlier match coordinates in image1 (N, 2).
        patch_size: Size of local patch.
        upsample_factor: Factor for subpixel accuracy.

    Returns:
        Tuple of (refined_pts0, refined_pts1) with float coordinates.
    """
    if len(pts0) == 0:
        return np.empty((0, 2), dtype=np.float64), np.empty((0, 2), dtype=np.float64)
    matches = np.arange(len(pts0))
    return refine_matches_subpixel(
        image0, image1, matches, matches, pts0, pts1,
        patch_size=patch_size, upsample_factor=upsample_factor,
    )
