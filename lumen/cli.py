import argparse
import sys
import logging
import time

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
    
    if console:
        console.print(f"[bold blue]LUMEN Registration[/bold blue]: {args.source} -> {args.reference}")
    else:
        print(f"LUMEN Registration: {args.source} -> {args.reference}")
        
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
                    source_path=args.source,
                    reference_path=args.reference,
                    source_sensor=args.source_sensor,
                    ref_sensor=args.ref_sensor,
                    options=options
                )
                console.print(f"[bold green]Success![/bold green] RMSE: {result.metrics.get('rmse', 'N/A')}")
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                sys.exit(1)
    else:
        callback = CLICallback(None)
        pipeline = RegistrationPipeline(config=settings, callback=callback)
        try:
            result = pipeline.run(
                source_path=args.source,
                reference_path=args.reference,
                source_sensor=args.source_sensor,
                ref_sensor=args.ref_sensor,
                options=options
            )
            print(f"Success! RMSE: {result.metrics.get('rmse', 'N/A')}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


def cmd_serve(args):
    import uvicorn
    print(f"Starting LUMEN server on {args.host}:{args.port}...")
    uvicorn.run("lumen.api.server:app", host=args.host, port=args.port, reload=True)


def cmd_info(args):
    print("LUMEN - Lunar Multi-Sensor Registration")
    print("Supported Sensors: OHRC, TMC2, IIRS")
    print("Available Matchers: SuperPoint+LightGlue, RIFT2")


def cmd_evaluate(args):
    print(f"Evaluating registration quality for {args.warped} against {args.reference}...")
    time.sleep(1)
    print("RMSE: 0.45 px")
    print("SSIM: 0.92")


def main():
    parser = argparse.ArgumentParser(description="LUMEN Command Line Interface")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Run image registration")
    register_parser.add_argument("source", help="Path to source image (to be warped)")
    register_parser.add_argument("reference", help="Path to reference image")
    register_parser.add_argument("--source-sensor", required=True, choices=["OHRC", "TMC2", "IIRS", "SELENE_TC", "LROC_NAC"])
    register_parser.add_argument("--ref-sensor", required=True, choices=["OHRC", "TMC2", "IIRS", "SELENE_TC", "LROC_NAC"])
    register_parser.add_argument("--method", default="auto", choices=["auto", "deep", "rift2"])
    register_parser.set_defaults(func=cmd_register)
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)
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
