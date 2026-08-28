"""
Grid-based Feature Sampler.
Ensures uniform spatial distribution of features/matches.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import cv2

logger = logging.getLogger(__name__)

__all__ = ['GridSampler']

class GridSampler:
    """
    Samples features evenly across a grid to ensure uniform spatial distribution.
    """
    def __init__(self, grid_size: Tuple[int, int] = (10, 10), 
                 min_per_cell: int = 1, max_per_cell: int = 5):
        """
        Initialize GridSampler.
        
        Args:
            grid_size: Number of grid cells (cols, rows).
            min_per_cell: Minimum target number of points per cell.
            max_per_cell: Maximum number of points to keep per cell.
        """
        self.grid_size = grid_size
        self.min_per_cell = min_per_cell
        self.max_per_cell = max_per_cell

    def sample_uniform(self, keypoints: np.ndarray, image_shape: Tuple[int, int], 
                       scores: Optional[np.ndarray] = None, 
                       top_k: int = 1) -> np.ndarray:
        """
        Sample points uniformly across the grid, keeping top_k per cell.
        
        Args:
            keypoints: (N, 2) array of keypoints.
            image_shape: (H, W) or (H, W, C) shape of the image.
            scores: (N,) optional array of scores to rank by.
            top_k: Number of points to keep per cell.
            
        Returns:
            Indices of the sampled keypoints.
        """
        h, w = image_shape[:2]
        cols, rows = self.grid_size
        
        cell_w = w / cols
        cell_h = h / rows
        
        if scores is None:
            scores = np.ones(len(keypoints))
            
        cell_indices = {}
        for i, (x, y) in enumerate(keypoints):
            c = int(np.clip(x // cell_w, 0, cols - 1))
            r = int(np.clip(y // cell_h, 0, rows - 1))
            
            if (r, c) not in cell_indices:
                cell_indices[(r, c)] = []
            cell_indices[(r, c)].append((i, scores[i]))
            
        selected_indices = []
        
        # First pass: take top_k from each cell
        for (r, c), pts in cell_indices.items():
            pts.sort(key=lambda x: x[1], reverse=True)
            selected_indices.extend([p[0] for p in pts[:top_k]])
            
        # Optional: fallback to neighboring cells if needed could be added here
        
        return np.array(selected_indices, dtype=int)

    def enforce_distribution(self, keypoints0: np.ndarray, keypoints1: np.ndarray,
                             image_shape: Tuple[int, int], scores: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Enforce spatial distribution on matched keypoints using image0's grid.
        
        Returns:
            mkpts0: Filtered keypoints0.
            mkpts1: Filtered keypoints1.
            mscores: Filtered scores.
            stats: Coverage statistics.
        """
        indices = self.sample_uniform(keypoints0, image_shape, scores, top_k=self.max_per_cell)
        
        if len(indices) == 0:
            return np.empty((0, 2)), np.empty((0, 2)), np.empty((0,)), {}
            
        mkpts0 = keypoints0[indices]
        mkpts1 = keypoints1[indices]
        
        mscores = scores[indices] if scores is not None else np.ones(len(indices))
        
        stats = self.compute_coverage_stats(mkpts0, image_shape)
        return mkpts0, mkpts1, mscores, stats

    def compute_coverage_stats(self, keypoints: np.ndarray, image_shape: Tuple[int, int]) -> Dict[str, Any]:
        """
        Compute grid coverage statistics.
        
        Args:
            keypoints: (N, 2) array of keypoints.
            image_shape: Image shape.
            
        Returns:
            Dictionary with coverage_ratio, empty_cells, cell_histogram, spatial_entropy.
        """
        h, w = image_shape[:2]
        cols, rows = self.grid_size
        
        cell_w = w / cols
        cell_h = h / rows
        
        hist = np.zeros((rows, cols), dtype=int)
        
        for x, y in keypoints:
            c = int(np.clip(x // cell_w, 0, cols - 1))
            r = int(np.clip(y // cell_h, 0, rows - 1))
            hist[r, c] += 1
            
        total_cells = rows * cols
        filled_cells = np.sum(hist > 0)
        empty_cells = total_cells - filled_cells
        coverage_ratio = filled_cells / total_cells if total_cells > 0 else 0
        
        # Spatial entropy
        probs = hist.flatten() / max(len(keypoints), 1)
        probs = probs[probs > 0]
        spatial_entropy = -np.sum(probs * np.log2(probs)) if len(probs) > 0 else 0.0
        
        return {
            'coverage_ratio': coverage_ratio,
            'empty_cells': int(empty_cells),
            'filled_cells': int(filled_cells),
            'cell_histogram': hist.tolist(),
            'spatial_entropy': float(spatial_entropy)
        }
        
    def visualize_grid(self, image: np.ndarray, keypoints: np.ndarray) -> np.ndarray:
        """
        Draw grid overlay on image with colored dots for matches.
        
        Args:
            image: Background image.
            keypoints: Keypoints to draw.
            
        Returns:
            Visualization image.
        """
        vis = image.copy()
        if len(vis.shape) == 2:
            vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)
            
        h, w = vis.shape[:2]
        cols, rows = self.grid_size
        
        cell_w = int(w / cols)
        cell_h = int(h / rows)
        
        # Draw grid lines
        for r in range(1, rows):
            y = r * cell_h
            cv2.line(vis, (0, y), (w, y), (255, 255, 255), 1, cv2.LINE_AA)
        for c in range(1, cols):
            x = c * cell_w
            cv2.line(vis, (x, 0), (x, h), (255, 255, 255), 1, cv2.LINE_AA)
            
        # Draw keypoints
        for x, y in keypoints:
            cv2.circle(vis, (int(x), int(y)), 3, (0, 255, 0), -1, cv2.LINE_AA)
            
        return vis
