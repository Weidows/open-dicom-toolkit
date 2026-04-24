"""Unified entry point for DICOM Agent Toolkit.

Launch with:
  uv run python src/main.py

Override config with environment variables:
  DICOM_HOST=127.0.0.1 DICOM_PORT=9000 uv run python src/main.py
"""

import logging
import os
import sys
from pathlib import Path

# When run directly as a script, ensure project root is on PYTHONPATH
if __name__ == "__main__" and (__package__ is None or __package__ == ""):
  _project_root = Path(__file__).resolve().parent.parent
  if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import uvicorn

from src.config import load_config
from src.server import create_app


def main() -> None:
  """Main entry point."""
  config_path = os.environ.get("CONFIG_PATH")
  config = load_config(config_path)

  # Setup logging
  logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
  )
  logger = logging.getLogger(__name__)

  logger.info("Starting DICOM Agent Toolkit")
  logger.info("Config loaded: host=%s port=%s ui=%s", config.host, config.port, config.enable_ui)

  # Ensure directories exist
  os.makedirs(config.upload_dir, exist_ok=True)
  os.makedirs(config.output_dir, exist_ok=True)

  app = create_app(config)

  uvicorn.run(
    app,
    host=config.host,
    port=config.port,
    reload=config.reload,
  )


if __name__ == "__main__":
  main()
