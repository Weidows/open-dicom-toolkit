"""Registry for managing Operators."""
from typing import Type, Any

from .operator import OperatorBase, OperatorMeta


class Registry:
    """Plugin registry for managing Operators."""

    def __init__(self):
        self._operators: dict[str, Type[OperatorBase]] = {}
        self._metadata: dict[str, OperatorMeta] = {}

    def register(self, operator_cls: Type[OperatorBase], meta: OperatorMeta) -> None:
        """Register an operator with its metadata.

        Args:
            operator_cls: The operator class to register.
            meta: Metadata describing the operator.
        """
        self._operators[meta.name] = operator_cls
        self._metadata[meta.name] = meta

    def list_operators(self) -> list[str]:
        """List all registered operator names."""
        return list(self._operators.keys())

    def list_by_capability(self, capability: str) -> list[str]:
        """List operators that have a specific capability.

        Args:
            capability: The capability to filter by.

        Returns:
            List of operator names with the specified capability.
        """
        return [
            name
            for name, meta in self._metadata.items()
            if capability in meta.capabilities
        ]

    def get(self, name: str, config: dict = None) -> OperatorBase:
        """Get an operator instance by name.

        Args:
            name: The operator name.
            config: Configuration to pass to the operator.

        Returns:
            An instance of the requested operator.

        Raises:
            KeyError: If the operator is not found.
        """
        if name not in self._operators:
            raise KeyError(f"Operator '{name}' not found in registry")
        return self._operators[name](config or {})

    def get_metadata(self, name: str) -> OperatorMeta:
        """Get metadata for an operator.

        Args:
            name: The operator name.

        Returns:
            The operator metadata.

        Raises:
            KeyError: If the operator is not found.
        """
        if name not in self._metadata:
            raise KeyError(f"Operator '{name}' not found in registry")
        return self._metadata[name]


# Global registry instance
_global_registry = Registry()


def get_registry() -> Registry:
    """Get the global registry instance."""
    return _global_registry