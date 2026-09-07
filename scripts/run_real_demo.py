import os
import sys
import json
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from lumen.pipeline.orchestrator import RegistrationPipeline
from lumen.registration.warp import create_registered_product

def load_checkpoints(json_path):
    if not os.path.exists(json_path):
        print(f"Warning: Checkpoints file {json_path} not found. Running without explicit checkpoints.")
        return None
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    pts_src = data.get("source_points", [])
    pts_ref = data.get("reference_points", [])
    
    if pts_src and pts_ref:
        return {"pts_src": np.array(pts_src), "pts_ref": np.array(pts_ref)}
    return None

def run_pair(pipeline, src_path, ref_path, src_sensor, ref_sensor, output_dir, checkpoints):
    print(f"\n{'='*60}")
    print(f"Running Registration: {src_sensor} -> {ref_sensor}")
    print(f"Source: {src_path}")
    print(f"Reference: {ref_path}")
    print(f"{'='*60}")
    
    try:
        debug_dir = os.path.join(output_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)

        # Run pipeline with debug preview generation
        result = pipeline.run(
            source_path=src_path,
            reference_path=ref_path,
            source_sensor=src_sensor,
            ref_sensor=ref_sensor,
            options={
                "feature_method": "auto",
                "scale_ratio": 1.0,
                "debug_dir": debug_dir,
            },
            checkpoints=checkpoints
        )
        
        print("\n--- Full Metrics Dict ---")
        for k, v in result.metrics.items():
            print(f"{k}: {v}")
            
        print(f"\nElapsed time: {result.elapsed_seconds:.2f} seconds")
        
        # Save GeoTIFF
        out_tif = os.path.join(output_dir, f"{src_sensor}_to_{ref_sensor}_registered.tif")
        # In RegistrationResult, the registered image is available via result.warped_image
        # We need the reference image for creating the product if we want to inherit metadata.
        # But we can also just use create_registered_product for writing.
        # RegistrationPipeline already returned transform_matrix.
        # Actually create_registered_product takes reference, but we can just pass the path.
        
        product_info = create_registered_product(
            source=result.warped_image,
            reference=ref_path,
            transform=result.transform_matrix,
            output_path=out_tif,
            source_sensor=src_sensor,
            ref_sensor=ref_sensor,
            rmse=result.metrics.get("rmse")
        )
        print(f"\nSaved GeoTIFF: {out_tif}")
        
        # Save Checkerboard
        if result.checkerboard_image is not None:
            out_cb = os.path.join(output_dir, f"{src_sensor}_to_{ref_sensor}_checkerboard.jpg")
            # OpenCV writes BGR, if it's grayscale it handles it automatically
            # If it's a float image, scale to 255
            cb_img = result.checkerboard_image
            if cb_img.dtype == np.float32 or cb_img.dtype == np.float64:
                cb_img = (np.clip(cb_img, 0, 1) * 255).astype(np.uint8)
            cv2.imwrite(out_cb, cb_img)
            print(f"Saved Checkerboard: {out_cb}")
            
    except Exception as e:
        print("\nPipeline crashed with the following traceback:")
        traceback.print_exc()

def main():
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data" / "raw"
    
    # Real paths
    tmc_nca_xml = str(data_dir / "ch2_tmc_nca_20260813T0627378526_d_img_d18" / "data" / "calibrated" / "20260813" / "ch2_tmc_nca_20260813T0627378526_d_img_d18.xml")
    tmc_ncn_xml = str(data_dir / "ch2_tmc_ncn_20260813T0627378557_d_img_d18" / "data" / "calibrated" / "20260813" / "ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml")
    ohrc_xml = str(data_dir / "ch2_ohr_ncp_20260130T1309574436_d_img_d18" / "data" / "calibrated" / "20260130" / "ch2_ohr_ncp_20260130T1309574436_d_img_d18.xml")
    iirs_xml = str(data_dir / "ch2_iir_ndi_20250729T0936115604_d_rfl_d18_srd" / "data" / "derived" / "20250729" / "ch2_iir_ndi_20250729T0936115604_d_rfl_d18_srd.xml")
    
    # Create output directory
    output_dir = str(root_dir / "data" / "processed" / "demo_output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Load checkpoints
    ckpt_path_default = str(root_dir / "notebooks" / "checkpoints.json")
    checkpoints_default = load_checkpoints(ckpt_path_default)
    
    ckpt_path_tmc = str(root_dir / "data" / "checkpoints_tmc_tmc.json")
    checkpoints_tmc = load_checkpoints(ckpt_path_tmc)
    
    # Initialize pipeline
    pipeline = RegistrationPipeline(config={})
    
    # 1. TMC-TMC stereo pair (confirmed 92% geographic overlap)
    run_pair(pipeline, tmc_nca_xml, tmc_ncn_xml, "TMC", "TMC", output_dir, checkpoints_tmc)
    
    # 2. OHRC/TMC pair
    # run_pair(pipeline, ohrc_xml, tmc_nca_xml, "OHRC", "TMC", output_dir, checkpoints_default)
    
    # 3. OHRC/IIRS pair
    # run_pair(pipeline, ohrc_xml, iirs_xml, "OHRC", "IIRS", output_dir, checkpoints_default)

if __name__ == "__main__":
    main()
