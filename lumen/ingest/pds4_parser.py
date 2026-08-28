"""
PDS4 XML parsing module for Chandrayaan-2 payloads.
"""

import os
import xml.etree.ElementTree as ET
import logging
from typing import Dict, Any, Optional, Tuple, Union
from pathlib import Path
import numpy as np

# Optional rasterio import
try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

__all__ = ['PDS4Parser', 'parse_pds4', 'load_binary_image']

logger = logging.getLogger(__name__)

PDS_NS = {"pds": "http://pds.nasa.gov/pds4/pds/v1", "geom": "http://pds.nasa.gov/pds4/geom/v1"}


class PDS4Parser:
    """Parser for PDS4 XML labels associated with Chandrayaan-2 data."""
    
    def __init__(self, xml_path: Union[str, Path]):
        self.xml_path = Path(xml_path)
        self.tree = ET.parse(self.xml_path)
        self.root = self.tree.getroot()
        
    def _find_text(self, xpath: str, default: Any = None) -> Any:
        element = self.root.find(xpath, namespaces=PDS_NS)
        return element.text if element is not None else default

    def extract_metadata(self) -> Dict[str, Any]:
        """
        Extracts comprehensive metadata from the PDS4 label.
        
        Returns:
            Dict[str, Any]: Extracted metadata.
        """
        metadata = {}
        
        # Identification Area
        metadata['logical_identifier'] = self._find_text('.//pds:Identification_Area/pds:logical_identifier')
        metadata['title'] = self._find_text('.//pds:Identification_Area/pds:title')
        metadata['product_id'] = self._find_text('.//pds:Identification_Area/pds:logical_identifier').split(':')[-1] if metadata['logical_identifier'] else None
        
        # Observation Area
        metadata['start_date_time'] = self._find_text('.//pds:Observation_Area/pds:Time_Coordinates/pds:start_date_time')
        metadata['stop_date_time'] = self._find_text('.//pds:Observation_Area/pds:Time_Coordinates/pds:stop_date_time')
        
        # Investigation Area
        metadata['mission_name'] = self._find_text('.//pds:Observation_Area/pds:Investigation_Area/pds:name')
        
        # Observing System
        obs_sys_components = self.root.findall('.//pds:Observing_System_Component', namespaces=PDS_NS)
        instruments = []
        for comp in obs_sys_components:
            name = comp.find('pds:name', namespaces=PDS_NS)
            if name is not None:
                instruments.append(name.text)
        metadata['instruments'] = instruments

        # Geometry
        # Try both pds and geom namespaces for geometry
        inc = self._find_text('.//geom:Geometry/geom:Image_Geometry/geom:Illumination_Geometry/geom:incidence_angle')
        if inc is None:
            inc = self._find_text('.//pds:Geometry/pds:Image_Geometry/pds:Illumination_Geometry/pds:incidence_angle')
        metadata['incidence_angle'] = float(inc) if inc is not None else None
        
        emi = self._find_text('.//geom:Geometry/geom:Image_Geometry/geom:Illumination_Geometry/geom:emission_angle')
        if emi is None:
            emi = self._find_text('.//pds:Geometry/pds:Image_Geometry/pds:Illumination_Geometry/pds:emission_angle')
        metadata['emission_angle'] = float(emi) if emi is not None else None
        
        pha = self._find_text('.//geom:Geometry/geom:Image_Geometry/geom:Illumination_Geometry/geom:phase_angle')
        if pha is None:
            pha = self._find_text('.//pds:Geometry/pds:Image_Geometry/pds:Illumination_Geometry/pds:phase_angle')
        metadata['phase_angle'] = float(pha) if pha is not None else None

        # Data Object extraction (Array_2D or Array_2D_Image)
        array_node = self.root.find('.//pds:File_Area_Observational/pds:Array_2D_Image', namespaces=PDS_NS)
        if array_node is None:
            array_node = self.root.find('.//pds:File_Area_Observational/pds:Array_2D', namespaces=PDS_NS)
            
        if array_node is not None:
            offset_node = array_node.find('pds:offset', namespaces=PDS_NS)
            metadata['data_offset'] = int(offset_node.text) if offset_node is not None else 0
            
            axes = array_node.findall('pds:Axis_Array', namespaces=PDS_NS)
            lines = 0
            samples = 0
            for axis in axes:
                axis_name = axis.find('pds:axis_name', namespaces=PDS_NS).text
                elements = int(axis.find('pds:elements', namespaces=PDS_NS).text)
                if axis_name.lower() == 'line':
                    lines = elements
                elif axis_name.lower() == 'sample':
                    samples = elements
            metadata['lines'] = lines
            metadata['samples'] = samples
            
            element_array = array_node.find('pds:Element_Array', namespaces=PDS_NS)
            if element_array is not None:
                data_type = element_array.find('pds:data_type', namespaces=PDS_NS).text
                metadata['data_type'] = data_type
        
        # File info
        file_node = self.root.find('.//pds:File_Area_Observational/pds:File', namespaces=PDS_NS)
        if file_node is not None:
            metadata['file_name'] = file_node.find('pds:file_name', namespaces=PDS_NS).text

        return metadata


def parse_pds4(xml_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Parses a PDS4 XML file and returns its metadata.
    
    Args:
        xml_path (Union[str, Path]): Path to the PDS4 XML file.
        
    Returns:
        Dict[str, Any]: Extracted metadata.
    """
    parser = PDS4Parser(xml_path)
    return parser.extract_metadata()


def _pds_type_to_numpy(data_type: str) -> np.dtype:
    """Map PDS4 data types to numpy dtypes."""
    type_map = {
        'UnsignedMSB2': np.dtype('>u2'),
        'UnsignedLSB2': np.dtype('<u2'),
        'SignedMSB2': np.dtype('>i2'),
        'SignedLSB2': np.dtype('<i2'),
        'UnsignedByte': np.dtype('u1'),
        'IEEE754MSBSingle': np.dtype('>f4'),
        'IEEE754LSBSingle': np.dtype('<f4')
    }
    if data_type not in type_map:
        logger.warning(f"Unknown data type {data_type}, defaulting to uint8.")
        return np.dtype('u1')
    return type_map[data_type]


def load_binary_image(
    xml_path: Union[str, Path],
    img_path: Optional[Union[str, Path]] = None
) -> np.ndarray:
    """
    Loads binary image data corresponding to a PDS4 label.
    
    Args:
        xml_path (Union[str, Path]): Path to the PDS4 XML file.
        img_path (Optional[Union[str, Path]]): Optional explicit path to the image file.
            If not provided, defaults to the file specified in the XML or the same
            name as the XML with an .img extension.
            
    Returns:
        np.ndarray: The image data.
    """
    meta = parse_pds4(xml_path)
    xml_path = Path(xml_path)
    
    if img_path is None:
        if 'file_name' in meta and meta['file_name']:
            img_path = xml_path.parent / meta['file_name']
        else:
            img_path = xml_path.with_suffix('.img')
            
    if not img_path.exists():
        raise FileNotFoundError(f"Image file not found: {img_path}")
        
    dtype = _pds_type_to_numpy(meta.get('data_type', 'UnsignedByte'))
    offset = meta.get('data_offset', 0)
    shape = (meta.get('lines', 0), meta.get('samples', 0))
    
    if shape[0] == 0 or shape[1] == 0:
        raise ValueError("Invalid image dimensions found in metadata.")
        
    if HAS_RASTERIO:
        try:
            with rasterio.open(img_path) as src:
                return src.read(1)
        except Exception as e:
            logger.info(f"Rasterio load failed ({e}), falling back to raw binary read.")
    
    # Raw binary read fallback
    with open(img_path, 'rb') as f:
        f.seek(offset)
        data = np.fromfile(f, dtype=dtype, count=shape[0]*shape[1])
        data = data.reshape(shape)
        
    return data
