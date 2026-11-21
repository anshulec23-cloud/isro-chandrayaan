"""Subpixel refinement must actually improve tie-point precision."""

import cv2
import numpy as np
import pytest

from lumen.geometry.subpixel import refine_subpixel


@pytest.fixture(scope="module")
def known_shift():
    rng = np.random.default_rng(1)
    ref = cv2.GaussianBlur(rng.random((400, 400)).astype(np.float32), (0, 0), 2.5)
    t = np.array([3.37, -1.62])  # source point = reference point + t
    src = cv2.warpAffine(ref, np.float32([[1, 0, t[0]], [0, 1, t[1]]]), (400, 400),
                         flags=cv2.INTER_CUBIC)
    pts_ref = rng.uniform(80, 320, (30, 2))
    noisy_src = pts_ref + t + rng.normal(0, 0.6, pts_ref.shape)  # matcher-like noise
    return src, ref, pts_ref, noisy_src, t


def _error(pts_src, pts_ref, t):
    return float(np.sqrt(np.mean(np.sum((pts_src - pts_ref - t) ** 2, axis=1))))


def test_refinement_reduces_error_tenfold(known_shift):
    src, ref, pts_ref, noisy_src, t = known_shift
    before = _error(noisy_src, pts_ref, t)
    refined_src, refined_ref = refine_subpixel(src, ref, noisy_src, pts_ref)
    after = _error(refined_src, refined_ref, t)
    # The previous implementation truncated coordinates to integers and came
    # out slightly *worse* than its input (0.88 → 0.90 px on this data).
    assert before > 0.5
    assert after < before / 10


def test_reference_points_unchanged(known_shift):
    src, ref, pts_ref, noisy_src, _ = known_shift
    _, refined_ref = refine_subpixel(src, ref, noisy_src, pts_ref)
    np.testing.assert_array_equal(refined_ref, pts_ref)


def test_border_and_flat_points_left_alone():
    img = np.zeros((100, 100), np.float32)
    pts = np.array([[5.0, 5.0], [50.0, 50.0]])  # near border; flat patch
    out, _ = refine_subpixel(img, img, pts, pts)
    np.testing.assert_array_equal(out, pts)


def test_empty_input():
    out0, out1 = refine_subpixel(np.zeros((10, 10)), np.zeros((10, 10)), np.empty((0, 2)), np.empty((0, 2)))
    assert out0.shape == (0, 2) and out1.shape == (0, 2)
