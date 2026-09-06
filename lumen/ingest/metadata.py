"""
Metadata structures and utilities for Chandrayaan-2 payloads.
"""

import math
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union

from lumen.ingest.pds4_parser import MissingMetadataError

__all__ = [
    'SENSOR_SPECS',
    'MissingMetadataError',
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
        'sensor_technology': 'pushbroom spectrometer'
    },
    'SELENE_TC': {
        'resolution_m': 7.4,
        'spectral_range_nm': (450, 700),
        'bands': 1,
        'swath_km': 35.0,
        'type': 'panchromatic',
        'sensor_technology': 'Terrain Camera stereo pushbroom'
    },
    'LROC_NAC': {
        'resolution_m': 0.5,
        'spectral_range_nm': (400, 750),
        'bands': 1,
        'swath_km': 5.0,
        'type': 'panchromatic',
        'sensor_technology': 'Narrow Angle Camera linescan'
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


def _get_val(obj: Any, keys: list, default: Any = None) -> Any:
    """Helper to retrieve attribute or dict value across potential field name aliases."""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] is not None:
                return obj[k]
    else:
        for k in keys:
            if hasattr(obj, k):
                val = getattr(obj, k)
                if val is not None:
                    return val
    return default


def extract_metadata(label: Any, file_name: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Extract standard metadata dictionary from a PDS4 label dictionary or object.
    
    Validates that required geometric and illumination fields (sun_azimuth,
    sun_elevation, orbit_position/spacecraft_altitude, and pixel_resolution/gsd)
    are present. Fails loudly with MissingMetadataError if any required field is missing.
    
    Args:
        label: PDS4 label dictionary (from parse_pds4) or object.
        file_name: Optional file path or identifier for error reporting.

    Returns:
        Dict[str, Any]: Extracted and validated metadata dictionary.

    Raises:
        MissingMetadataError: If any required metadata field is absent.
    """
    source_file = _get_val(label, ['xml_path', 'file_name', 'path'], file_name or '<unknown file>')

    # 1. Sun Azimuth
    sun_az = _get_val(label, ['sun_azimuth', 'solar_azimuth', 'sun_az'])
    if sun_az is None:
        raise MissingMetadataError('sun_azimuth', source_file)

    # 2. Sun Elevation
    sun_el = _get_val(label, ['sun_elevation', 'solar_elevation', 'sun_el'])
    if sun_el is None:
        raise MissingMetadataError('sun_elevation', source_file)

    # 3. Orbit Position / Spacecraft Altitude
    orbit_pos = _get_val(label, ['spacecraft_altitude', 'orbit_position', 'altitude', 'imaging_orbit_number', 'orbit'])
    if orbit_pos is None:
        raise MissingMetadataError('orbit_position', source_file)

    # 4. GSD / Pixel Resolution
    sensor = _get_val(label, ['sensor', 'instrument', 'instruments'])
    if isinstance(sensor, list) and sensor:
        sensor_name = sensor[0]
    else:
        sensor_name = str(sensor) if sensor else 'UNKNOWN'

    gsd = _get_val(label, ['pixel_resolution', 'gsd', 'resolution_m', 'resolution'])
    if gsd is None:
        if sensor_name.upper() in SENSOR_SPECS:
            gsd = SENSOR_SPECS[sensor_name.upper()]['resolution_m']
        else:
            raise MissingMetadataError('gsd', source_file)

    # Illumination angles (incidence, emission, phase)
    incidence = _get_val(label, ['incidence_angle', 'solar_incidence'])
    if incidence is None:
        incidence = 90.0 - float(sun_el)

    emission = _get_val(label, ['emission_angle', 'emission'], 0.0)
    
    phase = _get_val(label, ['phase_angle', 'phase'])
    if phase is None:
        phase = compute_phase_angle(float(incidence), float(emission), float(sun_az), 0.0)

    start_time = _get_val(label, ['start_date_time', 'start_time', 'time'], '')

    return {
        'sensor': sensor_name,
        'start_time': str(start_time),
        'sun_azimuth': float(sun_az),
        'solar_azimuth': float(sun_az),
        'sun_elevation': float(sun_el),
        'solar_elevation': float(sun_el),
        'orbit_position': float(orbit_pos) if isinstance(orbit_pos, (int, float)) else str(orbit_pos),
        'spacecraft_altitude': float(orbit_pos) if isinstance(orbit_pos, (int, float)) else str(orbit_pos),
        'gsd': float(gsd),
        'pixel_resolution': float(gsd),
        'incidence_angle': float(incidence),
        'emission_angle': float(emission),
        'phase_angle': float(phase),
        'xml_path': str(source_file),
    }
