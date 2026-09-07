"""
Technique 1: Real Lommel-Seeliger Photometric Normalization on Chandrayaan-2 TMC-2
before SIFT / ORB Feature Matching against JAXA SELENE TC.
"""

import sys
from pathlib import Path
import numpy as np
import cv2
import rasterio
from rasterio.windows import from_bounds

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lumen.ingest.selene_adapter import load_selene_image, parse_selene_pds3
from lumen.ingest.pds4_parser import parse_pds4
from lumen.preprocess.photometric import lommel_seeliger_normalize, create_shadow_mask
from lumen.preprocess.radiometric import apply_clahe, normalize_to_float
from lumen.geometry.outlier_reject import estimate_transform_magsac
from lumen.evaluation.metrics import compute_ssim

def run_technique_1():
    print("=================================================================")
    print("TECHNIQUE 1: LOMMEL-SEELIGER PHOTOMETRIC NORMALIZATION + SIFT/ORB")
    print("=================================================================")

    # 1. Geographic Overlap
    overlap_bbox = (141.0, -9.0, 142.707, -6.0) # (min_lon, min_lat, max_lon, max_lat)
    print(f"Target Footprint Overlap Bounding Box: {overlap_bbox}")

    # 2. Ingest Metadata from raw XML
    tmc_xml = PROJECT_ROOT / "data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml"
    meta_tmc = parse_pds4(tmc_xml, validate_required=False)
    sun_el = float(meta_tmc.get("solar_elevation") or meta_tmc.get("sun_elevation") or 50.94)
    sun_az = float(meta_tmc.get("solar_azimuth") or meta_tmc.get("sun_azimuth") or 69.56)
    inc_angle = 90.0 - sun_el
    emi_angle = float(meta_tmc.get("emission_angle") or 0.0)
    phase_angle = float(meta_tmc.get("phase_angle") or inc_angle)
    print(f"ISRO TMC-2 Telemetry: Solar El={sun_el}°, Az={sun_az}°, Incidence={inc_angle:.2f}°, Emission={emi_angle:.2f}°, Phase={phase_angle:.2f}°")

    # 3. Load Datasets over the shared overlap
    tmc_tif = PROJECT_ROOT / "data/processed/real_ortho_outputs/tmc_ncn_ortho.tif"
    print(f"Loading TMC-2 from: {tmc_tif}")
    with rasterio.open(tmc_tif) as src:
        win = from_bounds(*overlap_bbox, transform=src.transform)
        tmc_crop = src.read(1, window=win)
    print(f"TMC-2 crop shape: {tmc_crop.shape}, dtype: {tmc_crop.dtype}, min: {tmc_crop.min()}, max: {tmc_crop.max()}")

    selene_lbl = PROJECT_ROOT / "data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.lbl"
    print(f"Loading JAXA SELENE TC from: {selene_lbl}")
    selene_crop, effective_bbox = load_selene_image(selene_lbl, bbox_crop=overlap_bbox)
    print(f"SELENE crop shape: {selene_crop.shape}, dtype: {selene_crop.dtype}, min: {selene_crop.min()}, max: {selene_crop.max()}")

    # 4. Match dimensions for direct comparison (e.g. 2048 x 1165)
    target_h = 2048
    aspect = selene_crop.shape[1] / selene_crop.shape[0]
    target_w = int(target_h * aspect)
    print(f"Resampling to common analysis grid: {target_h} x {target_w}")

    tmc_matched = cv2.resize(tmc_crop.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)
    selene_matched = cv2.resize(selene_crop.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)

    # 5. Apply Pipeline's actual Lommel-Seeliger Normalization to TMC
    print("\nApplying Lommel-Seeliger normalization to Chandrayaan-2 TMC-2...")
    tmc_float = normalize_to_float(tmc_matched)

    inc_arr = np.full(tmc_float.shape, inc_angle, dtype=np.float32)
    emi_arr = np.full(tmc_float.shape, emi_angle, dtype=np.float32)
    phase_arr = np.full(tmc_float.shape, phase_angle, dtype=np.float32)

    # Create shadow mask
    shadow_mask = create_shadow_mask(tmc_float, inc_arr, dn_threshold=1e-3, inc_threshold=85.0)
    print(f"Shadow mask pixels: {np.sum(shadow_mask)} / {shadow_mask.size} ({np.mean(shadow_mask)*100:.2f}%)")

    # Apply Lommel-Seeliger (standard alpha=30.0)
    tmc_ls = lommel_seeliger_normalize(
        image=tmc_float,
        inc=inc_arr,
        emi=emi_arr,
        phase=phase_arr,
        shadow_mask=shadow_mask,
        alpha=30.0
    )
    # Finish with CLAHE as in lumen pipeline Stage 4
    tmc_ls_clahe = apply_clahe(tmc_ls)
    if tmc_ls_clahe.dtype == np.uint16:
        tmc_u8 = (tmc_ls_clahe / 256.0).astype(np.uint8)
    elif tmc_ls_clahe.dtype != np.uint8:
        mn, mx = tmc_ls_clahe.min(), tmc_ls_clahe.max()
        tmc_u8 = (((tmc_ls_clahe - mn) / (mx - mn)) * 255.0).astype(np.uint8) if mx > mn else np.zeros_like(tmc_ls_clahe, dtype=np.uint8)
    else:
        tmc_u8 = tmc_ls_clahe

    # Normalize SELENE reference
    sel_p1, sel_p99 = np.percentile(selene_matched[selene_matched > 0], (1, 99))
    sel_norm = np.clip((selene_matched - sel_p1) / (sel_p99 - sel_p1), 0.0, 1.0)
    sel_clahe = apply_clahe(sel_norm)
    if sel_clahe.dtype == np.uint16:
        selene_u8 = (sel_clahe / 256.0).astype(np.uint8)
    else:
        selene_u8 = (sel_clahe * 255.0).astype(np.uint8)

    # Save output artifacts
    out_dir = PROJECT_ROOT / "data/processed/cross_mission_technique1"
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "tmc_lommel_seeliger.png"), tmc_u8)
    cv2.imwrite(str(out_dir / "selene_normalized.png"), selene_u8)
    print(f"Saved normalized arrays to {out_dir}")

    # 6. Feature Matching: SIFT
    print("\n--- 6A. SIFT Feature Matching ---")
    sift = cv2.SIFT_create(nfeatures=4000)
    kp_tmc, des_tmc = sift.detectAndCompute(tmc_u8, None)
    kp_sel, des_sel = sift.detectAndCompute(selene_u8, None)
    print(f"SIFT keypoints detected: TMC-2={len(kp_tmc)}, SELENE={len(kp_sel)}")

    bf = cv2.BFMatcher(cv2.NORM_L2)
    raw_matches = bf.knnMatch(des_tmc, des_sel, k=2)

    # Lowe ratio test at 0.80
    good_sift = [m for m, n in raw_matches if m.distance < 0.80 * n.distance]
    print(f"SIFT Candidate Matches (Lowe ratio < 0.80): {len(good_sift)}")

    sift_inliers = 0
    sift_inlier_ratio = 0.0
    sift_rmse = None
    if len(good_sift) >= 4:
        pts_src = np.float32([kp_tmc[m.queryIdx].pt for m in good_sift])
        pts_dst = np.float32([kp_sel[m.trainIdx].pt for m in good_sift])

        H, inlier_mask = estimate_transform_magsac(pts_src, pts_dst, confidence=0.999, max_iters=5000)
        sift_inliers = int(np.sum(inlier_mask))
        sift_inlier_ratio = float(sift_inliers / len(good_sift))
        print(f"SIFT MAGSAC++ inliers: {sift_inliers} / {len(good_sift)} ({sift_inlier_ratio*100:.2f}%)")

        if sift_inliers >= 4:
            pts_src_in = pts_src[inlier_mask]
            pts_dst_in = pts_dst[inlier_mask]
            pts_src_h = np.column_stack([pts_src_in, np.ones(len(pts_src_in))])
            proj = (H @ pts_src_h.T).T
            proj = proj[:, :2] / proj[:, 2:]
            residuals = np.linalg.norm(proj - pts_dst_in, axis=1)
            sift_rmse = float(np.sqrt(np.mean(residuals**2)))
            print(f"SIFT Residual Homography Error: {sift_rmse:.2f} px")
            print(f"Transformation matrix H:\n{H}")
    else:
        print("Fewer than 4 candidate matches found.")

    # 7. Feature Matching: ORB
    print("\n--- 6B. ORB Feature Matching ---")
    orb = cv2.ORB_create(nfeatures=4000)
    kp_tmc_orb, des_tmc_orb = orb.detectAndCompute(tmc_u8, None)
    kp_sel_orb, des_sel_orb = orb.detectAndCompute(selene_u8, None)
    print(f"ORB keypoints detected: TMC-2={len(kp_tmc_orb)}, SELENE={len(kp_sel_orb)}")

    orb_inliers = 0
    orb_inlier_ratio = 0.0
    if des_tmc_orb is not None and des_sel_orb is not None:
        bf_hamming = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        orb_matches = bf_hamming.match(des_tmc_orb, des_sel_orb)
        print(f"ORB Candidate Matches (cross-checked): {len(orb_matches)}")
        if len(orb_matches) >= 4:
            pts_src_orb = np.float32([kp_tmc_orb[m.queryIdx].pt for m in orb_matches])
            pts_dst_orb = np.float32([kp_sel_orb[m.trainIdx].pt for m in orb_matches])
            H_orb, mask_orb = estimate_transform_magsac(pts_src_orb, pts_dst_orb)
            orb_inliers = int(np.sum(mask_orb))
            orb_inlier_ratio = float(orb_inliers / len(orb_matches))
            print(f"ORB MAGSAC++ inliers: {orb_inliers} / {len(orb_matches)} ({orb_inlier_ratio*100:.2f}%)")

    # 8. Summary of Technique 1
    print("\n=================================================================")
    print("TECHNIQUE 1 VERDICT & EMPIRICAL FINDINGS:")
    print(f"SIFT Candidate Matches: {len(good_sift)}")
    print(f"SIFT Inliers: {sift_inliers} ({sift_inlier_ratio*100:.2f}%)")
    print(f"ORB Candidate Matches: {len(orb_matches) if des_tmc_orb is not None else 0}")
    print(f"ORB Inliers: {orb_inliers} ({orb_inlier_ratio*100:.2f}%)")
    print("=================================================================")

if __name__ == "__main__":
    run_technique_1()
