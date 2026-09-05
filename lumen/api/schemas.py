from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

__all__ = [
    "SensorType",
    "RegistrationRequest",
    "RegistrationResponse",
    "JobStatus",
    "MatchPoint",
    "EvaluationMetrics",
    "SensorInfo",
    "PipelineOptions",
]

class SensorType(str, Enum):
    OHRC = "OHRC"
    TMC2 = "TMC2"
    IIRS = "IIRS"


class PipelineOptions(BaseModel):
    feature_method: str = Field(default="auto", description="Feature matching method: auto, deep, or rift2")
    photometric_model: str = Field(default="lommel_seeliger", description="Photometric model to use")
    grid_size: int = Field(default=32, ge=8, le=128)
    max_keypoints: int = Field(default=2048, ge=100)
    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    
    model_config = ConfigDict(extra="forbid")


class RegistrationRequest(BaseModel):
    source_sensor: SensorType
    reference_sensor: SensorType
    source_path: str
    reference_path: str
    options: Optional[PipelineOptions] = None
    
    model_config = ConfigDict(extra="ignore")


class RegistrationResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_time: float = Field(description="Estimated processing time in seconds")


class EvaluationMetrics(BaseModel):
    rmse: float
    rmse_x: float
    rmse_y: float
    inlier_ratio: float
    inlier_count: int
    total_matches: int
    ssim: float
    reprojection_error: float
    coverage_ratio: float


class JobStatus(BaseModel):
    status: str = Field(description="pending, processing, completed, or failed")
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    stage_name: str = ""
    metrics: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    source_image_url: Optional[str] = None
    reference_image_url: Optional[str] = None
    checkerboard_image_url: Optional[str] = None
    geotiff_url: Optional[str] = None
    match_points: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class MatchPoint(BaseModel):
    x_source: float
    y_source: float
    x_reference: float
    y_reference: float
    confidence: float
    is_inlier: bool


class SensorInfo(BaseModel):
    name: str
    gsd: float = Field(description="Ground Sample Distance in meters")
    spectral_range: str
    swath_width: float = Field(description="Swath width in km")
    description: str
