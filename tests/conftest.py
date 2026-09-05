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
        sensor = 'OHRC'
        solar_elevation = 45.0
        sun_elevation = 45.0
        solar_azimuth = 90.0
        sun_azimuth = 90.0
        incidence_angle = 45.0
        emission_angle = 0.0
        phase_angle = 45.0
        spacecraft_altitude = 113.30
        orbit_position = 113.30
        pixel_resolution = 0.25
        gsd = 0.25
    return SensorMetadata()

@pytest.fixture
def valid_pds4_xml():
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1" xmlns:isda="https://isda.issdc.gov.in/pds4/isda/v1">
    <Identification_Area>
        <logical_identifier>urn:isro:isda:ch2_cho.ohr:sample_valid</logical_identifier>
        <title>Valid PDS4 Label</title>
        <version_id>1.0</version_id>
    </Identification_Area>
    <Observation_Area>
        <Time_Coordinates>
            <start_date_time>2026-01-30T13:09:57.4436Z</start_date_time>
            <stop_date_time>2026-01-30T13:10:13.4276Z</stop_date_time>
        </Time_Coordinates>
        <Mission_Area>
            <isda:Product_Parameters>
                <isda:sun_azimuth unit="deg">11.213302</isda:sun_azimuth>
                <isda:sun_elevation unit="deg">6.967384</isda:sun_elevation>
                <isda:spacecraft_altitude unit="km">113.30</isda:spacecraft_altitude>
                <isda:pixel_resolution unit="m/pixel">0.29</isda:pixel_resolution>
                <isda:solar_incidence unit="deg">83.032616</isda:solar_incidence>
            </isda:Product_Parameters>
        </Mission_Area>
    </Observation_Area>
</Product_Observational>
'''
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as f:
        f.write(xml_content.encode('utf-8'))
        name = f.name
    yield name
    if os.path.exists(name):
        os.remove(name)

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
