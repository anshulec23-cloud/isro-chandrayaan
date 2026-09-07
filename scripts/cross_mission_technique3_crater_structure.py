"""
Technique 3: Crater-Based Structural Matching (Point-Set Invariant)
for Chandrayaan-2 TMC-2 Nadir vs JAXA SELENE TC.

Extracts crater rims via edge/Hough circles, computes relative spatial
distance/size descriptors, and matches crater centroids via RANSAC.
"""

import sys
from pathlib import Path
import numpy as np
import cv2
import rasterio
from rasterio.windows import from_bounds
from scipy.spatial import KDTree

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lumen.ingest.selene_adapter import load_selene_image
from lumen.preprocess.radiometric import apply_clahe
from lumen.geometry.outlier_reject import estimate_transform_magsac

def detect_craters(image: np.ndarray, min_radius: int = 12, max_radius: int = 120) -> list[tuple[float, float, float]]:
    """
    Detect craters using a combination of Canny edges and Hough Circle Transform.
    Returns list of (x, y, radius).
    """
    blurred = cv2.GaussianBlur(image, (9, 9), 2.0)
    
    # Adaptive Hough Circles
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min_radius * 1.5,
        param1=50,
        param2=28,
        minRadius=min_radius,
        maxRadius=max_radius
    )
    
    detected = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype(int)
        for (x, y, r) in circles:
            # Boundary guard
            if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
                # Verify local non-zero
                if image[y, x] > 0:
                    detected.append((float(x), float(y), float(r)))
    return detected

def build_crater_descriptors(craters: list[tuple[float, float, float]], k_neighbors: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """
    Build relative geometric distance/scale descriptors for each crater.
    Invariant to rotation, translation, and absolute lighting.
    """
    if len(craters) < k_neighbors + 1:
        return np.empty((0, 2)), np.empty((0, k_neighbors * 2))
        
    pts = np.array([[c[0], c[1]] for c in craters], dtype=np.float32)
    radii = np.array([c[2] for c in craters], dtype=np.float32)
    
    tree = KDTree(pts)
    descriptors = []
    
    for i, pt in enumerate(pts):
        dists, idxs = tree.query(pt, k=k_neighbors + 1)
        # Skip self (index 0)
        n_dists = dists[1:]
        n_idxs = idxs[1:]
        
        # Scale-invariant relative distances: dist / self_radius
        rel_dists = n_dists / (radii[i] + 1e-3)
        # Relative sizes: neighbor_radius / self_radius
        rel_sizes = radii[n_idxs] / (radii[i] + 1e-3)
        
        # Sort by distance for order invariance
        sort_order = np.argsort(rel_dists)
        feat = np.concatenate([rel_dists[sort_order], rel_sizes[sort_order]])
        descriptors.append(feat)
        
    return pts, np.array(descriptors, dtype=np.float32)

def run_technique_3():
    print("=================================================================")
    print("TECHNIQUE 3: CRATER-BASED STRUCTURAL MATCHING (POINT-SET RANSAC)")
    print("=================================================================")

    overlap_bbox = (141.0, -9.0, 142.707, -6.0)

    # 1. Load data
    tmc_tif = PROJECT_ROOT / "data/processed/real_ortho_outputs/tmc_ncn_ortho.tif"
    with rasterio.open(tmc_tif) as src:
        win = from_bounds(*overlap_bbox, transform=src.transform)
        tmc_crop = src.read(1, window=win)

    selene_lbl = PROJECT_ROOT / "data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.lbl"
    selene_crop, _ = load_selene_image(selene_lbl, bbox_crop=overlap_bbox)

    target_h = 2048
    target_w = int(target_h * (selene_crop.shape[1] / selene_crop.shape[0]))
    tmc_res = cv2.resize(tmc_crop.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)
    sel_res = cv2.resize(selene_crop.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)

    p1, p99 = np.percentile(tmc_res[tmc_res > 0], (1, 99))
    tmc_u8 = (apply_clahe(np.clip((tmc_res - p1) / (p99 - p1), 0, 1)) * 255.0).astype(np.uint8)

    p1_s, p99_s = np.percentile(sel_res[sel_res > 0], (1, 99))
    selene_u8 = (apply_clahe(np.clip((sel_res - p1_s) / (p99_s - p1_s), 0, 1)) * 255.0).astype(np.uint8)

    # 2. Detect craters
    print("\nDetecting craters on Chandrayaan-2 TMC-2 and JAXA SELENE TC...")
    craters_tmc = detect_craters(tmc_u8, min_radius=10, max_radius=100)
    craters_sel = detect_craters(selene_u8, min_radius=10, max_radius=100)
    print(f"Craters detected: TMC-2 = {len(craters_tmc)}, SELENE TC = {len(craters_sel)}")

    # 3. Compute relative geometric constellation descriptors
    k_neighbors = 5
    pts_tmc, desc_tmc = build_crater_descriptors(craters_tmc, k_neighbors=k_neighbors)
    pts_sel, desc_sel = build_crater_descriptors(craters_sel, k_neighbors=k_neighbors)

    if len(desc_tmc) == 0 or len(desc_sel) == 0:
        print("Not enough craters found to construct geometric constellations.")
        return

    # 4. Match crater descriptors
    bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
    matches = bf.match(desc_tmc, desc_sel)
    print(f"Candidate matched crater pairs (cross-checked): {len(matches)}")

    inliers_count = 0
    inlier_ratio = 0.0
    rmse = None

    if len(matches) >= 4:
        pts0 = np.float32([pts_tmc[m.queryIdx] for m in matches])
        pts1 = np.float32([pts_sel[m.trainIdx] for m in matches])

        # RANSAC Rigid/Affine Fit
        M, mask = cv2.estimateAffinePartial2D(pts0, pts1, method=cv2.RANSAC, ransacReprojThreshold=15.0)
        if mask is not None:
            inliers = mask.ravel().astype(bool)
            inliers_count = int(np.sum(inliers))
            inlier_ratio = float(inliers_count / len(matches))
            print(f"RANSAC Inlier Crater Pairs: {inliers_count} / {len(matches)} ({inlier_ratio*100:.2f}%)")

            if inliers_count >= 3:
                pts0_in = pts0[inliers]
                pts1_in = pts1[inliers]
                pts0_h = np.column_stack([pts0_in, np.ones(len(pts0_in))])
                proj = (M @ pts0_h.T).T
                residuals = np.linalg.norm(proj - pts1_in, axis=1)
                rmse = float(np.sqrt(np.mean(residuals**2)))
                print(f"Crater Centroid Alignment RMSE: {rmse:.2f} px")
                print(f"Affine Transform M:\n{M}")
    else:
        print("Fewer than 4 crater pairs matched.")

    # 5. Visual output
    out_dir = PROJECT_ROOT / "data/processed/cross_mission_technique3"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Draw detected craters on copies
    vis_tmc = cv2.cvtColor(tmc_u8, cv2.COLOR_GRAY2BGR)
    for (x, y, r) in craters_tmc:
        cv2.circle(vis_tmc, (int(x), int(y)), int(r), (0, 165, 255), 2)
        cv2.circle(vis_tmc, (int(x), int(y)), 2, (0, 0, 255), -1)

    vis_sel = cv2.cvtColor(selene_u8, cv2.COLOR_GRAY2BGR)
    for (x, y, r) in craters_sel:
        cv2.circle(vis_sel, (int(x), int(y)), int(r), (0, 255, 0), 2)
        cv2.circle(vis_sel, (int(x), int(y)), 2, (0, 0, 255), -1)

    cv2.imwrite(str(out_dir / "tmc_craters.png"), vis_tmc)
    cv2.imwrite(str(out_dir / "selene_craters.png"), vis_sel)

    print("\n=================================================================")
    print("TECHNIQUE 3 VERDICT & EMPIRICAL FINDINGS:")
    print(f"TMC-2 Craters Detected:  {len(craters_tmc)}")
    print(f"SELENE Craters Detected: {len(craters_sel)}")
    print(f"Candidate Crater Pairs:  {len(matches)}")
    print(f"RANSAC Inliers:          {inliers_count} ({inlier_ratio*100:.2f}%)")
    if rmse is not None:
        print(f"Centroid Fit RMSE:       {rmse:.2f} px")
    print("=================================================================")

if __name__ == "__main__":
    run_technique_3()
