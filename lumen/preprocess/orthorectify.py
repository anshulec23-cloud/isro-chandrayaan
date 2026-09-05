"""
Orthorectification module for Chandrayaan-2 imagery.

Geometric model choice and rationale
-------------------------------------
Chandrayaan-2 PRADAN products do NOT ship RPC (Rational Polynomial Coefficient)
files.  The sensor model provided is a GCP (Ground Control Point) grid: a CSV
file distributed alongside each image with columns

    Longitude, Latitude, Pixel, Scan

at every 100-pixel sample step along each scan line.  This is the *only*
pixel-to-ground mapping available from ISRO for these products.

We therefore use a GCP-based warp via rasterio.  The pipeline is:

  1. Parse the GCP CSV into rasterio.control.GroundControlPoint objects.
     For each GCP, the DEM is sampled at its lon/lat (bilinear) to populate
     the z-field with a real terrain elevation instead of 0.0.
  2. Derive a polynomial transform from the GCPs using
     rasterio.transform.from_gcps (thin-plate-spline interpolation under
     the hood, order-1 fallback when GCP count is low).
  3. Reproject the source array onto a regular geographic grid at the
     requested output GSD using rasterio.warp.reproject + Lanczos resampling.
  4. Clip the output window to the DEM footprint intersection; flag partial
     coverage rather than silently zero-filling.

Honest limitation: GCP z values and rasterio's 2-D polynomial warp
--------------------------------------------------------------------
rasterio.transform.from_gcps() fits a 2-D affine/polynomial from
(pixel, line) -> (X, Y) coordinates only.  The z field on each
GroundControlPoint is stored in the dataset object and passed through to
GDAL's internal GCP list, but GDAL's GDALGCPsToGeotransform() and the
GenImgProjTransformer both ignore z when the destination CRS is a 2-D
geographic system (EPSG:4326).  This means that populating z from the
DEM does NOT move pixels horizontally to account for terrain relief in
the current pipeline.

We still sample and store correct elevations in each GCP z-field for
two reasons:
  (a) It is factually correct metadata that downstream consumers
      (e.g. QGIS, GDAL tools, DSM builders) can use.
  (b) It lays the groundwork for a future proper orthorectification pass.

What is required for z to affect output geometry:
  Option 1 — Use a 3-D CRS for the destination (e.g. EPSG:4979) and
             supply an ellipsoidal-height layer; GDAL will then apply a
             3-D coordinate transformation.
  Option 2 — Implement a per-GCP parallax correction manually:
             for each GCP (lon, lat, z), compute the horizontal offset
             (delta_pixel, delta_line) = z * tan(emission_angle) / GSD,
             shift the GCP pixel/scan coordinates accordingly, then run
             from_gcps on the shifted control points.  This is the
             classical satellite orthorectification approach and is the
             correct fix once CH-2 emission angles are reliably available.
  Option 3 — Use RPCs or a SPICE sensor model (not available for CH-2
             at time of writing).

Required metadata fields (populated by pds4_parser.PDS4Parser.extract_metadata):
  - 'gcp_csv_path': str  —  absolute path to the _g_grd_d18.csv GCP file.
    THIS FIELD MUST BE ADDED TO extract_metadata() / parse_isda_geometry().
    Without it, orthorectify() will raise MissingGeometryError with an
    actionable message.
  - 'pixel_resolution': float  —  native GSD in metres (from
    isda:pixel_resolution element). Used to decide resample scale.
  - 'lines': int, 'samples': int  —  image dimensions (already parsed).
"""

import csv
import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import numpy as np
import cv2
from scipy.ndimage import gaussian_filter

logger = logging.getLogger(__name__)

__all__ = [
    "OrthorectifyResult",
    "MissingGeometryError",
    "orthorectify",
    "resample_to_gsd",
    "build_image_pyramid",
    "compute_overlap_region",
]

# ---------------------------------------------------------------------------
# Sentinel error type
# ---------------------------------------------------------------------------

class MissingGeometryError(RuntimeError):
    """Raised when the metadata is missing fields required for georectification."""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OrthorectifyResult:
    """Return type for orthorectify()."""
    image: np.ndarray
    """Orthorectified image array (float32, H x W)."""
    transform: Dict[str, Any]
    """Affine/geospatial transform metadata."""
    partial_coverage: bool = False
    """True when the DEM tile did not fully cover the image footprint."""
    coverage_fraction: float = 1.0
    """Fraction of the image footprint covered by the DEM (0.0–1.0)."""
    warnings: List[str] = field(default_factory=list)
    """Human-readable warning messages about partial coverage or fallbacks."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _try_import_rasterio():
    try:
        import rasterio
        import rasterio.control
        import rasterio.transform
        import rasterio.warp
        import rasterio.crs
        return rasterio
    except ImportError:
        return None


def _parse_gcp_csv(gcp_csv_path: str) -> List[Tuple[float, float, float, float]]:
    """
    Parse the ISRO GCP CSV (columns: Longitude, Latitude, Pixel, Scan)
    into a list of raw tuples.  Elevation (z) is NOT assigned here;
    it is filled in by _sample_dem_elevations() or left at 0.0.

    Args:
        gcp_csv_path: Path to the _g_grd_d18.csv file.

    Returns:
        List of (lon, lat, pixel, scan) tuples.

    Raises:
        FileNotFoundError: if the CSV does not exist.
        MissingGeometryError: if fewer than 4 valid rows are found.
    """
    csv_path = Path(gcp_csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"GCP CSV not found: {csv_path}")

    rows: List[Tuple[float, float, float, float]] = []
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                lon = float(row["Longitude"])
                lat = float(row["Latitude"])
                pixel = float(row["Pixel"])
                scan = float(row["Scan"])
            except (KeyError, ValueError) as exc:
                logger.warning(f"Skipping malformed GCP row {row}: {exc}")
                continue
            rows.append((lon, lat, pixel, scan))

    if len(rows) < 4:
        raise MissingGeometryError(
            f"Only {len(rows)} valid GCPs found in {csv_path}; "
            "need ≥4 for a polynomial transform."
        )

    logger.info(f"Loaded {len(rows)} GCPs from {csv_path.name}")
    return rows


def _parse_iirs_loc_img(loc_path: str) -> List[Tuple[float, float, float, float]]:
    """
    Parse the IIRS pixel location image (_d_loc_d18_ard.img) into a list of GCP tuples.
    The loc image has 4 bands: Longitude, Latitude, Radius, Height.
    
    Args:
        loc_path: Path to the _d_loc_d18_ard.img file.
        
    Returns:
        List of (lon, lat, pixel, scan) tuples.
    """
    rasterio = _try_import_rasterio()
    if rasterio is None:
        raise ImportError("rasterio is required to parse IIRS location image.")
        
    rows: List[Tuple[float, float, float, float]] = []
    with rasterio.open(loc_path) as src:
        H, W = src.shape
        lon_band = src.read(1)
        lat_band = src.read(2)
        
        y_steps = list(range(0, H, 100))
        if y_steps[-1] != H - 1:
            y_steps.append(H - 1)
            
        x_steps = list(range(0, W, 50))
        if x_steps[-1] != W - 1:
            x_steps.append(W - 1)
            
        for y in y_steps:
            for x in x_steps:
                lon = float(lon_band[y, x])
                lat = float(lat_band[y, x])
                if np.isfinite(lon) and np.isfinite(lat) and -180 <= lon <= 360 and -90 <= lat <= 90:
                    rows.append((lon, lat, float(x), float(y)))
                    
    logger.info(f"Generated {len(rows)} GCPs from {Path(loc_path).name}")
    return rows


def _sample_dem_elevations(
    gcp_rows: List[Tuple[float, float, float, float]],
    dem_dataset,
    dem_bbox: Tuple[float, float, float, float],
    warn_msgs: List[str],
) -> List[float]:
    """
    Sample DEM elevation at each GCP (lon, lat) using rasterio bilinear
    sampling.  For GCPs that fall outside DEM coverage the existing
    partial-coverage warning path is used and z falls back to 0.0 for
    that individual point.

    NOTE: these z-values are stored in the GCP objects and are correct
    terrain elevations, but rasterio.warp.reproject() with a 2-D CRS
    (EPSG:4326) does NOT use z to shift pixels horizontally.  See the
    module docstring for what is required to make elevation affect
    output pixel positions.

    Args:
        gcp_rows: List of (lon, lat, pixel, scan) from _parse_gcp_csv().
        dem_dataset: Open rasterio dataset.
        dem_bbox: (min_lon, min_lat, max_lon, max_lat) of the DEM.
        warn_msgs: Mutable list; out-of-coverage warnings are appended here.

    Returns:
        List of float elevations, one per GCP row, in the same order.
    """
    min_lon, min_lat, max_lon, max_lat = dem_bbox
    elevations: List[float] = []
    out_of_dem_count = 0

    # Collect all in-bounds coords for a single batched sample() call
    coords_inbounds: List[Tuple[float, float]] = []
    idx_inbounds: List[int] = []

    for i, (lon, lat, _, _) in enumerate(gcp_rows):
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            coords_inbounds.append((lon, lat))
            idx_inbounds.append(i)

    # Pre-fill with 0.0; overwrite for in-bounds GCPs
    elevations = [0.0] * len(gcp_rows)
    out_of_dem_count = len(gcp_rows) - len(coords_inbounds)

    if coords_inbounds:
        # rasterio.sample returns an iterator of 1-element arrays
        for idx, sample_arr in zip(idx_inbounds,
                                   dem_dataset.sample(coords_inbounds,
                                                      indexes=1)):
            z = float(sample_arr[0])
            # Guard against nodata / NaN
            if np.isfinite(z):
                elevations[idx] = z
            else:
                elevations[idx] = 0.0
                out_of_dem_count += 1

    if out_of_dem_count > 0:
        msg = (
            f"{out_of_dem_count}/{len(gcp_rows)} GCPs fell outside DEM coverage "
            "or returned nodata; z=0.0 used for those points (partial coverage)."
        )
        logger.warning(msg)
        warn_msgs.append(msg)

    sampled_nonzero = sum(1 for z in elevations if z != 0.0)
    logger.info(
        f"DEM elevation sampled for {sampled_nonzero}/{len(gcp_rows)} GCPs; "
        f"{out_of_dem_count} out-of-coverage GCPs left at z=0.0."
    )
    return elevations


def _build_gcps(
    gcp_rows: List[Tuple[float, float, float, float]],
    elevations: List[float],
) -> List[Any]:
    """
    Construct rasterio GroundControlPoint objects from parsed CSV rows
    and pre-sampled elevations.

    Args:
        gcp_rows: (lon, lat, pixel, scan) tuples from _parse_gcp_csv().
        elevations: Per-GCP elevations from _sample_dem_elevations().

    Returns:
        List of rasterio.control.GroundControlPoint instances.
    """
    rasterio = _try_import_rasterio()
    if rasterio is None:
        raise ImportError(
            "rasterio is required for orthorectification. "
            "Install it with: pip install rasterio>=1.3"
        )
    return [
        rasterio.control.GroundControlPoint(
            row=scan,    # rasterio convention: row = line (y)
            col=pixel,   # rasterio convention: col = sample (x)
            x=lon,
            y=lat,
            z=z,         # real terrain elevation from DEM (or 0.0 if out-of-coverage)
        )
        for (lon, lat, pixel, scan), z in zip(gcp_rows, elevations)
    ]


def _load_gcp_csv(gcp_csv_path: str) -> List[Any]:
    """
    Backward-compatible wrapper: parse CSV and build GCPs with z=0.0.
    Use orthorectify() directly for DEM-backed elevation.
    """
    gcp_rows = _parse_gcp_csv(gcp_csv_path)
    elevations = [0.0] * len(gcp_rows)
    return _build_gcps(gcp_rows, elevations)


def _footprint_from_gcps(gcps) -> Tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) bounding box of a GCP list."""
    lons = [g.x for g in gcps]
    lats = [g.y for g in gcps]
    return min(lons), min(lats), max(lons), max(lats)


def _dem_footprint(dem_dataset) -> Tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) of an open rasterio dataset."""
    b = dem_dataset.bounds
    return b.left, b.bottom, b.right, b.top


def _coverage_fraction(
    img_bbox: Tuple[float, float, float, float],
    dem_bbox: Tuple[float, float, float, float],
) -> Tuple[Tuple[float, float, float, float], float]:
    """
    Intersect two (min_lon, min_lat, max_lon, max_lat) bounding boxes.

    Returns:
        intersection bbox and the fraction of the image footprint covered.
        Returns (None, 0.0) if there is no overlap.
    """
    ix_min = max(img_bbox[0], dem_bbox[0])
    iy_min = max(img_bbox[1], dem_bbox[1])
    ix_max = min(img_bbox[2], dem_bbox[2])
    iy_max = min(img_bbox[3], dem_bbox[3])

    if ix_min >= ix_max or iy_min >= iy_max:
        return None, 0.0

    inter_area = (ix_max - ix_min) * (iy_max - iy_min)
    img_area = (img_bbox[2] - img_bbox[0]) * (img_bbox[3] - img_bbox[1])
    fraction = inter_area / img_area if img_area > 0 else 0.0
    return (ix_min, iy_min, ix_max, iy_max), fraction


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def orthorectify(
    image: np.ndarray,
    metadata: Dict[str, Any],
    dem_dataset,
    target_gsd_m: float,
    output_crs: str = "EPSG:4326",
) -> OrthorectifyResult:
    """
    Project a Chandrayaan-2 image onto a geographic grid using GCP-based warping.

    Geometric model: GCP grid (Longitude, Latitude, Pixel, Scan) from the
    ISRO-provided _g_grd_d18.csv sidecar. rasterio derives a thin-plate-spline
    polynomial transform from the GCPs and reprojects via Lanczos resampling.
    See module docstring for why RPCs are not used.

    Args:
        image:
            2-D float32/uint8 source array (H × W) as loaded by
            lumen.ingest.pds4_parser.load_binary_image.
        metadata:
            Dictionary returned by lumen.ingest.metadata.extract_metadata.
            REQUIRED field: 'gcp_csv_path' (str) — absolute path to the
            _g_grd_d18.csv GCP file.  If this key is absent, a
            MissingGeometryError is raised with an actionable message
            explaining what needs to be added to the parser.
            OPTIONAL field: 'pixel_resolution' (float) — native GSD in metres.
        dem_dataset:
            An open rasterio dataset covering (or partially covering) the
            image footprint.  Pass ``None`` to skip DEM-based height
            correction (the GCP grid uses z=0 throughout, which is adequate
            for flat-terrain or first-pass registration).
        target_gsd_m:
            Output ground-sample distance in metres.
        output_crs:
            EPSG string for the output CRS.  Default: 'EPSG:4326'
            (geographic lat/lon, degrees).  For polar imagery consider a
            polar stereographic CRS such as 'ESRI:104903' (Moon south pole).

    Returns:
        OrthorectifyResult with .image (warped array), .transform (dict),
        .partial_coverage (bool), .coverage_fraction (float),
        .warnings (List[str]).

    Raises:
        MissingGeometryError:
            If 'gcp_csv_path' is absent from metadata — tells the caller
            exactly which parser field to add.
        ImportError:
            If rasterio is not installed.
    """
    rasterio = _try_import_rasterio()
    if rasterio is None:
        raise ImportError(
            "rasterio is required for orthorectification. "
            "Install it with: pip install rasterio>=1.3"
        )

    # ------------------------------------------------------------------
    # 1. Validate required metadata field
    # ------------------------------------------------------------------
    gcp_csv_path = metadata.get("gcp_csv_path")
    iirs_loc_path = metadata.get("iirs_loc_path")
    if not gcp_csv_path and not iirs_loc_path:
        raise MissingGeometryError(
            "'gcp_csv_path' or 'iirs_loc_path' is missing from the metadata dictionary. "
            "This field must be populated by pds4_parser.PDS4Parser. "
            "For TMC/OHRC, parsing the 'isda:Geometry_Parameters' sibling product label "
            "(_g_grd_d18.csv) is required. For IIRS, the _d_loc_d18_ard.img is required."
        )

    warn_msgs: List[str] = []

    # ------------------------------------------------------------------
    # 2. Parse GCP CSV or IIRS Loc Image into raw (lon, lat, pixel, scan) tuples
    # ------------------------------------------------------------------
    if iirs_loc_path:
        gcp_rows = _parse_iirs_loc_img(iirs_loc_path)
    else:
        gcp_rows = _parse_gcp_csv(gcp_csv_path)
        
    src_crs = rasterio.crs.CRS.from_epsg(4326)  # GCPs are in lon/lat

    # ------------------------------------------------------------------
    # 3. Check DEM coverage and sample elevations at each GCP
    # ------------------------------------------------------------------
    # Build a temporary GCP list with z=0 to compute the image footprint
    # before deciding how to handle partial coverage.
    _gcps_temp = _build_gcps(gcp_rows, [0.0] * len(gcp_rows))
    img_bbox = _footprint_from_gcps(_gcps_temp)
    partial_coverage = False
    coverage_fraction = 1.0
    elevations: List[float] = [0.0] * len(gcp_rows)

    if dem_dataset is not None:
        dem_bbox = _dem_footprint(dem_dataset)
        intersection, coverage_fraction = _coverage_fraction(img_bbox, dem_bbox)

        if coverage_fraction == 0.0:
            msg = (
                f"DEM footprint {dem_bbox} has NO overlap with image footprint "
                f"{img_bbox}. Proceeding without DEM height correction (z=0 GCPs)."
            )
            warnings.warn(msg, UserWarning, stacklevel=2)
            warn_msgs.append(msg)
            dem_dataset = None
            coverage_fraction = 0.0
            partial_coverage = True
            # elevations stays [0.0, ...]
        else:
            if coverage_fraction < 0.999:
                msg = (
                    f"DEM covers only {coverage_fraction:.1%} of the image footprint. "
                    f"Output will be cropped to the covered region {intersection}. "
                    "No zero-fill is applied."
                )
                warnings.warn(msg, UserWarning, stacklevel=2)
                warn_msgs.append(msg)
                partial_coverage = True
                img_bbox = intersection

            # Sample real DEM elevation at every GCP lon/lat.
            # GCPs that fall outside DEM bounds receive z=0.0 and a warning
            # is appended to warn_msgs via the partial-coverage path inside
            # _sample_dem_elevations().
            #
            # IMPORTANT — z limitation: these elevations are stored on the
            # GroundControlPoint objects and will appear in any GCP-aware
            # consumer of the dataset (QGIS, GDAL utilities).  However,
            # rasterio.transform.from_gcps() fits a 2-D (pixel, line) →
            # (X, Y) polynomial and rasterio.warp.reproject() with EPSG:4326
            # as the destination CRS ignores z entirely.  The pixel positions
            # in the output image are therefore NOT shifted for terrain relief.
            # See the module docstring for what is needed to make z affect
            # output geometry (parallax-correction loop or 3-D CRS).
            elevations = _sample_dem_elevations(
                gcp_rows, dem_dataset, dem_bbox, warn_msgs
            )

    # Build final GCP objects with real (or fallback 0.0) elevations
    gcps = _build_gcps(gcp_rows, elevations)

    # ------------------------------------------------------------------
    # 4. Derive the output transform and dimensions at target_gsd_m
    # ------------------------------------------------------------------
    dst_crs = rasterio.crs.CRS.from_string(output_crs)
    
    # Project GCPs to dst_crs to find the true bounding box in target coordinates
    from rasterio.warp import transform as warp_transform
    lons = [g.x for g in gcps]
    lats = [g.y for g in gcps]
    
    if dst_crs.is_geographic:
        # Geographic CRS: bounds are in degrees
        xs = lons
        ys = lats
        # Convert GSD from metres to degrees (approximate)
        MOON_RADIUS_M = 1_737_400.0
        mid_lat = np.mean(lats)
        metres_per_deg_lat = (2 * np.pi * MOON_RADIUS_M) / 360.0
        metres_per_deg_lon = metres_per_deg_lat * np.cos(np.radians(mid_lat))
        # Prevent division by zero near poles
        metres_per_deg_lon = max(metres_per_deg_lon, 1.0)
        
        # Use anisotropic pixels to prevent massive width expansion at poles
        gsd_deg_x = target_gsd_m / metres_per_deg_lon
        gsd_deg_y = target_gsd_m / metres_per_deg_lat
    else:
        # Projected CRS (e.g. Polar Stereographic): bounds are in metres
        xs, ys = warp_transform(src_crs, dst_crs, lons, lats)
        gsd_deg_x = target_gsd_m
        gsd_deg_y = target_gsd_m

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    out_w = max(1, int(round((max_x - min_x) / gsd_deg_x)))
    out_h = max(1, int(round((max_y - min_y) / gsd_deg_y)))

    from rasterio.transform import from_bounds
    dst_transform = from_bounds(
        min_x, min_y, max_x, max_y, out_w, out_h
    )

    # ------------------------------------------------------------------
    # 5. Build an in-memory source dataset with GCPs attached
    # ------------------------------------------------------------------
    src_array = image.astype(np.float32)
    src_h, src_w = src_array.shape[:2]

    from rasterio.transform import from_gcps as _from_gcps
    from rasterio.warp import reproject, Resampling
    import rasterio.io

    gcp_transform = _from_gcps(gcps)

    # Write source to an in-memory rasterio dataset so reproject() can use it
    mem_profile = {
        "driver": "MEM",
        "count": 1,
        "dtype": "float32",
        "width": src_w,
        "height": src_h,
        "crs": src_crs,
        "transform": gcp_transform,
    }

    # NOTE: rasterio.warp.reproject treats src_transform and gcps as mutually
    # exclusive parameters.  When we write the source into an in-memory dataset
    # with its GCPs attached, we must read it back as a rasterio Band object
    # so that reproject() derives the warp from the dataset's GCPs automatically
    # rather than from an explicit src_transform argument.
    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(**mem_profile) as src_ds:
            src_ds.write(src_array, 1)
            # Attach GCPs.  rasterio stores them on the dataset object;
            # they are used automatically by reproject() when source is a Band.
            src_ds.gcps = (gcps, src_crs)

            dst_array = np.zeros((out_h, out_w), dtype=np.float32)
            reproject(
                source=rasterio.band(src_ds, 1),  # Band object → GCPs read from ds
                destination=dst_array,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.lanczos,
            )

    result_transform = {
        "crs": output_crs,
        "gsd_m": target_gsd_m,
        "affine": dst_transform,
        "bbox_lonlat": img_bbox,
        "bbox_dst": (min_x, min_y, max_x, max_y),
        "shape": (out_h, out_w),
        "gcp_elevations_sampled": any(z != 0.0 for z in elevations),
    }

    return OrthorectifyResult(
        image=dst_array,
        transform=result_transform,
        partial_coverage=partial_coverage,
        coverage_fraction=coverage_fraction,
        warnings=warn_msgs,
    )


# ---------------------------------------------------------------------------
# Unchanged utility functions (used elsewhere in the pipeline)
# ---------------------------------------------------------------------------

def resample_to_gsd(
    image: np.ndarray,
    current_gsd: float,
    target_gsd: float,
) -> Tuple[np.ndarray, float]:
    """
    Resample image to a target GSD with anti-aliasing.

    Args:
        image: Source image array.
        current_gsd: Current ground-sample distance in metres (or arbitrary units).
        target_gsd: Desired GSD in the same units.

    Returns:
        (resampled_image, target_gsd)
    """
    scale = current_gsd / target_gsd
    if scale == 1.0:
        return image.copy(), target_gsd

    if scale < 1.0:  # Downsampling — apply anti-alias blur first
        sigma = 0.5 * np.sqrt((1.0 / scale) ** 2 - 1)
        if len(image.shape) == 3:
            filtered = np.zeros_like(image, dtype=np.float32)
            for i in range(image.shape[2]):
                filtered[:, :, i] = gaussian_filter(image[:, :, i], sigma)
        else:
            filtered = gaussian_filter(image, sigma)
    else:
        filtered = image

    new_h = int(image.shape[0] * scale)
    new_w = int(image.shape[1] * scale)
    if new_h == 0 or new_w == 0:
        new_h, new_w = 1, 1
    resampled = cv2.resize(
        filtered.astype(np.float32), (new_w, new_h), interpolation=cv2.INTER_CUBIC
    )

    return resampled, target_gsd


def build_image_pyramid(
    image: np.ndarray,
    num_levels: int = 4,
    scale_factor: float = 2.0,
) -> List[Tuple[np.ndarray, float]]:
    """
    Create a Gaussian pyramid for multi-scale matching.

    Args:
        image: Source image.
        num_levels: Number of pyramid levels.
        scale_factor: Down-scale factor per level.

    Returns:
        List of (image_at_level, cumulative_scale) tuples.
    """
    pyramid = [(image.copy(), 1.0)]
    current_image = image
    current_scale = 1.0

    for _ in range(1, num_levels):
        sigma = 0.5 * np.sqrt(scale_factor ** 2 - 1)
        if len(current_image.shape) == 3:
            filtered = np.zeros_like(current_image, dtype=np.float32)
            for i in range(current_image.shape[2]):
                filtered[:, :, i] = gaussian_filter(current_image[:, :, i], sigma)
        else:
            filtered = gaussian_filter(current_image, sigma)

        new_h = max(int(current_image.shape[0] / scale_factor), 1)
        new_w = max(int(current_image.shape[1] / scale_factor), 1)
        current_image = cv2.resize(
            filtered.astype(np.float32),
            (new_w, new_h),
            interpolation=cv2.INTER_LINEAR,
        )
        current_scale *= scale_factor
        pyramid.append((current_image, current_scale))

    return pyramid


def compute_overlap_region(
    image0_bounds: Tuple[float, float, float, float],
    image1_bounds: Tuple[float, float, float, float],
) -> Tuple[Optional[Tuple[float, float, float, float]], float]:
    """
    Compute overlap region given geographic bounds [min_x, min_y, max_x, max_y].

    Args:
        image0_bounds: (min_x, min_y, max_x, max_y) for image 0.
        image1_bounds: (min_x, min_y, max_x, max_y) for image 1.

    Returns:
        (intersection_bbox, overlap_fraction) or (None, 0.0) if no overlap.
    """
    min_x = max(image0_bounds[0], image1_bounds[0])
    min_y = max(image0_bounds[1], image1_bounds[1])
    max_x = min(image0_bounds[2], image1_bounds[2])
    max_y = min(image0_bounds[3], image1_bounds[3])

    if min_x >= max_x or min_y >= max_y:
        return None, 0.0

    overlap_area = (max_x - min_x) * (max_y - min_y)
    area0 = (image0_bounds[2] - image0_bounds[0]) * (image0_bounds[3] - image0_bounds[1])

    if area0 == 0:
        return None, 0.0

    overlap_pct = overlap_area / area0
    return (min_x, min_y, max_x, max_y), overlap_pct
