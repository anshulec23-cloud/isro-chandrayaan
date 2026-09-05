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
from lumen.ingest.metadata import extract_metadata, compute_scale_ratio, get_bridge_sensor, SENSOR_SPECS
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
from lumen.evaluation.metrics import compute_rmse, compute_ssim, compute_inlier_ratio, create_checkerboard

logger = logging.getLogger(__name__)

__all__ = [
    "RegistrationResult",
    "PipelineStage",
    "PipelineCallback",
    "RegistrationPipeline",
]

# Maximum output dimension (px) applied AFTER orthorectification.
_MAX_ORTHO_DIM: int = 2048


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
            source_img, source_meta = self._ingest(source_path)
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
            source_pre = self._normalize_image(source_ortho, source_meta)
            ref_pre = self._normalize_image(ref_ortho, ref_meta)
            if debug_path:
                _save_debug_preview(source_pre, debug_path / f"{pair_name}_src_04_photometric_norm.png")
                _save_debug_preview(ref_pre, debug_path / f"{pair_name}_ref_04_photometric_norm.png")

            self._notify_complete(PipelineStage.PREPROCESS)

            # ── 3. FEATURES ────────────────────────────────────────────────
            self._notify_start(PipelineStage.FEATURES, f"Extracting features using method: {method}")
            scale_ratio = options.get("scale_ratio") or (src_gsd / ref_gsd if ref_gsd > 0 else 1.0)
            if method == "auto" and scale_ratio > 20:
                logger.info("Scale ratio > 20, using bridge registration")
                matches = self._bridge_feature_extraction(source_pre, ref_pre, source_sensor, ref_sensor)
            else:
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
            overlay = np.zeros_like(warped)

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
                match_overlay_image=overlay
            )

        except NoOverlapError:
            # Re-raise without wrapping — the message already names both footprints.
            raise
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise RuntimeError(f"Registration pipeline failed: {e}") from e

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _ingest(self, path: Union[str, Path]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Parse PDS4 XML and load the raw binary array."""
        logger.debug(f"Ingesting {path}")
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
    ) -> np.ndarray:
        """Apply radiometric normalisation and photometric correction.

        Called AFTER overlap cropping so normalisation is only computed on
        the shared region that will actually be fed to the feature matcher.
        """
        logger.debug(f"Normalizing image {image.shape}")

        img_float = normalize_to_float(image)

        sun_el   = metadata.get('solar_elevation',    45.0)
        view_el  = metadata.get('instrument_elevation', 90.0)
        phase_ang = metadata.get('phase_angle',        45.0)

        inc   = np.full(img_float.shape, 90.0 - sun_el)
        emi   = np.full(img_float.shape, 90.0 - view_el)
        phase = np.full(img_float.shape, phase_ang)

        img_photo, _, _ = photometric_normalize(img_float, inc, emi, phase)
        return apply_clahe(img_photo)

    # Preserved unchanged from previous version:

    def _extract_features(
        self, image0: np.ndarray, image1: np.ndarray,
        method: str, sensor0: str, sensor1: str
    ) -> Dict[str, Any]:
        if method == "auto":
            method = "deep" if sensor0 == sensor1 else "rift2"

        if method == "deep":
            matcher = DeepMatcher()
            return matcher.match(image0, image1)
        elif method == "rift2":
            return match_rift2(image0, image1)
        else:
            raise ValueError(f"Unknown matcher: {method}")

    def _bridge_feature_extraction(
        self, image0: np.ndarray, image1: np.ndarray,
        sensor0: str, sensor1: str
    ) -> Dict[str, Any]:
        logger.warning("Bridge registration logic skeleton. Falling back to direct RIFT2.")
        return self._extract_features(image0, image1, "rift2", sensor0, sensor1)

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

        if len(inlier_pts0) > 0:
            pts_src_h = np.hstack([inlier_pts0, np.ones((len(inlier_pts0), 1))])
            pts_proj = (transform @ pts_src_h.T).T
            pts_transformed = pts_proj[:, :2] / pts_proj[:, 2:]
            inlier_rmse_dict = compute_rmse(inlier_pts1, pts_transformed)
            metrics["rmse"] = inlier_rmse_dict.get("rmse", 0.0)
            metrics["rmse_x"] = inlier_rmse_dict.get("rmse_x", 0.0)
            metrics["rmse_y"] = inlier_rmse_dict.get("rmse_y", 0.0)

        if checkpoints is not None:
            if isinstance(checkpoints, tuple) and len(checkpoints) == 2:
                pts_src_chk, pts_ref_chk = checkpoints
                pts_src_chk = np.asarray(pts_src_chk, dtype=np.float64)
                pts_ref_chk = np.asarray(pts_ref_chk, dtype=np.float64)
                if len(pts_src_chk) > 0 and len(pts_ref_chk) > 0:
                    pts_src_h = np.hstack([pts_src_chk, np.ones((len(pts_src_chk), 1))])
                    pts_proj = (transform @ pts_src_h.T).T
                    pts_transformed = pts_proj[:, :2] / pts_proj[:, 2:]
                    metrics.update(compute_rmse(pts_ref_chk, pts_transformed))
            elif isinstance(checkpoints, dict):
                pts_ref_chk = checkpoints.get('pts_ref', checkpoints.get('reference'))
                pts_src_chk = checkpoints.get('pts_src', checkpoints.get('source'))
                if pts_ref_chk is not None and pts_src_chk is not None:
                    pts_src_chk = np.asarray(pts_src_chk, dtype=np.float64)
                    pts_ref_chk = np.asarray(pts_ref_chk, dtype=np.float64)
                    if len(pts_src_chk) > 0 and len(pts_ref_chk) > 0:
                        pts_src_h = np.hstack([pts_src_chk, np.ones((len(pts_src_chk), 1))])
                        pts_proj = (transform @ pts_src_h.T).T
                        pts_transformed = pts_proj[:, :2] / pts_proj[:, 2:]
                        metrics.update(compute_rmse(pts_ref_chk, pts_transformed))

        return metrics
