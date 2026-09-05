"""
Tests for lumen.preprocess.orthorectify.

These tests cover:

1. resample_to_gsd / build_image_pyramid  (existing, now with real assertions)
2. orthorectify() with a synthetic GCP CSV + synthetic DEM
   - Asserts output is NOT pixel-identical to input
   - Asserts metadata fields are populated
3. orthorectify() with partial DEM coverage
   - Asserts partial_coverage=True and warning is emitted
4. orthorectify() with no DEM
   - Should still work (z=0 GCPs)
5. orthorectify() without 'gcp_csv_path' in metadata
   - Must raise MissingGeometryError with an informative message
"""

import csv
import io
import os
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lumen.preprocess.orthorectify import (
    MissingGeometryError,
    OrthorectifyResult,
    build_image_pyramid,
    orthorectify,
    resample_to_gsd,
)

# ──────────────────────────────────────────────
# Check rasterio availability early – skip the
# orthorectification tests cleanly if absent.
# ──────────────────────────────────────────────
try:
    import rasterio
    import rasterio.io
    import rasterio.transform
    import rasterio.crs
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

SKIP_NO_RASTERIO = pytest.mark.skipif(
    not HAS_RASTERIO,
    reason="rasterio not installed",
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def synthetic_image():
    """64 × 64 float32 image with non-uniform content (checkerboard + noise)."""
    np.random.seed(7)
    base = np.random.rand(64, 64).astype(np.float32) * 0.4
    # Add structure so resampling produces clearly different output
    checker = np.indices((64, 64)).sum(axis=0) % 8 < 4
    base[checker] += 0.5
    return base


@pytest.fixture(scope="module")
def synthetic_gcp_csv(tmp_path_factory):
    """
    Write a tiny GCP CSV that covers a 1° × 1° lon/lat patch near the
    lunar south pole.  The grid has one GCP per 16 pixels (4 × 4 = 16 GCPs
    over the 64 × 64 image).
    """
    tmp = tmp_path_factory.mktemp("gcp")
    csv_path = tmp / "test_gcps.csv"
    img_w, img_h = 64, 64
    step = 16
    lon0, lat0 = 24.0, -85.5
    # 1 deg longitude ≈ 0.02 deg per 16-pixel step in our synthetic image
    dlon_per_px = 1.0 / img_w
    dlat_per_px = 1.0 / img_h

    rows = [["Longitude", "Latitude", "Pixel", "Scan"]]
    for scan in range(0, img_h + 1, step):
        for pixel in range(0, img_w + 1, step):
            lon = lon0 + pixel * dlon_per_px
            lat = lat0 + scan * dlat_per_px
            rows.append([f"{lon:.7f}", f"{lat:.7f}", str(pixel), str(scan)])

    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)

    return str(csv_path)


@pytest.fixture(scope="module")
def synthetic_dem_full(tmp_path_factory):
    """
    A rasterio MemoryFile dataset that FULLY covers the image footprint
    (24.0°–25.0° lon, -85.5°–-84.5° lat).
    """
    if not HAS_RASTERIO:
        pytest.skip("rasterio not installed")

    dem_data = (np.random.rand(64, 64).astype(np.float32) * 500 + 1000)
    transform = rasterio.transform.from_bounds(23.5, -86.0, 25.5, -84.0, 64, 64)
    crs = rasterio.crs.CRS.from_epsg(4326)

    memfile = rasterio.io.MemoryFile()
    with memfile.open(
        driver="GTiff", height=64, width=64, count=1,
        dtype="float32", crs=crs, transform=transform
    ) as ds:
        ds.write(dem_data, 1)
    # Return the open memfile so caller can open it; caller is responsible for closing
    return memfile


@pytest.fixture(scope="module")
def synthetic_dem_partial(tmp_path_factory):
    """
    A rasterio MemoryFile dataset that covers ONLY the left half of the
    image footprint, forcing partial_coverage=True.
    """
    if not HAS_RASTERIO:
        pytest.skip("rasterio not installed")

    dem_data = (np.random.rand(64, 32).astype(np.float32) * 500 + 1000)
    transform = rasterio.transform.from_bounds(23.5, -86.0, 24.5, -84.0, 32, 64)
    crs = rasterio.crs.CRS.from_epsg(4326)

    memfile = rasterio.io.MemoryFile()
    with memfile.open(
        driver="GTiff", height=64, width=32, count=1,
        dtype="float32", crs=crs, transform=transform
    ) as ds:
        ds.write(dem_data, 1)
    return memfile


# ──────────────────────────────────────────────
# resample_to_gsd tests (unchanged helper)
# ──────────────────────────────────────────────

def test_resample_to_gsd_identity(synthetic_image):
    resampled, gsd = resample_to_gsd(synthetic_image, 1.0, 1.0)
    assert np.allclose(synthetic_image, resampled)
    assert gsd == 1.0


def test_resample_to_gsd_downsample(synthetic_image):
    resampled, gsd = resample_to_gsd(synthetic_image, 1.0, 2.0)
    assert resampled.shape[0] == synthetic_image.shape[0] // 2
    assert gsd == 2.0


def test_resample_to_gsd_upsample(synthetic_image):
    resampled, gsd = resample_to_gsd(synthetic_image, 2.0, 1.0)
    assert resampled.shape[0] == synthetic_image.shape[0] * 2
    assert gsd == 1.0


# ──────────────────────────────────────────────
# build_image_pyramid tests
# ──────────────────────────────────────────────

def test_build_image_pyramid_levels(synthetic_image):
    pyramid = build_image_pyramid(synthetic_image, num_levels=3, scale_factor=2.0)
    assert len(pyramid) == 3
    assert pyramid[0][1] == 1.0
    assert pyramid[1][1] == 2.0
    assert pyramid[2][1] == 4.0
    assert pyramid[1][0].shape[0] == synthetic_image.shape[0] // 2


# ──────────────────────────────────────────────
# MissingGeometryError tests
# ──────────────────────────────────────────────

def test_orthorectify_raises_when_gcp_missing(synthetic_image):
    """orthorectify() must raise MissingGeometryError when gcp_csv_path absent."""
    metadata = {}  # no gcp_csv_path
    with pytest.raises(MissingGeometryError, match="gcp_csv_path"):
        orthorectify(synthetic_image, metadata, dem_dataset=None, target_gsd_m=5.0)


def test_missing_geometry_error_is_actionable(synthetic_image):
    """The error message must mention what field to add and where."""
    metadata = {}
    with pytest.raises(MissingGeometryError) as exc_info:
        orthorectify(synthetic_image, metadata, dem_dataset=None, target_gsd_m=5.0)
    msg = str(exc_info.value)
    assert "parse_isda_geometry" in msg or "pds4_parser" in msg, (
        "Error should reference the parser that needs to be updated"
    )
    assert "gcp_csv_path" in msg


# ──────────────────────────────────────────────
# Full orthorectification tests (require rasterio)
# ──────────────────────────────────────────────

@SKIP_NO_RASTERIO
def test_orthorectify_output_not_identical_to_input(
    synthetic_image, synthetic_gcp_csv, synthetic_dem_full
):
    """
    The core correctness assertion: orthorectified output must NOT be
    pixel-identical to the input.  A real projection changes the pixel
    layout — even at the same resolution.
    """
    metadata = {"gcp_csv_path": synthetic_gcp_csv}
    with synthetic_dem_full.open() as dem_ds:
        result = orthorectify(
            synthetic_image, metadata, dem_dataset=dem_ds, target_gsd_m=1852.0
        )

    assert isinstance(result, OrthorectifyResult)
    assert result.image.dtype == np.float32
    assert result.image.ndim == 2

    # The output will have different spatial extent / shape than input
    # because GCPs map it to geographic coordinates.
    # Even if shapes happen to match: pixels MUST be rearranged.
    resized_input = synthetic_image
    out = result.image

    if resized_input.shape == out.shape:
        assert not np.array_equal(resized_input, out), (
            "orthorectify() returned an array pixel-identical to its input — "
            "this means no projection was applied."
        )

    # Output should not be all zeros (would mean the GCP warp produced empty output)
    assert out.max() > 0.0, "Orthorectified output is entirely zero — warp failed."


@SKIP_NO_RASTERIO
def test_orthorectify_result_has_transform_metadata(
    synthetic_image, synthetic_gcp_csv, synthetic_dem_full
):
    """Result transform dict must contain expected keys."""
    metadata = {"gcp_csv_path": synthetic_gcp_csv}
    with synthetic_dem_full.open() as dem_ds:
        result = orthorectify(
            synthetic_image, metadata, dem_dataset=dem_ds, target_gsd_m=1852.0
        )

    for key in ("crs", "gsd_m", "affine", "bbox_lonlat", "shape"):
        assert key in result.transform, f"Missing key '{key}' in result.transform"
    assert result.transform["gsd_m"] == 1852.0


@SKIP_NO_RASTERIO
def test_orthorectify_without_dem(synthetic_image, synthetic_gcp_csv):
    """orthorectify() must work when dem_dataset=None (z=0 GCPs)."""
    metadata = {"gcp_csv_path": synthetic_gcp_csv}
    result = orthorectify(
        synthetic_image, metadata, dem_dataset=None, target_gsd_m=1852.0
    )
    assert isinstance(result, OrthorectifyResult)
    assert result.image.ndim == 2


@SKIP_NO_RASTERIO
def test_orthorectify_partial_coverage_flagged(
    synthetic_image, synthetic_gcp_csv, synthetic_dem_partial
):
    """Partial DEM coverage must set partial_coverage=True and emit a warning."""
    metadata = {"gcp_csv_path": synthetic_gcp_csv}
    with synthetic_dem_partial.open() as dem_ds:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = orthorectify(
                synthetic_image, metadata, dem_dataset=dem_ds, target_gsd_m=1852.0
            )

    assert result.partial_coverage is True, (
        "partial_coverage should be True when DEM covers only part of the footprint"
    )
    assert result.coverage_fraction < 1.0
    assert len(result.warnings) > 0, "At least one warning string should be set"

    # A Python UserWarning should also have been raised
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) > 0, "No UserWarning was emitted for partial coverage"


@SKIP_NO_RASTERIO
def test_orthorectify_no_dem_overlap_emits_warning(
    synthetic_image, synthetic_gcp_csv, tmp_path
):
    """
    When the DEM has zero overlap with the image footprint, a warning must
    be emitted and orthorectification must still proceed (without DEM).
    """
    # DEM at completely different longitude
    dem_data = np.ones((32, 32), dtype=np.float32) * 1000
    transform = rasterio.transform.from_bounds(0.0, 0.0, 1.0, 1.0, 32, 32)
    crs = rasterio.crs.CRS.from_epsg(4326)

    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff", height=32, width=32, count=1,
            dtype="float32", crs=crs, transform=transform
        ) as dem_ds_write:
            dem_ds_write.write(dem_data, 1)

        with memfile.open() as dem_ds:
            metadata = {"gcp_csv_path": synthetic_gcp_csv}
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = orthorectify(
                    synthetic_image, metadata, dem_dataset=dem_ds, target_gsd_m=1852.0
                )

    assert result.partial_coverage is True
    assert result.coverage_fraction == 0.0
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert any("NO overlap" in str(w.message) for w in user_warnings), (
        "Expected a UserWarning mentioning 'NO overlap'"
    )


# ──────────────────────────────────────────────
# GCP z-elevation sampling tests
# ──────────────────────────────────────────────

@SKIP_NO_RASTERIO
def test_gcp_z_sampled_from_dem_gradient(synthetic_gcp_csv, tmp_path):
    """
    With a DEM that has a clear elevation gradient (min=0 m, max=4095 m),
    the GCP z-values used in orthorectify() must NOT all be 0.0.

    This is a regression guard for the DEM-sampling step.  It does NOT assert
    that output pixel positions are shifted by terrain (they aren't — see the
    module docstring on the 2-D polynomial z-limitation).  It asserts that
    _sample_dem_elevations() correctly reads the DEM and populates z.
    """
    from lumen.preprocess.orthorectify import _parse_gcp_csv, _sample_dem_elevations

    # Build a DEM with a strong elevation gradient (row * 100 m per row)
    dem_w, dem_h = 64, 64
    dem_arr = np.zeros((dem_h, dem_w), dtype=np.float32)
    for row in range(dem_h):
        dem_arr[row, :] = row * 100.0   # 0 m at top, 6300 m at bottom

    dem_bounds = (23.5, -86.0, 25.5, -84.0)  # fully covers GCP footprint
    dem_tf = rasterio.transform.from_bounds(*dem_bounds, dem_w, dem_h)
    dem_crs = rasterio.crs.CRS.from_epsg(4326)

    gcp_rows = _parse_gcp_csv(synthetic_gcp_csv)

    with rasterio.io.MemoryFile() as mf:
        with mf.open(driver="GTiff", height=dem_h, width=dem_w, count=1,
                     dtype="float32", crs=dem_crs, transform=dem_tf) as ds:
            ds.write(dem_arr, 1)

        with mf.open() as dem_ds:
            dem_bbox = (
                dem_ds.bounds.left, dem_ds.bounds.bottom,
                dem_ds.bounds.right, dem_ds.bounds.top,
            )
            warn_msgs: list = []
            elevations = _sample_dem_elevations(gcp_rows, dem_ds, dem_bbox, warn_msgs)

    assert len(elevations) == len(gcp_rows), (
        "Should return one elevation per GCP row"
    )
    assert any(z != 0.0 for z in elevations), (
        "All GCP z-values are 0.0 even though DEM has a strong elevation gradient. "
        "_sample_dem_elevations() is not sampling the DEM correctly."
    )
    assert not all(z == elevations[0] for z in elevations), (
        "All GCP z-values are identical — elevation gradient not being reflected. "
        "Sampling may be using a fixed point instead of per-GCP coordinates."
    )


@SKIP_NO_RASTERIO
def test_gcp_z_is_zero_without_dem(synthetic_gcp_csv):
    """
    When orthorectify() is called with dem_dataset=None, GCP z must stay 0.0
    throughout (no DEM sampling attempted).
    """
    from lumen.preprocess.orthorectify import _parse_gcp_csv

    gcp_rows = _parse_gcp_csv(synthetic_gcp_csv)

    # Verify that _parse_gcp_csv itself doesn't assign elevations
    for lon, lat, pixel, scan in gcp_rows:
        assert isinstance(lon, float)
        assert isinstance(lat, float)

    # Run full orthorectify without DEM and check the result flag
    import numpy as np
    img = np.random.rand(64, 64).astype(np.float32)
    metadata = {"gcp_csv_path": synthetic_gcp_csv}
    result = orthorectify(img, metadata, dem_dataset=None, target_gsd_m=1852.0)

    # When no DEM is supplied, the result transform must NOT claim elevations were sampled
    assert result.transform.get("gcp_elevations_sampled") is False, (
        "gcp_elevations_sampled should be False when no DEM is provided"
    )

