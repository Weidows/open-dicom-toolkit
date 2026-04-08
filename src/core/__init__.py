"""DICOM Platform - AI Agent-driven DICOM analysis toolkit."""
import logging

from .operator import OperatorBase, OperatorMeta
from .registry import Registry, get_registry
from .task_capability import TaskCapability

logger = logging.getLogger(__name__)

__all__ = [
    "OperatorBase",
    "OperatorMeta",
    "TaskCapability",
    "Registry",
    "get_registry",
]


def _create_metadata_from_operator(operator_cls: type) -> OperatorMeta:
    """Create OperatorMeta from operator class attributes (backward compatible)."""
    # Try to get metadata via get_metadata method
    if hasattr(operator_cls, "get_metadata"):
        return operator_cls.get_metadata()

    # Fallback: create from class attributes
    return OperatorMeta(
        name=getattr(operator_cls, "name", operator_cls.__name__),
        version=getattr(operator_cls, "version", "0.1.0"),
        capabilities=getattr(operator_cls, "capabilities", []),
        input_schema=getattr(operator_cls, "input_schema", {}),
        output_schema=getattr(operator_cls, "output_schema", {}),
        description=getattr(operator_cls, "__doc__", ""),
    )


def _init_plugins() -> None:
    """Auto-discover and register all plugins at startup."""
    registry = get_registry()

    # Import and register builtin operators
    try:
        from ..operators import BUILTIN_OPERATORS

        for op in BUILTIN_OPERATORS:
            meta = _create_metadata_from_operator(op)
            registry.register(op, meta)
            logger.info(f"Registered builtin operator: {meta.name}")
    except ImportError:
        pass  # No builtin operators yet

    # Discover and load pip plugins
    registry.discover_plugins()


# Initialize plugins on module import
_init_plugins()