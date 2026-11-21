import argparse
import sys
import logging

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    has_rich = True
except ImportError:
    has_rich = False

from lumen.pipeline.orchestrator import RegistrationPipeline, PipelineStage
from lumen.config import get_settings

__all__ = ["main"]

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s" if not has_rich else "%(message)s"
    )

def cmd_register(args):
    settings = get_settings()
    console = Console() if has_rich else None

    src_path = args.source or args.source_flag
    ref_path = args.reference or args.reference_flag
    if not src_path or not ref_path:
        msg = "Error: Both source and reference image paths must be provided."
        if console:
            console.print(f"[bold red]{msg}[/bold red]")
        else:
            print(msg)
        sys.exit(1)

    def infer_sensor(p_str: str, default: str) -> str:
        s = str(p_str).lower()
        if "tmc" in s:
            return "TMC2"
        if "ohr" in s:
            return "OHRC"
        if "iir" in s:
            return "IIRS"
        if "selene" in s or "tco_map" in s or s.endswith(".lbl"):
            return "SELENE_TC"
        if "lroc" in s or "nac" in s or "m1418" in s:
            return "LROC_NAC"
        return default

    src_sensor = args.source_sensor or infer_sensor(src_path, "TMC2")
    ref_sensor = args.ref_sensor or infer_sensor(ref_path, "TMC2")
    
    if console:
        console.print(f"[bold blue]LUMEN Registration[/bold blue]: {src_path} ({src_sensor}) -> {ref_path} ({ref_sensor})")
    else:
        print(f"LUMEN Registration: {src_path} ({src_sensor}) -> {ref_path} ({ref_sensor})")
        
    class CLICallback:
        def __init__(self, progress):
            self.progress = progress
            self.task_id = None
            
        def on_stage_start(self, stage: PipelineStage, message: str) -> None:
            if self.progress:
                if self.task_id is not None:
                    self.progress.remove_task(self.task_id)
                self.task_id = self.progress.add_task(f"[green]{stage.name}:[/green] {message}", total=100)
            else:
                print(f"Starting {stage.name}: {message}")

        def on_stage_complete(self, stage: PipelineStage, metrics=None) -> None:
            if self.progress and self.task_id is not None:
                self.progress.update(self.task_id, completed=100)
            else:
                print(f"Completed {stage.name}")

        def on_progress(self, stage: PipelineStage, pct: float, message: str) -> None:
            if self.progress and self.task_id is not None:
                self.progress.update(self.task_id, completed=pct, description=f"[green]{stage.name}:[/green] {message}")

    options = {
        "feature_method": args.method,
        "photometric_method": getattr(args, "photometric_method", "auto"),
    }
    
    if has_rich:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            callback = CLICallback(progress)
            pipeline = RegistrationPipeline(config=settings, callback=callback)
            try:
                result = pipeline.run(
                    source_path=src_path,
                    reference_path=ref_path,
                    source_sensor=src_sensor,
                    ref_sensor=ref_sensor,
                    options=options
                )
                console.print("[bold green]Registration converged.[/bold green]")
                console.print(_format_metrics(result))
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                sys.exit(1)
    else:
        callback = CLICallback(None)
        pipeline = RegistrationPipeline(config=settings, callback=callback)
        try:
            result = pipeline.run(
                source_path=src_path,
                reference_path=ref_path,
                source_sensor=src_sensor,
                ref_sensor=ref_sensor,
                options=options
            )
            print("Registration converged.")
            print(_format_metrics(result))
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


def cmd_serve(args):
    import uvicorn
    print(f"Starting LUMEN server on {args.host}:{args.port}...")
    uvicorn.run("lumen.api.server:app", host=args.host, port=args.port, reload=args.reload)


def cmd_info(args):
    print("LUMEN - Lunar Multi-Sensor Registration")
    print("Supported Sensors: OHRC, TMC2, IIRS, SELENE_TC, LROC_NAC")
    print("Available Matchers: SuperPoint+LightGlue, RIFT2, SIFT")


def _format_metrics(result) -> str:
    m = result.metrics
    lines = [
        f"  matches          : {m.get('inlier_count', 0)} inliers / {m.get('total_matches', 0)} candidates"
        f" ({100 * m.get('inlier_ratio', 0.0):.1f}%)",
        f"  fit residual RMSE: {m['rmse']:.3f} px" if "rmse" in m else "  fit residual RMSE: n/a",
    ]
    if "checkpoint_rmse" in m:
        lines.append(
            f"  checkpoint RMSE  : {m['checkpoint_rmse']:.3f} px on {m['checkpoint_count']} held-out points"
        )
    lines.append(f"  SSIM             : {m.get('ssim', float('nan')):.4f}")
    lines.append(f"  runtime          : {result.elapsed_seconds:.1f} s")
    return "\n".join(lines)


def _load_gray(path: str):
    import numpy as np
    from pathlib import Path

    p = Path(path)
    if p.suffix.lower() in (".tif", ".tiff"):
        import rasterio

        with rasterio.open(p) as ds:
            return ds.read(1).astype(np.float32)
    import cv2

    img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {p}")
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img.astype(np.float32)


def cmd_evaluate(args):
    """Compare an already-warped image with its reference (same pixel grid)."""
    import numpy as np
    from lumen.evaluation.metrics import compute_ssim

    warped = _load_gray(args.warped)
    reference = _load_gray(args.reference)
    if warped.shape != reference.shape:
        print(f"Error: shapes differ {warped.shape} vs {reference.shape}; "
              "evaluate expects the warped image on the reference grid.")
        sys.exit(1)

    valid = (warped != 0) & (reference != 0)  # ignore warp no-data borders
    if valid.sum() < 100:
        print("Error: fewer than 100 overlapping valid pixels.")
        sys.exit(1)
    a = warped[valid] - warped[valid].mean()
    b = reference[valid] - reference[valid].mean()
    ncc = float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-12))

    print(f"Evaluating {args.warped} against {args.reference}")
    print(f"  valid overlap : {100 * valid.mean():.1f}% of pixels")
    print(f"  SSIM          : {compute_ssim(warped, reference):.4f}")
    print(f"  NCC           : {ncc:.4f}")


def main():
    parser = argparse.ArgumentParser(description="LUMEN Command Line Interface")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Run image registration")
    register_parser.add_argument("source", nargs="?", default=None, help="Path to source image (to be warped)")
    register_parser.add_argument("reference", nargs="?", default=None, help="Path to reference image")
    register_parser.add_argument("--source", dest="source_flag", default=None, help="Path to source image")
    register_parser.add_argument("--reference", dest="reference_flag", default=None, help="Path to reference image")
    register_parser.add_argument("--source-sensor", choices=["OHRC", "TMC2", "IIRS", "SELENE_TC", "LROC_NAC"], default=None, help="Source sensor")
    register_parser.add_argument("--ref-sensor", choices=["OHRC", "TMC2", "IIRS", "SELENE_TC", "LROC_NAC"], default=None, help="Reference sensor")
    register_parser.add_argument("--method", default="auto", choices=["auto", "deep", "rift2", "sift"])
    register_parser.add_argument("--photometric-method", default="auto", choices=["auto", "lommel_seeliger", "minnaert", "none"])
    register_parser.set_defaults(func=cmd_register)
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes (development)")
    serve_parser.set_defaults(func=cmd_serve)
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show system info")
    info_parser.set_defaults(func=cmd_info)
    
    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate pre-registered pair")
    eval_parser.add_argument("warped", help="Path to warped image")
    eval_parser.add_argument("reference", help="Path to reference image")
    eval_parser.set_defaults(func=cmd_evaluate)
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    args.func(args)

if __name__ == "__main__":
    main()
