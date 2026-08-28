import numpy as np
import cv2
from scipy.ndimage import gaussian_filter

def orthorectify(image, dem, rpc_model, output_gsd, output_crs='EPSG:4326'):
    """
    DEM-based orthorectification.
    """
    # Simplified simulation for orthorectification
    ortho_image = np.copy(image)
    transform = {'crs': output_crs, 'gsd': output_gsd}
    return ortho_image, transform

def resample_to_gsd(image, current_gsd, target_gsd):
    """
    Resample image to a target GSD with anti-aliasing.
    """
    scale = current_gsd / target_gsd
    if scale == 1.0:
        return image.copy(), target_gsd
    
    if scale < 1.0:  # Downsampling
        sigma = 0.5 * np.sqrt((1.0 / scale)**2 - 1)
        if len(image.shape) == 3:
            filtered = np.zeros_like(image, dtype=np.float32)
            for i in range(image.shape[2]):
                filtered[:,:,i] = gaussian_filter(image[:,:,i], sigma)
        else:
            filtered = gaussian_filter(image, sigma)
    else:
        filtered = image
        
    new_h = int(image.shape[0] * scale)
    new_w = int(image.shape[1] * scale)
    if new_h == 0 or new_w == 0:
        new_h, new_w = 1, 1
    resampled = cv2.resize(filtered.astype(np.float32), (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    
    return resampled, target_gsd

def build_image_pyramid(image, num_levels=4, scale_factor=2.0):
    """
    Create Gaussian pyramid for multi-scale matching.
    """
    pyramid = [(image.copy(), 1.0)]
    current_image = image
    current_scale = 1.0
    
    for _ in range(1, num_levels):
        sigma = 0.5 * np.sqrt(scale_factor**2 - 1)
        if len(current_image.shape) == 3:
            filtered = np.zeros_like(current_image, dtype=np.float32)
            for i in range(current_image.shape[2]):
                filtered[:,:,i] = gaussian_filter(current_image[:,:,i], sigma)
        else:
            filtered = gaussian_filter(current_image, sigma)
            
        new_h = max(int(current_image.shape[0] / scale_factor), 1)
        new_w = max(int(current_image.shape[1] / scale_factor), 1)
        current_image = cv2.resize(filtered.astype(np.float32), (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        current_scale *= scale_factor
        pyramid.append((current_image, current_scale))
        
    return pyramid

def compute_overlap_region(image0_bounds, image1_bounds):
    """
    Compute overlap region given geographic bounds [min_x, min_y, max_x, max_y].
    """
    min_x = max(image0_bounds[0], image1_bounds[0])
    min_y = max(image0_bounds[1], image1_bounds[1])
    max_x = min(image0_bounds[2], image1_bounds[2])
    max_y = min(image0_bounds[3], image1_bounds[3])
    
    if min_x >= max_x or min_y >= max_y:
        return None, 0.0
        
    overlap_area = (max_x - min_x) * (max_y - min_y)
    area0 = (image0_bounds[2] - image0_bounds[0]) * (image0_bounds[3] - image0_bounds[1])
    
    if area0 == 0:
        return None, 0.0
        
    overlap_pct = overlap_area / area0
    
    return (min_x, min_y, max_x, max_y), overlap_pct
