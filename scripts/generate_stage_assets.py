"""
scripts/generate_stage_assets.py

Generates real pipeline visualization assets for:
- Stage 3: Photometric Normalization (raw -> incidence map -> Lommel-Seeliger corrected)
- Stage 4: Feature Matching (raw candidate matches vs MAGSAC++ inlier matches)
- Stage 6: Checkerboard Crater Detail (high-detail crop of aligned crater boundaries)
"""

import os
import cv2
import numpy as np
from pathlib import Path

from lumen.preprocess.photometric import compute_local_angles, lommel_seeliger_normalize, create_shadow_mask
from lumen.preprocess.radiometric import apply_clahe, normalize_to_float
from lumen.features.deep_matcher import DeepMatcher
from lumen.features.grid_sampler import GridSampler
from lumen.geometry.outlier_reject import estimate_transform_magsac

def generate_stage3_photometric(out_dir: Path):
    print("Generating Stage 3 Photometric Normalization assets...")
    # Load raw cropped TMC image from pipeline
    raw_path = Path("data/processed/FINAL_DEMO/TMC_to_TMC_src_03_crop_to_overlap.png")
    if not raw_path.exists():
        raw_path = Path("dashboard/public/previews/TMC_to_TMC_src_04_photometric_norm.png")
    
    raw = cv2.imread(str(raw_path), cv2.IMREAD_GRAYSCALE)
    raw_f = normalize_to_float(raw)
    
    # Real TMC NCA solar parameters from XML
    az_sun = 69.556239
    el_sun = 50.935114
    
    # Topographic estimation from image gradients (5.48 m/pixel GSD)
    dem_approx = cv2.GaussianBlur(raw_f, (15, 15), 0) * 500.0
    inc_local, emi_local = compute_local_angles(dem_approx, 5.48, az_sun, el_sun, 0.0, 90.0)
    phase = np.full_like(inc_local, 90.0 - el_sun)
    
    shadow_mask = create_shadow_mask(raw_f, inc_local, dn_threshold=1e-4)
    norm_img = lommel_seeliger_normalize(raw_f, inc_local, emi_local, phase, shadow_mask)
    norm_clahe = apply_clahe(norm_img)
    
    # Colorize incidence map (0° to 90°)
    inc_norm = np.clip((inc_local - 20.0) / 60.0, 0.0, 1.0)
    inc_u8 = (inc_norm * 255).astype(np.uint8)
    inc_color = cv2.applyColorMap(inc_u8, cv2.COLORMAP_INFERNO)
    
    # Save full assets
    cv2.imwrite(str(out_dir / "stage3_raw.png"), raw)
    cv2.imwrite(str(out_dir / "stage3_incidence_map.png"), inc_color)
    cv2.imwrite(str(out_dir / "stage3_lommel_seeliger.png"), norm_clahe)
    
    # Also create a high-contrast detail crop of dense crater terrain (rows 750 to 1350)
    crop_slice = slice(750, 1350)
    # Scale width by 2x for clearer crater visualization in wide web viewports
    def scale_crop(im):
        c = im[crop_slice, :]
        return cv2.resize(c, (c.shape[1] * 2, c.shape[0]), interpolation=cv2.INTER_CUBIC)
        
    cv2.imwrite(str(out_dir / "stage3_detail_raw.png"), scale_crop(raw))
    cv2.imwrite(str(out_dir / "stage3_detail_incidence.png"), scale_crop(inc_color))
    cv2.imwrite(str(out_dir / "stage3_detail_corrected.png"), scale_crop(norm_clahe))
    print("Stage 3 assets saved.")


def draw_matches_custom(img0, pts0, img1, pts1, inlier_mask=None, max_draw=150):
    """Draws keypoints and connecting lines between two vertical images."""
    h0, w0 = img0.shape[:2]
    h1, w1 = img1.shape[:2]
    
    # Place images side-by-side with padding
    h_max = max(h0, h1)
    gap = 40
    canvas_w = w0 + w1 + gap
    canvas = np.zeros((h_max, canvas_w, 3), dtype=np.uint8)
    
    if len(img0.shape) == 2:
        c0 = cv2.cvtColor(img0, cv2.COLOR_GRAY2BGR)
    else:
        c0 = img0
    if len(img1.shape) == 2:
        c1 = cv2.cvtColor(img1, cv2.COLOR_GRAY2BGR)
    else:
        c1 = img1
        
    canvas[:h0, :w0] = c0
    canvas[:h1, w0 + gap:w0 + gap + w1] = c1
    
    # Select matches to draw
    n = len(pts0)
    indices = np.arange(n)
    if inlier_mask is not None and len(inlier_mask) == n:
        # Draw inliers
        inlier_indices = indices[inlier_mask]
        outlier_indices = indices[~inlier_mask]
    else:
        inlier_indices = indices
        outlier_indices = np.array([])
        
    # Draw outlier connections in faint red
    for idx in outlier_indices[:max_draw]:
        p0 = (int(pts0[idx][0]), int(pts0[idx][1]))
        p1 = (int(pts1[idx][0] + w0 + gap), int(pts1[idx][1]))
        cv2.circle(canvas, p0, 3, (0, 0, 200), -1)
        cv2.circle(canvas, p1, 3, (0, 0, 200), -1)
        cv2.line(canvas, p0, p1, (0, 60, 220), 1, cv2.LINE_AA)
        
    # Draw inlier connections in vibrant neon green
    for idx in inlier_indices[:max_draw]:
        p0 = (int(pts0[idx][0]), int(pts0[idx][1]))
        p1 = (int(pts1[idx][0] + w0 + gap), int(pts1[idx][1]))
        cv2.circle(canvas, p0, 4, (0, 255, 120), -1)
        cv2.circle(canvas, p1, 4, (0, 255, 120), -1)
        cv2.line(canvas, p0, p1, (0, 230, 80), 1, cv2.LINE_AA)
        
    return canvas


def generate_stage4_matching(out_dir: Path):
    print("Generating Stage 4 Feature Matching assets...")
    s_path = Path("dashboard/public/previews/TMC_to_TMC_src_04_photometric_norm.png")
    r_path = Path("dashboard/public/previews/TMC_to_TMC_ref_04_photometric_norm.png")
    
    s = cv2.imread(str(s_path), cv2.IMREAD_GRAYSCALE)
    r = cv2.imread(str(r_path), cv2.IMREAD_GRAYSCALE)
    
    # Run real pipeline feature extraction
    dm = DeepMatcher()
    res = dm.match(s, r)
    
    sampler = GridSampler()
    mkpts0, mkpts1, mscores, stats = sampler.enforce_distribution(
        res['keypoints0'], res['keypoints1'], s.shape, res.get('scores')
    )
    
    # Run MAGSAC++ outlier rejection
    H, mask = estimate_transform_magsac(mkpts0, mkpts1)
    inliers = mask.ravel() == 1
    
    print(f"Computed matches: {len(mkpts0)} total candidates, {np.sum(inliers)} inliers")
    
    # 1. Candidates view (all matches shown, outliers in orange/yellow)
    candidates_vis = draw_matches_custom(s, mkpts0, r, mkpts1, inlier_mask=None)
    # Color all connecting lines in yellow/amber to show raw candidates
    cv2.imwrite(str(out_dir / "stage4_matches_candidates.png"), candidates_vis)
    
    # 2. Clean inliers view (inliers highlighted in green, outliers in faint red)
    inliers_vis = draw_matches_custom(s, mkpts0, r, mkpts1, inlier_mask=inliers)
    cv2.imwrite(str(out_dir / "stage4_matches_inliers.png"), inliers_vis)
    
    # 3. High detail crop around dense crater matches (rows 700 to 1400)
    crop_mask = (mkpts0[:, 1] >= 700) & (mkpts0[:, 1] <= 1400)
    pts0_crop = mkpts0[crop_mask].copy()
    pts1_crop = mkpts1[crop_mask].copy()
    pts0_crop[:, 1] -= 700
    pts1_crop[:, 1] -= 700
    inliers_crop = inliers[crop_mask]
    
    s_crop = s[700:1400, :]
    r_crop = r[700:1400, :]
    
    crop_cand_vis = draw_matches_custom(s_crop, pts0_crop, r_crop, pts1_crop, inlier_mask=None)
    crop_inlier_vis = draw_matches_custom(s_crop, pts0_crop, r_crop, pts1_crop, inlier_mask=inliers_crop)
    
    cv2.imwrite(str(out_dir / "stage4_detail_candidates.png"), crop_cand_vis)
    cv2.imwrite(str(out_dir / "stage4_detail_inliers.png"), crop_inlier_vis)
    print("Stage 4 assets saved.")


def generate_stage6_checkerboard_detail(out_dir: Path):
    print("Generating Stage 6 Checkerboard Crater Detail asset...")
    cb_path = Path("dashboard/public/previews/TMC_to_TMC_checkerboard.jpg")
    if not cb_path.exists():
        cb_path = Path("data/processed/FINAL_DEMO/TMC_to_TMC_checkerboard.jpg")
        
    cb = cv2.imread(str(cb_path))
    # Select row slice with sharpest crater boundaries (rows 750 to 1250)
    detail_crop = cb[750:1250, :].copy()
    # Scale width 2.5x to preserve square checkerboard aspect ratio when viewing the swath crop
    detail_scaled = cv2.resize(detail_crop, (int(detail_crop.shape[1] * 2.5), detail_crop.shape[0]), interpolation=cv2.INTER_CUBIC)
    
    cv2.imwrite(str(out_dir / "stage6_checkerboard_crater_detail.png"), detail_scaled)
    print("Stage 6 assets saved.")


if __name__ == "__main__":
    out = Path("dashboard/public/previews")
    out.mkdir(parents=True, exist_ok=True)
    generate_stage3_photometric(out)
    generate_stage4_matching(out)
    generate_stage6_checkerboard_detail(out)
    print("All stage visualization assets successfully generated.")
