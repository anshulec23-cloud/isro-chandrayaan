"""Evaluation metrics."""

import numpy as np
import pytest

from lumen.evaluation.metrics import (
    compute_inlier_ratio,
    compute_reprojection_error,
    compute_rmse,
    compute_ssim,
    create_checkerboard,
    create_false_color_overlay,
)


def test_rmse_zero_error():
    pts = np.random.default_rng(0).uniform(0, 100, (20, 2))
    assert compute_rmse(pts, pts.copy()) == {"rmse": 0.0, "rmse_x": 0.0, "rmse_y": 0.0}


def test_rmse_known_error():
    ref = np.zeros((10, 2))
    moved = ref + np.array([3.0, 4.0])
    assert compute_rmse(ref, moved)["rmse"] == pytest.approx(5.0)


def test_rmse_directional():
    ref = np.zeros((10, 2))
    moved = ref + np.array([2.0, 0.0])
    r = compute_rmse(ref, moved)
    assert r["rmse_x"] == pytest.approx(2.0)
    assert r["rmse_y"] == pytest.approx(0.0)


def test_inlier_ratio_all_inliers(matched_points):
    pts1, _ = matched_points
    assert compute_inlier_ratio(len(pts1), len(pts1)) == 1.0
    assert compute_inlier_ratio(5, 4) == pytest.approx(0.8)


def test_inlier_ratio_no_matches():
    assert compute_inlier_ratio(0, 0) == 0.0


def test_ssim_identical_images(sample_image):
    assert compute_ssim(sample_image, sample_image.copy()) == pytest.approx(1.0)


def test_ssim_different_images(sample_image_pair):
    img0, img1, _ = sample_image_pair
    assert compute_ssim(img0, img1) < 0.5


def test_reprojection_error_identity():
    pts = np.random.default_rng(1).uniform(0, 100, (10, 2))
    assert compute_reprojection_error(pts, pts, np.eye(3)) == pytest.approx(0.0)


def test_reprojection_error_known_transform():
    pts = np.random.default_rng(2).uniform(0, 100, (10, 2))
    H = np.array([[1, 0, 3.0], [0, 1, 4.0], [0, 0, 1]])
    assert compute_reprojection_error(pts, pts + [3.0, 4.0], H) == pytest.approx(0.0, abs=1e-9)
    assert compute_reprojection_error(pts, pts, H) == pytest.approx(5.0)


def test_checkerboard_shape(sample_image_pair):
    img0, img1, _ = sample_image_pair
    assert create_checkerboard(img0, img1).shape == img0.shape


def test_checkerboard_alternation():
    a = np.ones((8, 8))
    b = np.zeros((8, 8))
    cb = create_checkerboard(a, b, grid_size=(2, 2))
    assert cb[0, 0] == 0 and cb[0, 7] == 1 and cb[7, 0] == 1 and cb[7, 7] == 0


def test_false_color_overlay_channels(sample_image):
    ov = create_false_color_overlay(sample_image, np.zeros_like(sample_image) + 0.5)
    assert ov.shape == (*sample_image.shape, 3) and ov.dtype == np.uint8
    assert ov[..., 0].max() == 0          # blue unused
    assert ov[..., 2].std() > 0           # red carries the warped image
    with pytest.raises(ValueError):
        create_false_color_overlay(sample_image, sample_image[:10])
