"""Main orchestration pipeline for the LUMEN project."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import numpy as np

from lumen.config import Settings
from lumen.ingest.pds4_parser import parse_pds4_label, load_image_from_pds4
from lumen.ingest.metadata import extract_metadata
from lumen.preprocess.photometric import photometric_normalize
from lumen.features.deep_matcher import DeepMatcher
from lumen.geometry.outlier_reject import estimate_transform_magsac
from lumen.registration.warp import create_registered_product
from lumen.evaluation.metrics import compute_reprojection_error, compute_ssim

@dataclass
class RegistrationResult:
    warped_image: np.ndarray
    transform_matrix: np.ndarray
    match_points: list[dict[str, float]]
    metrics: dict[str, float]
    metadata: dict[str, Any]

class RegistrationPipeline:
    def __init__(self, config: Settings):
        self.config = config
        self.matcher = DeepMatcher()
        
    def run(self, source_path: Path, reference_path: Path, 
            source_sensor: str, ref_sensor: str) -> RegistrationResult:
        """Run the full end-to-end registration pipeline."""
        
        # 1. Ingest
        src_label = parse_pds4_label(source_path)
        ref_label = parse_pds4_label(reference_path)
        
        src_img = load_image_from_pds4(src_label)
        ref_img = load_image_from_pds4(ref_label)
        
        src_meta = extract_metadata(src_label)
        
        # 2. Preprocess (Photometric normalization)
        src_norm = photometric_normalize(src_img, src_meta)
        ref_norm = ref_img # Assuming reference is already standard
        
        # 3. Features
        match_data = self.matcher.match(src_norm, ref_norm)
        kp0 = match_data['keypoints0']
        kp1 = match_data['keypoints1']
        
        # 4. Geometry
        transform, inlier_mask = estimate_transform_magsac(kp0, kp1, 
                                                          confidence=self.config.MAGSAC_CONFIDENCE,
                                                          max_iters=self.config.MAGSAC_MAX_ITERS)
        
        # 5. Registration
        product = create_registered_product(src_img, ref_img, transform)
        warped_img = product['warped_image']
        
        # 6. Evaluation
        inliers_src = kp0[inlier_mask]
        inliers_dst = kp1[inlier_mask]
        repr_err = compute_reprojection_error(inliers_src, inliers_dst, transform)
        ssim_val = compute_ssim(warped_img, ref_img)
        
        metrics = {
            "reprojection_error": repr_err,
            "ssim": ssim_val,
            "inlier_ratio": float(np.sum(inlier_mask)) / max(len(kp0), 1)
        }
        
        matches = [{"x_src": float(p[0]), "y_src": float(p[1]), "x_ref": float(q[0]), "y_ref": float(q[1])} 
                   for p, q in zip(inliers_src, inliers_dst)]
        
        return RegistrationResult(
            warped_image=warped_img,
            transform_matrix=transform,
            match_points=matches,
            metrics=metrics,
            metadata={"source": str(source_path), "reference": str(reference_path)}
        )
