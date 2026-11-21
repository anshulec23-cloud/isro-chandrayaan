"""Reproducible accuracy benchmark on real Chandrayaan-2 data.

Runs the full LUMEN pipeline on an overlapping product pair and writes:

* ``docs/results/benchmark.json``  – every number quoted in the README
* ``docs/images/*.png``            – checkerboard and false-colour overlays

Accuracy is reported two ways:

* **fit residual** – RMSE of the inliers that produced the homography.
  Optimistic by construction (the model was fitted to these points).
* **held-out RMSE** – 5-fold cross-validation: the homography is re-fitted on
  80 % of the inlier tie-points and evaluated on the 20 % it never saw.  This is
  the number to quote as accuracy.

Usage (from the repository root)::

    python scripts/benchmark.py                      # TMC-2 aft vs nadir, all matchers
    python scripts/benchmark.py --methods sift       # one matcher

The PDS4 products must be in ``data/raw/`` (PRADAN requires an ISRO login, so
they are not in the repository; product IDs are listed in the README).
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lumen.evaluation.metrics import create_checkerboard, create_false_color_overlay  # noqa: E402
from lumen.pipeline.orchestrator import RegistrationPipeline  # noqa: E402

PAIRS = {
    "tmc_aft_vs_nadir": {
        "source": "data/raw/ch2_tmc_nca_20260813T0627378526_d_img_d18/data/calibrated/20260813/"
                  "ch2_tmc_nca_20260813T0627378526_d_img_d18.xml",
        "reference": "data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/"
                     "ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml",
        "source_sensor": "TMC2",
        "ref_sensor": "TMC2",
        # Two ways of running the same pair:
        #  * full_overlap  – the whole 22°-long shared strip resampled to
        #                    2048 px (~330 m/px), as the dashboard demo did.
        #  * native_window – a ~12 x 12 km window read at native 5.48 m/px;
        #                    this is the run that reflects TMC-2 accuracy.
        "modes": {
            "full_overlap": {},
            "native_window": {"roi_lonlat": (141.60, -17.20, 142.02, -16.80), "max_ortho_dim": 4096},
        },
    },
    # Cross-mission: Chandrayaan-2 TMC-2 nadir vs JAXA SELENE (Kaguya) Terrain
    # Camera ortho-mosaic.  SELENE data is public (JAXA DARTS); see README.
    "tmc_vs_selene_tc": {
        "source": "data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/"
                  "ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml",
        "reference": "data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.lbl",
        "source_sensor": "TMC2",
        "ref_sensor": "SELENE_TC",
        "modes": {
            "full_overlap": {},
            "native_window": {"roi_lonlat": (141.80, -7.70, 142.20, -7.30), "max_ortho_dim": 4096},
        },
    },
}


def cpu_name() -> str:
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    return platform.processor() or platform.machine()


def device_name() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return f"GPU: {torch.cuda.get_device_name(0)}"
    except ImportError:
        pass
    return f"CPU: {cpu_name()}"


def held_out_rmse(src: np.ndarray, ref: np.ndarray, folds: int = 5, seed: int = 0) -> dict:
    """K-fold cross-validated reprojection RMSE of a homography fit."""
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(src))
    errors = []
    for k in range(folds):
        test = order[k::folds]
        train = np.setdiff1d(order, test)
        H, _ = cv2.findHomography(src[train], ref[train], 0)  # least squares on clean inliers
        proj = cv2.perspectiveTransform(src[test].reshape(-1, 1, 2), H).reshape(-1, 2)
        errors.append(proj - ref[test])
    err = np.concatenate(errors)
    return {
        "rmse": float(np.sqrt(np.mean(np.sum(err ** 2, axis=1)))),
        "rmse_x": float(np.sqrt(np.mean(err[:, 0] ** 2))),
        "rmse_y": float(np.sqrt(np.mean(err[:, 1] ** 2))),
        "points": int(len(err)),
        "folds": folds,
    }


def to_u8(img: np.ndarray) -> np.ndarray:
    valid = img[img != 0]
    lo, hi = np.percentile(valid, (1, 99)) if valid.size else (0, 1)
    return (np.clip((img - lo) / max(hi - lo, 1e-9), 0, 1) * 255).astype(np.uint8)


def crop_detail(img: np.ndarray, size: int = 512) -> np.ndarray:
    """Centre crop at full analysis resolution, where misregistration is visible."""
    h, w = img.shape[:2]
    y0, x0 = max(0, h // 2 - size // 2), max(0, w // 2 - size // 2)
    return img[y0:y0 + size, x0:x0 + size]


def run(pair_name: str, method: str, mode: str, images_dir: Path) -> dict:
    pair = PAIRS[pair_name]
    pipeline = RegistrationPipeline(config={})
    t0 = time.perf_counter()
    result = pipeline.run(
        source_path=ROOT / pair["source"],
        reference_path=ROOT / pair["reference"],
        source_sensor=pair["source_sensor"],
        ref_sensor=pair["ref_sensor"],
        options={"feature_method": method, **pair["modes"][mode]},
    )
    runtime = time.perf_counter() - t0
    m = result.metrics
    gsd = float(result.metadata["target_gsd_m"])

    inl = [p for p in result.match_points if p["inlier"]]
    src = np.float32([[p["src_x"], p["src_y"]] for p in inl])
    ref = np.float32([[p["dst_x"], p["dst_y"]] for p in inl])
    cv = held_out_rmse(src, ref)

    # Pixel scale of the analysis grid actually used for matching (the overlap
    # crop is resampled to <= 2048 px, so it can be coarser than native GSD).
    bbox = result.metadata["overlap_bbox"]
    m_per_deg = 2 * np.pi * 1_737_400 / 360
    lat_span_m = abs(bbox[3] - bbox[1]) * m_per_deg
    analysis_m_per_px = lat_span_m / result.reference_image.shape[0]

    tag = f"{pair_name}_{mode}_{method}"
    warped, refimg = result.warped_image, result.reference_image
    w_crop, r_crop = crop_detail(to_u8(warped)), crop_detail(to_u8(refimg))
    cb = create_checkerboard(w_crop, r_crop, grid_size=(4, 4))  # tiles sized to the crop
    cb[w_crop == 0] = 0
    cv2.imwrite(str(images_dir / f"{tag}_checkerboard.png"), cb)
    cv2.imwrite(str(images_dir / f"{tag}_falsecolor.png"),
                crop_detail(create_false_color_overlay(warped, refimg)))

    return {
        "pair": pair_name,
        "mode": mode,
        "method": method,
        "matcher_mode": _matcher_mode(method),
        "source": Path(pair["source"]).stem,
        "reference": Path(pair["reference"]).stem,
        "candidates": m["total_matches"],
        "inliers": m["inlier_count"],
        "inlier_ratio": round(m["inlier_ratio"], 4),
        "fit_rmse_px": round(m["rmse"], 3),
        "heldout_rmse_px": round(cv["rmse"], 3),
        "heldout_rmse_x_px": round(cv["rmse_x"], 3),
        "heldout_rmse_y_px": round(cv["rmse_y"], 3),
        "heldout_points": cv["points"],
        "analysis_m_per_px": round(analysis_m_per_px, 2),
        "heldout_rmse_m": round(cv["rmse"] * analysis_m_per_px, 1),
        "native_gsd_m": round(gsd, 2),
        "ssim": round(m["ssim"], 4),
        "analysis_grid_px": list(refimg.shape),
        "overlap_bbox_lonlat": [round(v, 4) for v in bbox],
        "runtime_s": round(runtime, 1),
    }


def _matcher_mode(method: str) -> str:
    if method != "deep":
        return method
    from lumen.features.deep_matcher import DeepMatcher

    return "superpoint+lightglue" if DeepMatcher().mode == "lightglue" else "orb (lightglue not installed)"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pairs", nargs="+", default=list(PAIRS), choices=list(PAIRS))
    ap.add_argument("--methods", nargs="+", default=["deep", "sift", "rift2"])
    ap.add_argument("--modes", nargs="+", default=["full_overlap", "native_window"])
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)

    images_dir = ROOT / "docs" / "images"
    results_dir = ROOT / "docs" / "results"
    images_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    for pair in args.pairs:
        for mode in args.modes:
            if mode not in PAIRS[pair]["modes"]:
                continue
            for method in args.methods:
                print(f"[{pair} / {mode}] {method} ...", flush=True)
                try:
                    r = run(pair, method, mode, images_dir)
                except Exception as exc:  # report failures instead of hiding them
                    r = {"pair": pair, "mode": mode, "method": method, "error": str(exc)}
                print(json.dumps(r), flush=True)
                runs.append(r)

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "device": device_name(),
        "python": platform.python_version(),
        "opencv": cv2.__version__,
        "runs": runs,
    }
    (results_dir / "benchmark.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {results_dir / 'benchmark.json'}")


if __name__ == "__main__":
    main()
