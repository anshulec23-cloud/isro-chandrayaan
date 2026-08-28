"""
Deep Learning-based Feature Matcher using SuperPoint and LightGlue.
"""

import time
import logging
import warnings
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import cv2

import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)

__all__ = ['DeepMatcher']

# Attempt to load lightglue
try:
    from lightglue import SuperPoint, LightGlue
    from lightglue.utils import numpy_image_to_torch, rbd
    HAS_LIGHTGLUE = True
    HAS_KORNIA_LG = False
except ImportError:
    HAS_LIGHTGLUE = False
    try:
        from kornia.feature import SuperPoint, LightGlue, match_smnn
        HAS_KORNIA_LG = True
    except ImportError:
        HAS_KORNIA_LG = False

class DeepMatcher:
    """
    Feature matcher using SuperPoint + LightGlue, with fallback to ORB + BFMatcher.
    """
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
                 max_keypoints: int = 2048, resize_max: int = 1024):
        self.device = torch.device(device)
        self.max_keypoints = max_keypoints
        self.resize_max = resize_max
        self.mode = 'orb'
        
        if HAS_LIGHTGLUE:
            logger.info("Initializing standalone LightGlue.")
            self.extractor = SuperPoint(max_num_keypoints=max_keypoints).eval().to(self.device)
            self.matcher = LightGlue(features='superpoint').eval().to(self.device)
            self.mode = 'lightglue'
        elif HAS_KORNIA_LG:
            logger.info("Initializing Kornia LightGlue.")
            self.extractor = SuperPoint(max_num_keypoints=max_keypoints).eval().to(self.device)
            # Kornia's LightGlue might need different instantiation based on version
            self.matcher = LightGlue(features='superpoint').eval().to(self.device)
            self.mode = 'kornia'
        else:
            logger.warning("LightGlue not found. Falling back to ORB + BFMatcher.")
            self.extractor = cv2.ORB_create(nfeatures=max_keypoints)
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            self.mode = 'orb'

    def _preprocess_image(self, image: np.ndarray) -> Tuple[torch.Tensor, Tuple[int, int]]:
        """Convert numpy image to torch tensor, normalize, resize if needed."""
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        h, w = image.shape
        orig_shape = (w, h)
        
        if max(h, w) > self.resize_max:
            scale = self.resize_max / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        if self.mode in ('lightglue', 'kornia'):
            # Convert to float and [0, 1]
            img_tensor = torch.from_numpy(image).float() / 255.0
            # [1, 1, H, W]
            img_tensor = img_tensor.unsqueeze(0).unsqueeze(0).to(self.device)
            return img_tensor, orig_shape
        else:
            return image, orig_shape

    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect keypoints and descriptors."""
        tensor, orig_shape = self._preprocess_image(image)
        h, w = image.shape[:2] if len(image.shape) < 3 else image.shape[:2]
        
        if self.mode == 'lightglue':
            with torch.no_grad():
                pred = self.extractor({'image': tensor})
            # Remove batch dim
            pred = {k: v[0].cpu().numpy() for k, v in pred.items()}
            # Rescale keypoints back
            scale_x = orig_shape[0] / tensor.shape[-1]
            scale_y = orig_shape[1] / tensor.shape[-2]
            pred['keypoints'][:, 0] *= scale_x
            pred['keypoints'][:, 1] *= scale_y
            return pred
        elif self.mode == 'kornia':
            with torch.no_grad():
                # Kornia SuperPoint returns (keypoints, scores, descriptors)
                mask = torch.ones_like(tensor)
                kpts, scores, descs = self.extractor(tensor, mask)
                kpts = kpts[0].cpu().numpy()
                scores = scores[0].cpu().numpy()
                descs = descs[0].cpu().numpy()
                scale_x = orig_shape[0] / tensor.shape[-1]
                scale_y = orig_shape[1] / tensor.shape[-2]
                kpts[:, 0] *= scale_x
                kpts[:, 1] *= scale_y
                return {'keypoints': kpts, 'scores': scores, 'descriptors': descs}
        else:
            kpts, descs = self.extractor.detectAndCompute(tensor, None)
            if kpts:
                kpts_np = np.array([kp.pt for kp in kpts])
                scores = np.array([kp.response for kp in kpts])
            else:
                kpts_np = np.empty((0, 2))
                scores = np.empty((0,))
                descs = np.empty((0, 32))
            
            scale_x = orig_shape[0] / tensor.shape[1] if isinstance(tensor, np.ndarray) else 1.0
            scale_y = orig_shape[1] / tensor.shape[0] if isinstance(tensor, np.ndarray) else 1.0
            if len(kpts_np) > 0:
                kpts_np[:, 0] *= scale_x
                kpts_np[:, 1] *= scale_y
                
            return {'keypoints': kpts_np, 'scores': scores, 'descriptors': descs}

    def match(self, image0: np.ndarray, image1: np.ndarray) -> Dict[str, Any]:
        """Full pipeline: preprocess -> detect both -> match."""
        start_time = time.time()
        
        tensor0, orig_shape0 = self._preprocess_image(image0)
        tensor1, orig_shape1 = self._preprocess_image(image1)
        
        if self.mode == 'lightglue':
            with torch.no_grad():
                pred0 = self.extractor({'image': tensor0})
                pred1 = self.extractor({'image': tensor1})
                matches = self.matcher({'image0': pred0, 'image1': pred1})
                
            # Parse matches
            m = matches['matches'][0].cpu().numpy()
            scores = matches['scores'][0].cpu().numpy()
            
            kp0 = pred0['keypoints'][0].cpu().numpy()
            kp1 = pred1['keypoints'][0].cpu().numpy()
            
            mkpts0 = kp0[m[:, 0]]
            mkpts1 = kp1[m[:, 1]]
            
            # Rescale
            scale0_x = orig_shape0[0] / tensor0.shape[-1]
            scale0_y = orig_shape0[1] / tensor0.shape[-2]
            scale1_x = orig_shape1[0] / tensor1.shape[-1]
            scale1_y = orig_shape1[1] / tensor1.shape[-2]
            
            mkpts0[:, 0] *= scale0_x
            mkpts0[:, 1] *= scale0_y
            mkpts1[:, 0] *= scale1_x
            mkpts1[:, 1] *= scale1_y
            
        elif self.mode == 'kornia':
            with torch.no_grad():
                mask0 = torch.ones_like(tensor0)
                mask1 = torch.ones_like(tensor1)
                kp0, scores0, desc0 = self.extractor(tensor0, mask0)
                kp1, scores1, desc1 = self.extractor(tensor1, mask1)
                
                # Format for LightGlue (depends on Kornia version)
                # This assumes a simplified interface
                data = {
                    'image0': {'keypoints': kp0, 'descriptors': desc0},
                    'image1': {'keypoints': kp1, 'descriptors': desc1}
                }
                out = self.matcher(data)
                
            m = out['matches'][0].cpu().numpy()
            scores = out['scores'][0].cpu().numpy()
            
            kp0_np = kp0[0].cpu().numpy()
            kp1_np = kp1[0].cpu().numpy()
            
            mkpts0 = kp0_np[m[:, 0]]
            mkpts1 = kp1_np[m[:, 1]]
            
            # Rescale
            scale0_x = orig_shape0[0] / tensor0.shape[-1]
            scale0_y = orig_shape0[1] / tensor0.shape[-2]
            scale1_x = orig_shape1[0] / tensor1.shape[-1]
            scale1_y = orig_shape1[1] / tensor1.shape[-2]
            
            mkpts0[:, 0] *= scale0_x
            mkpts0[:, 1] *= scale0_y
            mkpts1[:, 0] *= scale1_x
            mkpts1[:, 1] *= scale1_y

        else:
            kpts0, desc0 = self.extractor.detectAndCompute(tensor0, None)
            kpts1, desc1 = self.extractor.detectAndCompute(tensor1, None)
            
            if desc0 is not None and desc1 is not None:
                matches = self.matcher.match(desc0, desc1)
                mkpts0 = np.float32([kpts0[m.queryIdx].pt for m in matches])
                mkpts1 = np.float32([kpts1[m.trainIdx].pt for m in matches])
                scores = np.float32([1.0 / (1.0 + m.distance) for m in matches])
            else:
                mkpts0 = np.empty((0, 2))
                mkpts1 = np.empty((0, 2))
                scores = np.empty((0,))
                
            scale0_x = orig_shape0[0] / tensor0.shape[1]
            scale0_y = orig_shape0[1] / tensor0.shape[0]
            scale1_x = orig_shape1[0] / tensor1.shape[1]
            scale1_y = orig_shape1[1] / tensor1.shape[0]
            
            if len(mkpts0) > 0:
                mkpts0[:, 0] *= scale0_x
                mkpts0[:, 1] *= scale0_y
                mkpts1[:, 0] *= scale1_x
                mkpts1[:, 1] *= scale1_y

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Matched {len(mkpts0)} points in {elapsed_ms:.2f} ms")
        
        return {
            'keypoints0': mkpts0,
            'keypoints1': mkpts1,
            'scores': scores,
            'num_matches': len(mkpts0),
            'elapsed_ms': elapsed_ms
        }

    def match_multiscale(self, image0: np.ndarray, image1: np.ndarray, scales: List[float] = [1.0, 0.5, 0.25]) -> Dict[str, Any]:
        """Run matching at multiple scales and merge."""
        start_time = time.time()
        
        all_kpts0 = []
        all_kpts1 = []
        all_scores = []
        
        for scale in scales:
            if scale != 1.0:
                h0, w0 = image0.shape[:2]
                h1, w1 = image1.shape[:2]
                img0_s = cv2.resize(image0, (int(w0*scale), int(h0*scale)))
                img1_s = cv2.resize(image1, (int(w1*scale), int(h1*scale)))
            else:
                img0_s = image0
                img1_s = image1
                
            res = self.match(img0_s, img1_s)
            
            if res['num_matches'] > 0:
                kpts0 = res['keypoints0']
                kpts1 = res['keypoints1']
                
                if scale != 1.0:
                    kpts0 /= scale
                    kpts1 /= scale
                    
                all_kpts0.append(kpts0)
                all_kpts1.append(kpts1)
                all_scores.append(res['scores'])
                
        if all_kpts0:
            mkpts0 = np.concatenate(all_kpts0, axis=0)
            mkpts1 = np.concatenate(all_kpts1, axis=0)
            scores = np.concatenate(all_scores, axis=0)
            
            # Simple NMS / deduplication could be added here
            # For now, just return all
        else:
            mkpts0 = np.empty((0, 2))
            mkpts1 = np.empty((0, 2))
            scores = np.empty((0,))
            
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Multiscale matched {len(mkpts0)} points in {elapsed_ms:.2f} ms")
        
        return {
            'keypoints0': mkpts0,
            'keypoints1': mkpts1,
            'scores': scores,
            'num_matches': len(mkpts0),
            'elapsed_ms': elapsed_ms
        }
