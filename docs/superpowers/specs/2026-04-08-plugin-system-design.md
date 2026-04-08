# Plugin System Design

**Date:** 2026-04-08
**Topic:** Plugin System with pip auto-discovery
**Status:** Approved

## Overview

Design a flexible plugin system for DICOM Agent Toolkit that supports:
- pip package installation with auto-discovery
- Multiple tasks per plugin (detection, segmentation, etc.)
- Multiple body parts/targets per plugin
- Version management for models
- Unified registry for builtin + pip plugins

---

## 1. Core Data Structures

### TaskCapability

```python
@dataclass
class TaskCapability:
    # Task type
    task: str  # "detection", "segmentation", "classification", "measurement"
    target: str  # "carotid_plaque", "thyroid_nodule", "liver_mass"
    target_region: str  # "intima", "carotid_artery", "thyroid"

    # Input/Output
    input_format: str  # "image_2d", "image_3d", "cine"
    output_formats: list[str]  # ["bbox", "mask", "polygon", "confidence"]

    # Model Info
    model_framework: str  # "onnx", "pytorch", "tensorrt"
    model_input_size: tuple[int, int]  # (512, 512)

    # Constraints
    conditions: dict  # {"modality": ["US"], "body_part": ["neck"]}
```

### OperatorMeta

```python
@dataclass
class OperatorMeta:
    name: str  # "carotid_plaque_seg"
    display_name: str  # "颈动脉斑块分割"
    version: str  # "1.0.0"
    description: str
    capabilities: list[TaskCapability]

    # Backward compatible schemas
    input_schema: dict
    output_schema: dict

    # Resources
    resource_requirements: dict  # {"gpu": True, "gpu_memory_mb": 2048}

    # Source
    source: str  # "builtin", "pip"
    package: str  # "dicom-plugin-carotid-seg" or "src.operators"

    # Dependencies
    dependencies: dict  # {"onnxruntime": ">=1.16"}

    # Entry point
    entry_point: str  # "dicom_platform.plugins.carotid_seg"
```

---

## 2. Plugin Declaration Mechanism

### pip package pyproject.toml

```toml
[project]
name = "dicom-plugin-carotid-seg"
version = "1.0.0"
dependencies = ["onnxruntime>=1.16"]

[project.entry-points."dicom_platform.plugins"]
carotid_seg = "dicom_plugin_carotid_seg:register"
```

### Register Function Template

```python
# dicom_plugin_carotid_seg/__init__.py
from dicom_platform.core import OperatorBase, OperatorMeta, TaskCapability, get_registry

def register(registry=None):
    if registry is None:
        from dicom_platform.core import get_registry
        registry = get_registry()

    meta = OperatorMeta(
        name="carotid_plaque_seg",
        display_name="��动脉斑块分割",
        version="1.0.0",
        description="基于 UNet 的颈动脉斑块分割",
        capabilities=[
            TaskCapability(
                task="segmentation",
                target="carotid_plaque",
                target_region="carotid_artery",
                input_format="image_2d",
                output_formats=["mask", "bbox"],
                model_framework="onnx",
                model_input_size=(512, 512),
                conditions={"modality": ["US"], "body_part": ["neck"]},
            ),
            # ... more capabilities
        ],
        input_schema={"image": "ndarray"},
        output_schema={"mask": "ndarray", "bbox": "list"},
        source="pip",
        package="dicom-plugin-carotid-seg",
        resource_requirements={"gpu": True, "gpu_memory_mb": 2048},
        dependencies={"onnxruntime": ">=1.16"},
    )
    registry.register(CarotidPlaqueOperator, meta)
```

---

## 3. Registry Extension

### New Methods

```python
class Registry:
    # Existing methods...

    def register_plugin(self, entry_point: str):
        """Load plugin from entry point"""

    def discover_plugins(self):
        """Scan and load all installed plugins (called at startup)"""

    def list_by_task(self, task: str) -> list[str]:
        """Find by task type"""

    def list_by_target(self, target: str) -> list[str]:
        """Find by target (plaque, mass)"""

    def list_by_body_part(self, body_part: str) -> list[str]:
        """Find by body part (carotid, thyroid)"""

    def list_by_modality(self, modality: str) -> list[str]:
        """Find by imaging modality (US, CT, MR)"""

    def get_compatible_operators(
        self, task: str, target: str = None, modality: str = None
    ) -> list[str]:
        """Find compatible plugins for Planner capability matching"""
```

---

## 4. Startup Discovery Flow

```python
# src/core/__init__.py
def _init_plugins():
    """Auto-discover and register all plugins at startup"""
    registry = get_registry()

    # 1. Register builtin plugins
    for op in BUILTIN_OPERATORS:
        registry.register(op, op.get_metadata())

    # 2. Discover and load pip plugins
    registry.discover_plugins()

_init_plugins()
```

---

## 5. Query Examples

```python
registry = get_registry()

# Find all detection plugins for carotid plaque
detection_ops = registry.list_by_task("detection")
carotid_detection = [n for n in detection_ops if "carotid" in n]

# Find US segmentation plugins
us_segmentation = registry.get_compatible_operators(
    task="segmentation",
    modality="US"
)

# Get plugin details
meta = registry.get_metadata("carotid_plaque_seg")
print(meta.capabilities[0].output_formats)  # ['mask', 'bbox']
```

---

## 6. Directory Structure

```
open-dicom-toolkit/
├── src/
│   ├── core/
│   │   ├── registry.py      # Extended with discovery
│   │   ├── operator.py      # TaskCapability, OperatorMeta
│   │   └── __init__.py      # _init_plugins()
│   └── operators/           # Builtin implementations
├── docs/
│   └── plugin-system.md     # Plugin development guide
└── pyproject.toml           # Main package config
```