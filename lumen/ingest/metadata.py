"""Metadata extraction and standardization."""

from dataclasses import dataclass
from typing import Optional
from .pds4_parser import PDS4Label

@dataclass
class SensorMetadata:
    """Standardized metadata across different sensors."""
    sensor_name: str
    gsd: float
    spectral_range: tuple[float, float]
    swath_width: float
    sun_elevation: float
    sun_azimuth: float
    incidence_angle: float
    emission_angle: float
    phase_angle: float
    acquisition_time: str
    lat_center: float
    lon_center: float

SENSOR_SPECS = {
    "OHRC": {"spectral_range": (0.4, 0.9), "swath_width": 3.0},
    "TMC2": {"spectral_range": (0.4, 0.85), "swath_width": 20.0},
    "IIRS": {"spectral_range": (0.8, 5.0), "swath_width": 20.0}
}

def extract_metadata(label: PDS4Label) -> SensorMetadata:
    """Extract standard metadata from a PDS4 label.
    
    Args:
        label: The parsed PDS4 label.
        
    Returns:
        SensorMetadata object.
    """
    specs = SENSOR_SPECS.get(label.instrument, {"spectral_range": (0.0, 0.0), "swath_width": 0.0})
    phase_angle = label.incidence_angle + label.emission_angle # simplified phase angle calculation
    return SensorMetadata(
        sensor_name=label.instrument,
        gsd=label.gsd,
        spectral_range=specs["spectral_range"],
        swath_width=specs["swath_width"],
        sun_elevation=label.sun_elevation,
        sun_azimuth=label.sun_azimuth,
        incidence_angle=label.incidence_angle,
        emission_angle=label.emission_angle,
        phase_angle=phase_angle,
        acquisition_time=label.start_time,
        lat_center=0.0, # Placeholder
        lon_center=0.0  # Placeholder
    )
