"""Pydantic schemas for the FastAPI service."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class RegistrationRequest(BaseModel):
    source_path: str = Field(..., description="Path to the source PDS4 XML label")
    reference_path: str = Field(..., description="Path to the reference PDS4 XML label")
    source_sensor: str = Field(..., description="Source sensor name (e.g., TMC2, OHRC)")
    ref_sensor: str = Field(..., description="Reference sensor name")
    options: Optional[Dict[str, Any]] = None

class RegistrationResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime

class EvaluationMetrics(BaseModel):
    rmse: Optional[float] = None
    rmse_x: Optional[float] = None
    rmse_y: Optional[float] = None
    inlier_ratio: Optional[float] = None
    inlier_count: Optional[int] = None
    ssim: Optional[float] = None
    reprojection_error: Optional[float] = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    metrics: Optional[EvaluationMetrics] = None
    error: Optional[str] = None

class MatchPoint(BaseModel):
    x_source: float
    y_source: float
    x_reference: float
    y_reference: float
    confidence: float
