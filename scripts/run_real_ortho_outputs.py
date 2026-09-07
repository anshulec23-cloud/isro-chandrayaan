import sys
from pathlib import Path
import rasterio

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lumen.ingest.pds4_parser import parse_pds4, load_binary_image
from lumen.ingest.metadata import extract_metadata
from lumen.preprocess.orthorectify import orthorectify

def process_product(xml_path_str, output_tiff):
    print(f"\nProcessing {xml_path_str}...")
    
    label = parse_pds4(xml_path_str)
    img = load_binary_image(xml_path_str)
    meta = extract_metadata(label)
    
    if 'gcp_csv_path' in label and label['gcp_csv_path']:
        meta['gcp_csv_path'] = label['gcp_csv_path']
    if 'iirs_loc_path' in label and label['iirs_loc_path']:
        meta['iirs_loc_path'] = label['iirs_loc_path']
        
    gsd = meta.get('pixel_resolution', 5.0)
    print(f"Native GSD: {gsd} m")
    
    # Cap dimensions inside orthorectify can be used, but since we are producing real outputs
    # maybe we shouldn't pass max_dim if we want the full thing, or just pass a large max_dim?
    # Actually orthorectify doesn't cap dimensions itself; orchestrator does it *after* orthorectify.
    # So orthorectify produces the full grid.
    
    try:
        res = orthorectify(
            image=img,
            metadata=meta,
            dem_dataset=None,  # Not using DEM for this pass
            target_gsd_m=gsd
        )
    except Exception as e:
        print(f"Orthorectification failed: {e}")
        return False
        
    out_img = res.image
    out_transform = res.transform["affine"]
    out_crs = res.transform["crs"]
    
    print(f"Warped image shape: {out_img.shape}")
    print(f"Bounds: {res.transform['bbox_lonlat']}")
    
    # Save as GeoTIFF
    out_path = Path(output_tiff)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure shape has height, width
    height, width = out_img.shape
    
    with rasterio.open(
        out_path, 'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=out_img.dtype,
        crs=out_crs,
        transform=out_transform,
        compress='lzw',
        BIGTIFF='YES'
    ) as dst:
        dst.write(out_img, 1)
        
    print(f"Saved real GeoTIFF to: {out_path}")
    return True

if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent
    
    products = [
        ("data/raw/ch2_ohr_ncp_20260130T1309574436_d_img_d18/data/calibrated/20260130/ch2_ohr_ncp_20260130T1309574436_d_img_d18.xml", "ohrc_calibrated_ortho.tif"),
    ]
    
    out_dir = root_dir / "data" / "processed" / "real_ortho_outputs"
    
    for rel_path, out_name in products:
        full_path = root_dir / rel_path
        out_tiff = out_dir / out_name
        process_product(str(full_path), str(out_tiff))
