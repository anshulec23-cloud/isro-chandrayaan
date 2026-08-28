import pytest
import numpy as np
from pathlib import Path
from lumen.config import Settings
from lumen.ingest.metadata import SensorMetadata

@pytest.fixture
def sample_image():
    """Create a sample synthetic image."""
    return np.random.randint(0, 255, (100, 100), dtype=np.uint8)

@pytest.fixture
def sample_metadata():
    """Create mock sensor metadata."""
    return SensorMetadata(
        sensor_name="TMC2",
        gsd=5.0,
        spectral_range=(0.4, 0.85),
        swath_width=20.0,
        sun_elevation=30.0,
        sun_azimuth=120.0,
        incidence_angle=60.0,
        emission_angle=0.0,
        phase_angle=60.0,
        acquisition_time="2023-01-01T00:00:00",
        lat_center=0.0,
        lon_center=0.0
    )

@pytest.fixture
def test_config():
    """Create test configuration."""
    return Settings(GPU_ENABLED=False)
