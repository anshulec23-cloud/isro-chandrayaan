import numpy as np
from lumen.features.grid_sampler import GridSampler

def test_grid_sampler():
    sampler = GridSampler(grid_size=(2, 2))
    keypoints = np.array([
        [10, 10], [15, 15],  # Cell 0,0
        [40, 10],            # Cell 0,1
        [10, 40],            # Cell 1,0
        [40, 40]             # Cell 1,1
    ])
    scores = np.array([0.5, 0.9, 0.8, 0.7, 0.6])
    
    indices = sampler.sample_uniform(keypoints, scores, (50, 50))
    assert len(indices) == 4
    # The higher score in cell 0,0 should be chosen
    assert 1 in indices
    assert 0 not in indices
