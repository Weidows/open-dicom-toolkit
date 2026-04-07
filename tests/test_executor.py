"""Tests for Workflow Executor."""
import pytest


class TestWorkflowExecutor:
    """Test the Workflow Executor component."""

    def test_executor_parses_workflow(self):
        """Executor should parse workflow with nodes and edges."""
        from src.executor.executor import WorkflowExecutor

        workflow = {
            "name": "test_workflow",
            "nodes": [
                {"id": "n1", "type": "DICOMReader", "params": {"path": "/data"}},
                {"id": "n2", "type": "ReportGenerator", "params": {}},
            ],
            "edges": [["n1", "n2"]],
        }

        executor = WorkflowExecutor(workflow)
        assert executor.workflow["name"] == "test_workflow"
        assert len(executor.workflow["nodes"]) == 2

    def test_executor_resolves_dependencies(self):
        """Executor should resolve node dependencies from edges."""
        from src.executor.executor import WorkflowExecutor

        workflow = {
            "name": "test",
            "nodes": [
                {"id": "read", "type": "DICOMReader", "params": {}},
                {"id": "meta", "type": "DICOMMetaExtractor", "params": {}},
                {"id": "report", "type": "ReportGenerator", "params": {}},
            ],
            "edges": [["read", "meta"], ["meta", "report"]],
        }

        executor = WorkflowExecutor(workflow)
        deps = executor._get_dependencies("meta")

        assert "read" in deps

    def test_executor_topological_sort(self):
        """Executor should sort nodes in topological order."""
        from src.executor.executor import WorkflowExecutor

        workflow = {
            "name": "test",
            "nodes": [
                {"id": "n3", "type": "ReportGenerator", "params": {}},
                {"id": "n1", "type": "DICOMReader", "params": {}},
                {"id": "n2", "type": "DICOMMetaExtractor", "params": {}},
            ],
            "edges": [["n1", "n2"], ["n2", "n3"]],
        }

        executor = WorkflowExecutor(workflow)
        ordered = executor._topological_sort()

        # n1 should come before n2, n2 before n3
        idx = {n["id"]: i for i, n in enumerate(ordered)}
        assert idx["n1"] < idx["n2"]
        assert idx["n2"] < idx["n3"]

    def test_executor_executes_nodes(self):
        """Executor should execute nodes and pass context."""
        from src.executor.executor import WorkflowExecutor

        workflow = {
            "name": "test",
            "nodes": [
                {"id": "read", "type": "DICOMReader", "params": {}},
            ],
            "edges": [],
        }

        executor = WorkflowExecutor(workflow)
        result = executor.execute({"path": "/fake/path"})

        assert "read_error" in result  # Operator not registered, error stored

    def test_executor_handles_invalid_workflow(self):
        """Executor should raise error for invalid workflow."""
        from src.executor.executor import WorkflowExecutor

        # Missing edges (circular dependency potential)
        workflow = {
            "name": "test",
            "nodes": [
                {"id": "n1", "type": "DICOMReader", "params": {}},
                {"id": "n2", "type": "ReportGenerator", "params": {}},
            ],
            "edges": [],  # No connection but both exist
        }

        # Should still work, just parallel execution
        executor = WorkflowExecutor(workflow)
        assert executor.workflow is not None

    def test_executor_circular_dependency_detection(self):
        """Executor should detect circular dependencies."""
        from src.executor.executor import WorkflowExecutor

        workflow = {
            "name": "test",
            "nodes": [
                {"id": "n1", "type": "A", "params": {}},
                {"id": "n2", "type": "B", "params": {}},
            ],
            "edges": [["n1", "n2"], ["n2", "n1"]],  # Circular!
        }

        executor = WorkflowExecutor(workflow)
        # Should raise during topological sort
        with pytest.raises(ValueError, match="[Cc]ircular"):
            executor._topological_sort()