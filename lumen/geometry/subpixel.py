"""Subpixel refinement using Phase Correlation."""

import numpy as np
from skimage.registration import phase_cross_correlation
import cv2

def phase_correlate_subpixel(patch0: np.ndarray, patch1: np.ndarray, 
                             upsample_factor: int = 100) -> tuple[float, float, float]:
    """Perform phase correlation to find subpixel shifts between patches.
    
    Args:
        patch0: Source image patch.
        patch1: Reference image patch.
        upsample_factor: Upsampling factor for subpixel accuracy.
        
    Returns:
        Tuple of (dx, dy, confidence/error).
    """
    shift, error, diffphase = phase_cross_correlation(
        patch0, patch1, upsample_factor=upsample_factor, return_error=True)
    return float(shift[1]), float(shift[0]), float(error)

def refine_matches_subpixel(image0: np.ndarray, image1: np.ndarray, 
                            matches0: np.ndarray, matches1: np.ndarray, 
                            keypoints0: np.ndarray, keypoints1: np.ndarray, 
                            patch_size: int = 64, upsample_factor: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Refine match coordinates using phase correlation on local patches.
    
    Args:
        image0: Source image.
        image1: Reference image.
        matches0: Indices of matched keypoints in image0.
        matches1: Indices of matched keypoints in image1.
        keypoints0: Coordinates of keypoints in image0.
        keypoints1: Coordinates of keypoints in image1.
        patch_size: Size of local patch to extract around keypoints.
        upsample_factor: Factor for subpixel accuracy.
        
    Returns:
        Refined coordinates (refined_kp0, refined_kp1).
    """
    half_patch = patch_size // 2
    refined_kp0 = []
    refined_kp1 = []
    
    kp0_matched = keypoints0[matches0]
    kp1_matched = keypoints1[matches1]
    
    for i in range(len(kp0_matched)):
        x0, y0 = map(int, kp0_matched[i])
        x1, y1 = map(int, kp1_matched[i])
        
        # Ensure patches are within bounds
        if (x0 - half_patch < 0 or y0 - half_patch < 0 or 
            x1 - half_patch < 0 or y1 - half_patch < 0 or
            x0 + half_patch >= image0.shape[1] or y0 + half_patch >= image0.shape[0] or
            x1 + half_patch >= image1.shape[1] or y1 + half_patch >= image1.shape[0]):
            refined_kp0.append(kp0_matched[i])
            refined_kp1.append(kp1_matched[i])
            continue
            
        patch0 = image0[y0-half_patch:y0+half_patch, x0-half_patch:x0+half_patch]
        patch1 = image1[y1-half_patch:y1+half_patch, x1-half_patch:x1+half_patch]
        
        dx, dy, _ = phase_correlate_subpixel(patch0, patch1, upsample_factor)
        
        refined_kp0.append([x0 + dx, y0 + dy])
        refined_kp1.append([x1, y1]) # Keep ref stationary
        
    return np.array(refined_kp0), np.array(refined_kp1)
