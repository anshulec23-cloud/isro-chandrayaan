import rasterio
from rasterio.windows import from_bounds
import numpy as np
import cv2
from pathlib import Path
from lumen.ingest.selene_adapter import load_selene_image
from lumen.preprocess.radiometric import apply_clahe, normalize_to_float
from lumen.geometry.outlier_reject import estimate_transform_magsac
from lumen.features.rift2 import match_rift2

# 11.2 km x 11.2 km lunar crater region
patch_bbox = (142.022, -7.685, 142.392, -7.315) # (min_lon, min_lat, max_lon, max_lat)

print('=== 1. Loading TMC-2 Patch (ISRO) ===')
with rasterio.open('data/processed/real_ortho_outputs/tmc_ncn_ortho.tif') as src:
    win = from_bounds(*patch_bbox, transform=src.transform)
    tmc_patch = src.read(1, window=win)
print(f'TMC-2 patch shape: {tmc_patch.shape}')

print('\n=== 2. Loading SELENE TC Patch (JAXA) ===')
selene_lbl = 'data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.lbl'
selene_patch, _ = load_selene_image(selene_lbl, bbox_crop=patch_bbox)
print(f'SELENE patch shape: {selene_patch.shape}')

# Target resolution 1024 x 1024 for both
size = 1024
tmc_res = cv2.resize(tmc_patch.astype(np.float32), (size, size), interpolation=cv2.INTER_AREA)
sel_res = cv2.resize(selene_patch.astype(np.float32), (size, size), interpolation=cv2.INTER_AREA)

# Normalization & CLAHE
p1, p99 = np.percentile(tmc_res, (1, 99))
tmc_u8 = (apply_clahe(np.clip((tmc_res - p1) / (p99 - p1), 0, 1)) * 255).astype(np.uint8)

p1_s, p99_s = np.percentile(sel_res, (1, 99))
sel_u8 = (apply_clahe(np.clip((sel_res - p1_s) / (p99_s - p1_s), 0, 1)) * 255).astype(np.uint8)

out_dir = Path('data/processed/cross_mission_patch')
out_dir.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(out_dir / 'tmc_patch.png'), tmc_u8)
cv2.imwrite(str(out_dir / 'selene_patch.png'), sel_u8)
print('Saved patch previews to data/processed/cross_mission_patch/')

print('\n=== 3. Testing SIFT Matching ===')
sift = cv2.SIFT_create(nfeatures=2000)
kp0, des0 = sift.detectAndCompute(tmc_u8, None)
kp1, des1 = sift.detectAndCompute(sel_u8, None)
print(f'Detected SIFT keypoints: TMC={len(kp0)}, SELENE={len(kp1)}')

bf = cv2.BFMatcher()
matches = bf.knnMatch(des0, des1, k=2)
good = [m for m, n in matches if m.distance < 0.80 * n.distance]
print(f'Good matches (ratio 0.80): {len(good)}')

if len(good) >= 4:
    pts0 = np.float32([kp0[m.queryIdx].pt for m in good])
    pts1 = np.float32([kp1[m.trainIdx].pt for m in good])
    H, mask = cv2.findHomography(pts0, pts1, cv2.USAC_MAGSAC, 5.0)
    inliers = mask.ravel().astype(bool) if mask is not None else np.zeros(len(pts0), dtype=bool)
    n_inliers = int(np.sum(inliers))
    print(f'MAGSAC++ Inliers: {n_inliers} / {len(good)} ({n_inliers / len(good) * 100:.1f}%)')
    if n_inliers >= 4:
        pts0_h = np.column_stack([pts0[inliers], np.ones(n_inliers)])
        proj = (H @ pts0_h.T).T
        proj = proj[:, :2] / proj[:, 2:]
        residuals = np.linalg.norm(proj - pts1[inliers], axis=1)
        rmse = float(np.sqrt(np.mean(residuals**2)))
        print(f'Matcher Reprojection RMSE: {rmse:.3f} px')

print('\n=== 4. Testing Phase Correlation (Global Translation) ===')
f0 = np.fft.fft2(tmc_u8.astype(np.float32))
f1 = np.fft.fft2(sel_u8.astype(np.float32))
cross_power = (f0 * np.conj(f1)) / (np.abs(f0 * np.conj(f1)) + 1e-6)
corr = np.fft.ifft2(cross_power).real
y_shift, x_shift = np.unravel_index(np.argmax(corr), corr.shape)
if y_shift > size // 2: y_shift -= size
if x_shift > size // 2: x_shift -= size
print(f'Phase correlation peak offset: dx={x_shift}, dy={y_shift} (correlation peak: {corr.max():.4f})')
