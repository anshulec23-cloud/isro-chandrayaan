"""Feature extraction and matching: GridSampler, DeepMatcher (ORB fallback), RIFT2."""

import cv2
import numpy as np
import pytest

from lumen.features.grid_sampler import GridSampler
from lumen.features.rift2 import (
    compute_maximum_index_map,
    compute_phase_congruency,
    match_rift2,
)
from lumen.geometry.outlier_reject import estimate_transform_magsac


def _texture(size=600, seed=0):
    rng = np.random.default_rng(seed)
    img = cv2.GaussianBlur(rng.random((size, size)).astype(np.float32), (0, 0), 3)
    return (img - img.min()) / (img.max() - img.min())


@pytest.fixture(scope="module")
def shifted_pair():
    """(src, ref, t) where a source pixel p corresponds to reference pixel p + t."""
    base = _texture()
    ref = base[50:550, 50:550]
    src = base[57:557, 45:545]  # src(x, y) = base(x + 45, y + 57) = ref(x - 5, y + 7)
    return src, ref, np.array([-5.0, 7.0])


# ── GridSampler ────────────────────────────────────────────────────────────

def test_grid_sampler_uniform_selection():
    """Keeps at most top_k points per cell, choosing the highest scores."""
    sampler = GridSampler(grid_size=(2, 2))
    pts = np.array([[10, 10], [20, 20], [30, 30], [80, 80]], dtype=float)
    scores = np.array([0.1, 0.9, 0.5, 0.3])
    idx = sampler.sample_uniform(pts, (100, 100), scores, top_k=1)
    assert sorted(idx.tolist()) == [1, 3]  # best of the 3 in the top-left cell + the lone one


def test_grid_sampler_coverage_stats():
    sampler = GridSampler(grid_size=(4, 4))
    pts = np.array([[x * 25 + 5, y * 25 + 5] for x in range(4) for y in range(4)], dtype=float)
    stats = sampler.compute_coverage_stats(pts, (100, 100))
    assert stats["coverage_ratio"] == 1.0
    assert stats["empty_cells"] == 0
    assert stats["spatial_entropy"] == pytest.approx(4.0)  # log2(16) for a uniform spread


def test_grid_sampler_empty_cells():
    sampler = GridSampler(grid_size=(4, 4))
    stats = sampler.compute_coverage_stats(np.array([[5.0, 5.0]]), (100, 100))
    assert stats["filled_cells"] == 1
    assert stats["empty_cells"] == 15
    assert stats["coverage_ratio"] == pytest.approx(1 / 16)


# ── DeepMatcher (runs the ORB fallback when LightGlue is not installed) ─────

def test_deep_matcher_detect_shape(shifted_pair):
    from lumen.features.deep_matcher import DeepMatcher

    src, _, _ = shifted_pair
    out = DeepMatcher().detect(src)
    kp = out["keypoints"]
    assert kp.ndim == 2 and kp.shape[1] == 2 and len(kp) > 50
    assert (kp[:, 0] >= 0).all() and (kp[:, 0] < src.shape[1]).all()


def test_deep_matcher_match_shape(shifted_pair):
    from lumen.features.deep_matcher import DeepMatcher

    src, ref, t = shifted_pair
    m = DeepMatcher().match(src, ref)
    assert m["keypoints0"].shape == m["keypoints1"].shape
    assert m["num_matches"] == len(m["keypoints0"]) > 20
    H, mask = estimate_transform_magsac(m["keypoints0"], m["keypoints1"])
    assert mask.sum() > 20
    assert H[:2, 2] == pytest.approx(t, abs=0.5)


# ── RIFT2 ──────────────────────────────────────────────────────────────────

def test_rift2_phase_congruency_output_shape(shifted_pair):
    src, _, _ = shifted_pair
    pc, responses = compute_phase_congruency(src, nscale=4, norient=6)
    assert pc.shape == src.shape
    assert len(responses) == 6 and len(responses[0]) == 4
    # Regression: the frequency grid used to be in pixel units, which made
    # every Log-Gabor filter ~0 and this map identically zero.
    assert pc.max() > 0.1
    assert 0.0 <= pc.min() and pc.max() <= 1.0 + 1e-6


def test_rift2_phase_congruency_independent_of_input_range(shifted_pair):
    """[0, 1] floats and 0-255 values must give the same map (was a /255 bug)."""
    src, _, _ = shifted_pair
    pc_unit, _ = compute_phase_congruency(src)
    pc_255, _ = compute_phase_congruency(src * 255.0)
    np.testing.assert_allclose(pc_unit, pc_255, atol=1e-6)


def test_rift2_mim_value_range(shifted_pair):
    src, _, _ = shifted_pair
    _, responses = compute_phase_congruency(src, norient=6)
    mim = compute_maximum_index_map(responses, norient=6)
    assert mim.shape == src.shape
    assert mim.min() >= 0 and mim.max() <= 5
    assert len(np.unique(mim)) == 6  # textured image uses every orientation


def test_rift2_match_returns_coordinates(shifted_pair):
    src, ref, t = shifted_pair
    m = match_rift2(src, ref)
    assert m["num_matches"] > 100
    H, mask = estimate_transform_magsac(m["keypoints0"], m["keypoints1"])
    assert mask.mean() > 0.8
    assert H[:2, 2] == pytest.approx(t, abs=0.25)


def test_rift2_survives_contrast_inversion(shifted_pair):
    """The point of RIFT2: match across a radiometric change ORB/SIFT cannot handle."""
    src, ref, t = shifted_pair
    m = match_rift2(1.0 - src, ref)
    H, mask = estimate_transform_magsac(m["keypoints0"], m["keypoints1"])
    assert mask.sum() > 100
    assert H[:2, 2] == pytest.approx(t, abs=0.25)
