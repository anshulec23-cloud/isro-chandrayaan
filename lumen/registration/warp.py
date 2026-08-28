"""Image warping operations."""

import numpy as np
import cv2
from typing import Any

def warp_image(source: np.ndarray, transform_matrix: np.ndarray, 
               output_shape: tuple[int, int], method: str = 'cubic') -> np.ndarray:
    """Warp source image to reference perspective.
    
    Args:
        source: Source image to warp.
        transform_matrix: 3x3 homography matrix.
        output_shape: (height, width) of output image.
        method: Interpolation method.
        
    Returns:
        Warped image array.
    """
    interp = cv2.INTER_LINEAR
    if method == 'cubic':
        interp = cv2.INTER_CUBIC
    elif method == 'nearest':
        interp = cv2.INTER_NEAREST
        
    return cv2.warpPerspective(source, transform_matrix, (output_shape[1], output_shape[0]), 
                               flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

def create_registered_product(source: np.ndarray, reference: np.ndarray, 
                              transform: np.ndarray) -> dict[str, Any]:
    """Generate final registered product and metadata.
    
    Args:
        source: Source image.
        reference: Reference image defining the coordinate space.
        transform: Computed transformation matrix.
        
    Returns:
        Dictionary containing warped image and metadata.
    """
    warped = warp_image(source, transform, reference.shape[:2])
    return {
        "warped_image": warped,
        "transform_matrix": transform,
        "match_points": [] # To be populated by pipeline
    }
