"""
Geographic overlap cropping for orthorectified image pairs.

After both images are projected onto a common geographic grid (EPSG:4326)
by orthorectify(), their footprints are expressed as
(min_lon, min_lat, max_lon, max_lat) tuples in the same coordinate system.
This module computes the intersection of those footprints, optionally expands
it by a configurable buffer, and slices both numpy arrays to the pixels that
correspond to the shared region.

This step is inserted AFTER orthorectification and BEFORE feature extraction,
so that the matcher operates only on the scene content that both images share.
Running a feature matcher across non-overlapping content produces only spurious
matches, inflating the outlier ratio and wasting compute.

Public API
----------
NoOverlapError          — raised when no usable overlap is found.
compute_intersection    — compute the intersection bbox of two footprints.
crop_to_bbox            — crop a single image array to a geographic bbox.
crop_pair_to_overlap    — crop a matched source/reference pair to their overlap.

All geographic coordinates follow the rasterio / GeoTIFF convention:
    bbox = (min_lon, min_lat, max_lon, max_lat)
    rows run from max_lat (top/north) to min_lat (bottom/south).
"""

import logging
import math
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "NoOverlapError",
    "compute_intersection",
    "crop_to_bbox",
    "crop_pair_to_overlap",
]

# Type alias for a geographic bounding box (min_lon, min_lat, max_lon, max_lat).
_BBox = Tuple[float, float, float, float]


# ---------------------------------------------------------------------------
# Sentinel error
# ---------------------------------------------------------------------------

class NoOverlapError(ValueError):
    """Raised when two georeferenced images share no usable overlap region.

    Attributes
    ----------
    src_bbox : tuple
        Footprint of the source image  (min_lon, min_lat, max_lon, max_lat).
    ref_bbox : tuple
        Footprint of the reference image.
    intersection : tuple or None
        The computed intersection, or None when there is no overlap at all.
    min_area_threshold : float
        The minimum area (deg²) required for the overlap to be considered
        usable.
    """

    def __init__(
        self,
        src_bbox: _BBox,
        ref_bbox: _BBox,
        intersection: Optional[_BBox],
        min_area_threshold: float,
    ):
        self.src_bbox = src_bbox
        self.ref_bbox = ref_bbox
        self.intersection = intersection
        self.min_area_threshold = min_area_threshold

        if intersection is None:
            reason = "footprints do not intersect at all"
        else:
            area = _bbox_area(intersection)
            reason = (
                f"intersection area {area:.4e} deg² is below the minimum "
                f"threshold {min_area_threshold:.4e} deg²"
            )

        super().__init__(
            f"No usable overlap between source footprint {_fmt(src_bbox)} "
            f"and reference footprint {_fmt(ref_bbox)}: {reason}. "
            "Check that these two products cover the same ground area."
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fmt(bbox: _BBox) -> str:
    return (
        f"(lon [{bbox[0]:.4f}, {bbox[2]:.4f}], "
        f"lat [{bbox[1]:.4f}, {bbox[3]:.4f}])"
    )


def _bbox_area(bbox: _BBox) -> float:
    """Area of a geographic bbox in degrees²."""
    w = max(0.0, bbox[2] - bbox[0])
    h = max(0.0, bbox[3] - bbox[1])
    return w * h


def _validate_bbox(bbox: _BBox, name: str) -> None:
    min_lon, min_lat, max_lon, max_lat = bbox
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError(
            f"Invalid bbox for '{name}': min must be strictly less than max. "
            f"Got (min_lon={min_lon}, min_lat={min_lat}, "
            f"max_lon={max_lon}, max_lat={max_lat})."
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_intersection(
    bbox_a: _BBox,
    bbox_b: _BBox,
    buffer_fraction: float = 0.0,
) -> Optional[_BBox]:
    """Compute the intersection of two geographic bounding boxes.

    An optional ``buffer_fraction`` expands the intersection by a fraction of
    the shorter axis on each side before returning.  A positive value captures
    more context around the true overlap edge (useful to avoid clipping features
    that straddle the boundary).  The expanded region is NOT clamped to either
    input footprint — the caller should clamp if desired.

    Args:
        bbox_a:  First bbox  (min_lon, min_lat, max_lon, max_lat).
        bbox_b:  Second bbox (min_lon, min_lat, max_lon, max_lat).
        buffer_fraction:
            Fraction of ``min(overlap_width, overlap_height)`` added to each
            side of the intersection.  0.0 = exact intersection.  Negative
            values shrink the intersection (useful to avoid edge artefacts at
            resampling boundaries).

    Returns:
        The intersection bbox, or None if the boxes do not intersect.
    """
    ix_min = max(bbox_a[0], bbox_b[0])
    iy_min = max(bbox_a[1], bbox_b[1])
    ix_max = min(bbox_a[2], bbox_b[2])
    iy_max = min(bbox_a[3], bbox_b[3])

    if ix_min >= ix_max or iy_min >= iy_max:
        return None

    if buffer_fraction != 0.0:
        short_axis = min(ix_max - ix_min, iy_max - iy_min)
        buf = buffer_fraction * short_axis
        ix_min -= buf
        iy_min -= buf
        ix_max += buf
        iy_max += buf

    return (ix_min, iy_min, ix_max, iy_max)


def crop_to_bbox(
    image: np.ndarray,
    image_bbox: _BBox,
    target_bbox: _BBox,
) -> np.ndarray:
    """Crop a 2-D (or 3-D) image array to the pixels corresponding to
    *target_bbox*, given that the image currently covers *image_bbox*.

    Both bboxes must be in the same coordinate system (EPSG:4326 degrees).
    The image is assumed to be a north-up raster produced by
    ``orthorectify()``, i.e. row 0 maps to ``max_lat`` and the last row maps
    to ``min_lat``.

    Args:
        image:
            2-D (H, W) or 3-D (H, W, C) float32 array.
        image_bbox:
            Geographic extent of the full input image
            (min_lon, min_lat, max_lon, max_lat).
        target_bbox:
            Geographic extent to crop to.  Must overlap with image_bbox.

    Returns:
        The cropped sub-array (view into *image* where possible).

    Raises:
        ValueError: If target_bbox does not intersect image_bbox, or if
                    the resulting crop would be empty.
    """
    img_min_lon, img_min_lat, img_max_lon, img_max_lat = image_bbox
    tgt_min_lon, tgt_min_lat, tgt_max_lon, tgt_max_lat = target_bbox

    h, w = image.shape[:2]
    if h == 0 or w == 0:
        raise ValueError(f"Image array is empty: shape={image.shape}")

    # Pixels per degree for this image
    lon_per_px = (img_max_lon - img_min_lon) / w  # > 0
    lat_per_px = (img_max_lat - img_min_lat) / h  # > 0  (geographic height in deg / pixel count)
    # In a north-up raster, row index increases southward:
    #   row 0   → img_max_lat
    #   row h-1 → img_min_lat

    # Target bbox in pixel coordinates (floating point, then rounded)
    col_f_start = (tgt_min_lon - img_min_lon) / lon_per_px
    col_f_end   = (tgt_max_lon - img_min_lon) / lon_per_px
    row_f_start = (img_max_lat - tgt_max_lat) / lat_per_px   # north-up → top of target
    row_f_end   = (img_max_lat - tgt_min_lat) / lat_per_px   # north-up → bottom of target

    # Clamp to valid pixel range
    col_start = max(0, math.floor(col_f_start))
    col_end   = min(w, math.ceil(col_f_end))
    row_start = max(0, math.floor(row_f_start))
    row_end   = min(h, math.ceil(row_f_end))

    if col_start >= col_end or row_start >= row_end:
        raise ValueError(
            f"target_bbox {_fmt(target_bbox)} maps to an empty pixel region "
            f"(rows {row_start}:{row_end}, cols {col_start}:{col_end}) "
            f"within image of shape {image.shape} covering {_fmt(image_bbox)}."
        )

    logger.debug(
        f"crop_to_bbox: rows [{row_start}:{row_end}], cols [{col_start}:{col_end}] "
        f"from {image.shape} → ({row_end - row_start}, {col_end - col_start})"
    )
    return image[row_start:row_end, col_start:col_end]


def crop_pair_to_overlap(
    src_image: np.ndarray,
    src_bbox: _BBox,
    ref_image: np.ndarray,
    ref_bbox: _BBox,
    buffer_fraction: float = 0.0,
    min_area_threshold: float = 1e-10,
) -> Tuple[np.ndarray, np.ndarray, _BBox]:
    """Crop a source/reference image pair to their geographic overlap region.

    Both images must already be projected onto the **same geographic grid**
    (i.e. both orthorectified with the same output CRS and a compatible GSD).

    Steps
    -----
    1. Validate both bboxes.
    2. Compute the intersection (± buffer).
    3. Raise :class:`NoOverlapError` if the intersection is empty or its area
       is below ``min_area_threshold``.
    4. Crop each image to the pixel rows/columns that correspond to the
       intersection bbox.
    5. Return the two cropped arrays and the intersection bbox.

    Args:
        src_image:
            Source image array (2-D or 3-D, float32).
        src_bbox:
            Geographic footprint of the source image
            (min_lon, min_lat, max_lon, max_lat).
        ref_image:
            Reference image array (2-D or 3-D, float32).
        ref_bbox:
            Geographic footprint of the reference image.
        buffer_fraction:
            Fraction of ``min(overlap_width, overlap_height)`` by which to
            expand the intersection on each side before cropping.  Defaults to
            0.0 (exact intersection).  Positive values include a margin around
            the boundary.
        min_area_threshold:
            Minimum intersection area in degrees² for the overlap to be
            considered usable.  Default 1e-10 (≈ 0.3 m² at the Moon's
            equator, effectively "any non-zero overlap").  Increase this to
            reject pairs whose overlap is too small for reliable matching.

    Returns:
        ``(src_cropped, ref_cropped, intersection_bbox)``

        *src_cropped* and *ref_cropped* are numpy arrays covering the same
        geographic region.  *intersection_bbox* is the
        (min_lon, min_lat, max_lon, max_lat) of that shared region (before
        any buffer expansion; the expansion is applied to the crop only).

    Raises:
        NoOverlapError:
            When the intersection is empty or below ``min_area_threshold``,
            naming both footprints in the message.
        ValueError:
            If either bbox is malformed (min ≥ max).
    """
    _validate_bbox(src_bbox, "source")
    _validate_bbox(ref_bbox, "reference")

    # Compute exact intersection (no buffer) for area check
    exact_intersection = compute_intersection(src_bbox, ref_bbox, buffer_fraction=0.0)

    if exact_intersection is None:
        raise NoOverlapError(src_bbox, ref_bbox, None, min_area_threshold)

    area = _bbox_area(exact_intersection)
    if area < min_area_threshold:
        raise NoOverlapError(src_bbox, ref_bbox, exact_intersection, min_area_threshold)

    # Apply buffer to the crop window (expand slightly around true intersection)
    crop_bbox = compute_intersection(src_bbox, ref_bbox, buffer_fraction=buffer_fraction)
    # compute_intersection with buffer can produce a bbox that exceeds either
    # image's own footprint; crop_to_bbox() clamps pixel indices to [0, dim),
    # so no explicit clamping is needed here.

    logger.info(
        f"Overlap region: {_fmt(exact_intersection)} "
        f"({area:.6e} deg²). "
        f"Crop window (buffer={buffer_fraction:.3f}): {_fmt(crop_bbox)}"
    )

    src_cropped = crop_to_bbox(src_image, src_bbox, crop_bbox)
    ref_cropped = crop_to_bbox(ref_image, ref_bbox, crop_bbox)

    logger.info(
        f"Cropped source:    {src_image.shape} → {src_cropped.shape}"
    )
    logger.info(
        f"Cropped reference: {ref_image.shape} → {ref_cropped.shape}"
    )

    return src_cropped, ref_cropped, exact_intersection
