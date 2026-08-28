import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, Union
from pathlib import Path

import numpy as np

from lumen.ingest.pds4_parser import parse_pds4, load_binary_image
from lumen.ingest.metadata import extract_metadata, compute_scale_ratio, get_bridge_sensor
from lumen.preprocess.radiometric import apply_clahe, normalize_to_float
from lumen.preprocess.photometric import photometric_normalize
from lumen.features.deep_matcher import DeepMatcher
from lumen.features.rift2 import RIFT2Matcher
from lumen.geometry.outlier_reject import estimate_transform_magsac
from lumen.registration.warp import warp_image, create_registered_product
from lumen.evaluation.metrics import compute_rmse, compute_ssim, compute_inlier_ratio, create_checkerboard
# from lumen.geometry.estimation import estimate_magsac, refine_subpixel
# from lumen.geometry.warp import warp_image
# from lumen.evaluation.metrics import compute_all_metrics

logger = logging.getLogger(__name__)

__all__ = [
    "RegistrationResult",
    "PipelineStage",
    "PipelineCallback",
    "RegistrationPipeline",
]

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
        """Initialize the pipeline with configuration and optional callback.

        Args:
            config: Pipeline configuration object.
            callback: Optional callback for progress reporting.
        """
        self.config = config
        self.callback = callback
        logger.info("Initializing RegistrationPipeline")
        # Preload models if necessary based on config

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

    def run(self, source_path: str, reference_path: str, source_sensor: str, ref_sensor: str, 
            dem_path: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> RegistrationResult:
        """Run the full registration pipeline.

        Args:
            source_path: Path to the source image (to be warped).
            reference_path: Path to the reference image.
            source_sensor: Sensor identifier for the source image.
            ref_sensor: Sensor identifier for the reference image.
            dem_path: Optional path to a DEM for orthorectification.
            options: Optional override configuration options.

        Returns:
            RegistrationResult containing the registered image and metrics.
        """
        start_time = time.time()
        options = options or {}
        method = options.get("feature_method", "auto")

        try:
            # 1. INGEST
            self._notify_start(PipelineStage.INGEST, "Ingesting source and reference images")
            source_img, source_meta = self._ingest(source_path)
            ref_img, ref_meta = self._ingest(reference_path)
            dem_data = self._ingest(dem_path)[0] if dem_path else None
            self._notify_complete(PipelineStage.INGEST)

            # 2. PREPROCESS
            self._notify_start(PipelineStage.PREPROCESS, "Preprocessing images")
            source_pre = self._preprocess(source_img, source_meta, dem_data)
            ref_pre = self._preprocess(ref_img, ref_meta, dem_data)
            self._notify_complete(PipelineStage.PREPROCESS)

            # 3. FEATURES
            self._notify_start(PipelineStage.FEATURES, f"Extracting features using method: {method}")
            # Handling Bridge Registration logic if method='auto' implies extreme scale
            scale_ratio = options.get("scale_ratio", 1.0)
            if method == "auto" and scale_ratio > 20:
                logger.info("Scale ratio > 20, using bridge registration")
                matches = self._bridge_feature_extraction(source_pre, ref_pre, source_sensor, ref_sensor)
            else:
                matches = self._extract_features(source_pre, ref_pre, method, source_sensor, ref_sensor)
            
            self._notify_complete(PipelineStage.FEATURES, {"match_count": len(matches)})

            # 4. GEOMETRY
            self._notify_start(PipelineStage.GEOMETRY, "Estimating geometric transform")
            transform, inliers, outliers = self._estimate_geometry(matches)
            self._notify_complete(PipelineStage.GEOMETRY, {"inlier_count": len(inliers)})

            # 5. REGISTER
            self._notify_start(PipelineStage.REGISTER, "Warping source image")
            warped = self._register(source_pre, ref_pre, transform)
            self._notify_complete(PipelineStage.REGISTER)

            # 6. EVALUATE
            self._notify_start(PipelineStage.EVALUATE, "Evaluating registration quality")
            metrics = self._evaluate(warped, ref_pre, inliers, outliers, transform)
            self._notify_complete(PipelineStage.EVALUATE, metrics)

            elapsed = time.time() - start_time
            logger.info(f"Registration completed successfully in {elapsed:.2f}s")
            
            # Construct mock visualization images
            checkerboard = np.zeros_like(warped)
            overlay = np.zeros_like(warped)

            return RegistrationResult(
                warped_image=warped,
                transform_matrix=transform,
                match_points=inliers + outliers, # In reality, structured appropriately
                metrics=metrics,
                metadata={"source_sensor": source_sensor, "ref_sensor": ref_sensor},
                elapsed_seconds=elapsed,
                source_path=source_path,
                reference_path=reference_path,
                checkerboard_image=checkerboard,
                match_overlay_image=overlay
            )

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise RuntimeError(f"Registration pipeline failed: {e}") from e

    def _ingest(self, path: Union[str, Path]) -> Tuple[np.ndarray, Dict[str, Any]]:
        logger.debug(f"Ingesting {path}")
        label = parse_pds4(path)
        img = load_binary_image(label)
        meta = extract_metadata(label)
        return img, meta

    def _preprocess(self, image: np.ndarray, metadata: Dict[str, Any], dem: Optional[np.ndarray] = None) -> np.ndarray:
        logger.debug("Applying radiometric & photometric preprocessing")
        img_clahe = apply_clahe(image)
        img_float = normalize_to_float(img_clahe)
        img_photo = photometric_normalize(img_float, metadata, dem=dem)
        return img_photo

    def _extract_features(self, image0: np.ndarray, image1: np.ndarray, method: str, 
                          sensor0: str, sensor1: str) -> Dict[str, Any]:
        if method == "auto":
            if sensor0 == sensor1:
                method = "deep"
            else:
                method = "rift2"
                
        if method == "deep":
            matcher = DeepMatcher()
            return matcher.match(image0, image1)
        elif method == "rift2":
            matcher = RIFT2Matcher()
            return matcher.match(image0, image1)
        else:
            raise ValueError(f"Unknown matcher: {method}")

    def _bridge_feature_extraction(self, image0: np.ndarray, image1: np.ndarray, 
                                   sensor0: str, sensor1: str) -> Dict[str, Any]:
        # simplified fallback if bridge needed but intermediate not provided
        logger.warning("Bridge registration logic skeleton. Falling back to direct RIFT2.")
        return self._extract_features(image0, image1, "rift2", sensor0, sensor1)

    def _estimate_geometry(self, match_data: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        kp0 = match_data['keypoints0']
        kp1 = match_data['keypoints1']
        
        result = estimate_transform_magsac(kp0, kp1)
        transform = result.matrix
        inliers_mask = result.inlier_mask
        
        inliers_idx = np.where(inliers_mask)[0]
        outliers_idx = np.where(~inliers_mask)[0]
        
        return transform, inliers_idx, outliers_idx

    def _register(self, source: np.ndarray, reference: np.ndarray, transform: np.ndarray) -> np.ndarray:
        return warp_image(source, transform, reference.shape)

    def _evaluate(self, warped: np.ndarray, reference: np.ndarray, 
                  inlier_pts: np.ndarray, outlier_pts: np.ndarray, transform: np.ndarray) -> Dict[str, float]:
        
        ssim_val = compute_ssim(warped, reference)
        
        return {
            "inlier_ratio": float(len(inlier_pts)) / float(len(inlier_pts) + len(outlier_pts) + 1e-6),
            "inlier_count": int(len(inlier_pts)),
            "ssim": ssim_val
        }
