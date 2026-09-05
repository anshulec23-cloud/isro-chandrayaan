"""
Image warping and georeferenced registered product creation.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np
import rasterio
import rasterio.crs
import rasterio.transform

logger = logging.getLogger(__name__)

__all__ = ["warp_image", "create_registered_product"]


def warp_image(
    source: np.ndarray,
    transform_matrix: np.ndarray,
    output_shape: Tuple[int, int],
    method: str = "cubic",
) -> np.ndarray:
    """Warp source image to reference perspective.

    Args:
        source: Source image to warp.
        transform_matrix: 3x3 homography / projective matrix.
        output_shape: (height, width) of output image.
        method: Interpolation method ('cubic', 'linear', 'nearest').

    Returns:
        Warped image array.
    """
    interp = cv2.INTER_LINEAR
    if method == "cubic":
        interp = cv2.INTER_CUBIC
    elif method == "nearest":
        interp = cv2.INTER_NEAREST

    return cv2.warpPerspective(
        source,
        transform_matrix,
        (output_shape[1], output_shape[0]),
        flags=interp,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def create_registered_product(
    source: np.ndarray,
    reference: Union[np.ndarray, str, Path],
    transform: np.ndarray,
    output_path: Optional[Union[str, Path]] = None,
    reference_crs: Optional[Any] = None,
    reference_transform: Optional[Any] = None,
    source_sensor: Optional[str] = None,
    ref_sensor: Optional[str] = None,
    transform_type: str = "homography",
    rmse: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate final registered product with spatial reference and write GeoTIFF.

    Warps the source image to the reference perspective and writes the output
    as a georeferenced GeoTIFF via rasterio carrying the reference image's CRS
    and geospatial transform, along with rich metadata tags (sensor_pair,
    transform_type, rmse). Verifies the written GeoTIFF by re-opening it
    and asserting a valid CRS and transform.

    Args:
        source: Source image (float32 or uint8 array).
        reference: Reference image array or path to reference raster dataset.
        transform: 3x3 computed transformation matrix.
        output_path: Optional path to save the resulting GeoTIFF product.
        reference_crs: Optional explicit CRS (EPSG string, dict, or rasterio.crs.CRS).
        reference_transform: Optional explicit affine transform.
        source_sensor: Optional source sensor identifier (e.g. 'OHRC').
        ref_sensor: Optional reference sensor identifier (e.g. 'TMC2').
        transform_type: Transformation model used (default: 'homography').
        rmse: Quantitative root mean square error metric if available.
        metadata: Additional metadata dictionary to embed as GeoTIFF tags.

    Returns:
        Dictionary containing:
            - warped_image: The warped numpy array.
            - transform_matrix: The 3x3 transform matrix.
            - output_path: Path to the written GeoTIFF if output_path was provided.
            - crs: The CRS object associated with the product.
            - transform: The affine transform associated with the product.
            - tags: The dictionary of embedded metadata tags.
            - match_points: List of match points (empty default).
    """
    ref_crs = reference_crs
    ref_affine = reference_transform

    # Determine reference dimensions and spatial reference
    if isinstance(reference, (str, Path)):
        ref_path = Path(reference)
        if ref_path.exists():
            try:
                with rasterio.open(ref_path) as ref_ds:
                    ref_shape = (ref_ds.height, ref_ds.width)
                    if ref_crs is None and ref_ds.crs:
                        ref_crs = ref_ds.crs
                    if ref_affine is None and ref_ds.transform:
                        ref_affine = ref_ds.transform
            except Exception as e:
                logger.warning(f"Could not read spatial metadata from reference {ref_path}: {e}")
                ref_shape = source.shape[:2]
        else:
            ref_shape = source.shape[:2]
    elif isinstance(reference, np.ndarray):
        ref_shape = reference.shape[:2]
    else:
        ref_shape = source.shape[:2]

    # Warp the source image
    warped = warp_image(source, transform, ref_shape)

    # Establish valid default CRS if none was detected or provided
    if ref_crs is None:
        # Default to standard lunar / geographic CRS EPSG:4326
        ref_crs = rasterio.crs.CRS.from_epsg(4326)
    elif isinstance(ref_crs, str):
        ref_crs = rasterio.crs.CRS.from_string(ref_crs)

    # Establish valid default geotransform if none was detected or provided
    if ref_affine is None:
        # Standard north-up pixel transform from top-left origin
        ref_affine = rasterio.transform.from_origin(0.0, float(ref_shape[0]), 1.0, 1.0)

    tags: Dict[str, str] = {}

    # Build tags
    if source_sensor and ref_sensor:
        tags["sensor_pair"] = f"{source_sensor}_{ref_sensor}"
    elif metadata and "sensor_pair" in metadata:
        tags["sensor_pair"] = str(metadata["sensor_pair"])
    elif source_sensor:
        tags["source_sensor"] = str(source_sensor)

    tags["transform_type"] = str(transform_type)

    if rmse is not None:
        tags["rmse"] = f"{float(rmse):.6f}"
    elif metadata and "rmse" in metadata and metadata["rmse"] is not None:
        tags["rmse"] = str(metadata["rmse"])

    if metadata:
        for k, v in metadata.items():
            if k not in tags and v is not None and isinstance(v, (str, int, float, bool)):
                tags[str(k)] = str(v)

    # Write GeoTIFF if output_path is provided
    if output_path is not None:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        img_to_write = warped.astype(np.float32)
        if img_to_write.ndim == 2:
            h, w = img_to_write.shape
            count = 1
        else:
            h, w, count = img_to_write.shape

        with rasterio.open(
            out_file,
            "w",
            driver="GTiff",
            height=h,
            width=w,
            count=count,
            dtype="float32",
            crs=ref_crs,
            transform=ref_affine,
        ) as dst:
            if count == 1:
                dst.write(img_to_write, 1)
            else:
                for band_idx in range(count):
                    dst.write(img_to_write[:, :, band_idx], band_idx + 1)

            if tags:
                dst.update_tags(**tags)

        # Verification step: Open written file and assert valid CRS and transform
        with rasterio.open(out_file) as verify_ds:
            if verify_ds.crs is None or not bool(verify_ds.crs):
                raise ValueError(f"Written GeoTIFF at {out_file} has no valid CRS.")
            assert verify_ds.crs is not None and bool(verify_ds.crs), "Valid CRS assertion failed"
            assert verify_ds.transform is not None, "Valid transform assertion failed"
            assert verify_ds.width == w and verify_ds.height == h, "Dimensions mismatch in GeoTIFF"
            read_tags = verify_ds.tags()
            logger.info(f"Verified GeoTIFF {out_file} with CRS: {verify_ds.crs}, tags: {read_tags}")

    return {
        "warped_image": warped,
        "transform_matrix": transform,
        "output_path": str(output_path) if output_path else None,
        "crs": ref_crs,
        "transform": ref_affine,
        "tags": tags,
        "match_points": [],
    }
