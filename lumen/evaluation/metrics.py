"""Evaluation metrics for image registration."""

import numpy as np
from skimage.metrics import structural_similarity as ssim
import cv2
from typing import Any

def compute_rmse(pts_ref: np.ndarray, pts_transformed: np.ndarray) -> dict[str, float]:
    """Compute Root Mean Square Error between reference and transformed points.
    
    Args:
        pts_ref: Ground truth or reference points (N, 2).
        pts_transformed: Transformed source points (N, 2).
        
    Returns:
        Dictionary with overall rmse, rmse_x, rmse_y.
    """
    diff = pts_ref - pts_transformed
    mse_x = np.mean(diff[:, 0]**2)
    mse_y = np.mean(diff[:, 1]**2)
    return {
        "rmse": float(np.sqrt(mse_x + mse_y)),
        "rmse_x": float(np.sqrt(mse_x)),
        "rmse_y": float(np.sqrt(mse_y))
    }

def compute_inlier_ratio(total_matches: int, inlier_count: int) -> float:
    """Compute the ratio of inliers to total matches."""
    if total_matches == 0:
        return 0.0
    return float(inlier_count / total_matches)

def compute_ssim(image0: np.ndarray, image1: np.ndarray) -> float:
    """Compute Structural Similarity Index Measure.
    
    Images must be same size and type.
    """
    # Ensure uint8 for standard SSIM if they aren't already
    if image0.dtype != np.uint8:
        image0 = cv2.normalize(image0, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    if image1.dtype != np.uint8:
        image1 = cv2.normalize(image1, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    
    score, _ = ssim(image0, image1, full=True)
    return float(score)

def compute_reprojection_error(pts_src: np.ndarray, pts_dst: np.ndarray, transform: np.ndarray) -> float:
    """Compute mean reprojection error given a homography."""
    if len(pts_src) == 0:
        return 0.0
        
    pts_src_h = np.hstack([pts_src, np.ones((len(pts_src), 1))])
    pts_proj = (transform @ pts_src_h.T).T
    pts_proj = pts_proj[:, :2] / pts_proj[:, 2:]
    
    diff = pts_proj - pts_dst
    return float(np.mean(np.linalg.norm(diff, axis=1)))

def create_checkerboard(image0: np.ndarray, image1: np.ndarray, grid_size: tuple[int, int] = (8, 8)) -> np.ndarray:
    """Create a checkerboard overlay of two images for visual evaluation."""
    assert image0.shape == image1.shape
    h, w = image0.shape[:2]
    
    r_step = h // grid_size[0]
    c_step = w // grid_size[1]
    
    mask = np.indices((h, w))
    checker = ((mask[0] // r_step) + (mask[1] // c_step)) % 2
    
    result = np.where(checker, image0, image1)
    return result

def generate_evaluation_report(all_metrics: dict[str, Any]) -> dict[str, Any]:
    """Compile a final evaluation report."""
    return {
        "status": "success",
        "metrics": all_metrics
    }
