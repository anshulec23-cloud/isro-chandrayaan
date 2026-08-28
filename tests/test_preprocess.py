import numpy as np
from lumen.preprocess.radiometric import normalize_to_float
from lumen.preprocess.photometric import lommel_seeliger_normalize

def test_normalize_to_float(sample_image):
    norm = normalize_to_float(sample_image)
    assert norm.dtype == np.float32
    assert norm.max() <= 1.0
    assert norm.min() >= 0.0

def test_lommel_seeliger():
    img = np.ones((10, 10))
    res = lommel_seeliger_normalize(img, incidence=60.0, emission=0.0)
    assert res.shape == (10, 10)
    assert np.all(res > 0)
