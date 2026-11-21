import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lumen.preprocess.orthorectify import resample_to_gsd, build_image_pyramid, orthorectify

from lumen.preprocess.radiometric import apply_clahe, histogram_match, normalize_to_float
from lumen.preprocess.photometric import (
    compute_local_angles,
    lommel_seeliger_normalize,
    minnaert_normalize,
    photometric_normalize,
)


def _full(shape, value):
    return np.full(shape, float(value))


def test_clahe_output_range(sample_image):
    out = apply_clahe(sample_image)
    assert out.shape == sample_image.shape
    assert out.dtype == np.uint16  # float input is rescaled to the 16-bit range
    assert out.min() >= 0 and out.max() <= 65535


def test_clahe_enhances_contrast():
    rng = np.random.default_rng(0)
    low_contrast = (0.45 + 0.1 * rng.random((256, 256))).astype(np.float32)
    out = apply_clahe((low_contrast * 255).astype(np.uint8))
    assert out.std() > (low_contrast * 255).std()


def test_histogram_match_distributions(sample_image):
    target = sample_image ** 2
    matched = histogram_match(sample_image, target)
    assert abs(matched.mean() - target.mean()) < 0.01
    assert abs(matched.std() - target.std()) < 0.01


def test_normalize_to_float_range():
    img = np.arange(100, dtype=np.uint16).reshape(10, 10) * 300
    out = normalize_to_float(img)
    assert out.dtype == np.float32
    assert out.min() == 0.0 and out.max() == 1.0


def test_normalize_to_float_constant_image():
    out = normalize_to_float(np.full((10, 10), 7, dtype=np.uint16))
    assert out.dtype == np.float32 and not out.any()


def test_lommel_seeliger_reference_geometry(sample_image):
    """At the target geometry (inc = alpha, emi = 0, phase = alpha) nothing changes."""
    shape = sample_image.shape
    out = lommel_seeliger_normalize(
        sample_image, _full(shape, 30), _full(shape, 0), _full(shape, 30), alpha=30.0
    )
    np.testing.assert_allclose(out, sample_image, rtol=1e-6)


def test_lommel_seeliger_brightens_oblique_illumination(sample_image):
    shape = sample_image.shape
    out = lommel_seeliger_normalize(
        sample_image, _full(shape, 70), _full(shape, 0), _full(shape, 30), alpha=30.0
    )
    assert out.mean() > sample_image.mean()  # low sun → darker image → boosted


def test_lommel_seeliger_shadow_handling(sample_image):
    shape = sample_image.shape
    mask = np.zeros(shape, bool)
    mask[:10] = True
    out = lommel_seeliger_normalize(
        sample_image, _full(shape, 30), _full(shape, 0), _full(shape, 30), shadow_mask=mask
    )
    assert not out[:10].any()
    assert out[10:].any()


def test_minnaert_normalization(sample_image):
    shape = sample_image.shape
    # k = 1 reduces Minnaert to Lambert: R / cos(i).  cos(60°) = 0.5 → ×2.
    out = minnaert_normalize(sample_image, _full(shape, 60), _full(shape, 0), _full(shape, 60), k=1.0)
    np.testing.assert_allclose(out, sample_image * 2.0, rtol=1e-6)


def test_compute_local_angles_flat_dem():
    inc, emi = compute_local_angles(
        np.zeros((32, 32)), resolution=5.0, az_sun=90.0, el_sun=40.0, az_view=0.0, el_view=90.0
    )
    np.testing.assert_allclose(inc, 50.0, atol=1e-6)  # flat ground: inc = 90° - sun elevation
    np.testing.assert_allclose(emi, 0.0, atol=1e-6)


def test_compute_local_angles_sun_facing_slope():
    x = np.arange(64, dtype=float)
    dem = np.tile(-x * 5.0, (64, 1))  # surface dips toward +x (east), 45° slope at 5 m/px
    inc, _ = compute_local_angles(dem, 5.0, az_sun=90.0, el_sun=45.0, az_view=0.0, el_view=90.0)
    assert np.median(inc) == pytest.approx(0.0, abs=1e-6)  # slope faces the sun head-on


def test_photometric_normalize_dispatch(sample_image):
    shape = sample_image.shape
    emi, phase = _full(shape, 0), _full(shape, 30)
    _, _, meta_hi = photometric_normalize(sample_image, _full(shape, 75), emi, phase)
    _, _, meta_lo = photometric_normalize(sample_image, _full(shape, 20), emi, phase)
    assert meta_hi["method_used"] == "lommel_seeliger"
    assert meta_lo["method_used"] == "minnaert"
    with pytest.raises(ValueError):
        photometric_normalize(sample_image, _full(shape, 20), emi, phase, method="hapke")


def test_resample_to_gsd_identity(sample_image):
    resampled, gsd = resample_to_gsd(sample_image, 1.0, 1.0)
    assert np.allclose(sample_image, resampled)
    assert gsd == 1.0

def test_resample_to_gsd_downsample(sample_image):
    resampled, gsd = resample_to_gsd(sample_image, 1.0, 2.0)
    assert resampled.shape[0] == sample_image.shape[0] // 2
    assert gsd == 2.0

def test_resample_to_gsd_upsample(sample_image):
    resampled, gsd = resample_to_gsd(sample_image, 2.0, 1.0)
    assert resampled.shape[0] == sample_image.shape[0] * 2
    assert gsd == 1.0

def test_build_image_pyramid_levels(sample_image):
    pyramid = build_image_pyramid(sample_image, num_levels=3, scale_factor=2.0)
    assert len(pyramid) == 3
    assert pyramid[0][1] == 1.0
    assert pyramid[1][1] == 2.0
    assert pyramid[2][1] == 4.0
    assert pyramid[1][0].shape[0] == sample_image.shape[0] // 2
