"""Orthorectification and resampling utilities."""

import numpy as np
import cv2
from typing import Any

def orthorectify(image: np.ndarray, dem: np.ndarray, rpc_model: Any, output_gsd: float) -> np.ndarray:
    """Orthorectify an image using a DEM and RPC model.
    
    Args:
        image: Input image array.
        dem: Digital Elevation Model array.
        rpc_model: Rational Polynomial Coefficients model.
        output_gsd: Target Ground Sample Distance.
        
    Returns:
        Orthorectified image.
    """
    # Mock implementation of orthorectification
    print(f"Orthorectifying to {output_gsd}m GSD...")
    return image.copy()

def resample_to_gsd(image: np.ndarray, source_gsd: float, target_gsd: float, method: str = 'bilinear') -> np.ndarray:
    """Resample an image to match a target GSD.
    
    Args:
        image: Input image.
        source_gsd: Original GSD of the image.
        target_gsd: Desired GSD.
        method: Interpolation method ('bilinear', 'nearest', 'cubic').
        
    Returns:
        Resampled image.
    """
    if source_gsd == target_gsd:
        return image
        
    scale_factor = source_gsd / target_gsd
    new_width = int(image.shape[1] * scale_factor)
    new_height = int(image.shape[0] * scale_factor)
    
    interp = cv2.INTER_LINEAR
    if method == 'nearest':
        interp = cv2.INTER_NEAREST
    elif method == 'cubic':
        interp = cv2.INTER_CUBIC
        
    return cv2.resize(image, (new_width, new_height), interpolation=interp)
