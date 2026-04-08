# Planner Module

## Overview

LLM Planner that converts natural language instructions to workflow definitions.

## PlanningAgent

### Quick Start

```python
from src.planner import PlanningAgent

# Create planner
agent = PlanningAgent({})

# Generate workflow from instruction
instruction = "请分析这个超声病例，找出肿块并测量最大径"
workflow = agent.plan(instruction)

# Output as YAML
yaml_output = agent.to_yaml(workflow)
print(yaml_output)
```

### Methods

#### `__init__(config: dict)`

Initialize with optional configuration.

#### `list_capabilities() -> list[str]`

Returns all available capabilities from registered operators.

```python
caps = agent.list_capabilities()
print(caps)
# ['read', 'metadata', 'extract', 'preprocess', 'inference', ...]
```

#### `plan(instruction: str) -> dict`

Generate workflow from natural language instruction.

**Parameters:**

- `instruction`: Natural language task description (supports Chinese/English)

**Returns:**

- Workflow dictionary with structure:

```python
{
    "name": "generated_workflow",
    "nodes": [
        {"id": "node_0", "type": "dicom_reader", "params": {}},
        {"id": "node_1", "type": "meta_extractor", "params": {}},
        ...
    ],
    "edges": [["node_0", "node_1"], ...]
}
```

**Supported Instructions:**

| Instruction Keywords | Workflow Includes |
|---------------------|-------------------|
| `分割/segment` | model_operator → measurement_operator |
| `检测/detect/find` | model_operator → measurement_operator |
| `超声/ultrasound/us` | us_preprocess |
| `分析/analyze` | Full pipeline |

#### `to_yaml(workflow: dict) -> str`

Convert workflow to YAML string.

```python
yaml_str = agent.to_yaml(workflow)
```

---

## Examples

### Basic Analysis

```python
agent = PlanningAgent({})
workflow = agent.plan("分析这个DICOM文件")
# Output: nodes: [dicom_reader, meta_extractor, report_generator]
# edges: [[read, meta], [meta, report]]
```

### Segmentation Task

```python
agent = PlanningAgent({})
workflow = agent.plan("分割这个图像中的肿块")
# Output: nodes: [dicom_reader, meta_extractor, us_preprocess?, model_operator, measurement_operator, report_generator]
```

### English Instructions

```python
agent = PlanningAgent({})
workflow = agent.plan("detect lesions in this ultrasound scan")
# Same output structure, English keywords supported
```

---

## Integration with Executor

```python
from src.planner import PlanningAgent
from src.executor import execute_workflow

# Plan
agent = PlanningAgent({})
workflow = agent.plan("分析这个CT")

# Execute
result = execute_workflow(workflow, {"path": "/data/case1"})
print(result["report"])
```

---

## Advanced Usage

### Custom Capability Matching

The planner can be extended to use LLM for better capability matching:

```python
class LLMPlanningAgent(PlanningAgent):
    def plan(self, instruction: str) -> dict:
        # Use LLM to analyze instruction
        # Query registry for compatible operators
        # Generate workflow dynamically
        ...
```