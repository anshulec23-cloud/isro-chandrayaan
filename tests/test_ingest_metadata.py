"""
Unit tests for PDS4 parsing and metadata extraction validation.
Tests strict validation of required fields (sun_az, sun_el, orbit position, GSD).
"""

import os
import tempfile
import pytest
from pathlib import Path

from lumen.ingest.pds4_parser import PDS4Parser, parse_pds4, MissingMetadataError
from lumen.ingest.metadata import extract_metadata


def test_missing_sun_az_raises_exception():
    """Confirms that a label missing sun_azimuth raises MissingMetadataError rather than returning 0.0."""
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1" xmlns:isda="https://isda.issdc.gov.in/pds4/isda/v1">
    <Identification_Area>
        <logical_identifier>urn:isro:isda:ch2_cho.ohr:sample_no_sun_az</logical_identifier>
        <title>Missing Sun Az</title>
        <version_id>1.0</version_id>
    </Identification_Area>
    <Observation_Area>
        <Mission_Area>
            <isda:Product_Parameters>
                <!-- sun_azimuth is missing -->
                <isda:sun_elevation unit="deg">15.0</isda:sun_elevation>
                <isda:spacecraft_altitude unit="km">100.0</isda:spacecraft_altitude>
                <isda:pixel_resolution unit="m/pixel">0.25</isda:pixel_resolution>
            </isda:Product_Parameters>
        </Mission_Area>
    </Observation_Area>
</Product_Observational>
'''
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as f:
        f.write(xml_content.encode('utf-8'))
        xml_path = f.name

    try:
        # Both parse_pds4 and extract_metadata must fail loudly
        with pytest.raises(MissingMetadataError) as exc_info:
            parse_pds4(xml_path)
        assert "sun_azimuth" in str(exc_info.value)
        assert xml_path in str(exc_info.value)

        # Direct call to extract_metadata on a dict missing sun_azimuth
        incomplete_dict = {
            'sun_elevation': 15.0,
            'spacecraft_altitude': 100.0,
            'pixel_resolution': 0.25,
            'xml_path': xml_path
        }
        with pytest.raises(MissingMetadataError) as exc_info_dict:
            extract_metadata(incomplete_dict)
        assert "sun_azimuth" in str(exc_info_dict.value)
    finally:
        if os.path.exists(xml_path):
            os.remove(xml_path)


def test_missing_sun_el_raises_exception():
    """Confirms that a label missing sun_elevation raises MissingMetadataError."""
    incomplete_dict = {
        'sun_azimuth': 45.0,
        'spacecraft_altitude': 100.0,
        'pixel_resolution': 0.25,
        'xml_path': 'test_label.xml'
    }
    with pytest.raises(MissingMetadataError) as exc_info:
        extract_metadata(incomplete_dict)
    assert "sun_elevation" in str(exc_info.value)
    assert "test_label.xml" in str(exc_info.value)


def test_missing_orbit_position_raises_exception():
    """Confirms that a label missing orbit position / spacecraft altitude raises MissingMetadataError."""
    incomplete_dict = {
        'sun_azimuth': 45.0,
        'sun_elevation': 30.0,
        'pixel_resolution': 0.25,
        'xml_path': 'test_label.xml'
    }
    with pytest.raises(MissingMetadataError) as exc_info:
        extract_metadata(incomplete_dict)
    assert "orbit_position" in str(exc_info.value)


def test_missing_gsd_raises_exception():
    """Confirms that a label missing GSD / pixel resolution raises MissingMetadataError."""
    incomplete_dict = {
        'sun_azimuth': 45.0,
        'sun_elevation': 30.0,
        'spacecraft_altitude': 100.0,
        'xml_path': 'test_label.xml'
    }
    with pytest.raises(MissingMetadataError) as exc_info:
        extract_metadata(incomplete_dict)
    assert "gsd" in str(exc_info.value)


def test_valid_label_extracts_all_fields(valid_pds4_xml):
    """Confirms that a valid PDS4 XML parses without errors and populates all fields."""
    meta = parse_pds4(valid_pds4_xml)
    assert meta['sun_azimuth'] == pytest.approx(11.213302)
    assert meta['sun_elevation'] == pytest.approx(6.967384)
    assert meta['spacecraft_altitude'] == pytest.approx(113.30)
    assert meta['pixel_resolution'] == pytest.approx(0.29)

    extracted = extract_metadata(meta)
    assert extracted['solar_azimuth'] == pytest.approx(11.213302)
    assert extracted['solar_elevation'] == pytest.approx(6.967384)
    assert extracted['orbit_position'] == pytest.approx(113.30)
    assert extracted['gsd'] == pytest.approx(0.29)


def test_real_dataset_xml_parsing_if_available():
    """Test parsing real OHRC and TMC dataset XML files if present in data/raw."""
    ohr_path = Path('data/raw/ch2_ohr_ncp_20260130T1309574436_d_img_d18/data/calibrated/20260130/ch2_ohr_ncp_20260130T1309574436_d_img_d18.xml')
    tmc_path = Path('data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml')

    if ohr_path.exists():
        ohr_meta = parse_pds4(ohr_path)
        assert ohr_meta['sun_azimuth'] is not None
        assert ohr_meta['sun_elevation'] is not None
        assert ohr_meta['spacecraft_altitude'] is not None
        assert ohr_meta['pixel_resolution'] == pytest.approx(0.29)

    if tmc_path.exists():
        tmc_meta = parse_pds4(tmc_path)
        assert tmc_meta['sun_azimuth'] is not None
        assert tmc_meta['sun_elevation'] is not None
        assert tmc_meta['spacecraft_altitude'] is not None
        assert tmc_meta['pixel_resolution'] == pytest.approx(5.48)
