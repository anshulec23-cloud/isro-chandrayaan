"""
Photometric normalization models and utilities for lunar imagery.
"""

import numpy as np
import logging
from typing import Tuple, Dict, Any, Optional

__all__ = [
    'lommel_seeliger_normalize',
    'minnaert_normalize',
    'compute_local_angles',
    'create_shadow_mask',
    'photometric_normalize'
]

logger = logging.getLogger(__name__)


def _phase_function(alpha_deg: np.ndarray) -> np.ndarray:
    """Simple lunar phase function approximation."""
    alpha_rad = np.radians(alpha_deg)
    return np.exp(-0.04 * alpha_deg)  # Basic approximation


def lommel_seeliger_normalize(
    image: np.ndarray,
    inc: np.ndarray,
    emi: np.ndarray,
    phase: np.ndarray,
    shadow_mask: Optional[np.ndarray] = None,
    alpha: float = 30.0
) -> np.ndarray:
    """
    Applies Lommel-Seeliger normalization.
    
    Args:
        image: Input reflectance/radiance array.
        inc: Local incidence angles in degrees.
        emi: Local emission angles in degrees.
        phase: Phase angles in degrees.
        shadow_mask: Boolean mask of shadow regions (True = shadow).
        alpha: Target standard phase angle for normalization.
        
    Returns:
        np.ndarray: Normalized image.
    """
    mu0 = np.cos(np.radians(inc))
    mu = np.cos(np.radians(emi))
    
    # Epsilon guards for numerical stability
    mu0 = np.clip(mu0, 1e-6, 1.0)
    mu = np.clip(mu, 1e-6, 1.0)
    
    # LS reflectance model: R = f(alpha) * (mu0 / (mu0 + mu))
    f_alpha = _phase_function(phase)
    f_alpha_target = _phase_function(np.full_like(phase, alpha))
    
    # Compute correction factor
    # R_norm = R_obs * (R_model_target / R_model_obs)
    ls_obs = mu0 / (mu0 + mu)
    # Using standardized incidence (e.g. 30) and emission (0) could be better, 
    # but here we correct primarily for the topographic variation.
    # Target geometry assumes flat surface: inc = alpha, emi = 0
    mu0_target = np.cos(np.radians(alpha))
    mu_target = 1.0
    ls_target = mu0_target / (mu0_target + mu_target)
    
    correction = (f_alpha_target * ls_target) / (f_alpha * ls_obs)
    
    norm_img = image * correction
    
    if shadow_mask is not None:
        norm_img[shadow_mask] = 0.0
        
    return norm_img


def minnaert_normalize(
    image: np.ndarray,
    inc: np.ndarray,
    emi: np.ndarray,
    phase: np.ndarray,
    shadow_mask: Optional[np.ndarray] = None,
    k: Optional[float] = None
) -> np.ndarray:
    """
    Applies Minnaert normalization.
    
    Args:
        image: Input reflectance/radiance array.
        inc: Local incidence angles in degrees.
        emi: Local emission angles in degrees.
        phase: Phase angles in degrees.
        shadow_mask: Boolean mask of shadow regions (True = shadow).
        k: Minnaert parameter. If None, it is estimated via linear regression.
        
    Returns:
        np.ndarray: Normalized image.
    """
    mu0 = np.cos(np.radians(inc))
    mu = np.cos(np.radians(emi))
    
    mu0 = np.clip(mu0, 1e-6, 1.0)
    mu = np.clip(mu, 1e-6, 1.0)
    
    valid_mask = (mu0 > 1e-3) & (mu > 1e-3)
    if shadow_mask is not None:
        valid_mask &= ~shadow_mask
        
    if k is None:
        # Estimate k via log-space linear regression:
        # log(R * mu) = log(B0) + k * log(mu0 * mu)
        y = np.log(np.clip(image[valid_mask] * mu[valid_mask], 1e-6, None))
        x = np.log(np.clip(mu0[valid_mask] * mu[valid_mask], 1e-6, None))
        
        if len(x) > 10:
            A = np.vstack([x, np.ones(len(x))]).T
            k, _ = np.linalg.lstsq(A, y, rcond=None)[0]
            k = np.clip(k, 0.0, 1.0)
            logger.info(f"Auto-estimated Minnaert k: {k:.4f}")
        else:
            k = 0.5
            logger.warning("Not enough valid pixels to estimate k. Defaulting to 0.5.")
            
    # Normalize: R_norm = R_obs * (mu_target^k) / (mu0^k * mu^(k-1))
    # Target geometry: mu0_target = 1 (inc=0), mu_target = 1 (emi=0)
    # R_norm = R_obs / (mu0^k * mu^(k-1))
    correction = 1.0 / ((mu0**k) * (mu**(k - 1)))
    
    norm_img = image * correction
    
    if shadow_mask is not None:
        norm_img[shadow_mask] = 0.0
        
    return norm_img


def compute_local_angles(
    dem: np.ndarray,
    resolution: float,
    az_sun: float,
    el_sun: float,
    az_view: float,
    el_view: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes local incidence and emission angles using a DEM.
    
    Args:
        dem: Digital Elevation Model array.
        resolution: Spatial resolution in meters/pixel.
        az_sun: Sun azimuth angle in degrees.
        el_sun: Sun elevation angle in degrees.
        az_view: View azimuth angle in degrees.
        el_view: View elevation angle in degrees.
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: Local incidence and emission angles in degrees.
    """
    # Compute surface normals from gradient
    dy, dx = np.gradient(dem, resolution)
    
    # Normal vector: n = (-dz/dx, -dz/dy, 1) / ||n||
    nx = -dx
    ny = -dy
    nz = np.ones_like(dem)
    
    norm = np.sqrt(nx**2 + ny**2 + nz**2)
    nx /= norm
    ny /= norm
    nz /= norm
    
    # Sun vector: s = (sin(az)cos(el), cos(az)cos(el), sin(el))
    az_s_rad = np.radians(az_sun)
    el_s_rad = np.radians(el_sun)
    sx = np.sin(az_s_rad) * np.cos(el_s_rad)
    sy = np.cos(az_s_rad) * np.cos(el_s_rad)
    sz = np.sin(el_s_rad)
    
    # View vector
    az_v_rad = np.radians(az_view)
    el_v_rad = np.radians(el_view)
    vx = np.sin(az_v_rad) * np.cos(el_v_rad)
    vy = np.cos(az_v_rad) * np.cos(el_v_rad)
    vz = np.sin(el_v_rad)
    
    # Local incidence = arccos(n . s)
    dot_s = np.clip(nx*sx + ny*sy + nz*sz, -1.0, 1.0)
    inc_local = np.degrees(np.arccos(dot_s))
    
    # Local emission = arccos(n . v)
    dot_v = np.clip(nx*vx + ny*vy + nz*vz, -1.0, 1.0)
    emi_local = np.degrees(np.arccos(dot_v))
    
    return inc_local, emi_local


def create_shadow_mask(
    image: np.ndarray,
    inc: np.ndarray,
    dn_threshold: float,
    inc_threshold: float = 85.0
) -> np.ndarray:
    """
    Creates a binary mask of shadowed regions.
    
    Args:
        image: Input image array.
        inc: Incidence angles array.
        dn_threshold: Digital number threshold for shadows.
        inc_threshold: Incidence angle threshold above which shadows are assumed.
        
    Returns:
        np.ndarray: Boolean shadow mask (True = shadow).
    """
    mask = (image < dn_threshold) | (inc > inc_threshold)
    
    # Optional morphological operations could be applied here
    # from scipy.ndimage import binary_erosion, binary_dilation
    # mask = binary_erosion(mask, iterations=1)
    # mask = binary_dilation(mask, iterations=1)
    
    return mask


def photometric_normalize(
    image: np.ndarray,
    inc: np.ndarray,
    emi: np.ndarray,
    phase: np.ndarray,
    dn_threshold: float = 1e-4,
    method: str = 'auto'
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Orchestrates the photometric normalization process.
    
    Args:
        image: Input image.
        inc: Local incidence angles.
        emi: Local emission angles.
        phase: Phase angles.
        dn_threshold: Threshold for shadow masking.
        method: 'lommel_seeliger', 'minnaert', or 'auto'.
        
    Returns:
        Tuple: (Normalized image, Shadow mask, Metadata dictionary).
    """
    shadow_mask = create_shadow_mask(image, inc, dn_threshold)
    
    if method == 'auto':
        avg_inc = np.nanmean(inc[~shadow_mask])
        if avg_inc > 60:
            method = 'lommel_seeliger'
            logger.info("High incidence angles detected, auto-selected Lommel-Seeliger.")
        else:
            method = 'minnaert'
            logger.info("Moderate/low incidence angles detected, auto-selected Minnaert.")
            
    meta = {'method_used': method, 'shadow_pixels': int(np.sum(shadow_mask))}
    
    if method == 'lommel_seeliger':
        norm_img = lommel_seeliger_normalize(image, inc, emi, phase, shadow_mask)
    elif method == 'minnaert':
        norm_img = minnaert_normalize(image, inc, emi, phase, shadow_mask)
    else:
        raise ValueError(f"Unknown normalization method: {method}")
        
    return norm_img, shadow_mask, meta
