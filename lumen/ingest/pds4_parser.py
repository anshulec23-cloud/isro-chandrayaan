"""
PDS4 XML parsing module for Chandrayaan-2 payloads.
"""

import os
import xml.etree.ElementTree as ET
import logging
from typing import Dict, Any, Optional, Tuple, Union, List
from pathlib import Path
import numpy as np

# Optional rasterio import
try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

__all__ = ['PDS4Parser', 'parse_pds4', 'load_binary_image', 'MissingMetadataError', 'resolve_gcp_csv_path']

logger = logging.getLogger(__name__)

PDS_NS = {
    "pds": "http://pds.nasa.gov/pds4/pds/v1",
    "geom": "http://pds.nasa.gov/pds4/geom/v1",
    "isda": "https://isda.issdc.gov.in/pds4/isda/v1",
    "disp": "http://pds.nasa.gov/pds4/disp/v1",
    "sp": "http://pds.nasa.gov/pds4/sp/v1"
}


class MissingMetadataError(ValueError):
    """Raised when a required metadata field is missing from a PDS4 label."""
    def __init__(self, field_name: str, file_path: Union[str, Path] = "unknown"):
        self.field_name = field_name
        self.file_path = str(file_path)
        super().__init__(
            f"Missing required metadata field '{field_name}' in label file: {self.file_path}"
        )


class PDS4Parser:
    """Parser for PDS4 XML labels associated with Chandrayaan-2 and planetary data."""
    
    def __init__(self, xml_path: Union[str, Path]):
        self.xml_path = Path(xml_path)
        self.tree = ET.parse(self.xml_path)
        self.root = self.tree.getroot()
        
    def _find_text(self, xpath: str, default: Any = None) -> Any:
        element = self.root.find(xpath, namespaces=PDS_NS)
        return element.text.strip() if element is not None and element.text else default

    def _find_field(self, tag_names: List[str], default: Any = None) -> Any:
        """Find element text searching multiple namespaces and local tag fallbacks."""
        for tag in tag_names:
            for ns_prefix in ["isda", "geom", "pds", ""]:
                prefix = f"{ns_prefix}:" if ns_prefix else ""
                val = self._find_text(f".//{prefix}{tag}")
                if val is not None and val.strip() != "":
                    return val.strip()

        # Fallback searching all elements by local tag
        for elem in self.root.iter():
            local_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local_tag in tag_names and elem.text and elem.text.strip():
                return elem.text.strip()
        return default

    def extract_metadata(self, validate_required: bool = True) -> Dict[str, Any]:  # noqa: C901
        """
        Extracts comprehensive metadata from the PDS4 label.
        
        Args:
            validate_required: If True, raises MissingMetadataError if any required
                geometric/illumination field (sun_azimuth, sun_elevation,
                orbit position/spacecraft altitude, GSD/pixel resolution) is missing.

        Returns:
            Dict[str, Any]: Extracted metadata.

        Raises:
            MissingMetadataError: When a required metadata field is missing and validate_required is True.
        """
        metadata: Dict[str, Any] = {}
        metadata['xml_path'] = str(self.xml_path)
        metadata['file_name'] = self.xml_path.name
        
        # Identification Area
        metadata['logical_identifier'] = self._find_text('.//pds:Identification_Area/pds:logical_identifier')
        metadata['title'] = self._find_text('.//pds:Identification_Area/pds:title')
        if metadata['logical_identifier']:
            metadata['product_id'] = metadata['logical_identifier'].split(':')[-1]
        else:
            metadata['product_id'] = self.xml_path.stem
        
        # Observation Area
        metadata['start_date_time'] = self._find_text('.//pds:Observation_Area/pds:Time_Coordinates/pds:start_date_time')
        metadata['stop_date_time'] = self._find_text('.//pds:Observation_Area/pds:Time_Coordinates/pds:stop_date_time')
        metadata['start_time'] = metadata['start_date_time'] or ''
        
        # Investigation Area
        metadata['mission_name'] = self._find_text('.//pds:Observation_Area/pds:Investigation_Area/pds:name')
        
        # Observing System
        obs_sys_components = self.root.findall('.//pds:Observing_System_Component', namespaces=PDS_NS)
        instruments = []
        for comp in obs_sys_components:
            name = comp.find('pds:name', namespaces=PDS_NS)
            if name is not None and name.text:
                instruments.append(name.text.strip())
        metadata['instruments'] = instruments
        metadata['sensor'] = instruments[0] if instruments else 'UNKNOWN'

        # Illumination & Geometry fields
        sun_az_str = self._find_field(['sun_azimuth', 'solar_azimuth', 'sun_az'])
        metadata['sun_azimuth'] = float(sun_az_str) if sun_az_str is not None else None
        metadata['solar_azimuth'] = metadata['sun_azimuth']

        sun_el_str = self._find_field(['sun_elevation', 'solar_elevation', 'sun_el'])
        metadata['sun_elevation'] = float(sun_el_str) if sun_el_str is not None else None
        metadata['solar_elevation'] = metadata['sun_elevation']

        inc_str = self._find_field(['solar_incidence', 'incidence_angle'])
        if inc_str is not None:
            metadata['incidence_angle'] = float(inc_str)
        elif metadata['sun_elevation'] is not None:
            metadata['incidence_angle'] = 90.0 - metadata['sun_elevation']
        else:
            metadata['incidence_angle'] = None
        
        emi_str = self._find_field(['emission_angle', 'emission'])
        metadata['emission_angle'] = float(emi_str) if emi_str is not None else 0.0
        
        pha_str = self._find_field(['phase_angle', 'phase'])
        metadata['phase_angle'] = float(pha_str) if pha_str is not None else None

        # Spacecraft altitude / orbit position
        alt_str = self._find_field(['spacecraft_altitude', 'orbit_position', 'altitude', 'imaging_orbit_number', 'orbit'])
        metadata['spacecraft_altitude'] = float(alt_str) if alt_str is not None else None
        metadata['orbit_position'] = metadata['spacecraft_altitude']

        # Pixel resolution / GSD
        res_str = self._find_field(['pixel_resolution', 'gsd', 'resolution_m', 'resolution'])
        metadata['pixel_resolution'] = float(res_str) if res_str is not None else None
        metadata['gsd'] = metadata['pixel_resolution']

        # Spacecraft orientation angles
        roll_str = self._find_field(['roll'])
        pitch_str = self._find_field(['pitch'])
        yaw_str = self._find_field(['yaw'])
        metadata['roll'] = float(roll_str) if roll_str is not None else 0.0
        metadata['pitch'] = float(pitch_str) if pitch_str is not None else 0.0
        metadata['yaw'] = float(yaw_str) if yaw_str is not None else 0.0

        # Data Object extraction (Array_2D or Array_2D_Image)
        array_node = self.root.find('.//pds:File_Area_Observational/pds:Array_2D_Image', namespaces=PDS_NS)
        if array_node is None:
            array_node = self.root.find('.//pds:File_Area_Observational/pds:Array_2D', namespaces=PDS_NS)
            
        if array_node is not None:
            offset_node = array_node.find('pds:offset', namespaces=PDS_NS)
            metadata['data_offset'] = int(offset_node.text) if offset_node is not None and offset_node.text else 0
            
            axes = array_node.findall('pds:Axis_Array', namespaces=PDS_NS)
            lines = 0
            samples = 0
            for axis in axes:
                axis_name_node = axis.find('pds:axis_name', namespaces=PDS_NS)
                elements_node = axis.find('pds:elements', namespaces=PDS_NS)
                if axis_name_node is not None and elements_node is not None:
                    axis_name = axis_name_node.text.strip().lower()
                    elements = int(elements_node.text.strip())
                    if axis_name == 'line':
                        lines = elements
                    elif axis_name == 'sample':
                        samples = elements
            metadata['lines'] = lines
            metadata['samples'] = samples
            
            element_array = array_node.find('pds:Element_Array', namespaces=PDS_NS)
            if element_array is not None:
                data_type_node = element_array.find('pds:data_type', namespaces=PDS_NS)
                if data_type_node is not None and data_type_node.text:
                    metadata['data_type'] = data_type_node.text.strip()
        
        # File info
        file_node = self.root.find('.//pds:File_Area_Observational/pds:File', namespaces=PDS_NS)
        if file_node is not None:
            fn_node = file_node.find('pds:file_name', namespaces=PDS_NS)
            if fn_node is not None and fn_node.text:
                metadata['file_name'] = fn_node.text.strip()

        # Validation of required fields
        if validate_required:
            if metadata['sun_azimuth'] is None:
                raise MissingMetadataError('sun_azimuth', self.xml_path)
            if metadata['sun_elevation'] is None:
                raise MissingMetadataError('sun_elevation', self.xml_path)
            if metadata['spacecraft_altitude'] is None:
                raise MissingMetadataError('orbit_position', self.xml_path)
            if metadata['pixel_resolution'] is None:
                raise MissingMetadataError('gsd', self.xml_path)

        # Geometry resolution
        if metadata.get('sensor') == 'IIRS' or 'iir' in self.xml_path.name.lower():
            loc_path = resolve_iirs_loc_path(self.xml_path)
            metadata['iirs_loc_path'] = str(loc_path) if loc_path is not None else None
        else:
            gcp_csv = resolve_gcp_csv_path(self.xml_path)
            metadata['gcp_csv_path'] = str(gcp_csv) if gcp_csv is not None else None

        return metadata


def resolve_gcp_csv_path(xml_path: Union[str, Path]) -> Optional[Path]:
    """Locate the GCP CSV sidecar (_g_grd_d18.csv) for a given PDS4 product XML.

    ISRO distributes GCP grids alongside calibrated images under the standard
    product directory layout::

        <product_root>/
          data/calibrated/<date>/<product_id>_d_img_d18.xml   <- source XML
          geometry/calibrated/<date>/<product_id>_g_grd_d18.csv  <- GCP CSV

    For derived products (e.g. IIRS .qub under data/derived/) the same
    pattern holds with 'derived' instead of 'calibrated'.  For any layout
    that doesn't match we fall back to a recursive glob of geometry/**/*.csv
    from the product root.

    Args:
        xml_path: Absolute path to the PDS4 product XML file.

    Returns:
        Path to the GCP CSV if found, else None.
    """
    xml_path = Path(xml_path).resolve()

    # Walk upward until we find a directory that contains a 'geometry' sibling.
    # For a standard ISRO product the layout is:
    #   <product_root>/data/<level>/<date>/  <- xml_path is here
    # so we need to go up 3 levels to reach product_root.
    for num_parents in range(1, 6):
        if num_parents >= len(xml_path.parents):
            break
        candidate_root = xml_path.parents[num_parents - 1]
        geom_dir = candidate_root / "geometry"
        if not geom_dir.is_dir():
            # Also check one level higher (product_root)
            candidate_root = xml_path.parents[num_parents]
            geom_dir = candidate_root / "geometry"
            if not geom_dir.is_dir():
                continue

        # We found a geometry/ dir.  Prefer a CSV whose stem starts with the
        # same product-ID prefix as our XML (everything before '_d_').
        product_prefix = xml_path.stem.split("_d_")[0]
        csv_matches = list(geom_dir.glob("**/*.csv"))
        if not csv_matches:
            continue

        # First: exact prefix match
        for csv_file in csv_matches:
            if product_prefix and csv_file.name.startswith(product_prefix):
                logger.debug(f"Resolved GCP CSV (prefix match): {csv_file}")
                return csv_file

        # Fallback: any CSV in geometry/
        logger.debug(f"Resolved GCP CSV (first match): {csv_matches[0]}")
        return csv_matches[0]

    logger.warning(
        f"No GCP CSV found for {xml_path.name}. "
        "orthorectify() will raise MissingGeometryError unless gcp_csv_path "
        "is supplied another way."
    )
    return None


def resolve_iirs_loc_path(xml_path: Union[str, Path]) -> Optional[Path]:
    """Locate the IIRS pixel location image (_d_loc_d18_ard.img) for a given product.
    
    Args:
        xml_path: Absolute path to the PDS4 product XML file.
        
    Returns:
        Path to the _loc_ image if found, else None.
    """
    xml_path = Path(xml_path).resolve()
    
    # Check the same directory for a _d_loc_d18_ard.img
    # The prefix is usually up to the first '_d_'
    product_prefix = xml_path.stem.split("_d_")[0]
    loc_matches = list(xml_path.parent.glob(f"{product_prefix}_d_loc_*.img"))
    if not loc_matches:
        loc_matches = list(xml_path.parent.glob("*_d_loc_*.img"))
        
    if loc_matches:
        return loc_matches[0]
        
    return None


def parse_pds4(xml_path: Union[str, Path], validate_required: bool = True) -> Dict[str, Any]:
    """
    Parses a PDS4 XML file and returns its metadata.
    
    Args:
        xml_path: Path to the PDS4 XML file.
        validate_required: Whether to validate presence of required fields.
        
    Returns:
        Dict[str, Any]: Extracted metadata.

    Raises:
        MissingMetadataError: If required fields are missing and validate_required is True.
    """
    parser = PDS4Parser(xml_path)
    return parser.extract_metadata(validate_required=validate_required)


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
    # Parse without strict geometric validation just to load raw raster array
    meta = parse_pds4(xml_path, validate_required=False)
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
        # Fallback to file size if dimension not explicitly in header
        if HAS_RASTERIO:
            try:
                with rasterio.open(img_path) as src:
                    return src.read(1)
            except Exception as e:
                logger.info(f"Rasterio load failed ({e}), falling back to raw binary read.")
        raise ValueError(f"Invalid image dimensions {shape} found in metadata for {xml_path}.")
        
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
