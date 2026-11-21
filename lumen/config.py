import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings"]


class SensorConfig(BaseSettings):
    gsd: float = 1.0
    spectral_range: str = "visible"
    swath_width: float = 10.0


class Settings(BaseSettings):
    """Global configuration settings for LUMEN."""
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Paths
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")
    CACHE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / ".cache")
    
    # Pipeline Settings
    PIPELINE_TIMEOUT: int = Field(default=3600, description="Pipeline timeout in seconds")
    
    # Sensor configs
    SENSORS: Dict[str, SensorConfig] = Field(default_factory=dict)

    # Every field can be overridden with a LUMEN_-prefixed environment variable,
    # e.g. LUMEN_LOG_LEVEL=DEBUG or LUMEN_DATA_DIR=D:/lunar-data.
    # (pydantic v2 ignores the old Field(env=...) form, so overrides never worked.)
    model_config = SettingsConfigDict(
        env_prefix="LUMEN_",
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
