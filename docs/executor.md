# Executor Module

## Overview

Workflow Executor that parses and executes workflow definitions in topological order.

## WorkflowExecutor

### Quick Start

```python
from src.executor import WorkflowExecutor, execute_workflow

# Define workflow
workflow = {
    "name": "my_workflow",
    "nodes": [
        {"id": "read", "type": "dicom_reader", "params": {"path": "/data"}},
        {"id": "meta", "type": "meta_extractor", "params": {}},
        {"id": "report", "type": "report_generator", "params": {}},
    ],
    "edges": [
        ["read", "meta"],
        ["meta", "report"],
    ],
}

# Execute
executor = WorkflowExecutor(workflow)
result = executor.execute({"path": "/data/scan.dcm"})

# Or use convenience function
result = execute_workflow(workflow, {"path": "/data/scan.dcm"})
```

---

### Workflow Structure

```python
workflow = {
    "name": "workflow_name",
    "nodes": [
        {
            "id": "unique_node_id",
            "type": "operator_name",  # Must match registered operator (lowercase)
            "params": {"key": "value"}  # Operator config
        },
        ...
    ],
    "edges": [
        ["source_node_id", "target_node_id"],  # target depends on source
        ...
    ]
}
```

### Available Operator Types

| Type | Description |
|------|-------------|
| `dicom_reader` | Read DICOM files |
| `meta_extractor` | Extract DICOM metadata |
| `us_preprocess` | Ultrasound preprocessing |
| `model_operator` | Model inference |
| `measurement_operator` | Compute measurements |
| `report_generator` | Generate reports |

---

### Methods

#### `__init__(workflow: dict)`

Initialize executor with workflow definition.

#### `execute(initial_ctx: dict) -> dict`

Execute workflow in topological order.

**Parameters:**

- `initial_ctx`: Initial context with input data (e.g., `{"path": "/data"}`)

**Returns:**

- Final context with all operator outputs

**Error Handling:**

- Missing operator: Adds `{node_id}_error` to context
- Other errors: Added to context as `{node_id}_error`

---

### Internal Methods

#### `_get_dependencies(node_id: str) -> set`

Get nodes that must run before the given node.

#### `_topological_sort() -> list`

Sort nodes using Kahn's algorithm.

**Raises:** `ValueError` if circular dependency detected.

---

## Examples

### Simple Pipeline

```python
workflow = {
    "name": "simple_analysis",
    "nodes": [
        {"id": "n1", "type": "dicom_reader", "params": {}},
        {"id": "n2", "type": "report_generator", "params": {}},
    ],
    "edges": [["n1", "n2"]],
}

result = execute_workflow(workflow, {"path": "/data/scan.dcm"})
# result contains outputs from each node
```

### Full Pipeline with Model

```python
workflow = {
    "name": "segmentation_pipeline",
    "nodes": [
        {"id": "read", "type": "dicom_reader", "params": {}},
        {"id": "meta", "type": "meta_extractor", "params": {}},
        {"id": "preprocess", "type": "us_preprocess", "params": {}},
        {"id": "model", "type": "model_operator", "params": {"model": "seg_v1"}},
        {"id": "measure", "type": "measurement_operator", "params": {}},
        {"id": "report", "type": "report_generator", "params": {}},
    ],
    "edges": [
        ["read", "meta"],
        ["meta", "preprocess"],
        ["preprocess", "model"],
        ["model", "measure"],
        ["measure", "report"],
    ],
}

result = execute_workflow(workflow, {"path": "/data/ultrasound"})
print(result["report"])
```

### Parallel Execution (No Edges)

```python
workflow = {
    "name": "parallel_demo",
    "nodes": [
        {"id": "read1", "type": "dicom_reader", "params": {}},
        {"id": "read2", "type": "dicom_reader", "params": {}},
    ],
    "edges": [],  # No dependencies - run in parallel
}
```

### Error Handling

```python
workflow = {
    "name": "with_error",
    "nodes": [
        {"id": "read", "type": "dicom_reader", "params": {}},
        {"id": "unknown", "type": "NonExistentOperator", "params": {}},
    ],
    "edges": [["read", "unknown"]],
}

result = execute_workflow(workflow, {"path": "/data"})
print(result["unknown_error"])  # "Operator 'NonExistentOperator' not found"
```

---

## Circular Dependency Detection

```python
workflow = {
    "name": "invalid",
    "nodes": [
        {"id": "n1", "type": "dicom_reader", "params": {}},
        {"id": "n2", "type": "report_generator", "params": {}},
    ],
    "edges": [["n1", "n2"], ["n2", "n1"]],  # Circular!
}

executor = WorkflowExecutor(workflow)
executor.execute({})  # Raises ValueError: Circular dependency detected
```

---

## Integration with Planner

```python
from src.planner import PlanningAgent
from src.executor import execute_workflow

# Plan: Natural language → Workflow
agent = PlanningAgent({})
workflow = agent.plan("分析这个超声病例，找出肿块并测量最大径")

# Execute: Workflow → Results
result = execute_workflow(workflow, {"path": "/data/scan.dcm"})

print(result["report"])
```