# DICOM Agent Toolkit

AI Agent-driven DICOM medical imaging analysis toolkit.

## Quick Start

```python
from src.planner import PlanningAgent
from src.executor import execute_workflow

# 1. Plan - Convert natural language to workflow
agent = PlanningAgent({})
workflow = agent.plan("分析这个超声病例，找出肿块并测量最大径")

# 2. Execute - Run the workflow
result = execute_workflow(workflow, {"path": "/data/scan.dcm"})

# 3. Get results
print(result["report"])
```

## Installation

```bash
pip install -e .
```

## Usage

### CLI

```bash
# Analyze a DICOM file
python -m src.cli analyze /path/to/dicom.dcm -i "检测斑块并测量大小"

# Output workflow as YAML
python -m src.cli analyze /path/to/dicom.dcm -y

# Use custom ONNX model
python -m src.cli analyze /path/to/dicom.dcm -m models/plaque_detector.onnx
```

### REST API Server

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
- `POST /analyze` - Analyze DICOM file

### Python Client

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

## Plugin System

The toolkit supports extensible plugins for different medical imaging tasks.

### Built-in Operators

- `dicom_reader` - Read DICOM files
- `meta_extractor` - Extract DICOM metadata
- `us_preprocess` - Ultrasound image preprocessing
- `model_operator` - Run model inference
- `measurement_operator` - Compute measurements
- `report_generator` - Generate reports

### Pip Plugins

Plugins can be installed via pip and auto-discovered:

```bash
pip install dicom-plugin-carotid
```

Plugins define capabilities via `TaskCapability`:

```python
from src.core import TaskCapability

capability = TaskCapability(
    task="detection",
    target="carotid_plaque",
    target_region="carotid",
    conditions={"modality": ["US"]},
)
```

Find compatible plugins at runtime:

```python
from src.core import get_registry

registry = get_registry()
operators = registry.get_compatible_operators(
    task="detection",
    target="carotid_plaque",
    modality="US"
)
```

## Documentation

- [Core Module](core.md) - OperatorBase, TaskCapability, Registry
- [Operators](operators.md) - Built-in operators
- [Planner](planner.md) - LLM Planner usage
- [Executor](executor.md) - Workflow execution

## Architecture

```
src/
├── core/          # OperatorBase, TaskCapability, Registry
├── operators/     # Built-in operators (DICOMReader, etc.)
├── planner/       # PlanningAgent (NL → Workflow)
└── executor/      # WorkflowExecutor (DAG → Results)
```

## Testing

```bash
pytest tests/ -v
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

## License

MIT