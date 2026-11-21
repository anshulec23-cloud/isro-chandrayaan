"""
Tests for lumen.preprocess.overlap_crop

All tests use synthetic data (no real PDS4 files).

Geometry used throughout
------------------------
Image A:  100 rows × 200 cols, covers lon [10.0, 12.0], lat [20.0, 21.0]
           lon_per_px = 2.0/200 = 0.01 deg/px
           lat_per_px = 1.0/100 = 0.01 deg/px

Image B:  100 rows × 200 cols, covers lon [11.0, 13.0], lat [20.5, 21.5]
           lon_per_px = 0.01 deg/px
           lat_per_px = 0.01 deg/px

Exact intersection:  lon [11.0, 12.0], lat [20.5, 21.0]
  width  = 1.0 deg  → 100 px in A, 100 px in B
  height = 0.5 deg  →  50 px in A,  50 px in B

Pixel mapping (north-up, row 0 = max_lat):

  Image A (max_lat=21.0):
    col_start = (11.0 - 10.0) / 0.01 = 100
    col_end   = (12.0 - 10.0) / 0.01 = 200
    row_start = (21.0 - 21.0) / 0.01 =   0
    row_end   = (21.0 - 20.5) / 0.01 =  50
    → crop A[0:50, 100:200]  → shape (50, 100)

  Image B (max_lat=21.5):
    col_start = (11.0 - 11.0) / 0.01 =   0
    col_end   = (12.0 - 11.0) / 0.01 = 100
    row_start = (21.5 - 21.0) / 0.01 =  50
    row_end   = (21.5 - 20.5) / 0.01 = 100
    → crop B[50:100, 0:100]  → shape (50, 100)
"""

import math
import pytest
import numpy as np

from lumen.preprocess.overlap_crop import (
    NoOverlapError,
    compute_intersection,
    crop_to_bbox,
    crop_pair_to_overlap,
)

# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

BBOX_A = (10.0, 20.0, 12.0, 21.0)   # lon [10,12], lat [20,21]
BBOX_B = (11.0, 20.5, 13.0, 21.5)   # lon [11,13], lat [20.5,21.5]
EXACT_INTERSECTION = (11.0, 20.5, 12.0, 21.0)

# Disjoint bboxes — no overlap at all
BBOX_C = (50.0, 50.0, 60.0, 60.0)
BBOX_D = (70.0, 70.0, 80.0, 80.0)

# Touching at a single edge (zero-area intersection)
BBOX_E = (10.0, 20.0, 11.0, 21.0)
BBOX_F = (11.0, 20.0, 12.0, 21.0)


def _make_image(rows: int, cols: int, fill: float = 1.0) -> np.ndarray:
    """Return a constant float32 array."""
    return np.full((rows, cols), fill, dtype=np.float32)


def _make_gradient_image(rows: int, cols: int) -> np.ndarray:
    """Return an image where each pixel value = col index, for easy crop verification."""
    img = np.tile(np.arange(cols, dtype=np.float32), (rows, 1))
    return img


# ---------------------------------------------------------------------------
# compute_intersection
# ---------------------------------------------------------------------------

class TestComputeIntersection:

    def test_partial_overlap_correct_bbox(self):
        inter = compute_intersection(BBOX_A, BBOX_B)
        assert inter is not None
        assert inter == pytest.approx(EXACT_INTERSECTION)

    def test_no_overlap_returns_none(self):
        assert compute_intersection(BBOX_C, BBOX_D) is None

    def test_touching_edge_returns_none(self):
        """Zero-width intersection is treated as no overlap."""
        result = compute_intersection(BBOX_E, BBOX_F)
        # width = 11.0 - 11.0 = 0, so should be None (min >= max)
        assert result is None

    def test_identical_bboxes_returns_same(self):
        inter = compute_intersection(BBOX_A, BBOX_A)
        assert inter == pytest.approx(BBOX_A)

    def test_buffer_expands_intersection(self):
        inter_exact = compute_intersection(BBOX_A, BBOX_B, buffer_fraction=0.0)
        inter_buf   = compute_intersection(BBOX_A, BBOX_B, buffer_fraction=0.1)
        assert inter_exact is not None and inter_buf is not None
        # Buffer should expand on each side
        assert inter_buf[0] < inter_exact[0]   # min_lon smaller
        assert inter_buf[1] < inter_exact[1]   # min_lat smaller
        assert inter_buf[2] > inter_exact[2]   # max_lon larger
        assert inter_buf[3] > inter_exact[3]   # max_lat larger

    def test_negative_buffer_shrinks_intersection(self):
        inter_exact = compute_intersection(BBOX_A, BBOX_B, buffer_fraction=0.0)
        inter_shrunk = compute_intersection(BBOX_A, BBOX_B, buffer_fraction=-0.1)
        assert inter_exact is not None and inter_shrunk is not None
        assert inter_shrunk[0] > inter_exact[0]
        assert inter_shrunk[2] < inter_exact[2]


# ---------------------------------------------------------------------------
# crop_to_bbox
# ---------------------------------------------------------------------------

class TestCropToBbox:

    def test_partial_overlap_image_a(self):
        """Crop image A to the exact intersection bbox."""
        img_a = _make_image(100, 200)
        cropped = crop_to_bbox(img_a, BBOX_A, EXACT_INTERSECTION)
        # Expected: rows 0:50, cols 100:200 → (50, 100)
        assert cropped.shape == (50, 100)

    def test_partial_overlap_image_b(self):
        """Crop image B to the exact intersection bbox."""
        img_b = _make_image(100, 200)
        cropped = crop_to_bbox(img_b, BBOX_B, EXACT_INTERSECTION)
        # Expected: rows 50:100, cols 0:100 → (50, 100)
        assert cropped.shape == (50, 100)

    def test_crop_to_self_returns_full_image(self):
        """Cropping to the image's own bbox should return the full array."""
        img = _make_image(100, 200, fill=7.0)
        cropped = crop_to_bbox(img, BBOX_A, BBOX_A)
        assert cropped.shape == img.shape
        np.testing.assert_array_equal(cropped, img)

    def test_pixel_values_are_correct_slice(self):
        """Content of the crop must match the exact pixel slice of the source."""
        img_a = _make_gradient_image(100, 200)  # col values 0..199
        cropped = crop_to_bbox(img_a, BBOX_A, EXACT_INTERSECTION)
        # cols 100:200 → values 100..199
        assert cropped.shape == (50, 100)
        np.testing.assert_array_equal(cropped[0, :], np.arange(100, 200, dtype=np.float32))

    def test_non_overlapping_target_raises(self):
        """Crop with a target that doesn't intersect the image should raise ValueError."""
        img_a = _make_image(100, 200)
        with pytest.raises(ValueError, match="empty pixel region"):
            crop_to_bbox(img_a, BBOX_A, BBOX_C)


# ---------------------------------------------------------------------------
# crop_pair_to_overlap  — the main end-to-end function
# ---------------------------------------------------------------------------

class TestCropPairToOverlap:

    def test_partial_overlap_both_shapes_equal(self):
        """Both cropped images should have identical shapes (same geographic region)."""
        img_a = _make_image(100, 200, fill=1.0)
        img_b = _make_image(100, 200, fill=2.0)

        src_c, ref_c, inter = crop_pair_to_overlap(img_a, BBOX_A, img_b, BBOX_B)

        assert src_c.shape == ref_c.shape, (
            f"Cropped shapes must match: src={src_c.shape}, ref={ref_c.shape}"
        )

    def test_partial_overlap_correct_intersection_bbox(self):
        """Returned intersection bbox must match the geometric expectation."""
        img_a = _make_image(100, 200)
        img_b = _make_image(100, 200)

        _, _, inter = crop_pair_to_overlap(img_a, BBOX_A, img_b, BBOX_B)

        assert inter == pytest.approx(EXACT_INTERSECTION), (
            f"Expected intersection {EXACT_INTERSECTION}, got {inter}"
        )

    def test_partial_overlap_correct_crop_size(self):
        """Cropped output dimensions must correspond to the intersection region."""
        img_a = _make_image(100, 200)
        img_b = _make_image(100, 200)

        src_c, ref_c, inter = crop_pair_to_overlap(img_a, BBOX_A, img_b, BBOX_B)

        # Intersection: width=1.0 deg, height=0.5 deg
        # Image A: lon_per_px = 0.01, lat_per_px = 0.01
        # Expected crop: (50, 100)
        assert src_c.shape == (50, 100), f"src crop shape: {src_c.shape}"
        assert ref_c.shape == (50, 100), f"ref crop shape: {ref_c.shape}"

    def test_pixel_content_is_correct_region(self):
        """Verify pixel VALUES, not just shape, correspond to the right geographic slice."""
        # Image A: fill each row with its row index (0..99)
        img_a = np.tile(np.arange(100, dtype=np.float32).reshape(100, 1), (1, 200))
        img_b = _make_image(100, 200, fill=0.0)

        src_c, _, _ = crop_pair_to_overlap(img_a, BBOX_A, img_b, BBOX_B)
        # Intersection maps to rows 0:50 of image A → row values 0..49
        expected_rows = np.arange(50, dtype=np.float32)
        np.testing.assert_array_equal(src_c[:, 0], expected_rows)

    def test_no_overlap_raises_no_overlap_error(self):
        """Completely disjoint footprints must raise NoOverlapError."""
        img_c = _make_image(100, 100)
        img_d = _make_image(100, 100)

        with pytest.raises(NoOverlapError) as exc_info:
            crop_pair_to_overlap(img_c, BBOX_C, img_d, BBOX_D)

        err = exc_info.value
        # Error must identify both footprints
        assert err.src_bbox == BBOX_C
        assert err.ref_bbox == BBOX_D
        assert err.intersection is None
        # Human-readable message should mention both bboxes
        assert "source" in str(err).lower() or "50" in str(err)
        assert "reference" in str(err).lower() or "70" in str(err)

    def test_tiny_overlap_below_threshold_raises(self):
        """Overlap that exists but is below min_area_threshold must raise NoOverlapError."""
        # These bboxes overlap by 0.001 × 0.001 = 1e-6 deg²
        bbox_x = (10.0, 20.0, 10.5, 20.5)
        bbox_y = (10.499, 20.499, 11.0, 21.0)
        img_x = _make_image(100, 100)
        img_y = _make_image(100, 100)

        with pytest.raises(NoOverlapError) as exc_info:
            crop_pair_to_overlap(
                img_x, bbox_x, img_y, bbox_y,
                min_area_threshold=1.0,   # require ≥ 1 deg² → will fail
            )

        err = exc_info.value
        assert err.intersection is not None   # intersection exists but is tiny
        assert err.min_area_threshold == 1.0

    def test_buffer_expands_crop(self):
        """buffer_fraction > 0 should make the cropped arrays larger."""
        img_a = _make_image(100, 200)
        img_b = _make_image(100, 200)

        src_c_exact, _, _ = crop_pair_to_overlap(img_a, BBOX_A, img_b, BBOX_B,
                                                  buffer_fraction=0.0)
        src_c_buf,   _, _ = crop_pair_to_overlap(img_a, BBOX_A, img_b, BBOX_B,
                                                  buffer_fraction=0.2)

        # With a positive buffer the crop window is wider/taller
        assert src_c_buf.shape[0] >= src_c_exact.shape[0]
        assert src_c_buf.shape[1] >= src_c_exact.shape[1]

    def test_3d_image_preserved(self):
        """3-D (H, W, C) images must be cropped along spatial axes only."""
        img_a = np.ones((100, 200, 3), dtype=np.float32)
        img_b = np.ones((100, 200, 3), dtype=np.float32) * 2.0

        src_c, ref_c, _ = crop_pair_to_overlap(img_a, BBOX_A, img_b, BBOX_B)

        assert src_c.shape[2] == 3
        assert ref_c.shape[2] == 3
        assert src_c.shape[:2] == ref_c.shape[:2]

    def test_no_overlap_error_message_names_footprints(self):
        """The NoOverlapError string must explicitly name both bounding boxes."""
        img_c = _make_image(50, 50)
        img_d = _make_image(50, 50)

        with pytest.raises(NoOverlapError) as exc_info:
            crop_pair_to_overlap(img_c, BBOX_C, img_d, BBOX_D)

        msg = str(exc_info.value)
        # Message must contain coordinates from both bboxes
        assert "50" in msg or "60" in msg   # BBOX_C bounds
        assert "70" in msg or "80" in msg   # BBOX_D bounds
        assert "overlap" in msg.lower() or "intersect" in msg.lower()
