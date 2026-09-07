import rasterio
from rasterio.windows import from_bounds, Window
import numpy as np

overlap_bbox = (141.0, -9.0, 142.707, -6.0)
with rasterio.open('data/processed/real_ortho_outputs/tmc_ncn_ortho.tif') as src:
    win = from_bounds(*overlap_bbox, transform=src.transform)
    raw_tmc = src.read(1, window=win)
    valid = raw_tmc > 0
    rows = np.any(valid, axis=1)
    cols = np.any(valid, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    mid_r = (rmin + rmax) // 2
    mid_c = (cmin + cmax) // 2
    sub_size = 2048

    # Window in terms of the full GeoTIFF:
    full_col_off = win.col_off + mid_c - sub_size // 2
    full_row_off = win.row_off + mid_r - sub_size // 2
    central_win = Window(col_off=full_col_off, row_off=full_row_off, width=sub_size, height=sub_size)
    central_bounds = rasterio.windows.bounds(central_win, transform=src.transform)
    print(f'Central 100% valid Chandrayaan-2 window bounds: {central_bounds}')
