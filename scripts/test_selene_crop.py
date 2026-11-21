import numpy as np
import cv2

path = 'data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.img'
# Memory map the 12288 x 12288 uint16 array
arr = np.memmap(path, dtype='>u2', mode='r', shape=(12288, 12288))

# Extract the region overlapping Chandrayaan-2 TMC (Lon 141.0 to 142.71 -> cols 0 to 7004, Rows 0 to 12288)
# Let's take a 2048 x 2048 sub-sample to verify craters
sub = arr[2000:4048, 1000:3048]
print('Sub-array shape:', sub.shape)
print('Min:', sub.min(), 'Max:', sub.max(), 'Mean:', sub.mean())

# Normalize to uint8 using 2nd and 98th percentiles
p2, p98 = np.percentile(sub[sub > 0], (2, 98))
norm = np.clip((sub.astype(np.float32) - p2) / (p98 - p2), 0, 1)
u8 = (norm * 255).astype(np.uint8)

cv2.imwrite('data/reference/selene_tc/selene_crop_test.png', u8)
print('Saved data/reference/selene_tc/selene_crop_test.png, size:', u8.shape)
