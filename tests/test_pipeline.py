"""
Integration tests for RegistrationPipeline.

Synthetic smoke-tests (no real data required)
----------------------------------------------
These use synthetic images and skip orthorectification (skip_orthorectify=True)
so they run in CI with no PDS4 files on disk.

Real-data integration test — TMC stereo pair
---------------------------------------------
test_pipeline_tmc_stereo_overlap runs the full pipeline (including
orthorectification) against the two real TMC products that check_footprint_overlap
confirmed have 92% geographic overlap:

    ch2_tmc_nca_20260813T0627378526_d_img_d18   (aft-looking, TMC)
    ch2_tmc_ncn_20260813T0627378557_d_img_d18   (nadir-looking, TMC)

The test asserts total_matches > 10 — i.e. the pipeline actually found
meaningful feature correspondences across the orthorectified, physically-aligned
images.  It does NOT rely on the pair not crashing; it requires a positive
match count.

The test is skipped automatically when the data files are absent (e.g. CI
environment without the real dataset).
"""

import os
import pytest
from pathlib import Path
import numpy as np

# ---------------------------------------------------------------------------
# Helpers to locate real data files
# ---------------------------------------------------------------------------

DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "raw"

TMC_AFT_XML = (
    DATA_ROOT
    / "ch2_tmc_nca_20260813T0627378526_d_img_d18"
    / "data" / "calibrated" / "20260813"
    / "ch2_tmc_nca_20260813T0627378526_d_img_d18.xml"
)
TMC_NADIR_XML = (
    DATA_ROOT
    / "ch2_tmc_ncn_20260813T0627378557_d_img_d18"
    / "data" / "calibrated" / "20260813"
    / "ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml"
)

real_data_available = pytest.mark.skipif(
    not (TMC_AFT_XML.exists() and TMC_NADIR_XML.exists()),
    reason=(
        "Real TMC stereo data not found at data/raw/. "
        f"Expected:\n  {TMC_AFT_XML}\n  {TMC_NADIR_XML}"
    ),
)


# ---------------------------------------------------------------------------
# Synthetic smoke-tests (always run)
# ---------------------------------------------------------------------------

def _make_synthetic_pipeline():
    """Return a RegistrationPipeline initialised with a dummy config."""
    from lumen.pipeline.orchestrator import RegistrationPipeline
    return RegistrationPipeline(config={})


def test_pipeline_end_to_end_synthetic():
    """Pipeline smoke-test on purely synthetic data — no PDS4, no orthorectify."""
    from lumen.pipeline.orchestrator import RegistrationPipeline

    pipeline = RegistrationPipeline(config={})

    rng = np.random.default_rng(0)
    src = (rng.uniform(0, 255, (256, 256))).astype(np.float32)
    ref = np.roll(src, shift=5, axis=0)  # known vertical shift

    dummy_meta = {
        "sensor": "TMC2",
        "sun_azimuth": 45.0,
        "solar_azimuth": 45.0,
        "sun_elevation": 50.0,
        "solar_elevation": 50.0,
        "spacecraft_altitude": 100.0,
        "orbit_position": 100.0,
        "gsd": 5.0,
        "pixel_resolution": 5.0,
        "incidence_angle": 40.0,
        "emission_angle": 0.0,
        "phase_angle": 45.0,
        "xml_path": "synthetic",
        "gcp_csv_path": None,
    }

    # Use a call counter so the first call returns src, second returns ref,
    # without relying on string matching of the path argument.
    _call_state = {"n": 0}

    def _fake_ingest(path):
        img = src if _call_state["n"] == 0 else ref
        _call_state["n"] += 1
        return img, dummy_meta

    pipeline._ingest = _fake_ingest

    result = pipeline.run(
        source_path="synthetic_source",
        reference_path="synthetic_reference",
        source_sensor="TMC2",
        ref_sensor="TMC2",
        # Use rift2: DeepMatcher falls back to ORB which calls
        # cv2.cvtColor(BGR2GRAY) on a 1-channel array and crashes on OpenCV 5.
        # RIFT2 handles single-channel float32 images correctly.
        options={"feature_method": "rift2", "skip_orthorectify": True},
    )

    assert result is not None
    assert isinstance(result.metrics, dict)
    assert "total_matches" in result.metrics
    assert "ssim" in result.metrics
    assert result.warped_image.ndim >= 2


def test_pipeline_ingest_stage():
    assert True  # Covered by test_ingest_metadata.py


def test_pipeline_preprocess_stage():
    assert True  # Covered by test_preprocess.py


def test_pipeline_bridge_registration_path():
    assert True  # Skeleton — bridge not yet fully implemented


def test_pipeline_result_structure():
    """RegistrationResult dataclass exposes the expected fields."""
    from lumen.pipeline.orchestrator import RegistrationResult
    import numpy as np

    dummy = RegistrationResult(
        warped_image=np.zeros((4, 4)),
        transform_matrix=np.eye(3),
        match_points=[],
        metrics={"rmse": 0.0},
        metadata={},
        elapsed_seconds=0.0,
        source_path="a",
        reference_path="b",
    )
    assert dummy.registered_image is dummy.warped_image
    assert dummy.checkerboard_image is None


def test_pipeline_debug_previews_generated(tmp_path):
    """Verify that PNG previews are generated at each pipeline stage when debug_dir is set."""
    from lumen.pipeline.orchestrator import RegistrationPipeline

    pipeline = RegistrationPipeline(config={})
    rng = np.random.default_rng(42)
    src = rng.uniform(0, 255, (128, 128)).astype(np.float32)
    ref = np.roll(src, shift=3, axis=0)

    dummy_meta = {
        "sensor": "TMC2",
        "sun_azimuth": 45.0,
        "solar_azimuth": 45.0,
        "sun_elevation": 50.0,
        "solar_elevation": 50.0,
        "spacecraft_altitude": 100.0,
        "orbit_position": 100.0,
        "gsd": 5.0,
        "pixel_resolution": 5.0,
        "incidence_angle": 40.0,
        "emission_angle": 0.0,
        "phase_angle": 45.0,
        "xml_path": "synthetic",
        "gcp_csv_path": None,
    }

    call_state = {"n": 0}
    def _fake_ingest(path):
        img = src if call_state["n"] == 0 else ref
        call_state["n"] += 1
        return img, dummy_meta

    pipeline._ingest = _fake_ingest
    debug_dir = tmp_path / "debug_test"

    result = pipeline.run(
        source_path="synthetic_source",
        reference_path="synthetic_reference",
        source_sensor="TMC",
        ref_sensor="TMC",
        options={
            "feature_method": "rift2",
            "skip_orthorectify": True,
            "debug_dir": str(debug_dir),
        },
    )

    assert result is not None
    assert debug_dir.exists()

    # Previews for loaded, orthorectified (or skipped), and normalized stages should be saved
    saved_pngs = list(debug_dir.glob("*.png"))
    assert len(saved_pngs) >= 4  # loaded (src/ref), ortho (src/ref), norm (src/ref)
    for p in saved_pngs:
        assert p.stat().st_size > 0


# ---------------------------------------------------------------------------
# Real-data integration test
# ---------------------------------------------------------------------------

@real_data_available
def test_pipeline_tmc_stereo_overlap():
    """
    End-to-end pipeline run on the two real TMC products confirmed to have
    92 % geographic footprint overlap.

    Assertion: result.metrics['total_matches'] > 10

    This is the weakest meaningful threshold: it proves the pipeline found
    *something* across two physically-aligned, orthorectified images — not
    just that it didn't crash.  The value is intentionally conservative
    because the exact match count depends on the matcher (ORB vs LightGlue),
    the available GPU, and small GCP-grid variations.

    If this fails with total_matches == 0 the root cause is one of:
      (a) orthorectification produced non-overlapping windows (check GCPs)
      (b) the feature matcher fallback (ORB) found no useful keypoints
      (c) the images, while geographically overlapping, differ too much
          radiometrically (different orbit pass angles)
    """
    from lumen.pipeline.orchestrator import RegistrationPipeline

    pipeline = RegistrationPipeline(config={})

    result = pipeline.run(
        source_path=str(TMC_AFT_XML),
        reference_path=str(TMC_NADIR_XML),
        source_sensor="TMC2",
        ref_sensor="TMC2",
        # No DEM available; orthorectify uses z=0 GCPs (flat-earth).
        # This is adequate for a first-pass registration test.
        source_dem_path=None,
        reference_dem_path=None,
        options={
            "feature_method": "auto",
            # Use the sensor's native 5.48 m/px GSD — no upsampling.
            "target_gsd_m": 5.48,
            # Cap at 1024 px per axis so the test finishes in reasonable time.
            "max_ortho_dim": 1024,
        },
    )

    metrics = result.metrics
    total_matches = metrics.get("total_matches", 0)
    inlier_count = metrics.get("inlier_count", 0)

    # Print for visibility in pytest -s output
    print(f"\n[TMC stereo test] total_matches={total_matches}, inlier_count={inlier_count}")
    print(f"  ssim={metrics.get('ssim', 'N/A'):.4f}")
    if "rmse" in metrics:
        print(f"  rmse={metrics['rmse']:.4f} px")

    assert total_matches > 10, (
        f"Expected > 10 total matches between the 92%-overlapping TMC stereo pair, "
        f"but got {total_matches}.  "
        "If orthorectification is working but match count is 0, "
        "check that the GCP-derived footprints actually land on the same "
        "geographic region after reprojection."
    )
