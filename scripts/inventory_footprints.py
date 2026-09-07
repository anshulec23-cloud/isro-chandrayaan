import os
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import xml.etree.ElementTree as ET

# Import footprint extraction from existing script
from check_footprint_overlap import get_footprint_bbox

def get_sensor_type(filename: str) -> str:
    filename = filename.lower()
    if 'ohr' in filename:
        return 'OHRC'
    elif 'tmc' in filename:
        return 'TMC'
    elif 'iir' in filename:
        return 'IIRS'
    return 'UNKNOWN'

def main():
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data" / "raw"
    
    products = []
    
    # 1. Find all PDS4 XML products
    for root, dirs, files in os.walk(data_dir):
        for f in files:
            if f.endswith('.xml'):
                path = Path(root) / f
                try:
                    bbox, source_type = get_footprint_bbox(path)
                    min_lon, min_lat, max_lon, max_lat = bbox
                    area = (max_lon - min_lon) * (max_lat - min_lat)
                    sensor = get_sensor_type(f)
                    products.append({
                        'name': f,
                        'path': path,
                        'sensor': sensor,
                        'bbox': bbox,
                        'area': area
                    })
                except Exception as e:
                    print(f"Failed to process {f}: {e}")

    # 2. Print Inventory
    print("=" * 80)
    print("                      DATA INVENTORY")
    print("=" * 80)
    for p in products:
        b = p['bbox']
        print(f"{p['sensor']:4s} | {p['name']:40s} | Lon: {b[0]:.2f} to {b[2]:.2f}, Lat: {b[1]:.2f} to {b[3]:.2f} | Area: {p['area']:.4f}")
        
    # 3. Compute pairwise overlaps
    overlaps = []
    for i in range(len(products)):
        for j in range(i + 1, len(products)):
            p1 = products[i]
            p2 = products[j]
            
            # Skip if both are south-polar OHRC as instructed, but user said:
            # "DO check them against each other and note if any two OHRC frames overlap each other"
            # We check ALL pairs.
            
            b1 = p1['bbox']
            b2 = p2['bbox']
            
            ix_min = max(b1[0], b2[0])
            iy_min = max(b1[1], b2[1])
            ix_max = min(b1[2], b2[2])
            iy_max = min(b1[3], b2[3])
            
            if ix_min < ix_max and iy_min < iy_max:
                inter_area = (ix_max - ix_min) * (iy_max - iy_min)
                smaller_area = min(p1['area'], p2['area'])
                overlap_pct = (inter_area / smaller_area * 100.0) if smaller_area > 0 else 0
                overlaps.append({
                    'pair': (p1, p2),
                    'overlap_pct': overlap_pct,
                    'inter_area': inter_area
                })
                
    overlaps.sort(key=lambda x: x['overlap_pct'], reverse=True)
    
    print("\n" + "=" * 80)
    print("                      PAIRWISE OVERLAPS (Sorted)")
    print("=" * 80)
    
    has_cross_sensor_overlap = False
    
    for o in overlaps:
        p1, p2 = o['pair']
        pct = o['overlap_pct']
        print(f"[{p1['sensor']}-{p2['sensor']}] {pct:>6.2f}% overlap | {p1['name'][:25]} vs {p2['name'][:25]}")
        if p1['sensor'] != p2['sensor']:
            has_cross_sensor_overlap = True
            
    if not has_cross_sensor_overlap:
        print("\n" + "!" * 80)
        print("NO CROSS-SENSOR OVERLAPS FOUND IN CURRENT DATA/RAW.")
        print("Go download more data rather than assuming a bug.")
        print("!" * 80)

if __name__ == "__main__":
    main()
