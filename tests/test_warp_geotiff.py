"""
Unit tests for georeferenced registered GeoTIFF creation and verification.
"""

import os
import tempfile
import pytest
import numpy as np
import rasterio
import rasterio.crs
import rasterio.transform
from pathlib import Path

from lumen.registration.warp import warp_image, create_registered_product


def test_warp_image_transforms_array(sample_image):
    """Test basic warp_image perspective transformation."""
    # Identity transform
    H_eye = np.eye(3, dtype=np.float32)
    warped = warp_image(sample_image, H_eye, sample_image.shape[:2])
    assert warped.shape == sample_image.shape[:2]
    assert np.allclose(sample_image, warped)

    # Translation transform
    H_trans = np.array([[1.0, 0.0, 10.0],
                        [0.0, 1.0, 5.0],
                        [0.0, 0.0, 1.0]], dtype=np.float32)
    warped_trans = warp_image(sample_image, H_trans, sample_image.shape[:2])
    assert warped_trans.shape == sample_image.shape[:2]
    assert not np.array_equal(sample_image, warped_trans)


def test_create_registered_product_writes_geotiff(sample_image):
    """
    Test that create_registered_product writes a valid GeoTIFF carrying
    spatial reference (CRS, transform) and metadata tags (sensor_pair, transform_type, RMSE).
    Confirms by re-opening the written file with rasterio and asserting valid CRS.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp:
        out_tif = tmp.name

    try:
        ref_image = np.zeros((256, 256), dtype=np.float32)
        H = np.eye(3, dtype=np.float32)
        custom_crs = "EPSG:4326"
        custom_transform = rasterio.transform.from_origin(142.0, -3.0, 0.0001, 0.0001)

        result = create_registered_product(
            source=sample_image,
            reference=ref_image,
            transform=H,
            output_path=out_tif,
            reference_crs=custom_crs,
            reference_transform=custom_transform,
            source_sensor="OHRC",
            ref_sensor="TMC2",
            transform_type="homography",
            rmse=0.342,
            metadata={"mission": "Chandrayaan-2", "orbit": "31073"}
        )

        assert os.path.exists(out_tif)
        assert result["warped_image"] is not None
        assert result["output_path"] == str(out_tif)

        # Open written GeoTIFF with rasterio and assert CRS, transform, and tags
        with rasterio.open(out_tif) as ds:
            assert ds.crs is not None, "GeoTIFF must have a non-None CRS"
            assert bool(ds.crs), f"GeoTIFF CRS must be valid, got {ds.crs}"
            assert ds.crs.to_string() == "EPSG:4326"
            assert ds.width == 256 and ds.height == 256
            assert ds.transform is not None

            tags = ds.tags()
            assert tags.get("sensor_pair") == "OHRC_TMC2"
            assert tags.get("transform_type") == "homography"
            assert float(tags.get("rmse")) == pytest.approx(0.342, rel=1e-3)
            assert tags.get("mission") == "Chandrayaan-2"
            assert tags.get("orbit") == "31073"

            # Check raster data
            data = ds.read(1)
            assert data.shape == (256, 256)
            assert data.dtype == np.float32
    finally:
        if os.path.exists(out_tif):
            os.remove(out_tif)
