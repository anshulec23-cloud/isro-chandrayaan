"""
Interactive Manual Checkpoint / Tie-Point Picker for LUMEN.

Allows users to click corresponding points on two side-by-side displayed images
and saves the pixel coordinate pairs to a JSON file for held-out validation.

Usage:
    python notebooks/point_picker.py \
        --source data/raw/ch2_ohr.../ch2_ohr.xml \
        --reference data/raw/ch2_tmc.../ch2_tmc.xml \
        --output checkpoints.json

Controls:
    - Left Click on Left Image (Source): Set source tie-point coordinate.
    - Left Click on Right Image (Reference): Set corresponding reference coordinate.
    - Press 'u' or Backspace: Undo last point.
    - Press 's' or Enter: Save recorded points to JSON.
    - Press 'c': Clear all points.
    - Press 'q' or Esc: Quit / Finish.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lumen.ingest.pds4_parser import load_binary_image, parse_pds4
from lumen.features.iirs_pan import iirs_to_pan

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("point_picker")


def load_image_any(path: Union[str, Path]) -> np.ndarray:
    """Load image from PDS4 XML, GeoTIFF, or standard image format."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    # 1. PDS4 XML
    if p.suffix.lower() == ".xml":
        img = load_binary_image(p)
        if img.ndim == 3 and (img.shape[0] > 3 or img.shape[-1] > 3):
            img = iirs_to_pan(img)
        return img

    # 2. Rasterio / GeoTIFF
    try:
        import rasterio
        with rasterio.open(p) as src:
            data = src.read()
            if data.ndim == 3 and data.shape[0] > 1:
                if data.shape[0] > 3:
                    return iirs_to_pan(data)
                return np.mean(data, axis=0).astype(np.float32)
            elif data.ndim == 3:
                return data[0].astype(np.float32)
            return data.astype(np.float32)
    except Exception:
        pass

    # 3. OpenCV / PIL
    import cv2
    img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if img is not None:
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img.astype(np.float32)

    raise ValueError(f"Could not load image from {p}")


def normalize_display(img: np.ndarray) -> np.ndarray:
    """Normalize image array for high-contrast grayscale visualization."""
    arr = img.astype(np.float32)
    p2, p98 = np.percentile(arr[np.isfinite(arr)], (2, 98))
    if p98 > p2:
        arr = np.clip((arr - p2) / (p98 - p2), 0.0, 1.0)
    else:
        maxval = np.max(arr)
        if maxval > 0:
            arr = arr / maxval
    return arr


class ManualPointPicker:
    """Interactive GUI for selecting corresponding checkpoint pairs."""

    def __init__(
        self,
        source_img: np.ndarray,
        reference_img: np.ndarray,
        source_path: str = "source",
        reference_path: str = "reference",
        output_path: str = "checkpoints.json",
    ):
        self.source_img = source_img
        self.ref_img = reference_img
        self.source_path = source_path
        self.ref_path = reference_path
        self.output_path = Path(output_path)

        # Coordinate storage: list of (x, y) floats
        self.pts_src: List[Tuple[float, float]] = []
        self.pts_ref: List[Tuple[float, float]] = []

        # Current state: waiting for 'source' or 'reference' click
        self.pending_src_pt: Optional[Tuple[float, float]] = None

        # Plot artist handles for updating
        self.src_artists: List[Any] = []
        self.ref_artists: List[Any] = []

        self._setup_figure()

    def _setup_figure(self):
        self.fig, (self.ax_src, self.ax_ref) = plt.subplots(
            1, 2, figsize=(14, 8), sharex=False, sharey=False
        )
        self.fig.canvas.manager.set_window_title("LUMEN Manual Checkpoint Picker")

        # Display normalized images
        self.disp_src = normalize_display(self.source_img)
        self.disp_ref = normalize_display(self.ref_img)

        self.ax_src.imshow(self.disp_src, cmap="gray", origin="upper")
        self.ax_src.set_title(f"SOURCE (Image 1)\n{Path(self.source_path).name}", fontsize=11, fontweight="bold")
        self.ax_src.axis("on")

        self.ax_ref.imshow(self.disp_ref, cmap="gray", origin="upper")
        self.ax_ref.set_title(f"REFERENCE (Image 2)\n{Path(self.ref_path).name}", fontsize=11, fontweight="bold")
        self.ax_ref.axis("on")

        self.status_text = self.fig.suptitle(
            "CLICK #1: Select feature on SOURCE image (Left)",
            fontsize=12,
            fontweight="bold",
            color="navy",
        )

        plt.subplots_adjust(bottom=0.15)

        # Add Save & Undo & Clear buttons at bottom
        ax_save = plt.axes([0.70, 0.03, 0.12, 0.06])
        self.btn_save = Button(ax_save, "Save JSON", color="#d4edda", hovercolor="#c3e6cb")
        self.btn_save.on_clicked(lambda event: self.save_checkpoints())

        ax_undo = plt.axes([0.55, 0.03, 0.12, 0.06])
        self.btn_undo = Button(ax_undo, "Undo (u)", color="#fff3cd", hovercolor="#ffeeba")
        self.btn_undo.on_clicked(lambda event: self.undo_last_point())

        ax_clear = plt.axes([0.40, 0.03, 0.12, 0.06])
        self.btn_clear = Button(ax_clear, "Clear All", color="#f8d7da", hovercolor="#f5c6cb")
        self.btn_clear.on_clicked(lambda event: self.clear_all_points())

        # Connect event handlers
        self.cid_click = self.fig.canvas.mpl_connect("button_press_event", self.on_click)
        self.cid_key = self.fig.canvas.mpl_connect("key_press_event", self.on_key)

    def on_click(self, event):
        if event.inaxes not in (self.ax_src, self.ax_ref):
            return

        if event.button != 1:  # Left click only
            return

        x, y = float(event.xdata), float(event.ydata)

        if event.inaxes == self.ax_src:
            if self.pending_src_pt is not None:
                # User re-clicked source before clicking reference: update source point
                self._remove_last_src_artist()

            self.pending_src_pt = (x, y)
            idx = len(self.pts_src) + 1
            h_pt = self.ax_src.plot(x, y, marker="x", color="cyan", markersize=10, markeredgewidth=2)[0]
            h_txt = self.ax_src.text(x + 5, y - 5, f"#{idx}", color="yellow", fontsize=10, fontweight="bold")
            self.src_artists.append((h_pt, h_txt))
            self.fig.canvas.draw_idle()

            self.status_text.set_text(f"CLICK #{idx}: Now click matching feature on REFERENCE image (Right)")
            self.status_text.set_color("darkred")
            self.fig.canvas.draw_idle()

        elif event.inaxes == self.ax_ref:
            if self.pending_src_pt is None:
                self.status_text.set_text("Please click SOURCE image (Left) first before clicking Reference.")
                self.status_text.set_color("red")
                self.fig.canvas.draw_idle()
                return

            self.pts_src.append(self.pending_src_pt)
            self.pts_ref.append((x, y))
            self.pending_src_pt = None

            idx = len(self.pts_src)
            h_pt = self.ax_ref.plot(x, y, marker="x", color="magenta", markersize=10, markeredgewidth=2)[0]
            h_txt = self.ax_ref.text(x + 5, y - 5, f"#{idx}", color="yellow", fontsize=10, fontweight="bold")
            self.ref_artists.append((h_pt, h_txt))

            logger.info(f"Recorded checkpoint #{idx}: Src({self.pts_src[-1][0]:.2f}, {self.pts_src[-1][1]:.2f}) -> Ref({x:.2f}, {y:.2f})")

            self.status_text.set_text(
                f"Pair #{idx} recorded! Total pairs: {idx}. Click next feature on SOURCE image (or Save)."
            )
            self.status_text.set_color("green")
            self.fig.canvas.draw_idle()

    def _remove_last_src_artist(self):
        if self.src_artists and len(self.src_artists) > len(self.pts_src):
            h_pt, h_txt = self.src_artists.pop()
            h_pt.remove()
            h_txt.remove()

    def undo_last_point(self):
        if self.pending_src_pt is not None:
            self.pending_src_pt = None
            self._remove_last_src_artist()
            self.status_text.set_text(f"Cancelled pending point. Total pairs: {len(self.pts_src)}")
            self.fig.canvas.draw_idle()
            return

        if len(self.pts_src) > 0:
            p_src = self.pts_src.pop()
            p_ref = self.pts_ref.pop()
            if self.src_artists:
                h_pt, h_txt = self.src_artists.pop()
                h_pt.remove()
                h_txt.remove()
            if self.ref_artists:
                h_pt, h_txt = self.ref_artists.pop()
                h_pt.remove()
                h_txt.remove()

            logger.info(f"Removed checkpoint pair ({p_src} -> {p_ref})")
            self.status_text.set_text(f"Undid pair #{len(self.pts_src) + 1}. Total pairs: {len(self.pts_src)}")
            self.status_text.set_color("navy")
            self.fig.canvas.draw_idle()

    def clear_all_points(self):
        self.pts_src.clear()
        self.pts_ref.clear()
        self.pending_src_pt = None
        for h_pt, h_txt in self.src_artists:
            h_pt.remove()
            h_txt.remove()
        for h_pt, h_txt in self.ref_artists:
            h_pt.remove()
            h_txt.remove()
        self.src_artists.clear()
        self.ref_artists.clear()
        self.status_text.set_text("Cleared all checkpoints. CLICK #1: Select on SOURCE image")
        self.status_text.set_color("navy")
        self.fig.canvas.draw_idle()

    def on_key(self, event):
        if event.key in ("u", "backspace"):
            self.undo_last_point()
        elif event.key in ("s", "enter"):
            self.save_checkpoints()
        elif event.key == "c":
            self.clear_all_points()
        elif event.key in ("q", "escape"):
            if len(self.pts_src) > 0:
                self.save_checkpoints()
            plt.close(self.fig)

    def save_checkpoints(self) -> str:
        """Save recorded tie points to standard JSON format."""
        if len(self.pts_src) == 0:
            logger.warning("No checkpoint pairs recorded yet to save.")
            self.status_text.set_text("Cannot save: No pairs recorded yet.")
            self.status_text.set_color("red")
            self.fig.canvas.draw_idle()
            return ""

        pairs_list = []
        for i, (p0, p1) in enumerate(zip(self.pts_src, self.pts_ref), start=1):
            pairs_list.append({
                "id": i,
                "source": [float(p0[0]), float(p0[1])],
                "reference": [float(p1[0]), float(p1[1])],
            })

        output_data = {
            "source_path": str(self.source_path),
            "reference_path": str(self.ref_path),
            "num_checkpoints": len(pairs_list),
            "pts_src": [[float(p[0]), float(p[1])] for p in self.pts_src],
            "pts_ref": [[float(p[0]), float(p[1])] for p in self.pts_ref],
            "pairs": pairs_list,
        }

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        msg = f"Saved {len(pairs_list)} checkpoint pairs to {self.output_path}"
        logger.info(msg)
        self.status_text.set_text(f"SUCCESS: {msg}")
        self.status_text.set_color("darkgreen")
        self.fig.canvas.draw_idle()
        return str(self.output_path)

    def show(self):
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Manual Checkpoint / Tie-Point Picker for LUMEN")
    parser.add_argument("--source", "-s", required=True, help="Path to source image or PDS4 XML")
    parser.add_argument("--reference", "-r", required=True, help="Path to reference image or PDS4 XML")
    parser.add_argument("--output", "-o", default="checkpoints.json", help="Path to output JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("  LUMEN Interactive Manual Checkpoint Picker")
    print("=" * 60)
    print(f"  Source:    {args.source}")
    print(f"  Reference: {args.reference}")
    print(f"  Output:    {args.output}")
    print("\nInstructions:")
    print("  1. Click a landmark on SOURCE (left) image.")
    print("  2. Click the matching landmark on REFERENCE (right) image.")
    print("  3. Repeat for 15-30 well-distributed landmarks across the overlap.")
    print("  4. Press 's' or click Save JSON to write the coordinates.")
    print("  5. Press 'u' to undo the last point.\n")

    src_img = load_image_any(args.source)
    ref_img = load_image_any(args.reference)

    picker = ManualPointPicker(
        source_img=src_img,
        reference_img=ref_img,
        source_path=args.source,
        reference_path=args.reference,
        output_path=args.output,
    )
    picker.show()


if __name__ == "__main__":
    main()
