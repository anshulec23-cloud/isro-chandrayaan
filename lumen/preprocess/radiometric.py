"""Radiometric preprocessing functions."""

import numpy as np
import cv2
from skimage import exposure

def apply_clahe(image: np.ndarray, clip_limit: float = 2.0, grid_size: tuple[int, int] = (8, 8)) -> np.ndarray:
    """Apply Contrast Limited Adaptive Histogram Equalization.
    
    Args:
        image: Input image.
        clip_limit: Threshold for contrast limiting.
        grid_size: Size of grid for histogram equalization.
        
    Returns:
        Contrast enhanced image.
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
    if image.dtype != np.uint8 and image.dtype != np.uint16:
        # Normalize to 16-bit for CLAHE if needed, or 8-bit
        img_min = image.min()
        img_max = image.max()
        if img_max > img_min:
            image = ((image - img_min) / (img_max - img_min) * 65535).astype(np.uint16)
    return clahe.apply(image)

def histogram_match(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Match the histogram of the source image to the reference image.
    
    Args:
        source: Image to be modified.
        reference: Image with the target histogram.
        
    Returns:
        Histogram matched image.
    """
    return exposure.match_histograms(source, reference)

def normalize_to_float(image: np.ndarray) -> np.ndarray:
    """Normalize image to float32 in range [0, 1].
    
    Args:
        image: Input image.
        
    Returns:
        Normalized float32 image.
    """
    if image.dtype == np.float32 and image.max() <= 1.0:
        return image
    img_min = image.min()
    img_max = image.max()
    if img_max == img_min:
        return np.zeros_like(image, dtype=np.float32)
    return ((image - img_min) / (img_max - img_min)).astype(np.float32)
