import cv2
import numpy as np
from lumen.ingest.selene_adapter import load_selene_image
from lumen.preprocess.overlap_crop import crop_to_bbox
from lumen.preprocess.radiometric import apply_clahe, normalize_to_float
from lumen.geometry.outlier_reject import estimate_transform_magsac
from lumen.features.deep_matcher import DeepMatcher
import rasterio

# Geographic overlap window
overlap_bbox = (141.0, -9.0, 142.71, -6.0) # (min_lon, min_lat, max_lon, max_lat)

print('=== 1. Loading SELENE cropped to overlap ===')
selene_lbl = 'data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.lbl'
selene_crop, selene_bbox = load_selene_image(selene_lbl, bbox_crop=overlap_bbox)
print('SELENE crop shape:', selene_crop.shape, 'bbox:', selene_bbox)

print('\n=== 2. Loading Chandrayaan-2 TMC-2 Nadir Ortho cropped to same overlap ===')
# Read from the orthorectified TMC GeoTIFF if available, or orthorectify window
tmc_ortho_path = Path('data/processed/FINAL_DEMO/tmc_ncn_ortho.tif')
if not tmc_ortho_path.exists():
    tmc_ortho_path = Path('data/processed/tmc_ncn_ortho.tif')

print('TMC Ortho exists:', tmc_ortho_path.exists())
if tmc_ortho_path.exists():
    with rasterio.open(tmc_ortho_path) as src:
        print('TMC GeoTIFF bounds:', src.bounds)
        # Windowed read from bounds
        from rasterio.windows import from_bounds
        win = from_bounds(*overlap_bbox, transform=src.transform)
        tmc_crop = src.read(1, window=win)
        print('TMC crop shape:', tmc_crop.shape)
else:
    # Read from data/processed/FINAL_DEMO
    print('Searching for orthorectified TMC...')
