import rasterio
from rasterio.windows import from_bounds
import numpy as np
import cv2
from pathlib import Path
from lumen.ingest.selene_adapter import load_selene_image
from lumen.preprocess.radiometric import apply_clahe, normalize_to_float
from lumen.geometry.outlier_reject import estimate_transform_magsac
from lumen.features.deep_matcher import DeepMatcher
from lumen.features.rift2 import match_rift2

# Bounding box of intersection
# Note: Lat runs from -9.0 to -6.0, Lon runs from 141.0 to 142.707
overlap_bbox = (141.0, -9.0, 142.707, -6.0)

print('=== 1. Reading windowed TMC-2 Nadir (ISRO) ===')
tmc_tif = 'data/processed/real_ortho_outputs/tmc_ncn_ortho.tif'
with rasterio.open(tmc_tif) as src:
    win = from_bounds(*overlap_bbox, transform=src.transform)
    tmc_crop = src.read(1, window=win)
    print(f'TMC-2 crop shape: {tmc_crop.shape}, min: {tmc_crop.min()}, max: {tmc_crop.max()}')

print('\n=== 2. Reading windowed SELENE TC (JAXA) ===')
selene_lbl = 'data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.lbl'
selene_crop, _ = load_selene_image(selene_lbl, bbox_crop=overlap_bbox)
print(f'SELENE crop shape: {selene_crop.shape}, min: {selene_crop.min()}, max: {selene_crop.max()}')

# Resize both to the SAME resolution for scale matching (target 2048 high)
target_h = 2048
target_w = int(target_h * (selene_crop.shape[1] / selene_crop.shape[0]))

tmc_resized = cv2.resize(tmc_crop.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)
selene_resized = cv2.resize(selene_crop.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)
print(f'Matched dimensions: {target_h} x {target_w}')

# Normalize and CLAHE
p1, p99 = np.percentile(tmc_resized[tmc_resized > 0], (1, 99))
tmc_norm = np.clip((tmc_resized - p1) / (p99 - p1), 0, 1)
tmc_u8 = (apply_clahe(tmc_norm) * 255).astype(np.uint8)

p1_s, p99_s = np.percentile(selene_resized[selene_resized > 0], (1, 99))
selene_norm = np.clip((selene_resized - p1_s) / (p99_s - p1_s), 0, 1)
selene_u8 = (apply_clahe(selene_norm) * 255).astype(np.uint8)

out_dir = Path('data/processed/cross_mission_matched')
out_dir.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(out_dir / 'tmc_norm.png'), tmc_u8)
cv2.imwrite(str(out_dir / 'selene_norm.png'), selene_u8)
print('Wrote normalized crops to data/processed/cross_mission_matched/')

# Feature matching with SIFT
print('\n=== 3. SIFT Feature Matching ===')
sift = cv2.SIFT_create(nfeatures=2000)
kp0, des0 = sift.detectAndCompute(tmc_u8, None)
kp1, des1 = sift.detectAndCompute(selene_u8, None)
print(f'SIFT keypoints: TMC={len(kp0)}, SELENE={len(kp1)}')

bf = cv2.BFMatcher()
raw_matches = bf.knnMatch(des0, des1, k=2)
good = []
for m, n in raw_matches:
    if m.distance < 0.75 * n.distance:
        good.append(m)
print(f'SIFT Good matches (Lowe ratio 0.75): {len(good)}')

if len(good) >= 4:
    pts0 = np.float32([kp0[m.queryIdx].pt for m in good])
    pts1 = np.float32([kp1[m.trainIdx].pt for m in good])
    H, inlier_mask = cv2.findHomography(pts0, pts1, cv2.USAC_MAGSAC, 5.0)
    inliers = inlier_mask.ravel().astype(bool) if inlier_mask is not None else np.zeros(len(pts0), dtype=bool)
    n_inliers = int(np.sum(inliers))
    print(f'MAGSAC++ Inliers: {n_inliers} / {len(good)} ({n_inliers / len(good) * 100:.1f}%)')
    if n_inliers >= 4:
        # Reprojection error
        pts0_h = np.column_stack([pts0[inliers], np.ones(n_inliers)])
        proj = (H @ pts0_h.T).T
        proj = proj[:, :2] / proj[:, 2:]
        residuals = np.linalg.norm(proj - pts1[inliers], axis=1)
        rmse = float(np.sqrt(np.mean(residuals**2)))
        print(f'Matcher Reprojection RMSE: {rmse:.3f} px')
else:
    print('Trying ORB...')
