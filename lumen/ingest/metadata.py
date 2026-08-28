"""
Metadata structures and utilities for Chandrayaan-2 payloads.
"""

import math
import logging
from typing import Dict, Any, Tuple, Optional

__all__ = [
    'SENSOR_SPECS',
    'compute_phase_angle',
    'get_bridge_sensor',
    'compute_scale_ratio',
    'detect_product_level',
    'extract_metadata'
]

logger = logging.getLogger(__name__)

# Sensor specifications for Chandrayaan-2 instruments
SENSOR_SPECS: Dict[str, Dict[str, Any]] = {
    'OHRC': {
        'resolution_m': 0.25,  # 0.25 - 0.32 m/px depending on altitude
        'spectral_range_nm': (450, 900),
        'bands': 1,
        'swath_km': 3.0,
        'type': 'panchromatic',
        'sensor_technology': 'TDI CCD'
    },
    'TMC2': {
        'resolution_m': 5.0,
        'spectral_range_nm': (500, 850),
        'bands': 1,
        'swath_km': 20.0,
        'type': 'panchromatic',
        'sensor_technology': 'stereo triplets (fore/nadir/aft at ±26°)'
    },
    'IIRS': {
        'resolution_m': 80.0,
        'spectral_range_nm': (800, 5000),
        'bands': 256,
        'swath_km': 20.0,
        'type': 'hyperspectral',
        'sensor_technology': 'imaging spectrometer'
    }
}


def compute_phase_angle(
    inc: float,
    emi: float,
    az_sun: float,
    az_view: float
) -> float:
    """
    Computes the phase angle from incidence, emission, and azimuth angles.
    cos(α) = cos(i)cos(e) + sin(i)sin(e)cos(φ_sun - φ_view)
    
    Args:
        inc (float): Incidence angle in degrees.
        emi (float): Emission angle in degrees.
        az_sun (float): Sun azimuth angle in degrees.
        az_view (float): View azimuth angle in degrees.
        
    Returns:
        float: Phase angle in degrees.
    """
    i_rad = math.radians(inc)
    e_rad = math.radians(emi)
    phi_sun_rad = math.radians(az_sun)
    phi_view_rad = math.radians(az_view)
    
    cos_alpha = (math.cos(i_rad) * math.cos(e_rad) + 
                 math.sin(i_rad) * math.sin(e_rad) * math.cos(phi_sun_rad - phi_view_rad))
    
    # Clip for numerical stability
    cos_alpha = max(-1.0, min(1.0, cos_alpha))
    
    return math.degrees(math.acos(cos_alpha))


def get_bridge_sensor(sensor_a: str, sensor_b: str) -> Optional[str]:
    """
    Determines the intermediate (bridge) sensor for hierarchical registration.
    E.g., mapping OHRC to IIRS might use TMC2 as a bridge.
    
    Args:
        sensor_a (str): Name of the first sensor.
        sensor_b (str): Name of the second sensor.
        
    Returns:
        Optional[str]: Name of the bridge sensor, if applicable.
    """
    sensors = {sensor_a.upper(), sensor_b.upper()}
    if 'OHRC' in sensors and 'IIRS' in sensors:
        return 'TMC2'
    return None


def compute_scale_ratio(sensor_a: str, sensor_b: str) -> float:
    """
    Computes the scale ratio (resolution A / resolution B) between two sensors.
    
    Args:
        sensor_a (str): Name of the first sensor.
        sensor_b (str): Name of the second sensor.
        
    Returns:
        float: The scale ratio.
        
    Raises:
        ValueError: If a sensor is not found in SENSOR_SPECS.
    """
    s_a = sensor_a.upper()
    s_b = sensor_b.upper()
    
    if s_a not in SENSOR_SPECS:
        raise ValueError(f"Unknown sensor: {sensor_a}")
    if s_b not in SENSOR_SPECS:
        raise ValueError(f"Unknown sensor: {sensor_b}")
        
    res_a = SENSOR_SPECS[s_a]['resolution_m']
    res_b = SENSOR_SPECS[s_b]['resolution_m']
    
    return res_a / res_b


def detect_product_level(product_id: str) -> str:
    """
    Infers the data processing level (e.g., L1, L2) from a product ID.
    
    Args:
        product_id (str): The product ID string.
        
    Returns:
        str: Detected product level ('L0', 'L1', 'L2', etc.) or 'UNKNOWN'.
    """
    pid_lower = product_id.lower()
    if '_l1' in pid_lower or 'level1' in pid_lower:
        return 'L1'
    elif '_l2' in pid_lower or 'level2' in pid_lower:
        return 'L2'
    elif '_l0' in pid_lower or 'level0' in pid_lower:
        return 'L0'
    
    return 'UNKNOWN'
def extract_metadata(label: Any) -> Dict[str, Any]:
    """Extract standard metadata dictionary from a PDS4 label object."""
    return {
        'sensor': label.instrument if hasattr(label, 'instrument') else 'UNKNOWN',
        'start_time': label.start_time if hasattr(label, 'start_time') else '',
        'sun_elevation': label.sun_elevation if hasattr(label, 'sun_elevation') else 0.0,
        'sun_azimuth': label.sun_azimuth if hasattr(label, 'sun_azimuth') else 0.0,
        'incidence_angle': label.incidence_angle if hasattr(label, 'incidence_angle') else 0.0,
        'emission_angle': label.emission_angle if hasattr(label, 'emission_angle') else 0.0,
    }
