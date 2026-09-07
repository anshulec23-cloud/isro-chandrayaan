import os
import rasterio
from rasterio.enums import Resampling
import cv2
import numpy as np
from pathlib import Path

def get_thumbnail(img, size=1000):
    """Returns a center square crop of the image."""
    if img is None:
        return None
    h, w = img.shape[:2]
    crop_h, crop_w = min(h, size), min(w, size)
    start_y = max(0, (h - crop_h) // 2)
    start_x = max(0, (w - crop_w) // 2)
    cropped = img[start_y:start_y+crop_h, start_x:start_x+crop_w]
    return cropped

def generate_previews():
    src_dir = Path("data/processed/real_ortho_outputs")
    dst_dir = Path("dashboard/public/previews")
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    tiffs = [
        "ohrc_calibrated_ortho.tif",
        "tmc_nca_ortho.tif",
        "tmc_ncn_ortho.tif",
        "iirs_ortho.tif"
    ]
    
    max_dim = 2000
    
    for tif_name in tiffs:
        src_path = src_dir / tif_name
        if not src_path.exists():
            print(f"Skipping {tif_name}, not found.")
            continue
            
        print(f"Processing {tif_name}...")
        with rasterio.open(src_path) as dataset:
            scale = min(max_dim / dataset.width, max_dim / dataset.height)
            if scale > 1.0:
                scale = 1.0
                
            out_shape = (
                dataset.count,
                int(dataset.height * scale),
                int(dataset.width * scale)
            )
            
            print(f"  Reading decimated shape {out_shape} (original: {dataset.shape})")
            data = dataset.read(out_shape=out_shape, resampling=Resampling.average)
            
            img = data[0]
            img = np.nan_to_num(img)
            valid = img[img > 0]
            if len(valid) == 0:
                img_8u = np.zeros_like(img, dtype=np.uint8)
            else:
                p2, p98 = np.percentile(valid, (2, 98))
                if p2 == p98:
                    img_8u = np.zeros_like(img, dtype=np.uint8)
                else:
                    img_norm = np.clip((img - p2) / (p98 - p2), 0, 1)
                    img_8u = (img_norm * 255).astype(np.uint8)
                    
            # Save Full Strip
            base_name = tif_name.replace(".tif", "")
            out_path = dst_dir / f"{base_name}.png"
            cv2.imwrite(str(out_path), img_8u)
            print(f"  Saved Full: {out_path}")

            # Save Thumbnail Crop (Center)
            thumb = get_thumbnail(img_8u, size=1000)
            if thumb is not None:
                thumb_path = dst_dir / f"{base_name}_thumb.png"
                cv2.imwrite(str(thumb_path), thumb)
                print(f"  Saved Thumb: {thumb_path}")

    # Copy the TMC checkerboard and registered results
    demo_dir = Path("data/processed/FINAL_DEMO")
    if demo_dir.exists():
        import shutil
        print("Copying FINAL_DEMO images...")
        for img in ["TMC_to_TMC_checkerboard.jpg", "TMC_to_TMC_ref_04_photometric_norm.png", "TMC_to_TMC_src_04_photometric_norm.png"]:
            if (demo_dir / img).exists():
                shutil.copy2(demo_dir / img, dst_dir / img)
                print(f"  Copied {img}")
                
        # The registered TIF is 2.3GB. We need to generate a preview for it too.
        reg_tif = demo_dir / "TMC_to_TMC_registered.tif"
        if reg_tif.exists():
            print(f"Processing TMC_to_TMC_registered.tif...")
            with rasterio.open(reg_tif) as dataset:
                scale = min(max_dim / dataset.width, max_dim / dataset.height)
                if scale > 1.0: scale = 1.0
                out_shape = (dataset.count, int(dataset.height * scale), int(dataset.width * scale))
                print(f"  Reading decimated shape {out_shape}")
                data = dataset.read(out_shape=out_shape, resampling=Resampling.average)
                img = data[0]
                img = np.nan_to_num(img)
                valid = img[img > 0]
                if len(valid) > 0:
                    p2, p98 = np.percentile(valid, (2, 98))
                    img_norm = np.clip((img - p2) / (p98 - p2 + 1e-6), 0, 1)
                    img_8u = (img_norm * 255).astype(np.uint8)
                else:
                    img_8u = np.zeros_like(img, dtype=np.uint8)
                
                out_path = dst_dir / "TMC_to_TMC_registered.png"
                cv2.imwrite(str(out_path), img_8u)
                print(f"  Saved Full: {out_path}")
                
                thumb = get_thumbnail(img_8u, size=1000)
                if thumb is not None:
                    thumb_path = dst_dir / "TMC_to_TMC_registered_thumb.png"
                    cv2.imwrite(str(thumb_path), thumb)
                    print(f"  Saved Thumb: {thumb_path}")

if __name__ == "__main__":
    generate_previews()
