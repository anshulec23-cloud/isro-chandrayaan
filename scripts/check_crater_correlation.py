import cv2
import numpy as np

tmc = cv2.imread('data/processed/cross_mission_patch/tmc_patch.png', cv2.IMREAD_GRAYSCALE)
sel = cv2.imread('data/processed/cross_mission_patch/selene_patch.png', cv2.IMREAD_GRAYSCALE)

# Let's find the brightest/darkest crater in tmc
# and template match it across selene
h, w = tmc.shape
# Pick a 128x128 crop around the center of tmc
patch = tmc[h//2 - 64:h//2 + 64, w//2 - 64:w//2 + 64]

res = cv2.matchTemplate(sel, patch, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
print(f'Template match max correlation: {max_val:.4f} at location {max_loc}')

# Also test horizontal and vertical flips
res_h = cv2.matchTemplate(cv2.flip(sel, 1), patch, cv2.TM_CCOEFF_NORMED)
print(f'Horizontal flip max correlation: {cv2.minMaxLoc(res_h)[1]:.4f}')

res_v = cv2.matchTemplate(cv2.flip(sel, 0), patch, cv2.TM_CCOEFF_NORMED)
print(f'Vertical flip max correlation: {cv2.minMaxLoc(res_v)[1]:.4f}')

res_hv = cv2.matchTemplate(cv2.flip(sel, -1), patch, cv2.TM_CCOEFF_NORMED)
print(f'Both flip max correlation: {cv2.minMaxLoc(res_hv)[1]:.4f}')
