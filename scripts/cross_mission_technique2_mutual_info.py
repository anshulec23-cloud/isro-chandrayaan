"""
Technique 2: Mutual Information (MI) Maximization Registration
for Chandrayaan-2 TMC-2 Nadir vs JAXA SELENE TC.

Searches over rigid/similarity parameters:
- Translation (dx, dy)
- Rotation (theta)
- Scale (s)
Maximizing Normalized Mutual Information (NMI).
"""

import sys
from pathlib import Path
import numpy as np
import cv2
import rasterio
from rasterio.windows import from_bounds
from scipy.optimize import minimize
from scipy.ndimage import rotate

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lumen.ingest.selene_adapter import load_selene_image
from lumen.preprocess.radiometric import apply_clahe, normalize_to_float
from skimage.metrics import structural_similarity as ssim

def compute_mutual_information(img1: np.ndarray, img2: np.ndarray, bins: int = 64) -> tuple[float, float]:
    """
    Compute Shannon Mutual Information (MI) and Normalized Mutual Information (NMI).
    Only evaluated over overlapping non-zero pixels.
    """
    # Valid overlap mask
    mask = (img1 > 0) & (img2 > 0)
    n_pts = np.sum(mask)
    if n_pts < 1000:
        return 0.0, 1.0

    v1 = img1[mask]
    v2 = img2[mask]

    # 2D Joint Histogram
    joint_hist, _, _ = np.histogram2d(v1, v2, bins=bins, range=[[0, 255], [0, 255]])
    p_joint = joint_hist / np.sum(joint_hist)

    # Marginals
    p1 = np.sum(p_joint, axis=1)
    p2 = np.sum(p_joint, axis=0)

    # Entropies
    eps = 1e-12
    h1 = -np.sum(p1[p1 > 0] * np.log2(p1[p1 > 0] + eps))
    h2 = -np.sum(p2[p2 > 0] * np.log2(p2[p2 > 0] + eps))
    h_joint = -np.sum(p_joint[p_joint > 0] * np.log2(p_joint[p_joint > 0] + eps))

    mi = h1 + h2 - h_joint
    nmi = (h1 + h2) / (h_joint + eps)

    return float(mi), float(nmi)

def transform_image(img: np.ndarray, dx: float, dy: float, theta_deg: float, scale: float, out_shape: tuple[int, int]) -> np.ndarray:
    """Apply similarity transformation: scale, rotation, translation."""
    h, w = img.shape
    center = (w / 2.0, h / 2.0)
    M = cv2.getRotationMatrix2D(center, theta_deg, scale)
    M[0, 2] += dx
    M[1, 2] += dy
    warped = cv2.warpAffine(img, M, (out_shape[1], out_shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return warped

def run_technique_2():
    print("=================================================================")
    print("TECHNIQUE 2: MUTUAL INFORMATION (MI) REGISTRATION")
    print("=================================================================")

    overlap_bbox = (141.0, -9.0, 142.707, -6.0)

    # Load TMC-2
    tmc_tif = PROJECT_ROOT / "data/processed/real_ortho_outputs/tmc_ncn_ortho.tif"
    with rasterio.open(tmc_tif) as src:
        win = from_bounds(*overlap_bbox, transform=src.transform)
        tmc_crop = src.read(1, window=win)

    # Load SELENE
    selene_lbl = PROJECT_ROOT / "data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.lbl"
    selene_crop, _ = load_selene_image(selene_lbl, bbox_crop=overlap_bbox)

    # Downsample to 1024 x 582 for fast numerical optimization
    target_h = 1024
    target_w = int(target_h * (selene_crop.shape[1] / selene_crop.shape[0]))
    print(f"Working optimization resolution: {target_h} x {target_w}")

    tmc_res = cv2.resize(tmc_crop.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)
    sel_res = cv2.resize(selene_crop.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA)

    p1, p99 = np.percentile(tmc_res[tmc_res > 0], (1, 99))
    tmc_u8 = np.clip((tmc_res - p1) / (p99 - p1) * 255.0, 0, 255).astype(np.uint8)

    p1_s, p99_s = np.percentile(sel_res[sel_res > 0], (1, 99))
    sel_u8 = np.clip((sel_res - p1_s) / (p99_s - p1_s) * 255.0, 0, 255).astype(np.uint8)

    # 1. Baseline MI before registration
    initial_mi, initial_nmi = compute_mutual_information(tmc_u8, sel_u8)
    initial_ssim = ssim(tmc_u8, sel_u8)
    print(f"\nInitial Alignment Metrics (Identity Transform):")
    print(f"  Mutual Information (MI): {initial_mi:.4f} bits")
    print(f"  Normalized MI (NMI):     {initial_nmi:.4f}")
    print(f"  Baseline SSIM:           {initial_ssim:.4f}")

    # 2. Multi-resolution Grid Search for Translation (dx, dy)
    print("\nExecuting Coarse Grid Search for (dx, dy)...")
    best_nmi = initial_nmi
    best_params = (0.0, 0.0, 0.0, 1.0) # dx, dy, theta, scale

    dx_grid = np.linspace(-30, 30, 13)
    dy_grid = np.linspace(-30, 30, 13)

    for dx in dx_grid:
        for dy in dy_grid:
            w_img = transform_image(tmc_u8, dx, dy, 0.0, 1.0, sel_u8.shape)
            _, nmi_val = compute_mutual_information(w_img, sel_u8)
            if nmi_val > best_nmi:
                best_nmi = nmi_val
                best_params = (dx, dy, 0.0, 1.0)

    print(f"Coarse Grid Best NMI: {best_nmi:.4f} at dx={best_params[0]:.1f}, dy={best_params[1]:.1f}")

    # 3. Fine Continuous Optimization (Powell Method)
    print("\nExecuting Continuous Nelder-Mead Optimization on (dx, dy, theta, scale)...")
    def cost_func(params):
        dx, dy, theta, scale = params
        w_img = transform_image(tmc_u8, dx, dy, theta, scale, sel_u8.shape)
        _, nmi_val = compute_mutual_information(w_img, sel_u8)
        # We minimize negative NMI
        return -nmi_val

    x0 = [best_params[0], best_params[1], 0.0, 1.0]
    res_opt = minimize(
        cost_func,
        x0=x0,
        method="Powell",
        options={"maxiter": 50, "ftol": 1e-4, "disp": False}
    )

    opt_dx, opt_dy, opt_theta, opt_scale = res_opt.x
    opt_nmi = -res_opt.fun
    opt_warped = transform_image(tmc_u8, opt_dx, opt_dy, opt_theta, opt_scale, sel_u8.shape)
    opt_mi, _ = compute_mutual_information(opt_warped, sel_u8)
    opt_ssim = ssim(opt_warped, sel_u8)

    print("\n=================================================================")
    print("TECHNIQUE 2 VERDICT & EMPIRICAL FINDINGS:")
    print(f"Optimal Parameters Found:")
    print(f"  Translation dx:    {opt_dx:+.2f} px (scaled ~ {opt_dx*2:+.2f} px at 2048 res)")
    print(f"  Translation dy:    {opt_dy:+.2f} px (scaled ~ {opt_dy*2:+.2f} px at 2048 res)")
    print(f"  Rotation theta:    {opt_theta:+.3f} degrees")
    print(f"  Scale factor s:    {opt_scale:.4f}")
    print(f"Metric Comparison:")
    print(f"  Mutual Information: {initial_mi:.4f} -> {opt_mi:.4f} bits ({((opt_mi - initial_mi)/initial_mi)*100:+.2f}%)")
    print(f"  Normalized MI:      {initial_nmi:.4f} -> {opt_nmi:.4f}")
    print(f"  SSIM Correlation:   {initial_ssim:.4f} -> {opt_ssim:.4f}")
    print("=================================================================")

    # Save output artifacts
    out_dir = PROJECT_ROOT / "data/processed/cross_mission_technique2"
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "tmc_mi_warped.png"), opt_warped)
    cv2.imwrite(str(out_dir / "selene_target.png"), sel_u8)
    print(f"Saved warped images to {out_dir}")

if __name__ == "__main__":
    run_technique_2()
