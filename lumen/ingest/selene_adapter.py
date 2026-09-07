"""
Adapter for JAXA SELENE (Kaguya) Terrain Camera (TC) PDS3 products.

Provides parsing for PDS3 detached labels (.lbl) and memory-safe reading
of map-projected (Simple Cylindrical / EPSG:4326) orthorectified binary rasters (.img).
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
import rasterio
from rasterio.transform import from_bounds

logger = logging.getLogger(__name__)

__all__ = [
    "parse_selene_pds3",
    "load_selene_image",
    "export_selene_geotiff",
    "is_selene_product",
]


def is_selene_product(path: Union[str, Path]) -> bool:
    """Check if the path points to a SELENE/Kaguya product label."""
    p = Path(path)
    if p.suffix.lower() == ".lbl":
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(1024)
                return "SELENE" in head or "DATA_SET_ID" in head
        except Exception:
            return False
    return False


def parse_selene_pds3(lbl_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Parse a JAXA SELENE Terrain Camera PDS3 .lbl file.

    Extracts geographic bounds, map projection parameters, image dimensions,
    and radiometric scale factors.
    """
    lbl_p = Path(lbl_path)
    if not lbl_p.exists():
        raise FileNotFoundError(f"SELENE label not found: {lbl_p}")

    meta: Dict[str, Any] = {
        "mission": "SELENE",
        "sensor": "SELENE_TC",
        "instrument_name": "TERRAIN CAMERA",
        "instrument_host": "SELENE MAIN ORBITER (KAGUYA)",
        "lbl_path": str(lbl_p.resolve()),
        "is_orthorectified": True,
        "projection": "SIMPLE CYLINDRICAL",
        "crs": "EPSG:4326",
    }

    with open(lbl_p, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    def find_val(pattern: str, default=None, cast_fn=str):
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            val_str = m.group(1).strip()
            # Strip PDS unit markers like <deg>, <km>, etc.
            val_str = re.sub(r"<[^>]+>", "", val_str).strip()
            val_str = val_str.strip('"').strip("'")
            try:
                return cast_fn(val_str)
            except Exception:
                return val_str
        return default

    # Basic Product Identifiers
    meta["product_id"] = find_val(r"PRODUCT_ID\s*=\s*([^\r\n]+)", "SELENE_TC")
    meta["data_set_id"] = find_val(r"DATA_SET_ID\s*=\s*([^\r\n]+)", "")
    meta["file_name"] = find_val(r"FILE_NAME\s*=\s*([^\r\n]+)", "")

    # Resolve binary image path
    img_name = meta["file_name"] or f"{lbl_p.stem}.img"
    img_path = lbl_p.parent / img_name
    if not img_path.exists():
        # Case-insensitive fallback
        for candidate in lbl_p.parent.glob("*.[iI][mM][gG]"):
            if candidate.stem.lower() == lbl_p.stem.lower():
                img_path = candidate
                break
    meta["image_path"] = str(img_path.resolve())

    # Dimensions
    meta["lines"] = find_val(r"LINES\s*=\s*([0-9]+)", 12288, int)
    meta["samples"] = find_val(r"LINE_SAMPLES\s*=\s*([0-9]+)", 12288, int)
    meta["sample_bits"] = find_val(r"SAMPLE_BITS\s*=\s*([0-9]+)", 16, int)
    meta["sample_type"] = find_val(r"SAMPLE_TYPE\s*=\s*([^\r\n]+)", "MSB_UNSIGNED_INTEGER")
    meta["scaling_factor"] = find_val(r"SCALING_FACTOR\s*=\s*([0-9\.\-eE]+)", 0.0183, float)
    meta["offset"] = find_val(r"OFFSET\s*=\s*([0-9\.\-eE]+)", 0.0, float)

    # Geographic Bounds (Simple Cylindrical)
    ul_lat = find_val(r"UPPER_LEFT_LATITUDE\s*=\s*([0-9\.\-]+)", -6.0, float)
    ul_lon = find_val(r"UPPER_LEFT_LONGITUDE\s*=\s*([0-9\.\-]+)", 141.0, float)
    lr_lat = find_val(r"LOWER_RIGHT_LATITUDE\s*=\s*([0-9\.\-]+)", -9.0, float)
    lr_lon = find_val(r"LOWER_RIGHT_LONGITUDE\s*=\s*([0-9\.\-]+)", 144.0, float)

    meta["max_latitude"] = find_val(r"MAXIMUM_LATITUDE\s*=\s*([0-9\.\-]+)", max(ul_lat, lr_lat), float)
    meta["min_latitude"] = find_val(r"MINIMUM_LATITUDE\s*=\s*([0-9\.\-]+)", min(ul_lat, lr_lat), float)
    meta["min_longitude"] = find_val(r"WESTERNMOST_LONGITUDE\s*=\s*([0-9\.\-]+)", min(ul_lon, lr_lon), float)
    meta["max_longitude"] = find_val(r"EASTERNMOST_LONGITUDE\s*=\s*([0-9\.\-]+)", max(ul_lon, lr_lon), float)

    meta["bbox_lonlat"] = (
        meta["min_longitude"],
        meta["min_latitude"],
        meta["max_longitude"],
        meta["max_latitude"],
    )

    # Resolution & GSD
    # MAP_SCALE in km/pixel -> convert to metres
    map_scale_km = find_val(r"MAP_SCALE\s*=\s*([0-9\.\-eE]+)", 0.007403, float)
    meta["pixel_resolution"] = map_scale_km * 1000.0  # in metres (~7.40 m/px)
    meta["map_resolution_px_deg"] = find_val(r"MAP_RESOLUTION\s*=\s*([0-9\.\-]+)", 4096.0, float)

    # Standard Photometric Observation Geometry for SELENE Orthomap
    meta["incidence_angle"] = 30.0
    meta["emission_angle"] = 0.0
    meta["phase_angle"] = 30.0
    meta["solar_elevation"] = 60.0  # 90 - incidence
    meta["solar_azimuth"] = 0.0
    meta["instrument_elevation"] = 90.0

    return meta


def load_selene_image(
    lbl_path: Union[str, Path],
    bbox_crop: Optional[Tuple[float, float, float, float]] = None,
    dtype: str = "float32",
) -> Tuple[np.ndarray, Tuple[float, float, float, float]]:
    """
    Load a SELENE Terrain Camera image, optionally cropping to a target lon/lat bounding box.

    Parameters
    ----------
    lbl_path: Path to the .lbl file.
    bbox_crop: Optional (min_lon, min_lat, max_lon, max_lat) in EPSG:4326.
    dtype: Output numpy array dtype ('float32' or 'uint16').

    Returns
    -------
    (image_array, effective_bbox_lonlat)
    """
    meta = parse_selene_pds3(lbl_path)
    img_path = Path(meta["image_path"])
    if not img_path.exists():
        raise FileNotFoundError(f"Binary image file not found: {img_path}")

    lines = meta["lines"]
    samples = meta["samples"]

    # Read binary array via memory map (Big-endian unsigned 16-bit)
    raw_mmap = np.memmap(img_path, dtype=">u2", mode="r", shape=(lines, samples))

    if bbox_crop is None:
        arr = np.array(raw_mmap, dtype=np.float32 if dtype == "float32" else np.uint16)
        return arr, meta["bbox_lonlat"]

    # Compute line/sample window from geographic bounding box
    min_lon_full, min_lat_full, max_lon_full, max_lat_full = meta["bbox_lonlat"]
    c_min_lon, c_min_lat, c_max_lon, c_max_lat = bbox_crop

    # Clamp crop to product bounds
    i_min_lon = max(min_lon_full, c_min_lon)
    i_max_lon = min(max_lon_full, c_max_lon)
    i_min_lat = max(min_lat_full, c_min_lat)
    i_max_lat = min(max_lat_full, c_max_lat)

    if i_min_lon >= i_max_lon or i_min_lat >= i_max_lat:
        raise ValueError(
            f"Requested crop {bbox_crop} does not intersect SELENE product {meta['bbox_lonlat']}"
        )

    # Simple Cylindrical pixel mapping:
    # Row 0 is max_latitude, Row lines-1 is min_latitude
    # Col 0 is min_longitude, Col samples-1 is max_longitude
    px_per_deg_lat = lines / (max_lat_full - min_lat_full)
    px_per_deg_lon = samples / (max_lon_full - min_lon_full)

    row_start = int(np.clip((max_lat_full - i_max_lat) * px_per_deg_lat, 0, lines - 1))
    row_end = int(np.clip((max_lat_full - i_min_lat) * px_per_deg_lat, row_start + 1, lines))
    col_start = int(np.clip((i_min_lon - min_lon_full) * px_per_deg_lon, 0, samples - 1))
    col_end = int(np.clip((i_max_lon - min_lon_full) * px_per_deg_lon, col_start + 1, samples))

    logger.info(
        f"Cropping SELENE window: rows [{row_start}:{row_end}], cols [{col_start}:{col_end}] "
        f"for lon [{i_min_lon:.4f}, {i_max_lon:.4f}], lat [{i_min_lat:.4f}, {i_max_lat:.4f}]"
    )

    cropped = np.array(raw_mmap[row_start:row_end, col_start:col_end], dtype=np.float32 if dtype == "float32" else np.uint16)
    effective_bbox = (i_min_lon, i_min_lat, i_max_lon, i_max_lat)

    return cropped, effective_bbox


def export_selene_geotiff(
    lbl_path: Union[str, Path],
    out_geotiff_path: Union[str, Path],
    bbox_crop: Optional[Tuple[float, float, float, float]] = None,
) -> Path:
    """
    Convert a SELENE PDS3 image into a standard georeferenced GeoTIFF (EPSG:4326).
    """
    out_p = Path(out_geotiff_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    arr, (min_lon, min_lat, max_lon, max_lat) = load_selene_image(
        lbl_path, bbox_crop=bbox_crop, dtype="uint16"
    )

    h, w = arr.shape
    transform = from_bounds(min_lon, min_lat, max_lon, max_lat, w, h)

    with rasterio.open(
        out_p,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype=arr.dtype,
        crs="EPSG:4326",
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(arr, 1)

    logger.info(f"Wrote SELENE GeoTIFF: {out_p} ({w}x{h}, bbox={min_lon, min_lat, max_lon, max_lat})")
    return out_p
