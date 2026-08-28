import pytest
import numpy as np
import cv2
import tempfile
import os

@pytest.fixture
def sample_image():
    # 512x512 grayscale synthetic lunar surface
    np.random.seed(42)
    img = np.random.normal(0.5, 0.1, (512, 512))
    # synthetic crater
    cv2.circle(img, (256, 256), 50, 0.2, -1)
    cv2.circle(img, (256, 256), 40, 0.8, -1)
    return np.clip(img, 0, 1).astype(np.float32)

@pytest.fixture
def sample_image_pair(sample_image):
    img0 = sample_image
    # create an affine transformation
    M = np.float32([[1, 0, 20], [0, 1, -10]])
    img1 = cv2.warpAffine(img0, M, (512, 512))
    return img0, img1, M

@pytest.fixture
def sample_pds4_xml():
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:sample</logical_identifier>
        <version_id>1.0</version_id>
    </Identification_Area>
</Product_Observational>
'''
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as f:
        f.write(xml_content.encode('utf-8'))
        name = f.name
    yield name
    os.remove(name)

@pytest.fixture
def sample_dem():
    # 512x512 synthetic DEM
    x, y = np.meshgrid(np.linspace(-1, 1, 512), np.linspace(-1, 1, 512))
    r = np.sqrt(x**2 + y**2)
    dem = np.exp(-10*r**2) * 100 # elevation peak
    return dem.astype(np.float32)

@pytest.fixture
def sample_metadata():
    class SensorMetadata:
        solar_elevation = 45.0
        solar_azimuth = 90.0
        incidence_angle = 45.0
        emission_angle = 0.0
        phase_angle = 45.0
    return SensorMetadata()

@pytest.fixture
def config():
    class Config:
        device = 'cpu'
        num_features = 1000
    return Config()

@pytest.fixture
def matched_points():
    pts1 = np.float32([[10,10], [20,20], [30,30], [40,40], [100,100]])
    pts2 = np.float32([[12,12], [22,22], [32,32], [42,42], [200,200]]) # last is outlier
    return pts1, pts2
