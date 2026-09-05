"""
RIFT2 (Radiation-variation Insensitive Feature Transform 2) implementation.
"""

import time
import logging
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import cv2
import scipy.fft
from scipy.ndimage import gaussian_filter

from lumen.features.iirs_pan import iirs_to_pan

logger = logging.getLogger(__name__)

__all__ = ['compute_phase_congruency', 'compute_maximum_index_map', 
           'detect_keypoints', 'compute_rift2_descriptor', 'match_rift2']

def compute_phase_congruency(image: np.ndarray, nscale: int = 4, norient: int = 6, 
                             min_wavelength: float = 3.0, mult: float = 2.1, 
                             sigma_onf: float = 0.55) -> Tuple[np.ndarray, List[List[np.ndarray]]]:
    """
    Compute Phase Congruency using Log-Gabor filters.

    If ``image`` is a hyperspectral cube (3-D, more than 3 channels), it is
    first collapsed to a panchromatic proxy via ``iirs_to_pan``.  This is a
    defensive guard; the primary conversion point is ``match_rift2``.
    """
    # Defensive: collapse IIRS cube if passed directly.
    if image.ndim == 3 and (image.shape[-1] > 3 or
                            (image.shape[0] > 3 and image.shape[0] <= 256)):
        image = iirs_to_pan(image)

    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
    image = image.astype(float) / 255.0
    rows, cols = image.shape
    image_fft = scipy.fft.fft2(image)
    
    # Setup grid
    x, y = np.meshgrid(np.arange(-cols/2, cols/2), np.arange(-rows/2, rows/2))
    x = scipy.fft.ifftshift(x)
    y = scipy.fft.ifftshift(y)
    
    radius = np.sqrt(x**2 + y**2)
    radius[0, 0] = 1.0 # Avoid division by zero
    theta = np.arctan2(y, x)
    
    sintheta = np.sin(theta)
    costheta = np.cos(theta)
    
    pc_map = np.zeros((rows, cols))
    energy = np.zeros((rows, cols))
    sum_an = np.zeros((rows, cols))
    
    # Pre-calculate angular filter components
    angles = np.arange(norient) * np.pi / norient
    angular_filters = []
    dtheta_sigma = np.pi / norient / np.sqrt(np.log(2)/2)
    for o in range(norient):
        angl = angles[o]
        ds = sintheta * np.cos(angl) - costheta * np.sin(angl)
        dc = costheta * np.cos(angl) + sintheta * np.sin(angl)
        dtheta = np.abs(np.arctan2(ds, dc))
        angular_filters.append(np.exp((-dtheta**2) / (2 * dtheta_sigma**2)))
        
    responses = []
    
    for o in range(norient):
        orient_responses = []
        sum_E = np.zeros((rows, cols))
        sum_O = np.zeros((rows, cols))
        sum_A = np.zeros((rows, cols))
        
        for s in range(nscale):
            wavelength = min_wavelength * (mult ** s)
            fo = 1.0 / wavelength
            
            # Radial filter
            radial_filter = np.exp((-(np.log(radius / fo))**2) / (2 * np.log(sigma_onf)**2))
            radial_filter[0, 0] = 0
            
            filter = radial_filter * angular_filters[o]
            
            # Apply filter
            filtered_fft = image_fft * filter
            filtered = scipy.fft.ifft2(filtered_fft)
            
            even = np.real(filtered)
            odd = np.imag(filtered)
            
            orient_responses.append(np.sqrt(even**2 + odd**2))
            
            sum_E += even
            sum_O += odd
            sum_A += orient_responses[-1]
            
        responses.append(orient_responses)
        
        energy_o = np.sqrt(sum_E**2 + sum_O**2)
        energy += energy_o
        sum_an += sum_A
        
    pc_map = np.maximum(energy - 0.1, 0) / (sum_an + 1e-4)
    return pc_map, responses

def compute_maximum_index_map(responses: List[List[np.ndarray]], norient: int = 6) -> np.ndarray:
    """Compute Maximum Index Map (MIM) from Log-Gabor responses."""
    # responses is [norient][nscale]
    nscale = len(responses[0])
    rows, cols = responses[0][0].shape
    
    sum_amp = np.zeros((norient, rows, cols))
    
    for o in range(norient):
        for s in range(nscale):
            sum_amp[o] += responses[o][s]
            
    mim = np.argmax(sum_amp, axis=0).astype(np.uint8)
    return mim

def detect_keypoints(pc_map: np.ndarray, num_keypoints: int = 2000, 
                     response_threshold: float = 0.1) -> np.ndarray:
    """Extract keypoints from PC map using FAST or Harris on PC map."""
    # Normalize PC map to uint8
    pc_norm = cv2.normalize(pc_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # Using Shi-Tomasi on PC map as a proxy for max moment map
    keypoints = cv2.goodFeaturesToTrack(pc_norm, maxCorners=num_keypoints, 
                                        qualityLevel=response_threshold, minDistance=5)
    
    if keypoints is not None:
        return keypoints.reshape(-1, 2)
    return np.empty((0, 2))

def compute_rift2_descriptor(mim: np.ndarray, keypoints: np.ndarray, 
                             patch_size: int = 96, num_rings: int = 6, 
                             num_sectors: int = 6, norient: int = 6) -> np.ndarray:
    """Compute RIFT2 descriptor from MIM."""
    descriptors = []
    rows, cols = mim.shape
    half_patch = patch_size // 2
    
    # Precompute ring and sector indices for a generic patch
    y, x = np.mgrid[-half_patch:half_patch, -half_patch:half_patch]
    r = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x) + np.pi # 0 to 2*pi
    
    max_r = patch_size / 2.0
    ring_idx = np.clip(np.floor(r / (max_r / num_rings)), 0, num_rings - 1).astype(int)
    
    for kp in keypoints:
        kx, ky = int(kp[0]), int(kp[1])
        
        # Check bounds
        if (ky - half_patch < 0 or ky + half_patch >= rows or
            kx - half_patch < 0 or kx + half_patch >= cols):
            descriptors.append(np.zeros(num_rings * num_sectors * norient))
            continue
            
        patch_mim = mim[ky-half_patch:ky+half_patch, kx-half_patch:kx+half_patch]
        
        # Dominant orientation (simplified: mode of MIM in patch)
        hist, _ = np.histogram(patch_mim, bins=norient, range=(0, norient))
        dom_orient = np.argmax(hist)
        
        # Rotate sector grid
        # In full RIFT2, we rotate the coordinate frame. Here we rotate the angles.
        dom_angle = dom_orient * np.pi / norient
        rot_theta = np.mod(theta - dom_angle, 2*np.pi)
        sector_idx = np.clip(np.floor(rot_theta / (2*np.pi / num_sectors)), 0, num_sectors - 1).astype(int)
        
        # Build histogram
        desc = np.zeros(num_rings * num_sectors * norient)
        
        # Vectorized histogram building could be faster, but this is explicit
        for r_i in range(num_rings):
            for s_i in range(num_sectors):
                mask = (ring_idx == r_i) & (sector_idx == s_i)
                if np.any(mask):
                    vals = patch_mim[mask]
                    h, _ = np.histogram(vals, bins=norient, range=(0, norient))
                    idx = (r_i * num_sectors + s_i) * norient
                    desc[idx:idx+norient] = h
                    
        # L2 Normalize
        norm = np.linalg.norm(desc)
        if norm > 1e-6:
            desc /= norm
            
        descriptors.append(desc)
        
    return np.array(descriptors, dtype=np.float32)

def match_rift2(image0: np.ndarray, image1: np.ndarray, 
                num_keypoints: int = 1000) -> Dict[str, Any]:
    """Full RIFT2 matching pipeline.

    If either image is an IIRS hyperspectral cube (3-D, >3 channels), it is
    converted to a panchromatic proxy via ``iirs_to_pan`` before phase
    congruency computation.  See ``lumen.features.iirs_pan`` for the band
    selection rationale and the visible-band limitation.
    """
    start_time = time.time()

    # Convert IIRS hyperspectral cubes to 2-D pan proxy.
    # Without this, compute_phase_congruency silently passes through
    # cv2.cvtColor which only sees the first 3 of 256 bands.
    if image0.ndim == 3 and (image0.shape[-1] > 3 or
                             (image0.shape[0] > 3 and image0.shape[0] <= 256)):
        image0 = iirs_to_pan(image0)
    if image1.ndim == 3 and (image1.shape[-1] > 3 or
                             (image1.shape[0] > 3 and image1.shape[0] <= 256)):
        image1 = iirs_to_pan(image1)
    
    # Compute PC and MIM
    pc0, resp0 = compute_phase_congruency(image0)
    pc1, resp1 = compute_phase_congruency(image1)
    
    mim0 = compute_maximum_index_map(resp0)
    mim1 = compute_maximum_index_map(resp1)
    
    # Detect keypoints
    kp0 = detect_keypoints(pc0, num_keypoints)
    kp1 = detect_keypoints(pc1, num_keypoints)
    
    if len(kp0) == 0 or len(kp1) == 0:
        return {'keypoints0': np.empty((0, 2)), 'keypoints1': np.empty((0, 2)), 
                'scores': np.empty((0,)), 'num_matches': 0, 'elapsed_ms': 0}
    
    # Compute descriptors
    desc0 = compute_rift2_descriptor(mim0, kp0)
    desc1 = compute_rift2_descriptor(mim1, kp1)
    
    # Match using BFMatcher
    matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
    matches = matcher.match(desc0, desc1)
    
    mkpts0 = np.float32([kp0[m.queryIdx] for m in matches])
    mkpts1 = np.float32([kp1[m.trainIdx] for m in matches])
    scores = np.float32([1.0 / (1.0 + m.distance) for m in matches])
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    return {
        'keypoints0': mkpts0,
        'keypoints1': mkpts1,
        'scores': scores,
        'num_matches': len(mkpts0),
        'elapsed_ms': elapsed_ms
    }
