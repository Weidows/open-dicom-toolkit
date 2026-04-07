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

## Documentation

- [Core Module](core.md) - OperatorBase, Registry
- [Operators](operators.md) - Built-in operators
- [Planner](planner.md) - LLM Planner usage
- [Executor](executor.md) - Workflow execution

## Architecture

```
src/
├── core/          # OperatorBase, Registry
├── operators/     # DICOMReader, ModelOperator, etc.
├── planner/       # PlanningAgent (NL → Workflow)
└── executor/      # WorkflowExecutor (DAG → Results)
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT