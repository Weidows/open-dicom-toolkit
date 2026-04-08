# DICOM Agent Toolkit - End-to-End Demo

This demo shows how to use the DICOM Agent Toolkit for medical imaging analysis.

## Quick Start

### 1. CLI Usage

```bash
# Analyze a DICOM file
python -m src.cli analyze /path/to/dicom.dcm -i "检测斑块并测量大小"

# Output workflow as YAML
python -m src.cli analyze /path/to/dicom.dcm -y

# Use custom ONNX model
python -m src.cli analyze /path/to/dicom.dcm -m models/plaque_detector.onnx
```

### 2. Python API

```python
from src.planner import PlanningAgent
from src.executor import execute_workflow

# Plan
agent = PlanningAgent({})
workflow = agent.plan("分析这个超声病例，找出斑块")

# Execute
result = execute_workflow(workflow, {
    "path": "/data/patient_scan.dcm",
    "model_path": "models/plaque_detector.onnx"
})

print(result["report"])
```

### 3. REST API Server

```bash
# Start server
python -m src.server

# Or with Docker
docker-compose up -d
```

API endpoints:

- `GET /` - API info
- `GET /health` - Health check
- `GET /operators` - List available operators
- `POST /plan` - Generate workflow from instruction
- `POST /analyze` - Analyze DICOM file (multipart/form-data)

### 4. Python Client

```python
import requests

# Upload and analyze
with open("scan.dcm", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze",
        files={"file": f},
        data={"instruction": "检测颈动脉斑块"}
    )

result = response.json()
print(result["report"])
```

## Docker Compose

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Services:

- `orthanc` - DICOM server on port 8042
- `api` - Analysis API on port 8000