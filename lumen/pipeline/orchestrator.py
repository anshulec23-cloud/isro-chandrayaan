"""
End-to-end registration pipeline orchestrator for LUMEN.

Stage order
-----------
1. INGEST        — parse PDS4 XML, load raw binary array.  No resizing.
2. PREPROCESS    — split into three sub-steps:
     2a. Orthorectify each image individually onto a geographic grid at the
         shared target GSD.
     2b. Crop both orthorectified images to their geographic overlap region
         (raises NoOverlapError with both footprints named if there is none).
     2c. Radiometric/photometric normalisation on the cropped arrays.
3. FEATURES      — GridSampler → deep / RIFT2 feature extraction on the
                   spatially-aligned, overlap-cropped images.
4. GEOMETRY      — MAGSAC++ outlier rejection → subpixel refinement.
5. REGISTER      — perspective warp.
6. EVALUATE      — RMSE / SSIM / inlier metrics.

Why orthorectification comes before any resizing
-------------------------------------------------
The old MAX_DIM cv2.resize in _ingest() applied an arbitrary pixel cap before
any geometric correction.  This destroyed the GCP-derived pixel↔ground
relationship: a 80 000-line OHRC strip and a 13 000-line TMC strip were both
squashed to 2048 px, making their pixel scales physically incompatible.  The
cap now lives after orthorectification (configurable via max_ortho_dim) so
pixels in both images correspond to the same ground area.

Why overlap cropping is between orthorectification and feature extraction
-------------------------------------------------------------------------
Running a matcher across non-overlapping content produces only spurious
matches that inflate the outlier ratio and waste GPU compute.  After
orthorectification both images share the same CRS and GSD; the geographic
footprint intersection is trivially computable from their bbox_lonlat fields,
and the pixel crop is a simple array slice.  If the footprints do not
intersect, NoOverlapError is raised with both bounding boxes named —
catching this BEFORE the matcher avoids a confusing zero-match result.
"""

import logging
import time
import warnings
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, Union
from pathlib import Path

import numpy as np

from lumen.ingest.pds4_parser import parse_pds4, load_binary_image
from lumen.ingest.metadata import extract_metadata, SENSOR_SPECS
from lumen.preprocess.radiometric import apply_clahe, normalize_to_float
from lumen.preprocess.photometric import photometric_normalize
from lumen.preprocess.orthorectify import (
    orthorectify,
    OrthorectifyResult,
    MissingGeometryError,
    resample_to_gsd,
)
from lumen.preprocess.overlap_crop import (
    crop_pair_to_overlap,
    NoOverlapError,
)
from lumen.features.deep_matcher import DeepMatcher
from lumen.features.rift2 import match_rift2
from lumen.features.grid_sampler import GridSampler
from lumen.geometry.outlier_reject import estimate_transform_magsac
from lumen.geometry.subpixel import refine_subpixel
from lumen.registration.warp import warp_image, create_registered_product
from lumen.evaluation.metrics import compute_rmse, compute_ssim, compute_inlier_ratio, create_checkerboard, create_false_color_overlay

logger = logging.getLogger(__name__)

__all__ = [
    "RegistrationFailedError",
    "RegistrationResult",
    "PipelineStage",
    "PipelineCallback",
    "RegistrationPipeline",
]

# Maximum output dimension (px) applied AFTER orthorectification.
_MAX_ORTHO_DIM: int = 2048

# Metres per degree of arc on the lunar reference sphere (R = 1737.4 km).
_M_PER_DEG: float = 2.0 * np.pi * 1_737_400.0 / 360.0

# Pre-computed orthorectified GeoTIFFs (written by scripts/run_real_ortho_outputs.py).
# Anchored to the repository root so results don't depend on the working directory.
_ORTHO_CACHE_DIR: Path = Path(__file__).resolve().parents[2] / "data" / "processed" / "real_ortho_outputs"

# Fewer MAGSAC++ inliers than this means the homography is not trustworthy.
_MIN_INLIERS: int = 8


class RegistrationFailedError(RuntimeError):
    """Raised when matching/geometry did not produce a trustworthy transform."""


def _save_debug_preview(image: np.ndarray, output_path: Union[str, Path], max_dim: int = 2048) -> None:
    """Save a normalized uint8 PNG preview of an image array for visual inspection."""
    if image is None or image.size == 0:
        return
    try:
        import cv2
        img = np.squeeze(image)
        if img.ndim == 3:
            if img.shape[2] != 3:
                img = img[0] if img.shape[0] <= 4 else img[..., 0]

        img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        if img.size > 0:
            p1, p99 = np.percentile(img, (1, 99))
            if p99 > p1:
                img_norm = np.clip((img - p1) / (p99 - p1), 0.0, 1.0)
            else:
                mn, mx = img.min(), img.max()
                img_norm = (img - mn) / (mx - mn) if mx > mn else np.zeros_like(img)
        else:
            img_norm = np.zeros_like(img)

        img_u8 = (img_norm * 255.0).astype(np.uint8)
        h, w = img_u8.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
            step = max(1, int(1 / scale))
            if step > 2:
                img_u8 = img_u8[::step, ::step]
            img_u8 = cv2.resize(img_u8, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_p), img_u8)
        logger.info(f"Saved debug preview: {out_p.name} (shape {img_u8.shape})")
    except Exception as exc:
        logger.warning(f"Could not save debug preview {output_path}: {exc}")


@dataclass
class RegistrationResult:
    """Result of a registration pipeline run."""
    warped_image: np.ndarray
    transform_matrix: np.ndarray
    match_points: List[Dict[str, float]]
    metrics: Dict[str, float]
    metadata: Dict[str, Any]
    elapsed_seconds: float
    source_path: str
    reference_path: str
    checkerboard_image: Optional[np.ndarray] = None
    match_overlay_image: Optional[np.ndarray] = None
    source_image: Optional[np.ndarray] = None
    reference_image: Optional[np.ndarray] = None

    @property
    def registered_image(self) -> np.ndarray:
        return self.warped_image


class PipelineStage(Enum):
    """Stages of the LUMEN registration pipeline."""
    INGEST = auto()
    PREPROCESS = auto()
    FEATURES = auto()
    GEOMETRY = auto()
    REGISTER = auto()
    EVALUATE = auto()


class PipelineCallback(Protocol):
    """Protocol for pipeline progress callbacks."""
    def on_stage_start(self, stage: PipelineStage, message: str) -> None:
        ...

    def on_stage_complete(self, stage: PipelineStage, metrics: Optional[Dict[str, Any]] = None) -> None:
        ...

    def on_progress(self, stage: PipelineStage, progress: float, message: str) -> None:
        ...


class RegistrationPipeline:
    """End-to-end registration pipeline orchestrator for LUMEN."""

    def __init__(self, config: Any, callback: Optional[PipelineCallback] = None):
        self.config = config
        self.callback = callback
        logger.info("Initializing RegistrationPipeline")

    # ------------------------------------------------------------------
    # Callback helpers
    # ------------------------------------------------------------------

    def _notify_start(self, stage: PipelineStage, message: str) -> None:
        logger.info(f"Starting stage {stage.name}: {message}")
        if self.callback:
            self.callback.on_stage_start(stage, message)

    def _notify_complete(self, stage: PipelineStage, metrics: Optional[Dict[str, Any]] = None) -> None:
        logger.info(f"Completed stage {stage.name}")
        if self.callback:
            self.callback.on_stage_complete(stage, metrics)

    def _notify_progress(self, stage: PipelineStage, progress: float, message: str) -> None:
        if self.callback:
            self.callback.on_progress(stage, progress, message)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        source_path: Union[str, Path],
        reference_path: Union[str, Path],
        source_sensor: str,
        ref_sensor: str,
        source_dem_path: Optional[Union[str, Path]] = None,
        reference_dem_path: Optional[Union[str, Path]] = None,
        # Legacy single-DEM arg — applied to both images when per-image args absent.
        dem_path: Optional[Union[str, Path]] = None,
        options: Optional[Dict[str, Any]] = None,
        checkpoints: Optional[Union[Tuple[np.ndarray, np.ndarray], Dict[str, np.ndarray]]] = None,
    ) -> RegistrationResult:
        """Run the full registration pipeline.

        Args:
            source_path: Path to the source PDS4 XML (image to be warped).
            reference_path: Path to the reference PDS4 XML.
            source_sensor: Sensor identifier ('OHRC', 'TMC2', 'IIRS').
            ref_sensor: Sensor identifier for the reference.
            source_dem_path: Optional DEM GeoTIFF for source image footprint.
            reference_dem_path: Optional DEM GeoTIFF for reference footprint.
            dem_path: Legacy single-DEM kwarg (applied to both when per-image args absent).
            options: Optional dict of overrides:
                - 'feature_method'    : 'auto' | 'deep' | 'rift2'  (default 'auto')
                - 'target_gsd_m'      : shared output GSD in metres
                - 'skip_orthorectify' : bool  — bypass ortho + overlap crop (default False)
                - 'max_ortho_dim'     : int   — post-ortho pixel cap  (default 2048)
                - 'overlap_buffer_fraction': float — expand intersection crop
                                            on each side by this fraction of
                                            min(overlap_w, overlap_h).  Default 0.05.
                - 'overlap_min_area'  : float — minimum overlap area in deg²
                                            below which NoOverlapError is raised.
                                            Default 1e-10.
                - 'skip_overlap_crop' : bool  — bypass overlap crop step.
                                            Implied True when skip_orthorectify=True.
                - 'roi_lonlat'        : (min_lon, min_lat, max_lon, max_lat) — only
                                            read and match this part of the overlap.
                - 'min_inliers'       : int — fewer MAGSAC++ inliers raises
                                            RegistrationFailedError (default 8).
            checkpoints: Optional held-out tie-point pairs for RMSE evaluation.

        Returns:
            RegistrationResult.
        """
        start_time = time.time()
        options = options or {}
        method = options.get("feature_method", "auto")
        skip_ortho = bool(options.get("skip_orthorectify", False))
        skip_crop = bool(options.get("skip_overlap_crop", skip_ortho))
        max_ortho_dim = int(options.get("max_ortho_dim", _MAX_ORTHO_DIM))
        overlap_buffer = float(options.get("overlap_buffer_fraction", 0.05))
        overlap_min_area = float(options.get("overlap_min_area", 1e-10))

        debug_dir = options.get("debug_dir")
        debug_path = Path(debug_dir) if debug_dir else None
        pair_name = f"{source_sensor}_to_{ref_sensor}"

        _src_dem = source_dem_path or dem_path
        _ref_dem = reference_dem_path or dem_path

        try:
            # ── 1. INGEST ──────────────────────────────────────────────────
            self._notify_start(PipelineStage.INGEST, "Ingesting source and reference images")
            
            # Peek metadata to calculate mutual overlap bounding box for windowed I/O
            initial_bbox = None
            if not skip_crop:
                try:
                    src_peek = self._inspect_metadata(source_path)
                    ref_peek = self._inspect_metadata(reference_path)
                    if src_peek.get("bbox_lonlat") and ref_peek.get("bbox_lonlat"):
                        sb, rb = src_peek["bbox_lonlat"], ref_peek["bbox_lonlat"]
                        inter = (max(sb[0], rb[0]), max(sb[1], rb[1]), min(sb[2], rb[2]), min(sb[3], rb[3]))
                        roi = options.get("roi_lonlat")
                        if roi is not None:
                            # Restrict to a region of interest so a window of a
                            # long strip can be matched at native resolution
                            # instead of the whole overlap squeezed to max_ortho_dim.
                            inter = (max(inter[0], roi[0]), max(inter[1], roi[1]),
                                     min(inter[2], roi[2]), min(inter[3], roi[3]))
                        if inter[0] < inter[2] and inter[1] < inter[3]:
                            initial_bbox = inter
                            logger.info(f"Computed initial overlap window for windowed I/O: {initial_bbox}")
                        elif roi is not None:
                            raise NoOverlapError(f"roi_lonlat {tuple(roi)} does not intersect the pair's overlap")
                except NoOverlapError:
                    raise
                except Exception as e:
                    logger.debug(f"Metadata peek skipped: {e}")

            try:
                source_img, source_meta = self._ingest(source_path, bbox=initial_bbox)
            except TypeError:
                source_img, source_meta = self._ingest(source_path)

            try:
                ref_img, ref_meta = self._ingest(reference_path, bbox=initial_bbox)
            except TypeError:
                ref_img, ref_meta = self._ingest(reference_path)

            if debug_path:
                _save_debug_preview(source_img, debug_path / f"{pair_name}_src_01_loaded.png")
                _save_debug_preview(ref_img, debug_path / f"{pair_name}_ref_01_loaded.png")
            self._notify_complete(PipelineStage.INGEST)

            # ── 2. PREPROCESS ──────────────────────────────────────────────
            self._notify_start(PipelineStage.PREPROCESS, "Orthorectifying and preprocessing images")

            # Resolve shared target GSD (coarser of the two native GSDs).
            src_gsd = source_meta.get("pixel_resolution") or \
                SENSOR_SPECS.get(source_sensor.upper(), {}).get("resolution_m", 5.0)
            ref_gsd = ref_meta.get("pixel_resolution") or \
                SENSOR_SPECS.get(ref_sensor.upper(), {}).get("resolution_m", 5.0)

            if "target_gsd_m" in options:
                target_gsd_m = float(options["target_gsd_m"])
            else:
                target_gsd_m = max(src_gsd, ref_gsd)
                logger.info(
                    f"target_gsd_m not specified; using coarser native GSD "
                    f"({target_gsd_m:.2f} m) from {source_sensor}={src_gsd:.2f} m "
                    f"vs {ref_sensor}={ref_gsd:.2f} m."
                )

            # 2a. Orthorectify each image; obtain geographic footprint bbox.
            source_ortho, src_bbox = self._orthorectify_image(
                source_img, source_meta, target_gsd_m, _src_dem,
                skip_ortho=skip_ortho, max_dim=max_ortho_dim,
            )
            ref_ortho, ref_bbox = self._orthorectify_image(
                ref_img, ref_meta, target_gsd_m, _ref_dem,
                skip_ortho=skip_ortho, max_dim=max_ortho_dim,
            )
            if debug_path:
                _save_debug_preview(source_ortho, debug_path / f"{pair_name}_src_02_orthorectified.png")
                _save_debug_preview(ref_ortho, debug_path / f"{pair_name}_ref_02_orthorectified.png")

            # 2b. Crop both images to their geographic overlap.
            overlap_bbox = None
            if not skip_crop and src_bbox is not None and ref_bbox is not None:
                # NoOverlapError propagates to the caller with both footprints named.
                source_ortho, ref_ortho, overlap_bbox = crop_pair_to_overlap(
                    source_ortho, src_bbox,
                    ref_ortho,   ref_bbox,
                    buffer_fraction=overlap_buffer,
                    min_area_threshold=overlap_min_area,
                )
                logger.info(
                    f"Overlap crop: src {src_bbox} ∩ ref {ref_bbox} "
                    f"→ {overlap_bbox} "
                    f"(src cropped to {source_ortho.shape}, ref to {ref_ortho.shape})"
                )

                # Harmonize overlap arrays to common analysis grid to ensure 1:1 ground scale correspondence
                import cv2
                cur_max = max(max(source_ortho.shape[:2]), max(ref_ortho.shape[:2]))
                target_h = min(max_ortho_dim, cur_max)
                mid_lat = (overlap_bbox[1] + overlap_bbox[3]) / 2.0
                d_lon = abs(overlap_bbox[2] - overlap_bbox[0]) * np.cos(np.radians(mid_lat))
                d_lat = abs(overlap_bbox[3] - overlap_bbox[1])
                aspect = (d_lon / d_lat) if d_lat > 1e-6 else 1.0
                target_w = max(1, int(round(target_h * aspect)))

                if source_ortho.shape != (target_h, target_w):
                    source_ortho = cv2.resize(source_ortho.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)
                if ref_ortho.shape != (target_h, target_w):
                    ref_ortho = cv2.resize(ref_ortho.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)
                logger.info(f"Harmonized overlap crops to common analysis grid: ({target_h}, {target_w})")

                if debug_path:
                    _save_debug_preview(source_ortho, debug_path / f"{pair_name}_src_03_crop_to_overlap.png")
                    _save_debug_preview(ref_ortho, debug_path / f"{pair_name}_ref_03_crop_to_overlap.png")
            elif skip_crop:
                logger.info("Overlap crop skipped (skip_overlap_crop=True).")
            else:
                logger.warning(
                    "No geographic footprint available for one or both images "
                    "(skip_orthorectify=True or GCP CSV missing); overlap crop skipped."
                )

            # 2c. Radiometric / photometric normalisation on cropped arrays.
            photo_method = options.get("photometric_method", "auto")
            if photo_method == "auto":
                opticals = {"OHRC", "TMC2", "SELENE_TC", "LROC_NAC"}
                if source_sensor.upper() in opticals and ref_sensor.upper() in opticals and source_sensor.upper() != ref_sensor.upper():
                    photo_method = "lommel_seeliger"
                    logger.info(f"Cross-mission optical pair ({source_sensor} -> {ref_sensor}) detected; selecting Lommel-Seeliger normalisation.")

            source_pre = self._normalize_image(source_ortho, source_meta, photo_method=photo_method)
            ref_pre = self._normalize_image(ref_ortho, ref_meta, photo_method=photo_method)
            if debug_path:
                _save_debug_preview(source_pre, debug_path / f"{pair_name}_src_04_photometric_norm.png")
                _save_debug_preview(ref_pre, debug_path / f"{pair_name}_ref_04_photometric_norm.png")

            self._notify_complete(PipelineStage.PREPROCESS)

            # ── 3. FEATURES ────────────────────────────────────────────────
            self._notify_start(PipelineStage.FEATURES, f"Extracting features using method: {method}")
            # Both images are already resampled to the same target GSD above, so
            # the native scale gap (e.g. OHRC 0.25 m vs TMC-2 5 m = 20:1) is
            # absorbed by resampling, not by a separate "bridge" matcher.
            # Hierarchical bridge registration (OHRC→TMC→IIRS through an
            # intermediate image) is planned but not implemented.
            native_scale = max(src_gsd, ref_gsd) / max(min(src_gsd, ref_gsd), 1e-9)
            if native_scale > 20:
                logger.warning(
                    f"Native GSD ratio {native_scale:.0f}:1 — the finer image was "
                    f"downsampled to {target_gsd_m:.2f} m before matching, so its "
                    f"fine detail is not used."
                )
            matches = self._extract_features(source_pre, ref_pre, method, source_sensor, ref_sensor)

            sampler = GridSampler()
            mkpts0, mkpts1, mscores, stats = sampler.enforce_distribution(
                matches['keypoints0'], matches['keypoints1'], source_pre.shape, matches.get('scores')
            )
            matches['keypoints0'] = mkpts0
            matches['keypoints1'] = mkpts1
            if 'scores' in matches:
                matches['scores'] = mscores
            matches['num_matches'] = len(mkpts0)
            matches['grid_stats'] = stats

            self._notify_complete(PipelineStage.FEATURES, {"match_count": len(matches['keypoints0'])})

            # ── 4. GEOMETRY ────────────────────────────────────────────────
            self._notify_start(PipelineStage.GEOMETRY, "Estimating geometric transform with subpixel refinement")
            transform, inlier_pts0, inlier_pts1, outlier_pts0, outlier_pts1 = self._estimate_geometry(
                matches, source_pre, ref_pre
            )
            self._notify_complete(PipelineStage.GEOMETRY, {"inlier_count": len(inlier_pts0)})

            min_inliers = int(options.get("min_inliers", _MIN_INLIERS))
            if len(inlier_pts0) < min_inliers:
                # Previously the pipeline returned an identity transform and
                # reported "success" here, so a total matching failure looked
                # like a valid (if poor) registration.
                raise RegistrationFailedError(
                    f"Only {len(inlier_pts0)} MAGSAC++ inliers out of "
                    f"{len(inlier_pts0) + len(outlier_pts0)} candidate matches "
                    f"(need >= {min_inliers}); no trustworthy transform for "
                    f"{source_sensor} → {ref_sensor}."
                )

            # ── 5. REGISTER ────────────────────────────────────────────────
            self._notify_start(PipelineStage.REGISTER, "Warping source image")
            warped = self._register(source_pre, ref_pre, transform)
            self._notify_complete(PipelineStage.REGISTER)

            # ── 6. EVALUATE ────────────────────────────────────────────────
            self._notify_start(PipelineStage.EVALUATE, "Evaluating registration quality")
            metrics = self._evaluate(
                warped, ref_pre, inlier_pts0, inlier_pts1, outlier_pts0, transform,
                checkpoints=checkpoints
            )
            self._notify_complete(PipelineStage.EVALUATE, metrics)

            elapsed = time.time() - start_time
            logger.info(f"Registration completed successfully in {elapsed:.2f}s")

            checkerboard = (
                create_checkerboard(warped, ref_pre)
                if warped.shape == ref_pre.shape
                else np.zeros_like(warped)
            )
            overlay = (
                create_false_color_overlay(warped, ref_pre)
                if warped.shape == ref_pre.shape
                else None
            )

            match_points_list = []
            for p0, p1 in zip(inlier_pts0, inlier_pts1):
                match_points_list.append({
                    "src_x": float(p0[0]), "src_y": float(p0[1]),
                    "dst_x": float(p1[0]), "dst_y": float(p1[1]),
                    "inlier": True
                })
            for p0, p1 in zip(outlier_pts0, outlier_pts1):
                match_points_list.append({
                    "src_x": float(p0[0]), "src_y": float(p0[1]),
                    "dst_x": float(p1[0]), "dst_y": float(p1[1]),
                    "inlier": False
                })

            return RegistrationResult(
                warped_image=warped,
                transform_matrix=transform,
                match_points=match_points_list,
                metrics=metrics,
                metadata={
                    "source_sensor": source_sensor,
                    "ref_sensor": ref_sensor,
                    "source_meta": source_meta,
                    "ref_meta": ref_meta,
                    "target_gsd_m": target_gsd_m,
                    "overlap_bbox": overlap_bbox,
                },
                elapsed_seconds=elapsed,
                source_path=str(source_path),
                reference_path=str(reference_path),
                checkerboard_image=checkerboard,
                match_overlay_image=overlay,
                source_image=source_pre,
                reference_image=ref_pre
            )

        except (NoOverlapError, RegistrationFailedError):
            # Re-raise without wrapping — the messages are already specific.
            raise
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise RuntimeError(f"Registration pipeline failed: {e}") from e

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _inspect_metadata(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Inspect product header to extract footprint bbox and metadata without loading heavy image data."""
        p = Path(path)
        path_str = str(p).lower()
        from lumen.ingest.selene_adapter import is_selene_product, parse_selene_pds3
        if is_selene_product(p):
            return parse_selene_pds3(p)
        from lumen.ingest.lroc_adapter import is_lroc_product, parse_lroc_metadata
        if is_lroc_product(p):
            return parse_lroc_metadata(p)
        if path_str.endswith(('.tif', '.tiff')):
            try:
                import rasterio
                with rasterio.open(p) as src:
                    b = src.bounds
                    return {
                        "is_orthorectified": True,
                        "bbox_lonlat": (b.left, b.bottom, b.right, b.top),
                        "pixel_resolution": src.res[0] * _M_PER_DEG if src.crs and src.crs.is_geographic else src.res[0],
                    }
            except Exception:
                pass
        if path_str.endswith('.xml'):
            try:
                lbl = parse_pds4(p, validate_required=False)
                meta = extract_metadata(lbl)
                stem = p.name.lower()
                for key, tif_name in [("tmc_ncn", "tmc_ncn_ortho.tif"), ("tmc_nca", "tmc_nca_ortho.tif"), ("ohrc", "ohrc_calibrated_ortho.tif"), ("iirs", "iirs_ortho.tif")]:
                    if key in stem:
                        tif_p = _ORTHO_CACHE_DIR / tif_name
                        if tif_p.exists():
                            import rasterio
                            with rasterio.open(tif_p) as src:
                                b = src.bounds
                                meta["is_orthorectified"] = True
                                meta["bbox_lonlat"] = (b.left, b.bottom, b.right, b.top)
                                meta["ortho_tif_path"] = str(tif_p)
                return meta
            except Exception:
                pass
        return {}

    def _ingest(
        self,
        path: Union[str, Path],
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Parse PDS4 XML (or SELENE PDS3 LBL, LROC, or GeoTIFF) and load array."""
        logger.debug(f"Ingesting {path} (bbox={bbox})")
        p = Path(path)
        path_str = str(p).lower()

        from lumen.ingest.selene_adapter import is_selene_product, parse_selene_pds3, load_selene_image
        if is_selene_product(p):
            meta = parse_selene_pds3(p)
            img, eff_bbox = load_selene_image(p, bbox_crop=bbox)
            meta["bbox_lonlat"] = eff_bbox
            meta["is_orthorectified"] = True
            return img, meta

        from lumen.ingest.lroc_adapter import is_lroc_product, parse_lroc_metadata, load_lroc_image
        if is_lroc_product(p):
            meta = parse_lroc_metadata(p)
            img, eff_bbox = load_lroc_image(p, bbox_crop=bbox)
            meta["bbox_lonlat"] = eff_bbox
            meta["is_orthorectified"] = True
            return img, meta

        if path_str.endswith(('.tif', '.tiff')):
            import rasterio
            from rasterio.windows import from_bounds
            with rasterio.open(p) as src:
                b = src.bounds
                if bbox is not None:
                    win = from_bounds(*bbox, transform=src.transform)
                    img = src.read(1, window=win).astype(np.float32)
                    eff_bbox = bbox
                else:
                    img = src.read(1).astype(np.float32)
                    eff_bbox = (b.left, b.bottom, b.right, b.top)
                res = src.res[0] * _M_PER_DEG if src.crs and src.crs.is_geographic else src.res[0]
                meta = {
                    "is_orthorectified": True,
                    "bbox_lonlat": eff_bbox,
                    "pixel_resolution": res,
                }
                # Illumination geometry is only used if the GeoTIFF carries it.
                # (Previously every GeoTIFF was silently given the sun angles of
                # one specific TMC-2 product, 50.94°/69.56°.)
                tags = src.tags()
                for key in ("solar_elevation", "solar_azimuth", "phase_angle"):
                    if key in tags:
                        try:
                            meta[key] = float(tags[key])
                        except ValueError:
                            pass
            return img, meta

        # Check for pre-orthorectified GeoTIFF companion
        if path_str.endswith('.xml') and bbox is not None:
            stem = p.name.lower()
            for key, tif_name in [("tmc_ncn", "tmc_ncn_ortho.tif"), ("tmc_nca", "tmc_nca_ortho.tif"), ("ohrc", "ohrc_calibrated_ortho.tif"), ("iirs", "iirs_ortho.tif")]:
                if key in stem:
                    tif_p = _ORTHO_CACHE_DIR / tif_name
                    if tif_p.exists():
                        logger.info(f"Using pre-computed orthorectified GeoTIFF {tif_name} with windowed read over {bbox}")
                        img, meta = self._ingest(tif_p, bbox=bbox)
                        raw_label = parse_pds4(p, validate_required=False)
                        raw_meta = extract_metadata(raw_label)
                        meta.update({k: v for k, v in raw_meta.items() if k not in ("bbox_lonlat", "is_orthorectified")})
                        return img, meta

        label = parse_pds4(path)
        img = load_binary_image(path)
        meta = extract_metadata(label)
        if 'gcp_csv_path' in label and label['gcp_csv_path']:
            meta['gcp_csv_path'] = label['gcp_csv_path']
        if 'iirs_loc_path' in label and label['iirs_loc_path']:
            meta['iirs_loc_path'] = label['iirs_loc_path']
        return img, meta

    def _orthorectify_image(
        self,
        image: np.ndarray,
        metadata: Dict[str, Any],
        target_gsd_m: float,
        dem_path: Optional[Union[str, Path]] = None,
        *,
        skip_ortho: bool = False,
        max_dim: int = _MAX_ORTHO_DIM,
    ) -> Tuple[np.ndarray, Optional[Tuple[float, float, float, float]]]:
        """Project a raw image onto a geographic grid and cap pixel dimensions.

        Returns
        -------
        (image_array, bbox_lonlat)
            *image_array* is the orthorectified (or original, if skip_ortho)
            float32 array after optional downsampling.
            *bbox_lonlat* is ``(min_lon, min_lat, max_lon, max_lat)`` in
            EPSG:4326, or ``None`` when skip_ortho=True.
        """
        if metadata.get("is_orthorectified"):
            bbox = metadata.get("bbox_lonlat")
            logger.info(f"Product is already orthorectified. Footprint bbox: {bbox}")
            return image, bbox

        if skip_ortho:
            # Cap large raw images to prevent OOM in synthetic/test scenarios.
            if max(image.shape[:2]) > max_dim:
                import cv2
                scale = max_dim / max(image.shape[:2])
                new_h = max(1, int(image.shape[0] * scale))
                new_w = max(1, int(image.shape[1] * scale))
                step = max(1, int(1 / scale))
                if step > 2:
                    image = image[::step, ::step]
                image = cv2.resize(
                    image.astype(np.float32), (new_w, new_h), interpolation=cv2.INTER_NEAREST
                )
            return image, None

        dem_dataset = None
        if dem_path is not None:
            try:
                import rasterio
                dem_dataset = rasterio.open(dem_path)
            except Exception as exc:
                logger.warning(
                    f"Could not open DEM {dem_path}: {exc}. "
                    "Proceeding without DEM height correction."
                )

        try:
            ortho_result: OrthorectifyResult = orthorectify(
                image=image,
                metadata=metadata,
                dem_dataset=dem_dataset,
                target_gsd_m=target_gsd_m,
            )
            for w in ortho_result.warnings:
                logger.warning(f"orthorectify: {w}")
            image = ortho_result.image
            bbox = ortho_result.transform["bbox_lonlat"]
        finally:
            if dem_dataset is not None:
                try:
                    dem_dataset.close()
                except Exception:
                    pass

        # Cap post-ortho dimensions while preserving geographic aspect ratio.
        if max(image.shape[:2]) > max_dim:
            import cv2
            scale = max_dim / max(image.shape[:2])
            new_h = max(1, int(image.shape[0] * scale))
            new_w = max(1, int(image.shape[1] * scale))
            image = cv2.resize(
                image.astype(np.float32), (new_w, new_h), interpolation=cv2.INTER_AREA
            )
            logger.info(
                f"Post-ortho downsampled to ({new_h}, {new_w}) "
                f"(max_dim={max_dim}). Footprint bbox unchanged: {bbox}"
            )

        return image, bbox

    def _normalize_image(
        self,
        image: np.ndarray,
        metadata: Dict[str, Any],
        photo_method: str = "auto",
    ) -> np.ndarray:
        """Apply radiometric normalisation and photometric correction.

        Called AFTER overlap cropping so normalisation is only computed on
        the shared region that will actually be fed to the feature matcher.
        """
        logger.debug(f"Normalizing image {image.shape} with photometric method: {photo_method}")

        img_float = normalize_to_float(image)

        sun_el   = metadata.get('solar_elevation',    45.0)
        view_el  = metadata.get('instrument_elevation', 90.0)
        phase_ang = metadata.get('phase_angle',        45.0)

        inc   = np.full(img_float.shape, 90.0 - sun_el)
        emi   = np.full(img_float.shape, 90.0 - view_el)
        phase = np.full(img_float.shape, phase_ang)

        if photo_method == "none":
            img_photo = img_float
        else:
            img_photo, _, _ = photometric_normalize(img_float, inc, emi, phase, method=photo_method)
        clahe_out = apply_clahe(img_photo)
        if clahe_out.dtype == np.uint16:
            clahe_out = (clahe_out / 65535.0).astype(np.float32)
        elif clahe_out.dtype == np.uint8:
            clahe_out = (clahe_out / 255.0).astype(np.float32)
        return clahe_out

    # Preserved unchanged from previous version:

    def _extract_features(
        self, image0: np.ndarray, image1: np.ndarray,
        method: str, sensor0: str, sensor1: str
    ) -> Dict[str, Any]:
        if method == "auto":
            opticals = {"OHRC", "TMC2", "SELENE_TC", "LROC_NAC"}
            if sensor0.upper() in opticals and sensor1.upper() in opticals:
                if sensor0.upper() == sensor1.upper():
                    method = "deep"
                else:
                    # For cross-mission optical pairs, SIFT provides multi-scale octave invariance
                    method = "sift"
            else:
                method = "rift2"

        if method == "sift":
            import cv2
            sift = cv2.SIFT_create(nfeatures=4000)
            img0_u8 = (np.clip(image0, 0.0, 1.0) * 255.0).astype(np.uint8) if image0.max() <= 1.0 else image0.astype(np.uint8)
            img1_u8 = (np.clip(image1, 0.0, 1.0) * 255.0).astype(np.uint8) if image1.max() <= 1.0 else image1.astype(np.uint8)
            kp0, des0 = sift.detectAndCompute(img0_u8, None)
            kp1, des1 = sift.detectAndCompute(img1_u8, None)
            if des0 is not None and des1 is not None and len(kp0) >= 4 and len(kp1) >= 4:
                bf = cv2.BFMatcher(cv2.NORM_L2)
                raw_matches = bf.knnMatch(des0, des1, k=2)
                good = []
                for pair in raw_matches:
                    if len(pair) == 2:
                        m, n = pair
                        if m.distance < 0.80 * n.distance:
                            good.append(m)
                if good:
                    mkpts0 = np.float32([kp0[m.queryIdx].pt for m in good])
                    mkpts1 = np.float32([kp1[m.trainIdx].pt for m in good])
                    # Scores are similarities (higher = better), matching the
                    # convention of DeepMatcher/RIFT2 that GridSampler relies on.
                    # Raw SIFT distances (lower = better) made the grid sampler
                    # keep the *worst* match in every cell.
                    return {
                        'keypoints0': mkpts0,
                        'keypoints1': mkpts1,
                        'scores': np.array([1.0 / (1.0 + m.distance) for m in good], dtype=np.float32),
                        'num_matches': len(mkpts0)
                    }
            return {'keypoints0': np.empty((0, 2), dtype=np.float32), 'keypoints1': np.empty((0, 2), dtype=np.float32), 'num_matches': 0}

        if method == "deep":
            matcher = DeepMatcher()
            matches = matcher.match(image0, image1)
            # If deep matcher found very few points on cross-sensor imagery, attempt SIFT fallback
            if len(matches.get('keypoints0', [])) < 8 and sensor0 != sensor1:
                logger.info("Deep matcher found <8 correspondences on cross-sensor pair; attempting SIFT fallback.")
                try:
                    sift_matches = self._extract_features(image0, image1, "sift", sensor0, sensor1)
                    if len(sift_matches.get('keypoints0', [])) > len(matches.get('keypoints0', [])):
                        return sift_matches
                except Exception as e:
                    logger.warning(f"SIFT fallback failed: {e}")
                logger.info("Attempting RIFT2 fallback.")
                try:
                    rift_matches = match_rift2(image0, image1)
                    if len(rift_matches.get('keypoints0', [])) > len(matches.get('keypoints0', [])):
                        return rift_matches
                except Exception as e:
                    logger.warning(f"RIFT2 fallback failed: {e}")
            return matches
        elif method == "rift2":
            return match_rift2(image0, image1)
        else:
            raise ValueError(f"Unknown matcher: {method}")

    def _estimate_geometry(
        self, matches: Dict[str, Any], image0: np.ndarray, image1: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        pts0 = matches['keypoints0']
        pts1 = matches['keypoints1']

        if len(pts0) < 4 or len(pts1) < 4:
            return (
                np.eye(3),
                np.empty((0, 2), dtype=np.float64),
                np.empty((0, 2), dtype=np.float64),
                pts0, pts1,
            )

        transform, inlier_mask = estimate_transform_magsac(pts0, pts1)

        if inlier_mask is not None and np.any(inlier_mask):
            inlier_pts0 = pts0[inlier_mask]
            inlier_pts1 = pts1[inlier_mask]
            outlier_pts0 = pts0[~inlier_mask]
            outlier_pts1 = pts1[~inlier_mask]

            refined_inlier_pts0, refined_inlier_pts1 = refine_subpixel(
                image0, image1, inlier_pts0, inlier_pts1
            )
            if len(refined_inlier_pts0) >= 4:
                final_transform, _ = estimate_transform_magsac(
                    refined_inlier_pts0, refined_inlier_pts1
                )
                if final_transform is not None:
                    transform = final_transform

            return transform, refined_inlier_pts0, refined_inlier_pts1, outlier_pts0, outlier_pts1
        else:
            return (
                transform,
                np.empty((0, 2), dtype=np.float64),
                np.empty((0, 2), dtype=np.float64),
                pts0, pts1,
            )

    def _register(self, source: np.ndarray, reference: np.ndarray, transform: np.ndarray) -> np.ndarray:
        return warp_image(source, transform, reference.shape)

    def _evaluate(
        self,
        warped: np.ndarray,
        reference: np.ndarray,
        inlier_pts0: np.ndarray,
        inlier_pts1: np.ndarray,
        outlier_pts0: np.ndarray,
        transform: np.ndarray,
        checkpoints: Optional[Union[Tuple[np.ndarray, np.ndarray], Dict[str, np.ndarray]]] = None,
    ) -> Dict[str, float]:

        ssim_val = compute_ssim(warped, reference)
        total_matches = len(inlier_pts0) + len(outlier_pts0)
        inlier_ratio = compute_inlier_ratio(total_matches, len(inlier_pts0))

        metrics: Dict[str, Any] = {
            "inlier_ratio": inlier_ratio,
            "inlier_count": int(len(inlier_pts0)),
            "total_matches": int(total_matches),
            "ssim": ssim_val,
        }

        def project(pts: np.ndarray) -> np.ndarray:
            pts_h = np.hstack([pts, np.ones((len(pts), 1))])
            proj = (transform @ pts_h.T).T
            return proj[:, :2] / proj[:, 2:]

        # "rmse" is the fit residual on the inliers that produced the transform.
        # It is optimistic by construction; the honest accuracy number is
        # "checkpoint_rmse" below, measured on points never used for fitting.
        if len(inlier_pts0) > 0:
            fit = compute_rmse(inlier_pts1, project(np.asarray(inlier_pts0, dtype=np.float64)))
            metrics["rmse"] = fit["rmse"]
            metrics["rmse_x"] = fit["rmse_x"]
            metrics["rmse_y"] = fit["rmse_y"]

        pts_src_chk = pts_ref_chk = None
        if isinstance(checkpoints, tuple) and len(checkpoints) == 2:
            pts_src_chk, pts_ref_chk = checkpoints
        elif isinstance(checkpoints, dict):
            pts_ref_chk = checkpoints.get('pts_ref', checkpoints.get('reference'))
            pts_src_chk = checkpoints.get('pts_src', checkpoints.get('source'))
        if pts_src_chk is not None and pts_ref_chk is not None:
            pts_src_chk = np.asarray(pts_src_chk, dtype=np.float64).reshape(-1, 2)
            pts_ref_chk = np.asarray(pts_ref_chk, dtype=np.float64).reshape(-1, 2)
            if len(pts_src_chk) > 0 and len(pts_src_chk) == len(pts_ref_chk):
                chk = compute_rmse(pts_ref_chk, project(pts_src_chk))
                metrics["checkpoint_rmse"] = chk["rmse"]
                metrics["checkpoint_rmse_x"] = chk["rmse_x"]
                metrics["checkpoint_rmse_y"] = chk["rmse_y"]
                metrics["checkpoint_count"] = int(len(pts_src_chk))

        return metrics
