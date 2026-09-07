"""
scripts/check_footprint_overlap.py

Sanity check tool to parse GCP-derived bounding boxes for a given pair of
PDS4 XML datasets, compute geographic intersection area, and output overlap
percentage against the smaller footprint.
"""

import os
import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lumen.preprocess.orthorectify import (
    _parse_gcp_csv,
    _build_gcps,
    _footprint_from_gcps,
    compute_overlap_region
)


def find_gcp_csv_for_xml(xml_path: Path) -> Optional[Path]:
    """
    Attempt to locate the sibling GCP CSV file associated with a PDS4 product XML.
    Searches in geometry/ subdirectories within the product root.
    """
    xml_path = xml_path.resolve()
    
    # 1. Check if the input is already a CSV
    if xml_path.suffix.lower() == ".csv":
        return xml_path

    # 2. Check if product folder structure matches standard ISRO distribution:
    # <product_root>/data/calibrated/<date>/<name>_d_img_d18.xml
    # <product_root>/geometry/calibrated/<date>/<name>_g_grd_d18.csv
    for parent_level in range(1, min(5, len(xml_path.parents))):
        candidate_root = xml_path.parents[parent_level - 1]
        geom_dir = candidate_root / "geometry"
        if geom_dir.is_dir():
            csv_matches = list(geom_dir.glob("**/*.csv"))
            if csv_matches:
                # Prefer exact stem prefix match if available
                stem_prefix = xml_path.stem.split("_d_")[0]
                for csv_file in csv_matches:
                    if stem_prefix in csv_file.name:
                        return csv_file
                return csv_matches[0]

    # 3. Sibling file replacement
    sibling_csv = xml_path.with_suffix(".csv")
    if sibling_csv.exists():
        return sibling_csv

    return None


def parse_xml_corner_coordinates(xml_path: Path) -> Optional[Tuple[float, float, float, float]]:
    """
    Fallback parser: extracts bounding box from ISDA Geometry Parameters in PDS4 XML.
    Returns (min_lon, min_lat, max_lon, max_lat).
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Search for corner coordinates
        lats = []
        lons = []
        for elem in root.iter():
            tag_name = elem.tag.split("}")[-1].lower()
            if "latitude" in tag_name and elem.text and elem.text.strip():
                try:
                    lats.append(float(elem.text.strip()))
                except ValueError:
                    pass
            elif "longitude" in tag_name and elem.text and elem.text.strip():
                try:
                    lons.append(float(elem.text.strip()))
                except ValueError:
                    pass
                    
        if lats and lons:
            return min(lons), min(lats), max(lons), max(lats)
    except Exception as exc:
        print(f"Warning: Failed to parse corner coordinates from XML {xml_path}: {exc}")
    return None


def get_footprint_bbox(path: Path) -> Tuple[Tuple[float, float, float, float], str]:
    """
    Resolves the bounding box (min_lon, min_lat, max_lon, max_lat) for a given XML or CSV path.
    Reuses orthorectify.py GCP parser when available.
    """
    gcp_csv = find_gcp_csv_for_xml(path)
    
    if gcp_csv and gcp_csv.exists():
        gcp_rows = _parse_gcp_csv(str(gcp_csv))
        gcps = _build_gcps(gcp_rows, [0.0] * len(gcp_rows))
        bbox = _footprint_from_gcps(gcps)
        return bbox, f"GCP CSV ({gcp_csv})"
    
    # Fallback to XML label corner coordinates
    if path.suffix.lower() == ".xml" and path.exists():
        bbox = parse_xml_corner_coordinates(path)
        if bbox is not None:
            return bbox, "PDS4 XML Geometry Parameters"
            
    raise FileNotFoundError(
        f"Could not determine geographic footprint for {path}. "
        "No valid GCP CSV or XML corner coordinates found."
    )


def check_overlap(source_path: str, reference_path: str) -> Dict[str, Any]:
    """
    Calculates overlap metrics between source and reference footprints.
    """
    src_p = Path(source_path)
    ref_p = Path(reference_path)

    src_bbox, src_src = get_footprint_bbox(src_p)
    ref_bbox, ref_src = get_footprint_bbox(ref_p)

    min_lon_src, min_lat_src, max_lon_src, max_lat_src = src_bbox
    min_lon_ref, min_lat_ref, max_lon_ref, max_lat_ref = ref_bbox

    area_src = (max_lon_src - min_lon_src) * (max_lat_src - min_lat_src)
    area_ref = (max_lon_ref - min_lon_ref) * (max_lat_ref - min_lat_ref)

    # Compute intersection
    ix_min = max(min_lon_src, min_lon_ref)
    iy_min = max(min_lat_src, min_lat_ref)
    ix_max = min(max_lon_src, max_lon_ref)
    iy_max = min(max_lat_src, max_lat_ref)

    if ix_min < ix_max and iy_min < iy_max:
        inter_area = (ix_max - ix_min) * (iy_max - iy_min)
        inter_bbox = (ix_min, iy_min, ix_max, iy_max)
    else:
        inter_area = 0.0
        inter_bbox = None

    smaller_area = min(area_src, area_ref)
    larger_area = max(area_src, area_ref)
    overlap_pct_smaller = (inter_area / smaller_area * 100.0) if smaller_area > 0 else 0.0
    overlap_pct_src = (inter_area / area_src * 100.0) if area_src > 0 else 0.0
    overlap_pct_ref = (inter_area / area_ref * 100.0) if area_ref > 0 else 0.0

    return {
        "source": {
            "path": str(src_p),
            "source_type": src_src,
            "bbox": src_bbox,
            "min_lon": min_lon_src,
            "min_lat": min_lat_src,
            "max_lon": max_lon_src,
            "max_lat": max_lat_src,
            "area_deg2": area_src,
            "width_deg": max_lon_src - min_lon_src,
            "height_deg": max_lat_src - min_lat_src,
        },
        "reference": {
            "path": str(ref_p),
            "source_type": ref_src,
            "bbox": ref_bbox,
            "min_lon": min_lon_ref,
            "min_lat": min_lat_ref,
            "max_lon": max_lon_ref,
            "max_lat": max_lat_ref,
            "area_deg2": area_ref,
            "width_deg": max_lon_ref - min_lon_ref,
            "height_deg": max_lat_ref - min_lat_ref,
        },
        "intersection": {
            "bbox": inter_bbox,
            "area_deg2": inter_area,
            "overlap_pct_smaller": overlap_pct_smaller,
            "overlap_pct_source": overlap_pct_src,
            "overlap_pct_reference": overlap_pct_ref,
            "has_overlap": inter_area > 0,
        }
    }


def print_report(results: Dict[str, Any]):
    src = results["source"]
    ref = results["reference"]
    inter = results["intersection"]

    print("=" * 70)
    print("           LUMEN FOOTPRINT OVERLAP SANITY CHECK")
    print("=" * 70)
    print(f"\n[Source Image]")
    print(f"  Path:       {src['path']}")
    print(f"  Geom from:  {src['source_type']}")
    print(f"  Bounds:     Lon [{src['min_lon']:.6f} deg, {src['max_lon']:.6f} deg]")
    print(f"              Lat [{src['min_lat']:.6f} deg, {src['max_lat']:.6f} deg]")
    print(f"  Span:       {src['width_deg']:.6f} deg Lon x {src['height_deg']:.6f} deg Lat (Area: {src['area_deg2']:.6e} deg^2)")

    print(f"\n[Reference Image]")
    print(f"  Path:       {ref['path']}")
    print(f"  Geom from:  {ref['source_type']}")
    print(f"  Bounds:     Lon [{ref['min_lon']:.6f} deg, {ref['max_lon']:.6f} deg]")
    print(f"              Lat [{ref['min_lat']:.6f} deg, {ref['max_lat']:.6f} deg]")
    print(f"  Span:       {ref['width_deg']:.6f} deg Lon x {ref['height_deg']:.6f} deg Lat (Area: {ref['area_deg2']:.6e} deg^2)")

    print("-" * 70)
    print(f"[Intersection Analysis]")
    if inter["has_overlap"]:
        ibox = inter["bbox"]
        print(f"  Overlap Status:   FOUND OVERLAP")
        print(f"  Inter Bounds:     Lon [{ibox[0]:.6f} deg, {ibox[2]:.6f} deg]")
        print(f"                    Lat [{ibox[1]:.6f} deg, {ibox[3]:.6f} deg]")
        print(f"  Inter Area:       {inter['area_deg2']:.6e} deg^2")
        print(f"  Overlap % (Smaller Footprint):  {inter['overlap_pct_smaller']:.2f}%")
        print(f"  Overlap % (Source):             {inter['overlap_pct_source']:.2f}%")
        print(f"  Overlap % (Reference):          {inter['overlap_pct_reference']:.2f}%")
    else:
        print(f"  Overlap Status:   NO OVERLAP (0.00%)")
        print(f"  Inter Area:       0.0 deg^2")
        print(f"  Overlap % (Smaller Footprint):  0.00%")
        print(f"  Reason: Geographic bounding boxes are disjoint.")
        print(f"          Lon Diff: src [{src['min_lon']:.2f} deg, {src['max_lon']:.2f} deg] vs ref [{ref['min_lon']:.2f} deg, {ref['max_lon']:.2f} deg]")
        print(f"          Lat Diff: src [{src['min_lat']:.2f} deg, {src['max_lat']:.2f} deg] vs ref [{ref['min_lat']:.2f} deg, {ref['max_lat']:.2f} deg]")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Compute geographic footprint overlap between two PDS4 datasets."
    )
    parser.add_argument(
        "--source", "-s",
        type=str,
        help="Path to source PDS4 XML or GCP CSV"
    )
    parser.add_argument(
        "--reference", "-r",
        type=str,
        help="Path to reference PDS4 XML or GCP CSV"
    )

    args = parser.parse_args()

    # Default paths in data/raw if arguments are not provided
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data" / "raw"

    default_ohrc = data_dir / "ch2_ohr_ncp_20260130T1309574436_d_img_d18" / "data" / "calibrated" / "20260130" / "ch2_ohr_ncp_20260130T1309574436_d_img_d18.xml"
    default_tmc = data_dir / "ch2_tmc_nca_20260813T0627378526_d_img_d18" / "data" / "calibrated" / "20260813" / "ch2_tmc_nca_20260813T0627378526_d_img_d18.xml"

    src_path = args.source or str(default_ohrc)
    ref_path = args.reference or str(default_tmc)

    results = check_overlap(src_path, ref_path)
    print_report(results)


if __name__ == "__main__":
    main()
