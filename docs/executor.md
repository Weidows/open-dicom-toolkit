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
        {"id": "read", "type": "DICOMReader", "params": {"path": "/data"}},
        {"id": "meta", "type": "DICOMMetaExtractor", "params": {}},
        {"id": "report", "type": "ReportGenerator", "params": {}},
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
            "type": "OperatorType",  # Must match registered operator
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
        {"id": "n1", "type": "DICOMReader", "params": {}},
        {"id": "n2", "type": "ReportGenerator", "params": {}},
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
        {"id": "read", "type": "DICOMReader", "params": {}},
        {"id": "meta", "type": "DICOMMetaExtractor", "params": {}},
        {"id": "preprocess", "type": "USPreprocess", "params": {}},
        {"id": "model", "type": "ModelOperator", "params": {"model": "seg_v1"}},
        {"id": "measure", "type": "MeasurementOperator", "params": {}},
        {"id": "report", "type": "ReportGenerator", "params": {}},
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
        {"id": "read1", "type": "DICOMReader", "params": {}},
        {"id": "read2", "type": "DICOMReader", "params": {}},
    ],
    "edges": [],  # No dependencies - run in parallel
}
```

### Error Handling

```python
workflow = {
    "name": "with_error",
    "nodes": [
        {"id": "read", "type": "DICOMReader", "params": {}},
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
        {"id": "n1", "type": "A", "params": {}},
        {"id": "n2", "type": "B", "params": {}},
    ],
    "edges": [["n1", "n2"], ["n2", "n1"]],  # Circular!
}

executor = WorkflowExecutor(workflow)
executor.execute({})  # Raises ValueError: Circular dependency detected
```