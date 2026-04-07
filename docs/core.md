# Core Module

## Overview
Core abstractions for the DICOM Agent Toolkit - `OperatorBase` and `Registry`.

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
| `capabilities` | list[str] | List of capability tags |
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
from src.core import OperatorMeta

meta = OperatorMeta(
    name="my_op",
    version="1.0.0",
    capabilities=["segmentation"],
    input_schema={"image": "ndarray"},
    output_schema={"mask": "ndarray"},
    description="My operator description",
    resource_requirements={"gpu": True, "memory_mb": 2048},
)
```

---

## Registry

Plugin registry for managing operators.

### Usage

```python
from src.core import Registry, OperatorBase, OperatorMeta, get_registry

# Get global registry
registry = get_registry()

# Register an operator
registry.register(MyOperator, meta)

# List all operators
names = registry.list_operators()

# Filter by capability
segmentation_ops = registry.list_by_capability("segmentation")

# Get operator instance
operator = registry.get("my_op", {"param": "value"})
```

### Methods

#### `register(operator_cls, meta: OperatorMeta)`
Register an operator class with metadata.

#### `list_operators() -> list[str]`
Returns list of all registered operator names.

#### `list_by_capability(capability: str) -> list[str]`
Returns operators that have the specified capability.

#### `get(name: str, config: dict) -> OperatorBase`
Get an operator instance by name.

#### `get_metadata(name: str) -> OperatorMeta`
Get metadata for an operator.

---

## Quick Start

```python
from src.core import get_registry, OperatorBase, OperatorMeta
from src.operators import DICOMReader

# Use global registry
registry = get_registry()

# Get DICOMReader instance
reader = registry.get("dicom_reader", {"path": "/data/scan.dcm"})
result = reader.run({})

# Or use operator directly
reader = DICOMReader({"path": "/data/scan.dcm"})
result = reader.run({})
```