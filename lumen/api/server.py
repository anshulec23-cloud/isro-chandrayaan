"""FastAPI application for LUMEN."""

import uuid
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from lumen.api.schemas import RegistrationRequest, RegistrationResponse, JobStatus, MatchPoint
from lumen.pipeline.orchestrator import RegistrationPipeline
from lumen.config import config

# Store jobs in memory for demonstration
jobs_db: Dict[str, Any] = {}

app = FastAPI(title="LUMEN API", description="Lunar Multi-modal Engagement Network")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = None

@app.on_event("startup")
async def startup_event():
    global pipeline
    # Lifespan for GPU model loading
    pipeline = RegistrationPipeline(config)

@app.post("/api/v1/register", response_model=RegistrationResponse)
async def register_images(req: RegistrationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs_db[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "created_at": datetime.now(),
        "request": req
    }
    
    # Normally this would be a celery task or similar
    def run_job(j_id: str):
        jobs_db[j_id]["status"] = "processing"
        try:
            # Mock pipeline execution
            jobs_db[j_id]["status"] = "completed"
            jobs_db[j_id]["progress"] = 1.0
        except Exception as e:
            jobs_db[j_id]["status"] = "failed"
            jobs_db[j_id]["error"] = str(e)

    background_tasks.add_task(run_job, job_id)
    
    return RegistrationResponse(
        job_id=job_id,
        status="pending",
        created_at=jobs_db[job_id]["created_at"]
    )

@app.get("/api/v1/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(job_id=job_id, **jobs_db[job_id])

@app.get("/api/v1/jobs/{job_id}/matches")
async def get_matches(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"matches": []}

@app.get("/api/v1/jobs/{job_id}/metrics")
async def get_metrics(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"metrics": {}}

@app.get("/api/v1/sensors")
async def list_sensors():
    return {"sensors": ["OHRC", "TMC2", "IIRS"]}

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}
