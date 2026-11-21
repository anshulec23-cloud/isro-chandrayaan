"""Regenerate the dashboard's Stage 4 match images from a real pipeline run.

Runs the same configuration as the headline benchmark (TMC-2 aft → nadir,
native 5.2 m/px window, SIFT) and writes, into dashboard/public/previews/:

* stage4_matches_candidates.png / stage4_matches_inliers.png – whole window
* stage4_detail_candidates.png  / stage4_detail_inliers.png  – zoomed strip

and prints the candidate / inlier counts shown next to them on the page.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark import PAIRS  # noqa: E402
from lumen.pipeline.orchestrator import RegistrationPipeline  # noqa: E402

OUT = ROOT / "dashboard" / "public" / "previews"
AMBER, GREEN, RED = (61, 163, 232), (80, 230, 80), (40, 60, 230)


def to_bgr(img: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(img[img != 0], (1, 99))
    u8 = (np.clip((img - lo) / max(hi - lo, 1e-9), 0, 1) * 255).astype(np.uint8)
    return cv2.cvtColor(u8, cv2.COLOR_GRAY2BGR)


def draw(src, ref, p0, p1, inlier=None, gap=40, scale=1.0):
    """Source left, reference right, one line per correspondence."""
    s, r = to_bgr(src), to_bgr(ref)
    if scale != 1.0:
        s = cv2.resize(s, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        r = cv2.resize(r, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    h = max(s.shape[0], r.shape[0])
    canvas = np.zeros((h, s.shape[1] + gap + r.shape[1], 3), np.uint8)
    canvas[:s.shape[0], :s.shape[1]] = s
    canvas[:r.shape[0], s.shape[1] + gap:] = r
    off = s.shape[1] + gap
    order = range(len(p0)) if inlier is None else np.argsort(inlier)  # inliers drawn last
    for i in order:
        a = tuple(int(v) for v in p0[i] * scale)
        b = (int(p1[i][0] * scale) + off, int(p1[i][1] * scale))
        color = AMBER if inlier is None else (GREEN if inlier[i] else RED)
        cv2.line(canvas, a, b, color, 1, cv2.LINE_AA)
        cv2.circle(canvas, a, 3, color, -1, cv2.LINE_AA)
        cv2.circle(canvas, b, 3, color, -1, cv2.LINE_AA)
    return canvas


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    pair = PAIRS["tmc_aft_vs_nadir"]
    result = RegistrationPipeline(config={}).run(
        ROOT / pair["source"], ROOT / pair["reference"], pair["source_sensor"], pair["ref_sensor"],
        options={"feature_method": "sift", **pair["modes"]["native_window"]},
    )
    mp = result.match_points
    p0 = np.float32([[m["src_x"], m["src_y"]] for m in mp])
    p1 = np.float32([[m["dst_x"], m["dst_y"]] for m in mp])
    inl = np.array([m["inlier"] for m in mp])
    src, ref = result.source_image, result.reference_image

    # Whole window, scaled to a dashboard-friendly size.
    k = 900 / max(src.shape)
    cv2.imwrite(str(OUT / "stage4_matches_candidates.png"), draw(src, ref, p0, p1, scale=k))
    cv2.imwrite(str(OUT / "stage4_matches_inliers.png"), draw(src, ref, p0, p1, inl, scale=k))

    # Detail: a horizontal band through the middle at full resolution.
    h = src.shape[0]
    y0, y1 = int(h * 0.40), int(h * 0.40) + 500
    x0, x1 = int(src.shape[1] * 0.30), int(src.shape[1] * 0.30) + 500
    # The reference window follows the median source→reference offset so the
    # same ground appears in both halves.
    dx, dy = np.median(p1[inl] - p0[inl], axis=0).round().astype(int)
    rx0, ry0 = x0 + dx, y0 + dy
    keep = ((p0[:, 1] >= y0) & (p0[:, 1] < y1) & (p0[:, 0] >= x0) & (p0[:, 0] < x1)
            & (p1[:, 1] >= ry0) & (p1[:, 1] < ry0 + 500) & (p1[:, 0] >= rx0) & (p1[:, 0] < rx0 + 500))
    sc, rc = src[y0:y1, x0:x1], ref[ry0:ry0 + 500, rx0:rx0 + 500]
    q0, q1 = p0[keep] - np.float32([x0, y0]), p1[keep] - np.float32([rx0, ry0])
    cv2.imwrite(str(OUT / "stage4_detail_candidates.png"), draw(sc, rc, q0, q1))
    cv2.imwrite(str(OUT / "stage4_detail_inliers.png"), draw(sc, rc, q0, q1, inl[keep]))

    print(f"candidates={len(mp)} inliers={int(inl.sum())} ratio={inl.mean():.3f} "
          f"detail_points={int(keep.sum())}")


if __name__ == "__main__":
    main()
