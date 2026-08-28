import numpy as np
from lumen.evaluation.metrics import compute_rmse

def test_compute_rmse():
    pts_ref = np.array([[0, 0], [1, 1]])
    pts_trans = np.array([[0.1, -0.1], [0.9, 1.2]])
    
    res = compute_rmse(pts_ref, pts_trans)
    assert 'rmse' in res
    assert res['rmse'] > 0
    assert 'rmse_x' in res
    assert 'rmse_y' in res
