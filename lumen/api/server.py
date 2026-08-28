import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from lumen.api.schemas import RegistrationRequest, RegistrationResponse, JobStatus, EvaluationMetrics
from lumen.pipeline.orchestrator import RegistrationPipeline, PipelineStage
from lumen.config import get_settings

logger = logging.getLogger(__name__)

__all__ = ["app"]

# Job state management
jobs: Dict[str, Dict[str, Any]] = {}
thread_pool = ThreadPoolExecutor(max_workers=4)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for application startup and shutdown."""
    logger.info("Starting LUMEN API server...")
    # Initialize global resources, model cache, etc.
    yield
    logger.info("Shutting down LUMEN API server...")
    thread_pool.shutdown(wait=True)


app = FastAPI(
    title="LUMEN API",
    description="Lunar Multi-Sensor Registration API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the static dashboard
import os
dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dashboard")
if os.path.exists(dashboard_path):
    app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")

# Custom Middleware for Request ID Tracking could go here.

class WebhookCallback:
    def __init__(self, job_id: str):
        self.job_id = job_id
        
    def on_stage_start(self, stage: PipelineStage, message: str) -> None:
        if self.job_id in jobs:
            jobs[self.job_id]["stage"] = stage.name
            jobs[self.job_id]["message"] = message

    def on_stage_complete(self, stage: PipelineStage, metrics: Dict[str, Any] = None) -> None:
        if self.job_id in jobs:
            if metrics:
                jobs[self.job_id].setdefault("metrics", {}).update(metrics)

    def on_progress(self, stage: PipelineStage, progress: float, message: str) -> None:
        if self.job_id in jobs:
            jobs[self.job_id]["progress"] = progress
            jobs[self.job_id]["message"] = message


def run_registration_task(job_id: str, req: RegistrationRequest):
    """Background task to run registration."""
    try:
        jobs[job_id]["status"] = "processing"
        settings = get_settings()
        pipeline = RegistrationPipeline(config=settings, callback=WebhookCallback(job_id))
        
        # Use actual paths
        from pathlib import Path
        result = pipeline.run(
            source_path=Path(req.source_path),
            reference_path=Path(req.reference_path),
            source_sensor=req.source_sensor,
            ref_sensor=req.reference_sensor,
            dem_path=None,
            options=req.options.model_dump() if req.options else None
        )
        
        # Save output image to serve it
        output_dir = Path("dashboard/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        out_filename = f"{job_id}.jpg"
        out_path = output_dir / out_filename
        
        import cv2
        import numpy as np
        # Normalize and save the image
        img_out = result.registered_image
        if img_out.dtype != np.uint8:
            img_out = np.clip(img_out * 255.0, 0, 255).astype(np.uint8)
        cv2.imwrite(str(out_path), img_out)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result_metrics"] = result.metrics
        jobs[job_id]["image_url"] = f"/dashboard/outputs/{out_filename}"
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.post("/api/v1/register", response_model=RegistrationResponse)
async def create_registration_job(request: RegistrationRequest, background_tasks: BackgroundTasks):
    """Create a new registration job."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "stage": "INIT",
        "message": "Job created",
    }
    
    # Run in thread pool to not block async loop if it's CPU bound
    background_tasks.add_task(run_registration_task, job_id, request)
    
    return RegistrationResponse(
        job_id=job_id,
        status="pending",
        estimated_time=120.0
    )


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a specific job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return JobStatus(
        status=job["status"],
        progress=job.get("progress", 0.0),
        stage_name=job.get("stage", ""),
        metrics=job.get("result_metrics"),
        image_url=job.get("image_url")
    )


@app.websocket("/api/v1/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket for real-time updates."""
    await websocket.accept()
    if job_id not in jobs:
        await websocket.send_json({"error": "Job not found"})
        await websocket.close()
        return

    try:
        while True:
            job = jobs[job_id]
            await websocket.send_json({
                "status": job["status"],
                "progress": job.get("progress", 0.0),
                "stage": job.get("stage", ""),
                "message": job.get("message", "")
            })
            if job["status"] in ("completed", "failed"):
                break
            import asyncio
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload endpoint for PDS4 files."""
    # In production, save to persistent storage safely
    return {"filename": file.filename, "size": file.size}


@app.get("/health")
async def health_check():
    """Health check endpoint including GPU status mock."""
    return {"status": "healthy", "gpu": "available"}


if __name__ == "__main__":
    uvicorn.run("lumen.api.server:app", host="0.0.0.0", port=8000, reload=True)
