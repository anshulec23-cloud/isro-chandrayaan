import os
import cv2
import numpy as np
import json
import logging
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lumen.pipeline.orchestrator import RegistrationPipeline, crop_pair_to_overlap
from lumen.evaluation.metrics import compute_rmse

logging.basicConfig(level=logging.INFO)

def to_uint8(img):
    img = np.nan_to_num(img)
    valid = img[img > 0]
    if len(valid) == 0:
        return np.zeros_like(img, dtype=np.uint8)
    p2, p98 = np.percentile(valid, (2, 98))
    if p98 == p2:
        return np.zeros_like(img, dtype=np.uint8)
    img = np.clip((img - p2) / (p98 - p2), 0, 1)
    return (img * 255).astype(np.uint8)

def get_independent_sift_points(img1, img2, num_points=20):
    img1_8u = to_uint8(img1)
    img2_8u = to_uint8(img2)
    
    sift = cv2.SIFT_create(nfeatures=5000, contrastThreshold=0.02)
    kp1, des1 = sift.detectAndCompute(img1_8u, None)
    kp2, des2 = sift.detectAndCompute(img2_8u, None)
    
    flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
    matches = flann.knnMatch(des1, des2, k=2)
    
    good_matches = []
    for m, n in matches:
        if m.distance < 0.7 * n.distance:
            good_matches.append(m)
            
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 2)
    
    if len(src_pts) >= 4:
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        inlier_src = src_pts[mask.ravel() == 1]
        inlier_dst = dst_pts[mask.ravel() == 1]
    else:
        inlier_src = src_pts
        inlier_dst = dst_pts
        
    # Sample 20
    if len(inlier_src) > num_points:
        idx = np.random.choice(len(inlier_src), num_points, replace=False)
        inlier_src = inlier_src[idx]
        inlier_dst = inlier_dst[idx]
        
    return inlier_src, inlier_dst

def main():
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data" / "raw"
    
    tmc_nca_xml = str(data_dir / "ch2_tmc_nca_20260813T0627378526_d_img_d18" / "data" / "calibrated" / "20260813" / "ch2_tmc_nca_20260813T0627378526_d_img_d18.xml")
    tmc_ncn_xml = str(data_dir / "ch2_tmc_ncn_20260813T0627378557_d_img_d18" / "data" / "calibrated" / "20260813" / "ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml")
    
    pipeline = RegistrationPipeline(config={})
    
    print("1. Ingesting...")
    source_img, source_meta = pipeline._ingest(tmc_nca_xml)
    ref_img, ref_meta = pipeline._ingest(tmc_ncn_xml)
    
    print("2. Preprocessing (Orthorectify + Crop + Norm)...")
    target_gsd_m = 5.48
    source_ortho, src_bbox = pipeline._orthorectify_image(source_img, source_meta, target_gsd_m, max_dim=2048)
    ref_ortho, ref_bbox = pipeline._orthorectify_image(ref_img, ref_meta, target_gsd_m, max_dim=2048)
    
    source_crop, ref_crop, overlap_bbox = crop_pair_to_overlap(source_ortho, src_bbox, ref_ortho, ref_bbox)
    
    source_pre = pipeline._normalize_image(source_crop, source_meta)
    ref_pre = pipeline._normalize_image(ref_crop, ref_meta)
    
    print("3. Matching with Pipeline (LightGlue)...")
    matches = pipeline._extract_features(source_pre, ref_pre, "deep", "TMC", "TMC")
    transform, inlier_pts0, inlier_pts1, outlier_pts0, outlier_pts1 = pipeline._estimate_geometry(matches, source_pre, ref_pre)
    
    # Calculate Matcher RMSE
    pts_src_h = np.hstack([inlier_pts0, np.ones((len(inlier_pts0), 1))])
    pts_proj = (transform @ pts_src_h.T).T
    pts_transformed = pts_proj[:, :2] / pts_proj[:, 2:]
    matcher_rmse = compute_rmse(inlier_pts1, pts_transformed).get("rmse", 0.0)
    
    print("4. Extracting Independent Points (SIFT)...")
    sift_src, sift_ref = get_independent_sift_points(source_pre, ref_pre, 20)
    print(f"Found {len(sift_src)} independent points.")
    
    # Calculate Independent RMSE using the Pipeline's transform
    pts_src_h_sift = np.hstack([sift_src, np.ones((len(sift_src), 1))])
    pts_proj_sift = (transform @ pts_src_h_sift.T).T
    pts_transformed_sift = pts_proj_sift[:, :2] / pts_proj_sift[:, 2:]
    independent_rmse = compute_rmse(sift_ref, pts_transformed_sift).get("rmse", 0.0)
    
    print("-" * 50)
    print(f"Matcher-based RMSE (LightGlue): {matcher_rmse:.3f} px")
    print(f"Independent RMSE (SIFT):        {independent_rmse:.3f} px")
    print("-" * 50)
    
    # Save to JSON
    out_json = {
        "checkpoint_source": "independent_sift",
        "num_checkpoints": len(sift_src),
        "source_path": tmc_nca_xml,
        "reference_path": tmc_ncn_xml,
        "source_points": sift_src.tolist(),
        "reference_points": sift_ref.tolist(),
        "matcher_rmse": matcher_rmse,
        "independent_rmse": independent_rmse
    }
    
    out_path = root_dir / "data" / "independent_checkpoints_tmc_tmc.json"
    with open(out_path, "w") as f:
        json.dump(out_json, f, indent=4)
        
    print(f"Saved independent checkpoints to {out_path}")

if __name__ == '__main__':
    main()
