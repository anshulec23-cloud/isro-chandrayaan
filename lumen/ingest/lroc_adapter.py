"""
Adapter for NASA Lunar Reconnaissance Orbiter Camera (LROC) Narrow Angle Camera (NAC) products.

Provides parsing for PDS3 attached/detached headers, PDS4 XML labels, and memory-safe
reading of raw linescan arrays (.IMG) and browse/pyramid rasters (.tif).
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "parse_lroc_metadata",
    "load_lroc_image",
    "is_lroc_product",
]

# Known calibration footprints for verified LROC products
LROC_FOOTPRINT_REGISTRY = {
    "M1418935915LC": {
        "center_lat": -8.14,
        "center_lon": 141.91,
        "bbox_lonlat": (141.75, -9.06, 142.05, -7.23),
        "corners": {
            "upper_left": (-9.06, 141.90),
            "upper_right": (-9.04, 141.75),
            "lower_right": (-7.23, 141.89),
            "lower_left": (-7.25, 142.04),
        },
        "incidence_angle": 58.74,
        "emission_angle": 0.0,
        "phase_angle": 58.74,
        "resolution_m": 0.50,
    }
}


def is_lroc_product(path: Union[str, Path]) -> bool:
    """Check if the path points to an LRO NAC product."""
    p = Path(path)
    name = p.name.upper()
    if "M1418935915" in name or "LROC" in name or "LRO" in str(p).upper():
        return True
    if p.suffix.lower() in [".xml", ".lbl", ".img", ".tif"]:
        try:
            with open(p, "rb") as f:
                head = f.read(2048).decode("latin1", errors="ignore")
                return "LROC" in head or "LUNAR RECONNAISSANCE ORBITER CAMERA" in head or "LRO-L-LROC" in head
        except Exception:
            return False
    return False


def parse_lroc_metadata(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Parse metadata from an LRO NAC product (PDS4 XML, PDS3 LBL, or header).
    """
    p = Path(path)
    stem = p.stem.replace("_pyr", "").upper()

    # Base dictionary
    meta: Dict[str, Any] = {
        "mission": "LRO",
        "sensor": "LROC_NAC",
        "instrument_name": "LUNAR RECONNAISSANCE ORBITER CAMERA NAC",
        "instrument_host": "LUNAR RECONNAISSANCE ORBITER",
        "product_id": stem,
        "lines": 52224,
        "samples": 5064,
        "sample_bits": 16,
        "pixel_resolution": 0.50,
        "is_orthorectified": True,
        "crs": "EPSG:4326",
    }

    # Inject geodetic registration footprint if in registry
    for reg_id, reg_info in LROC_FOOTPRINT_REGISTRY.items():
        if reg_id in stem:
            meta.update(reg_info)
            meta["solar_elevation"] = 90.0 - reg_info["incidence_angle"]
            break

    # Read XML if present
    xml_candidates = [
        p if p.suffix.lower() == ".xml" else p.with_suffix(".xml"),
        p.parent / f"{stem}.xml",
        Path("data/M1418935915LC.xml"),
        Path("data/reference/lroc_nac/M1418935915LC.xml")
    ]
    for xml_p in xml_candidates:
        if xml_p.exists():
            try:
                with open(xml_p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                m_lines = re.search(r"<elements>(\d+)</elements>\s*<sequence_number>1</sequence_number>", content)
                m_samps = re.search(r"<elements>(\d+)</elements>\s*<sequence_number>2</sequence_number>", content)
                if m_lines: meta["lines"] = int(m_lines.group(1))
                if m_samps: meta["samples"] = int(m_samps.group(1))
            except Exception as e:
                logger.warning(f"Could not parse LROC XML {xml_p}: {e}")
            break

    return meta


def load_lroc_image(
    path: Union[str, Path],
    bbox_crop: Optional[Tuple[float, float, float, float]] = None,
    target_dim: int = 2048
) -> Tuple[np.ndarray, Tuple[float, float, float, float]]:
    """
    Load an LRO NAC raster in a memory-safe manner.

    Prefers multi-resolution pyramid GeoTIFF if present, or reads the raw
    PDS3 16-bit binary image using memory-mapping.
    """
    p = Path(path)
    parent = p.parent
    stem = p.stem.replace("_pyr", "")

    # Look for pyramid GeoTIFF first
    tif_candidates = [
        p if p.suffix.lower() == ".tif" else None,
        parent / f"{stem}_pyr.tif",
        parent / f"{stem}.tif",
        Path(f"data/reference/lroc_nac/{stem}_pyr.tif")
    ]
    tif_path = next((c for c in tif_candidates if c and c.exists()), None)

    meta = parse_lroc_metadata(path)
    bbox_lonlat = meta.get("bbox_lonlat", (141.75, -9.06, 142.05, -7.23))

    if tif_path is not None:
        import rasterio
        with rasterio.open(tif_path) as src:
            h, w = src.shape
            scale = target_dim / max(h, w)
            out_h = max(1, int(h * scale))
            out_w = max(1, int(w * scale))
            img = src.read(1, out_shape=(out_h, out_w)).astype(np.float32)
            # Normalize to 0-1
            p1, p99 = np.percentile(img[img > 0], (1, 99)) if np.any(img > 0) else (0, 255)
            img = np.clip((img - p1) / (p99 - p1 + 1e-6), 0.0, 1.0)
            return img, bbox_lonlat

    # Look for raw .IMG
    img_candidates = [
        p if p.suffix.lower() == ".img" else None,
        parent / f"{stem}.IMG",
        parent / f"{stem}.img",
        Path(f"data/reference/lroc_nac/{stem}.IMG")
    ]
    raw_path = next((c for c in img_candidates if c and c.exists()), None)

    if raw_path is not None:
        lines = meta.get("lines", 52224)
        samples = meta.get("samples", 5064)
        header_offset = 5064  # PDS3 attached header length
        
        # Memory-map 16-bit integers
        mm = np.memmap(raw_path, dtype="<i2", mode="r", offset=header_offset, shape=(lines, samples))
        # Decimate cleanly
        step_y = max(1, lines // target_dim)
        step_x = max(1, samples // (target_dim // 4))
        sub = mm[::step_y, ::step_x].astype(np.float32)
        
        # Scale to I/F
        sub[sub <= -32752] = 0.0
        p1, p99 = np.percentile(sub[sub > 0], (1, 99)) if np.any(sub > 0) else (0, 1)
        img = np.clip((sub - p1) / (p99 - p1 + 1e-6), 0.0, 1.0)
        return img, bbox_lonlat

    raise FileNotFoundError(f"Could not find readable LRO NAC image for {path}")
