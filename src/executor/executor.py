"""Workflow Executor - Execute workflow nodes in topological order."""
from typing import Any

from src.core import get_registry


class WorkflowExecutor:
    """Execute workflow nodes in dependency order."""

    def __init__(self, workflow: dict):
        """Initialize executor with workflow definition.

        Args:
            workflow: Workflow dict with 'nodes' and 'edges'.
        """
        self.workflow = workflow
        self.registry = get_registry()
        self._node_map = {node["id"]: node for node in workflow.get("nodes", [])}

    def _get_dependencies(self, node_id: str) -> set:
        """Get all nodes that the given node depends on.

        Args:
            node_id: The node ID to get dependencies for.

        Returns:
            Set of node IDs that must run before this node.
        """
        deps = set()
        for edge in self.workflow.get("edges", []):
            if len(edge) >= 2 and edge[1] == node_id:
                deps.add(edge[0])
        return deps

    def _topological_sort(self) -> list:
        """Sort nodes in topological order based on dependencies.

        Returns:
            List of nodes in execution order.

        Raises:
            ValueError: If circular dependency detected.
        """
        nodes = self.workflow.get("nodes", [])
        in_degree = {node["id"]: 0 for node in nodes}

        # Calculate in-degrees
        for edge in self.workflow.get("edges", []):
            if len(edge) >= 2:
                in_degree[edge[1]] = in_degree.get(edge[1], 0) + 1

        # Topological sort using Kahn's algorithm
        queue = [node["id"] for node in nodes if in_degree.get(node["id"], 0) == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(self._node_map[node_id])

            # Reduce in-degree for dependent nodes
            for edge in self.workflow.get("edges", []):
                if len(edge) >= 2 and edge[0] == node_id:
                    in_degree[edge[1]] -= 1
                    if in_degree[edge[1]] == 0:
                        queue.append(edge[1])

        # Check for circular dependencies
        if len(result) != len(nodes):
            raise ValueError("Circular dependency detected in workflow")

        return result

    def execute(self, initial_ctx: dict = None) -> dict:
        """Execute the workflow.

        Args:
            initial_ctx: Initial context with input data.

        Returns:
            Final context with all operator outputs.
        """
        ctx = initial_ctx or {}

        # Get execution order
        ordered_nodes = self._topological_sort()

        # Execute each node
        for node in ordered_nodes:
            node_type = node.get("type")
            node_params = node.get("params", {})

            try:
                # Get operator from registry
                operator = self.registry.get(node_type, node_params)
                # Execute and update context
                ctx = operator.run(ctx)
            except KeyError:
                # Operator not found - skip or raise
                ctx[f"{node['id']}_error"] = f"Operator '{node_type}' not found"
            except Exception as e:
                ctx[f"{node['id']}_error"] = str(e)

        return ctx


def execute_workflow(workflow: dict, initial_ctx: dict = None) -> dict:
    """Convenience function to execute a workflow.

    Args:
        workflow: Workflow definition.
        initial_ctx: Initial context.

    Returns:
        Final context after workflow execution.
    """
    executor = WorkflowExecutor(workflow)
    return executor.execute(initial_ctx)