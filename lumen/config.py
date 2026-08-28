"""Configuration settings for the LUMEN project."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Pydantic settings class for LUMEN."""
    DATA_DIR: Path = Path("data")
    RAW_DIR: Path = Path("data/raw")
    DEM_DIR: Path = Path("data/dem")
    PROCESSED_DIR: Path = Path("data/processed")
    
    GPU_ENABLED: bool = True
    SUPERPOINT_WEIGHTS_PATH: Optional[str] = None
    LIGHTGLUE_WEIGHTS_PATH: Optional[str] = None
    
    DEFAULT_GSD: float = 5.0
    MAGSAC_CONFIDENCE: float = 0.999
    MAGSAC_MAX_ITERS: int = 5000
    GRID_SIZE: tuple[int, int] = (8, 8)
    PHASE_CORRELATION_UPSAMPLE_FACTOR: int = 100
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

config = Settings()
