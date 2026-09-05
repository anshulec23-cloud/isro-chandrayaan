import os
import sys
import json
import random
import logging
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lumen.pipeline.orchestrator import RegistrationPipeline

def main():
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data" / "raw"
    
    # TMC-TMC Pair
    tmc_nca_xml = str(data_dir / "ch2_tmc_nca_20260813T0627378526_d_img_d18" / "data" / "calibrated" / "20260813" / "ch2_tmc_nca_20260813T0627378526_d_img_d18.xml")
    tmc_ncn_xml = str(data_dir / "ch2_tmc_ncn_20260813T0627378557_d_img_d18" / "data" / "calibrated" / "20260813" / "ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml")
    
    logging.basicConfig(level=logging.INFO)
    pipeline = RegistrationPipeline(config={})
    
    print("Running pipeline to extract inliers...")
    result = pipeline.run(
        source_path=tmc_nca_xml,
        reference_path=tmc_ncn_xml,
        source_sensor="TMC",
        ref_sensor="TMC",
        options={
            "feature_method": "auto",
            "scale_ratio": 1.0,
            "skip_overlap_crop": False,
        }
    )
    
    inliers = [p for p in result.match_points if p["inlier"]]
    print(f"Found {len(inliers)} inliers.")
    
    # Sample 20 inliers (spread them out or just randomly sample with a fixed seed for reproducibility)
    random.seed(42)
    if len(inliers) > 20:
        sampled = random.sample(inliers, 20)
    else:
        sampled = inliers
        
    pts_src = [[p["src_x"], p["src_y"]] for p in sampled]
    pts_ref = [[p["dst_x"], p["dst_y"]] for p in sampled]
    
    out_json = {
        "checkpoint_source": "sampled_from_inliers",
        "source_points": pts_src,
        "reference_points": pts_ref
    }
    
    out_path = root_dir / "data" / "checkpoints_tmc_tmc.json"
    with open(out_path, "w") as f:
        json.dump(out_json, f, indent=4)
        
    print(f"Saved {len(sampled)} checkpoints to {out_path}")

if __name__ == "__main__":
    main()
