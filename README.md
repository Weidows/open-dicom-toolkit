# DICOM Agent Toolkit

<p align="center">
  <strong>AI Agent-driven DICOM medical imaging analysis toolkit</strong><br>
  <a href="https://pypi.org/project/dicom-agent-toolkit/"><img src="https://img.shields.io/pypi/v/dicom-agent-toolkit" alt="PyPI"></a>
  <a href="https://github.com/Weidows/open-dicom-toolkit/actions"><img src="https://img.shields.io/github/actions/workflow/status/Weidows/open-dicom-toolkit/ci" alt="CI"></a>
  <a href="https://github.com/Weidows/open-dicom-toolkit/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/dicom-agent-toolkit" alt="License"></a>
</p>

AI-first DICOM 分析工具链，让 LLM Agent 能够自主选择、组合、执行检测/分割/测量/报告生成等任务。

## Features

- **AI-Driven Workflow**: 自然语言指令自动转换为可执行的工作流 DAG
- **Plugin Architecture**: 可扩展的算子系统，支持 pip 插件自动发现
- **Multi-Modality**: 支持 CT、MR、US 等多种医学影像模态
- **DICOM Native**: 完整保留 DICOM 元数据（PixelSpacing、ImageOrientation 等）
- **Model Agnostic**: 兼容 ONNX、TorchScript、TensorFlow 模型
- **REST API**: 开箱即用的 Web 服务，支持 DICOMweb 上传/拉取

## Quick Start

```python
from src.planner import PlanningAgent
from src.executor import execute_workflow

# 1. Plan - Convert natural language to workflow
agent = PlanningAgent({})
workflow = agent.plan("分析这个超声病例，找出斑块并测量最大径")

# 2. Execute - Run the workflow
result = execute_workflow(workflow, {"path": "/data/scan.dcm"})

# 3. Get results
print(result["report"])
```

## Installation

```bash
pip install -e .
```

## CLI Usage

```bash
# Analyze a DICOM file
python -m src.cli analyze /path/to/dicom.dcm -i "检测斑块并测量大小"

# Output workflow as YAML
python -m src.cli analyze /path/to/dicom.dcm -y
```

## REST API

```bash
# Start server
python -m src.server

# Or with Docker
docker-compose up -d
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| GET | `/operators` | List available operators |
| POST | `/plan` | Generate workflow from instruction |
| POST | `/analyze` | Analyze DICOM file |

## Architecture

```
src/
├── core/           # OperatorBase, TaskCapability, Registry
├── operators/      # Built-in operators (DICOMReader, ONNX runner, etc.)
├── planner/        # PlanningAgent (NL → Workflow)
└── executor/       # WorkflowExecutor (DAG → Results)
```

## Plugin System

Plugins are automatically discovered via pip entry points:

```toml
# pyproject.toml
[project.entry-points."dicom_platform.plugins"]
carotid_seg = "dicom_plugin_carotid:register"
```

Find compatible operators at runtime:

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

- [Core Module](docs/core.md) - OperatorBase, TaskCapability, Registry
- [Operators](docs/operators.md) - Built-in operators
- [Planner](docs/planner.md) - LLM Planner usage
- [Executor](docs/executor.md) - Workflow execution

## License

MIT