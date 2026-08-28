import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

__all__ = ["Settings", "get_settings"]


class SensorConfig(BaseSettings):
    gsd: float = 1.0
    spectral_range: str = "visible"
    swath_width: float = 10.0


class Settings(BaseSettings):
    """Global configuration settings for LUMEN."""
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LUMEN_LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LUMEN_LOG_FORMAT"
    )
    
    # Paths
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")
    CACHE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / ".cache")
    
    # Pipeline Settings
    PIPELINE_TIMEOUT: int = Field(default=3600, description="Pipeline timeout in seconds")
    
    # Sensor configs
    SENSORS: Dict[str, SensorConfig] = Field(default_factory=dict)

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @classmethod
    def load_from_yaml(cls, path: str) -> "Settings":
        """Load additional settings from a YAML file."""
        if not os.path.exists(path):
            return cls()
            
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        # Merge YAML data into settings
        # In a real scenario, deeper merge logic might be required
        return cls(**data)


_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        yaml_path = os.environ.get("LUMEN_CONFIG_PATH", "config.yaml")
        if os.path.exists(yaml_path):
            _settings_instance = Settings.load_from_yaml(yaml_path)
        else:
            _settings_instance = Settings()
    return _settings_instance
