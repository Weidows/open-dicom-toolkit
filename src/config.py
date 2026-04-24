"""Application configuration."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
  """Server configuration."""

  model_config = SettingsConfigDict(
    env_prefix="DICOM_",
    env_nested_delimiter="__",
    extra="ignore",
  )

  host: str = "0.0.0.0"
  port: int = 8000
  reload: bool = False

  # UI
  enable_ui: bool = True
  ui_title: str = "DICOM Agent Toolkit"
  ui_path: str = "/ui"

  # Paths
  model_path: Optional[str] = None
  upload_dir: str = "./uploads"
  output_dir: str = "./output"

  # Logging
  log_level: str = "INFO"

  # Features
  enable_radar: bool = True


def load_config(config_path: Optional[str] = None) -> ServerConfig:
  """Load configuration from YAML file and environment variables.

  Environment variables override file values.
  Example: DICOM_HOST=127.0.0.1 DICOM_PORT=9000

  Args:
    config_path: Path to YAML config file. If None, searches for
      config.yaml or config.yml in the current directory.

  Returns:
    ServerConfig instance.
  """
  if config_path is None:
    candidates = ["config.yaml", "config.yml"]
    for candidate in candidates:
      if os.path.exists(candidate):
        config_path = candidate
        break

  file_values: dict = {}
  if config_path and os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
      file_values = yaml.safe_load(f) or {}

  # Environment variables override file values.
  # Only pass file values for keys not present in env.
  filtered = {
    k: v
    for k, v in file_values.items()
    if f"DICOM_{k.upper()}" not in os.environ
  }

  return ServerConfig(**filtered)
