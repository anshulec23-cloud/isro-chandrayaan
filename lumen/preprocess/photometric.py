"""Photometric normalization functions for Sun angle invariance."""

import numpy as np
from typing import Optional
from lumen.ingest.metadata import SensorMetadata

def lommel_seeliger_normalize(image: np.ndarray, incidence: np.ndarray | float, 
                              emission: np.ndarray | float, 
                              ref_incidence: float = 30.0, 
                              ref_emission: float = 0.0) -> np.ndarray:
    """Apply Lommel-Seeliger photometric normalization.
    
    Args:
        image: Input radiance image.
        incidence: Incidence angle (degrees) map or scalar.
        emission: Emission angle (degrees) map or scalar.
        ref_incidence: Reference incidence angle to normalize to.
        ref_emission: Reference emission angle to normalize to.
        
    Returns:
        Normalized image.
    """
    inc_rad = np.radians(incidence)
    emi_rad = np.radians(emission)
    ref_inc_rad = np.radians(ref_incidence)
    ref_emi_rad = np.radians(ref_emission)
    
    mu_0 = np.cos(inc_rad)
    mu = np.cos(emi_rad)
    ref_mu_0 = np.cos(ref_inc_rad)
    ref_mu = np.cos(ref_emi_rad)
    
    correction_factor = (ref_mu_0 / (ref_mu_0 + ref_mu)) * ((mu_0 + mu) / mu_0)
    
    return np.clip(image * correction_factor, 0, None)

def minnaert_normalize(image: np.ndarray, incidence: np.ndarray | float, 
                       emission: np.ndarray | float, k: float = 0.6) -> np.ndarray:
    """Apply Minnaert photometric normalization.
    
    Args:
        image: Input radiance image.
        incidence: Incidence angle (degrees) map or scalar.
        emission: Emission angle (degrees) map or scalar.
        k: Minnaert constant.
        
    Returns:
        Normalized image.
    """
    inc_rad = np.radians(incidence)
    emi_rad = np.radians(emission)
    
    mu_0 = np.cos(inc_rad)
    mu = np.cos(emi_rad)
    
    # Avoid division by zero
    mu_0 = np.maximum(mu_0, 1e-5)
    mu = np.maximum(mu, 1e-5)
    
    correction = (mu_0 ** k) * (mu ** (k - 1))
    return np.clip(image / correction, 0, None)

def compute_local_angles(dem: np.ndarray, sun_azimuth: float, sun_elevation: float,
                         viewer_azimuth: float, viewer_elevation: float) -> tuple[np.ndarray, np.ndarray]:
    """Compute local incidence and emission angles using a DEM.
    
    Args:
        dem: Digital Elevation Model array.
        sun_azimuth: Sun azimuth angle in degrees.
        sun_elevation: Sun elevation angle in degrees.
        viewer_azimuth: Sensor azimuth angle in degrees.
        viewer_elevation: Sensor elevation angle in degrees.
        
    Returns:
        Tuple of (local_incidence_map, local_emission_map) in degrees.
    """
    # Simplified mock implementation
    local_incidence = np.full_like(dem, 90.0 - sun_elevation)
    local_emission = np.full_like(dem, 90.0 - viewer_elevation)
    return local_incidence, local_emission

def photometric_normalize(image: np.ndarray, metadata: SensorMetadata, 
                          dem: Optional[np.ndarray] = None, 
                          model: str = 'lommel_seeliger') -> np.ndarray:
    """Main entry point for photometric normalization.
    
    Args:
        image: Input image.
        metadata: Sensor metadata containing global angles.
        dem: Optional DEM for local angle computation.
        model: Model name ('lommel_seeliger' or 'minnaert').
        
    Returns:
        Normalized image.
    """
    if dem is not None:
        incidence, emission = compute_local_angles(
            dem, metadata.sun_azimuth, metadata.sun_elevation, 
            0.0, 90.0 - metadata.emission_angle
        )
    else:
        incidence = metadata.incidence_angle
        emission = metadata.emission_angle
        
    if model == 'lommel_seeliger':
        return lommel_seeliger_normalize(image, incidence, emission)
    elif model == 'minnaert':
        return minnaert_normalize(image, incidence, emission)
    else:
        raise ValueError(f"Unknown photometric model: {model}")
