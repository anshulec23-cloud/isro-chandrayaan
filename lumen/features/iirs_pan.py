"""
IIRS hyperspectral-to-panchromatic conversion for feature matching.

Why this module exists
----------------------
IIRS (Imaging Infrared Spectrometer) on Chandrayaan-2 is a 256-band
pushbroom spectrometer covering 712.3 – 5009.7 nm in BSQ float32 format
(250 samples × 13 067 lines × 256 bands per our sample product
ch2_iir_ndi_20250729T0936115604_d_rfl_d18_srd).

OHRC (500–800 nm) and TMC-2 (500–850 nm) are panchromatic sensors operating
in the visible.  Feeding a raw IIRS hyperspectral cube (H × W × 256 or
256 × H × W) into `deep_matcher.py` or `rift2.py` silently breaks those
matchers:
  • `_preprocess_image` in deep_matcher calls `cv2.cvtColor(img, COLOR_BGR2GRAY)`,
    which interprets a 256-channel array as a 256-channel BGR image and silently
    uses only channels 0/1/2 — bands at 712 nm, 729 nm, 746 nm.
  • `compute_phase_congruency` in rift2 calls `cv2.cvtColor(img, COLOR_BGR2GRAY)`
    for the same reason: only 3 of the 256 bands are consumed, arbitrarily.
Both paths return a 2-D image without raising any error.

This module provides the correct, explicit conversion and is the single
authoritative location for this logic.  Both matchers import and call
`iirs_to_pan` before any feature extraction step.

Spectral band selection rationale
----------------------------------
**We use a brightness-weighted average of IIRS bands whose centre wavelength
falls within 712–1000 nm (bands 0–12 in our product).**

Justification:
1. OHRC spans 500–800 nm; TMC-2 spans 500–850 nm.  The 712–1000 nm window
   is the longest-wavelength portion of the IIRS range that overlaps with the
   red-channel tail of both OHRC and TMC-2.

2. Lunar surface reflectance in the visible-NIR (600–1000 nm) is dominated by
   albedo differences between mare basalt and highland anorthosite.  These are
   the same morphological features that OHRC and TMC-2 image.  Averaging across
   this window preserves the spatial contrast relevant to feature matching.

3. Bands beyond 1000 nm introduce thermal emission contributions and deep
   atmospheric (H₂O, CO₂) absorption features that are not present in OHRC/TMC
   imagery and would confuse the matchers.

4. Weighting by the approximate solar irradiance at each wavelength (modelled
   as a Gaussian centred on 700 nm and falling off into the NIR) makes the
   composite mimic the photon-count weighting that a real panchromatic sensor
   would apply.

**What we explicitly cannot do and why**
  IIRS has NO blue or green bands (shortest wavelength: 712 nm).  OHRC and
  TMC-2 receive their primary visible contrast from 500–700 nm.  The
  panchromatic proxy produced here matches the NIR-albedo pattern of the
  surface, not the visible-albedo pattern.  For flat-to-gently-rolling terrain
  (low thermal gradient) these are generally correlated, but:
    - In permanently shadowed regions (PSRs) the NIR signal is near-zero and
      the IIRS-derived proxy will be dark / featureless even if OHRC images
      scattered light.
    - High-temperature regions will show MWIR thermal emission contamination
      even after wavelength clipping if the clip boundary is insufficiently
      conservative.

  This is the best proxy possible given available data.  Any claim that the
  IIRS-derived pan is radiometrically equivalent to OHRC/TMC visible imagery
  would be false.

Input format support
--------------------
IIRS .qub files are BSQ (Band Sequential): the array on disk is
  (bands, lines, samples) = (256, 13 067, 250)
When loaded with numpy (memmap or fromfile), the shape is (256, H, W).
`iirs_to_pan` accepts both (H, W, B) and (B, H, W) layouts and 2-D
single-band arrays (pass-through).
"""

import logging
import warnings
from typing import Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["iirs_to_pan", "IIRSConversionWarning"]

# IIRS wavelength vector from the sample product HDR (nm), bands 0..255
# Extracted from ch2_iir_ndi_20250729T0936115604_d_rfl_d18_srd.hdr
IIRS_WAVELENGTHS_NM: np.ndarray = np.array([
    712.3, 729.2, 746.0, 762.9, 779.7, 796.6, 813.4, 830.3, 847.2, 864.0,
    880.9, 897.7, 914.6, 931.4, 948.3, 965.1, 982.0, 998.8, 1015.7, 1032.5,
    1049.4, 1066.2, 1083.1, 1099.9, 1116.8, 1133.6, 1150.5, 1167.3, 1184.2,
    1201.1, 1217.9, 1234.8, 1251.6, 1268.5, 1285.3, 1302.2, 1319.0, 1335.9,
    1352.7, 1369.6, 1386.4, 1403.3, 1420.1, 1437.0, 1453.8, 1470.7, 1487.5,
    1504.4, 1521.2, 1538.1, 1555.0, 1571.8, 1588.7, 1605.5, 1622.4, 1639.2,
    1656.1, 1672.9, 1689.8, 1706.6, 1723.5, 1740.3, 1757.2, 1774.0, 1790.9,
    1807.7, 1824.6, 1841.4, 1858.3, 1875.1, 1892.0, 1908.9, 1925.7, 1942.6,
    1959.4, 1976.3, 1993.1, 2010.0, 2026.8, 2043.7, 2060.5, 2077.4, 2094.2,
    2111.1, 2127.9, 2144.8, 2161.6, 2178.5, 2195.3, 2212.2, 2229.0, 2245.9,
    2262.8, 2279.6, 2296.5, 2313.3, 2330.2, 2347.0, 2363.9, 2380.7, 2397.6,
    2414.4, 2431.3, 2448.1, 2465.0, 2481.8, 2498.7, 2515.5, 2532.4, 2549.2,
    2566.1, 2582.9, 2599.8, 2616.7, 2633.5, 2650.4, 2667.2, 2684.1, 2700.9,
    2717.8, 2734.6, 2751.5, 2768.3, 2785.2, 2802.0, 2818.9, 2835.7, 2852.6,
    2869.4, 2886.3, 2903.1, 2920.0, 2936.8, 2953.7, 2970.6, 2987.4, 3004.3,
    3021.1, 3038.0, 3054.8, 3071.7, 3088.5, 3105.4, 3122.2, 3139.1, 3155.9,
    3172.8, 3189.6, 3206.5, 3223.3, 3240.2, 3257.0, 3273.9, 3290.7, 3307.6,
    3324.5, 3341.3, 3358.2, 3375.0, 3391.9, 3408.7, 3425.6, 3442.4, 3459.3,
    3476.1, 3493.0, 3509.8, 3526.7, 3543.5, 3560.4, 3577.2, 3594.1, 3610.9,
    3627.8, 3644.6, 3661.5, 3678.3, 3695.2, 3712.1, 3728.9, 3745.8, 3762.6,
    3779.5, 3796.3, 3813.2, 3830.0, 3846.9, 3863.7, 3880.6, 3897.4, 3914.3,
    3931.1, 3948.0, 3964.8, 3981.7, 3998.5, 4015.4, 4032.2, 4049.1, 4066.0,
    4082.8, 4099.7, 4116.5, 4133.4, 4150.2, 4167.1, 4183.9, 4200.8, 4217.6,
    4234.5, 4251.3, 4268.2, 4285.0, 4301.9, 4318.7, 4335.6, 4352.4, 4369.3,
    4386.1, 4403.0, 4419.9, 4436.7, 4453.6, 4470.4, 4487.3, 4504.1, 4521.0,
    4537.8, 4554.7, 4571.5, 4588.4, 4605.2, 4622.1, 4638.9, 4655.8, 4672.6,
    4689.5, 4706.3, 4723.2, 4740.0, 4756.9, 4773.8, 4790.6, 4807.5, 4824.3,
    4841.2, 4858.0, 4874.9, 4891.7, 4908.6, 4925.4, 4942.3, 4959.1, 4976.0,
    4992.8, 5009.7,
], dtype=np.float32)

# The IIRS NIR window that overlaps with OHRC/TMC visible response.
# Bands whose centre wavelength is ≤ 1000 nm.
# For the standard 256-band product this is bands 0–17 (712.3–998.8 nm).
_NIR_WINDOW_MAX_NM: float = 1000.0

# Warning category used so callers can filter it precisely.
class IIRSConversionWarning(UserWarning):
    pass


def iirs_to_pan(
    cube: np.ndarray,
    wavelengths_nm: Optional[np.ndarray] = None,
    nir_max_nm: float = _NIR_WINDOW_MAX_NM,
) -> np.ndarray:
    """
    Convert an IIRS hyperspectral cube to a single-band panchromatic proxy
    suitable for feature matching against OHRC or TMC-2 imagery.

    Input layout:
        (B, H, W)  — BSQ/band-first, as loaded from IIRS .qub via numpy
        (H, W, B)  — band-last (rasterio convention)
        (H, W)     — already 2-D; returned unchanged with a log message

    Band selection:
        Bands whose centre wavelength is ≤ ``nir_max_nm`` (default 1000 nm)
        are selected.  They are averaged with weights proportional to a
        Gaussian solar irradiance model centred at 700 nm (σ = 150 nm), which
        mimics how a silicon-detector panchromatic sensor responds to the
        solar spectrum.  This places highest weight on the 712–880 nm range,
        i.e., the red/NIR tail shared by OHRC and TMC-2.

        If the supplied wavelength vector (or the default IIRS_WAVELENGTHS_NM)
        has no bands within the NIR window, a warning is raised and a simple
        mean of all bands is returned as a fallback — better than silent failure.

    Args:
        cube:           Hyperspectral array with 3 dimensions (any band-axis
                        position) or a 2-D array (pass-through).
        wavelengths_nm: Band centre wavelengths in nm, length == number of
                        bands.  Defaults to IIRS_WAVELENGTHS_NM from the
                        sample product HDR.
        nir_max_nm:     Upper wavelength cut-off (nm) for band selection.
                        Default 1000 nm.  Raise to include more NIR bands;
                        lower to be more conservative.

    Returns:
        float32 2-D array (H × W) in the range [0, 1], ready for the same
        normalisation path as OHRC/TMC images.

    Raises:
        ValueError: if cube is not 2-D or 3-D.
    """
    if cube.ndim == 2:
        logger.debug("iirs_to_pan: received 2-D array, returning as-is")
        arr = cube.astype(np.float32)
        if arr.max() > 1.0:
            arr = arr / arr.max()
        return arr

    if cube.ndim != 3:
        raise ValueError(
            f"iirs_to_pan: expected a 2-D or 3-D array, got shape {cube.shape}"
        )

    # ------------------------------------------------------------------
    # Normalise to (B, H, W)
    # ------------------------------------------------------------------
    # Layout detection strategy:
    #   We know the number of spectral bands (from wavelengths_nm if supplied,
    #   otherwise we check whether any axis equals len(IIRS_WAVELENGTHS_NM)=256).
    #
    #   Rule 1: if axis 0 == expected_bands → BSQ (B, H, W)  [IIRS .qub native]
    #   Rule 2: if axis 2 == expected_bands → band-last (H, W, B)
    #   Rule 3: if both or neither match, compare to default 256-band count.
    #   Rule 4: fall back to min-axis as band axis, emit warning.
    b0, b1, b2 = cube.shape

    if wavelengths_nm is not None:
        expected_bands = len(wavelengths_nm)
    else:
        # Check if any axis matches the default IIRS band count
        expected_bands = len(IIRS_WAVELENGTHS_NM)  # 256

    if b0 == expected_bands and b0 != b2:
        # (B, H, W) — BSQ
        data = cube.astype(np.float32)
    elif b2 == expected_bands and b2 != b0:
        # (H, W, B) — band-last
        data = np.moveaxis(cube, -1, 0).astype(np.float32)  # → (B, H, W)
    elif b0 == expected_bands and b2 == expected_bands:
        # Genuinely ambiguous (cube has same extent on first and last axis)
        warnings.warn(
            f"iirs_to_pan: ambiguous array shape {cube.shape} — both axis 0 "
            f"and axis 2 equal expected band count {expected_bands}; "
            "assuming BSQ (B, H, W) because IIRS .qub uses BSQ interleave.",
            IIRSConversionWarning,
            stacklevel=2,
        )
        data = cube.astype(np.float32)
    else:
        # No axis matches the expected band count.
        # Fall back: use whichever axis is smallest as the band axis.
        min_ax = int(np.argmin([b0, b1, b2]))
        if min_ax != 0:
            data = np.moveaxis(cube, min_ax, 0).astype(np.float32)
        else:
            data = cube.astype(np.float32)
        warnings.warn(
            f"iirs_to_pan: no axis of shape {cube.shape} equals expected band "
            f"count {expected_bands}.  Treating axis {min_ax} (size "
            f"{cube.shape[min_ax]}) as the band axis.  Supply wavelengths_nm "
            "to override.",
            IIRSConversionWarning,
            stacklevel=2,
        )

    n_bands = data.shape[0]

    if wavelengths_nm is None:
        if n_bands == len(IIRS_WAVELENGTHS_NM):
            wl = IIRS_WAVELENGTHS_NM
        else:
            warnings.warn(
                f"iirs_to_pan: cube has {n_bands} bands but IIRS_WAVELENGTHS_NM "
                f"has {len(IIRS_WAVELENGTHS_NM)} entries and no wavelengths_nm "
                f"was supplied.  Falling back to a uniform mean across all bands.",
                IIRSConversionWarning,
                stacklevel=2,
            )
            pan = np.mean(data, axis=0)
            return _normalise(pan)
    else:
        wl = np.asarray(wavelengths_nm, dtype=np.float32)
        if len(wl) != n_bands:
            raise ValueError(
                f"iirs_to_pan: wavelengths_nm has {len(wl)} entries "
                f"but cube has {n_bands} bands."
            )

    # ------------------------------------------------------------------
    # Select NIR window (712–1000 nm) — the OHRC/TMC overlap region
    # ------------------------------------------------------------------
    nir_mask = wl <= nir_max_nm
    n_nir = int(np.sum(nir_mask))

    if n_nir == 0:
        warnings.warn(
            f"iirs_to_pan: no bands found with wavelength ≤ {nir_max_nm} nm "
            f"(range is {wl.min():.1f}–{wl.max():.1f} nm).  "
            "Using a uniform mean of all bands as a fallback.  "
            "The resulting proxy will NOT correlate well with OHRC/TMC imagery.",
            IIRSConversionWarning,
            stacklevel=2,
        )
        pan = np.mean(data, axis=0)
        return _normalise(pan)

    nir_bands = data[nir_mask]   # (n_nir, H, W)
    nir_wl = wl[nir_mask]       # (n_nir,)

    # ------------------------------------------------------------------
    # Solar-irradiance weights: Gaussian centred at 700 nm, σ = 150 nm.
    # This approximates the photon-count weighting of a silicon-detector
    # panchromatic sensor (OHRC/TMC use silicon CCD/TDI detectors).
    # All weight values are positive within 712–1000 nm but peak at 712 nm,
    # falling off toward 1000 nm — intentionally down-weighting the longer
    # NIR tail that has less overlap with the vis-pan channel.
    # ------------------------------------------------------------------
    solar_center_nm = 700.0
    solar_sigma_nm = 150.0
    weights = np.exp(-0.5 * ((nir_wl - solar_center_nm) / solar_sigma_nm) ** 2)
    weights = weights / weights.sum()          # normalise to sum = 1
    weights = weights.reshape(-1, 1, 1)        # (n_nir, 1, 1) for broadcasting

    pan = np.sum(nir_bands * weights, axis=0)  # (H, W)

    logger.info(
        f"iirs_to_pan: combined {n_nir} bands ({nir_wl.min():.0f}–"
        f"{nir_wl.max():.0f} nm) with solar-irradiance weighting"
    )

    return _normalise(pan)


def _normalise(arr: np.ndarray) -> np.ndarray:
    """Clip negative reflectance values and scale to [0, 1] float32."""
    arr = np.clip(arr, 0.0, None)
    maxval = arr.max()
    if maxval > 1e-6:
        arr = arr / maxval
    return arr.astype(np.float32)
