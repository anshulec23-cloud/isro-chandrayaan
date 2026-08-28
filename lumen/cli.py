"""Command Line Interface for LUMEN."""

import argparse
import uvicorn
from pathlib import Path
from lumen.config import config
from lumen.pipeline.orchestrator import RegistrationPipeline

def serve(args):
    """Start the API server."""
    uvicorn.run("lumen.api.server:app", host=args.host, port=args.port, reload=True)

def register(args):
    """Run registration from CLI."""
    print(f"Registering {args.source} to {args.reference}...")
    pipeline = RegistrationPipeline(config)
    result = pipeline.run(Path(args.source), Path(args.reference), 
                          args.source_sensor, args.ref_sensor)
    print("Registration completed.")
    print(f"Metrics: {result.metrics}")

def main():
    parser = argparse.ArgumentParser(description="LUMEN - Lunar Multi-modal Engagement Network")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI server")
    serve_parser.add_argument("--host", default=config.API_HOST, help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=config.API_PORT, help="Port to bind to")

    # register command
    reg_parser = subparsers.add_parser("register", help="Run image registration pipeline")
    reg_parser.add_argument("--source", required=True, help="Path to source PDS4 label")
    reg_parser.add_argument("--reference", required=True, help="Path to reference PDS4 label")
    reg_parser.add_argument("--source-sensor", required=True, help="Source sensor (e.g. TMC2)")
    reg_parser.add_argument("--ref-sensor", required=True, help="Reference sensor")
    reg_parser.add_argument("--output", help="Path to save output")

    args = parser.parse_args()

    if args.command == "serve":
        serve(args)
    elif args.command == "register":
        register(args)

if __name__ == "__main__":
    main()
