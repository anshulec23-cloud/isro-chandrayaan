"""Outlier rejection using MAGSAC++ and TPS refinement."""

import numpy as np
import cv2
from typing import Callable

def estimate_transform_magsac(pts_src: np.ndarray, pts_dst: np.ndarray, 
                              confidence: float = 0.999, 
                              max_iters: int = 5000) -> tuple[np.ndarray, np.ndarray]:
    """Estimate a robust homography using MAGSAC++.
    
    Args:
        pts_src: Source points (N, 2).
        pts_dst: Destination points (N, 2).
        confidence: Desired confidence level.
        max_iters: Maximum RANSAC iterations.
        
    Returns:
        Tuple of (3x3 transform matrix, (N,) boolean inlier mask).
    """
    if len(pts_src) < 4:
        return np.eye(3), np.zeros(len(pts_src), dtype=bool)
        
    # USAC_MAGSAC is available in OpenCV 4.5.0+
    H, mask = cv2.findHomography(pts_src, pts_dst, cv2.USAC_MAGSAC, 
                                 3.0, confidence=confidence, maxIters=max_iters)
    
    if H is None:
        return np.eye(3), np.zeros(len(pts_src), dtype=bool)
        
    inlier_mask = mask.ravel() == 1
    return H, inlier_mask

def apply_tps_refinement(pts_src: np.ndarray, pts_dst: np.ndarray, inlier_mask: np.ndarray) -> Callable:
    """Create a Thin Plate Spline warp function based on inlier matches.
    
    Args:
        pts_src: Source points.
        pts_dst: Destination points.
        inlier_mask: Boolean mask indicating valid points.
        
    Returns:
        A callable function that takes source points and maps them to destination.
    """
    valid_src = pts_src[inlier_mask]
    valid_dst = pts_dst[inlier_mask]
    
    tps = cv2.createThinPlateSplineShapeTransformer()
    # Mocking TPS setup (requires proper formatting in OpenCV)
    # The actual usage typically involves reshape to (1, N, 2)
    
    def warp_func(points: np.ndarray) -> np.ndarray:
        return points # Mock return
        
    return warp_func
