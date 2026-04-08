# Core Module

## Overview

Core abstractions for the DICOM Agent Toolkit - `OperatorBase`, `TaskCapability`, and `Registry`.

## OperatorBase

Base abstract class for all operators in the platform.

### Class Definition

```python
from src.core import OperatorBase, OperatorMeta

class MyOperator(OperatorBase):
    name = "my_operator"
    version = "1.0.0"
    capabilities = ["segmentation", "detection"]
    input_schema = {"image": "ndarray", "meta": "dict"}
    output_schema = {"mask": "ndarray", "score": "float"}

    def __init__(self, config: dict):
        super().__init__(config)
        self.param = config.get("param", "default")

    def run(self, ctx: dict) -> dict:
        # Process ctx["image"]
        ctx["mask"] = result
        return ctx
```

### Class Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Unique operator name |
| `version` | str | Version string (e.g., "1.0.0") |
| `capabilities` | list | List of capability tags or TaskCapability objects |
| `input_schema` | dict | Input field types |
| `output_schema` | dict | Output field types |

### Methods

#### `__init__(config: dict)`

Initialize operator with configuration.

#### `run(ctx: dict) -> dict`

Execute the operator. Must be implemented by subclasses.

**Parameters:**

- `ctx`: Context dictionary containing input artifacts

**Returns:**

- Updated context with operator outputs

---

## OperatorMeta

Dataclass for operator metadata.

```python
from src.core import OperatorMeta, TaskCapability

# Using TaskCapability (recommended)
capabilities = [
    TaskCapability(
        task="detection",
        target="carotid_plaque",
        target_region="carotid",
        input_formats=["DICOM"],
        output_formats=["DICOM SR", "JSON"],
        conditions={"modality": ["US"], "probe_type": ["linear"]},
        model_info={"type": "ONNX", "path": "models/plaque_detector.onnx"},
    )
]

meta = OperatorMeta(
    name="plaque_detector",
    version="1.0.0",
    capabilities=capabilities,
    input_schema={"image": "ndarray"},
    output_schema={"predictions": "ndarray", "probabilities": "ndarray"},
    description="Carotid plaque detection for ultrasound images",
    resource_requirements={"gpu": True, "memory_mb": 2048},
    source="builtin",  # "builtin" or "pip"
    package="dicom-plugin-carotid",  # pip package name (for pip plugins)
    dependencies=["onnxruntime"],  # pip dependencies
    entry_point="dicom_plugin_carotid:register",  # registration function
)
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Unique operator name |
| `version` | str | Version string (e.g., "1.0.0") |
| `capabilities` | list | List of TaskCapability objects or legacy string list |
| `input_schema` | dict | Input field types |
| `output_schema` | dict | Output field types |
| `description` | str | Human-readable description |
| `resource_requirements` | dict | Hardware requirements (GPU, memory, etc.) |
| `source` | str | "builtin" or "pip" |
| `package` | str | pip package name (for pip plugins) |
| `dependencies` | list | pip dependencies |
| `entry_point` | str | Registration function path |

---

## TaskCapability

Structured capability definition for plugin discovery.

```python
from src.core import TaskCapability

capability = TaskCapability(
    task="detection",           # Task type: detection, segmentation, classification, measurement
    target="carotid_plaque",   # Target: carotid_plaque, thyroid_nodule, liver_mass
    target_region="carotid",   # Body region: carotid, thyroid, liver, breast
    input_formats=["DICOM", "NIfTI"],
    output_formats=["DICOM SR", "JSON", "NIfTI"],
    conditions={
        "modality": ["US", "CT"],       # Supported imaging modalities
        "probe_type": ["linear"],       # Probe types (for ultrasound)
        "contrast": [True, False],      # Contrast enhanced or not
    },
    model_info={
        "type": "ONNX",                 # Model format: ONNX, TorchScript, TensorFlow
        "path": "models/plaque_detector.onnx",
        "input_size": [224, 224],
        "classes": ["normal", "plaque"],
    },
)
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `task` | str | Task type: detection, segmentation, classification, measurement, report |
| `target` | str | Target pathology: carotid_plaque, thyroid_nodule, etc. |
| `target_region` | str | Body region: carotid, thyroid, liver, breast |
| `input_formats` | list | Supported input formats |
| `output_formats` | list | Output formats produced |
| `conditions` | dict | Additional conditions (modality, probe_type, contrast, etc.) |
| `model_info` | dict | Model details (type, path, input_size, classes) |

### Methods

#### `matches(task=None, target=None, modality=None) -> bool`

Check if capability matches given criteria.

```python
cap = TaskCapability(
    task="detection",
    target="carotid_plaque",
    conditions={"modality": ["US"]},
)

cap.matches(task="detection")  # True
cap.matches(task="segmentation")  # False
cap.matches(task="detection", modality="US")  # True
cap.matches(task="detection", modality="CT")  # False
```

---

## Registry

Plugin registry for managing operators. Supports both builtin operators and pip-installed plugins.

### Usage

```python
from src.core import Registry, OperatorBase, OperatorMeta, get_registry

# Get global registry (auto-initializes all plugins)
registry = get_registry()

# Register an operator manually
registry.register(MyOperator, meta)

# List all operators
names = registry.list_operators()

# Filter by capability (legacy string-based)
segmentation_ops = registry.list_by_capability("segmentation")

# Filter by task type (new TaskCapability-based)
detection_ops = registry.list_by_task("detection")

# Filter by target pathology
plaque_ops = registry.list_by_target("carotid_plaque")

# Filter by body region
carotid_ops = registry.list_by_body_part("carotid")

# Filter by imaging modality
us_ops = registry.list_by_modality("US")

# Find compatible operators (for Planner)
compatible = registry.get_compatible_operators(
    task="detection",
    target="carotid_plaque",
    modality="US"
)

# Get operator instance
operator = registry.get("my_op", {"param": "value"})

# Get metadata
meta = registry.get_metadata("my_op")
```

### Plugin Discovery

Pip-installed plugins are automatically discovered via `entry_points` in `setup.cfg` or `pyproject.toml`:

```toml
# pyproject.toml example for a plugin package
[project.entry-points."dicom_platform.plugins"]
carotid_seg = "dicom_plugin_carotid:register"
thyroid_nodule = "dicom_plugin_thyroid:register"
```

The `register` function signature:

```python
def register(registry: Registry) -> None:
    """Register plugin operators to the global registry."""
    registry.register(MyOperator, meta)
```

### Methods

#### `register(operator_cls, meta: OperatorMeta)`

Register an operator class with metadata.

#### `register_plugin(entry_point: str) -> bool`

Load plugin from entry point (e.g., `"dicom_plugin_carotid:register"`).

#### `discover_plugins() -> int`

Scan and load all pip-installed plugins via entry points. Returns count of loaded plugins.

#### `list_operators() -> list[str]`

Returns list of all registered operator names.

#### `list_by_task(task: str) -> list[str]`

Returns operators that support the specified task type.

#### `list_by_target(target: str) -> list[str]`

Returns operators that target the specified pathology.

#### `list_by_body_part(body_part: str) -> list[str]`

Returns operators for the specified body region.

#### `list_by_modality(modality: str) -> list[str]`

Returns operators for the specified imaging modality.

#### `get_compatible_operators(task, target=None, modality=None) -> list[str]`

Find operators matching all specified criteria (used by Planner).

#### `list_by_capability(capability: str) -> list[str]`

Legacy method - returns operators with specified capability string.

#### `get(name: str, config: dict) -> OperatorBase`

Get an operator instance by name.

#### `get_metadata(name: str) -> OperatorMeta`

Get metadata for an operator.

---

## Auto-Initialization

All builtin and pip plugins are automatically discovered and registered when importing `src.core`:

```python
# This automatically loads all plugins
from src.core import get_registry

registry = get_registry()
print(registry.list_operators())  # All registered operators
```

---

## Quick Start

```python
from src.core import get_registry, OperatorBase, OperatorMeta
from src.operators import DICOMReader

# Use global registry (auto-initializes all plugins)
registry = get_registry()

# Get DICOMReader instance
reader = registry.get("dicom_reader", {"path": "/data/scan.dcm"})
result = reader.run({})

# Or use operator directly
reader = DICOMReader({"path": "/data/scan.dcm"})
result = reader.run({})

# Find compatible operators for a task
detection_ops = registry.get_compatible_operators(
    task="detection",
    target="carotid_plaque",
    modality="US"
)
```