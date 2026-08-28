"""Grid-based sampling for enforcing uniform spatial distribution of keypoints."""

import numpy as np

class GridSampler:
    """Enforces uniform spatial distribution of keypoints using a grid."""
    
    def __init__(self, grid_size: tuple[int, int] = (8, 8)):
        """Initialize with grid size (rows, cols)."""
        self.grid_size = grid_size
        
    def sample_uniform(self, keypoints: np.ndarray, scores: np.ndarray, image_shape: tuple[int, int]) -> np.ndarray:
        """Select top-scoring keypoints per grid cell.
        
        Args:
            keypoints: (N, 2) array of coordinates.
            scores: (N,) array of confidence scores.
            image_shape: (height, width) of the image.
            
        Returns:
            Indices of selected keypoints.
        """
        h, w = image_shape[:2]
        r_step = h / self.grid_size[0]
        c_step = w / self.grid_size[1]
        
        selected_indices = []
        for r in range(self.grid_size[0]):
            for c in range(self.grid_size[1]):
                mask = (
                    (keypoints[:, 1] >= r * r_step) & (keypoints[:, 1] < (r + 1) * r_step) &
                    (keypoints[:, 0] >= c * c_step) & (keypoints[:, 0] < (c + 1) * c_step)
                )
                valid_idx = np.where(mask)[0]
                if len(valid_idx) > 0:
                    best_idx = valid_idx[np.argmax(scores[valid_idx])]
                    selected_indices.append(best_idx)
                    
        return np.array(selected_indices)
        
    def enforce_distribution(self, matches: np.ndarray, keypoints0: np.ndarray, 
                           keypoints1: np.ndarray, image_shape: tuple[int, int]) -> np.ndarray:
        """Filter matches to ensure uniform spatial distribution.
        
        Args:
            matches: Array of match pairs.
            keypoints0: Source keypoints.
            keypoints1: Reference keypoints.
            image_shape: Shape of the reference image.
            
        Returns:
            Filtered match array.
        """
        scores = np.ones(len(matches)) # Mock scores
        kp0 = keypoints0[matches[:, 0]]
        indices = self.sample_uniform(kp0, scores, image_shape)
        return matches[indices] if len(indices) > 0 else matches
