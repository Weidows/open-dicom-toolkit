"""Registry for managing Operators."""
import importlib
import importlib.util
import logging
from typing import Type, Any, Optional, Callable

from .operator import OperatorBase, OperatorMeta
from .task_capability import TaskCapability

logger = logging.getLogger(__name__)


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

    # ========== Plugin Discovery ==========

    def register_plugin(self, entry_point: str) -> bool:
        """Load plugin from entry point.

        Args:
            entry_point: Module path to the register function, e.g. "dicom_plugin_carotid_seg:register"

        Returns:
            True if successful, False otherwise.
        """
        try:
            module_path, func_name = entry_point.split(":")
            spec = importlib.util.find_spec(module_path)
            if spec is None:
                logger.warning(f"Cannot find module: {module_path}")
                return False

            module = importlib.import_module(module_path)
            register_func: Callable = getattr(module, func_name)
            register_func(self)
            logger.info(f"Loaded plugin from entry point: {entry_point}")
            return True
        except Exception as e:
            logger.error(f"Failed to load plugin from {entry_point}: {e}")
            return False

    def discover_plugins(self) -> int:
        """Scan and load all installed plugins via entry points.

        Returns:
            Number of plugins successfully loaded.
        """
        loaded = 0

        # Try to load from setuptools entry points
        try:
            from importlib.metadata import entry_points

            eps = entry_points()

            # Python 3.10+ uses SelectableGroups, earlier uses dict
            if hasattr(eps, 'select'):
                plugin_eps = eps.select(group="dicom_platform.plugins")
            else:
                plugin_eps = eps.get("dicom_platform.plugins", [])

            for ep in plugin_eps:
                entry_point = f"{ep.module}:{ep.attr}"
                if self.register_plugin(entry_point):
                    loaded += 1
        except ImportError:
            # Python < 3.10 fallback
            try:
                from importlib_metadata import entry_points
                eps = entry_points()

                if hasattr(eps, 'select'):
                    plugin_eps = eps.select(group="dicom_platform.plugins")
                else:
                    plugin_eps = eps.get("dicom_platform.plugins", [])

                for ep in plugin_eps:
                    entry_point = f"{ep.module}:{ep.attr}"
                    if self.register_plugin(entry_point):
                        loaded += 1
            except ImportError:
                logger.warning("No plugin discovery available (importlib_metadata not installed)")

        logger.info(f"Discovered {loaded} pip plugins")
        return loaded

    # ========== Query Methods ==========

    def list_operators(self) -> list[str]:
        """List all registered operator names."""
        return list(self._operators.keys())

    def list_by_task(self, task: str) -> list[str]:
        """Find operators by task type.

        Args:
            task: Task type (e.g., "detection", "segmentation")

        Returns:
            List of operator names that support the task.
        """
        result = []
        for name, meta in self._metadata.items():
            for cap in meta.capabilities:
                # Handle both TaskCapability objects and legacy string capabilities
                if hasattr(cap, 'task'):
                    if cap.task == task:
                        result.append(name)
                        break
                elif isinstance(cap, str) and cap == task:
                    result.append(name)
                    break
        return result

    def list_by_target(self, target: str) -> list[str]:
        """Find operators by target (plaque, mass, nodule).

        Args:
            target: Target name (e.g., "carotid_plaque", "thyroid_nodule")

        Returns:
            List of operator names that support the target.
        """
        result = []
        for name, meta in self._metadata.items():
            for cap in meta.capabilities:
                # Handle both TaskCapability objects and legacy string capabilities
                if hasattr(cap, 'target'):
                    if cap.target == target:
                        result.append(name)
                        break
        return result

    def list_by_body_part(self, body_part: str) -> list[str]:
        """Find operators by body part.

        Args:
            body_part: Body part (e.g., "carotid", "thyroid", "liver")

        Returns:
            List of operator names that support the body part.
        """
        result = []
        for name, meta in self._metadata.items():
            for cap in meta.capabilities:
                # Handle both TaskCapability objects
                if hasattr(cap, 'target_region'):
                    if cap.target_region == body_part:
                        result.append(name)
                        break
        return result

    def list_by_modality(self, modality: str) -> list[str]:
        """Find operators by imaging modality.

        Args:
            modality: Imaging modality (e.g., "US", "CT", "MR")

        Returns:
            List of operator names that support the modality.
        """
        result = []
        for name, meta in self._metadata.items():
            for cap in meta.capabilities:
                # Handle both TaskCapability objects
                if hasattr(cap, 'conditions'):
                    supported = cap.conditions.get("modality", [])
                    if modality in supported:
                        result.append(name)
                        break
        return result

    def get_compatible_operators(
        self,
        task: str,
        target: Optional[str] = None,
        modality: Optional[str] = None,
    ) -> list[str]:
        """Find compatible plugins for given criteria (used by Planner).

        Args:
            task: Task type (required)
            target: Target name (optional)
            modality: Imaging modality (optional)

        Returns:
            List of compatible operator names.
        """
        result = []
        for name, meta in self._metadata.items():
            for cap in meta.capabilities:
                # Handle both TaskCapability objects and legacy string capabilities
                if hasattr(cap, 'matches'):
                    if cap.matches(task=task, target=target, modality=modality):
                        result.append(name)
                        break
        return result

    # ========== Backward Compatible ==========

    def list_by_capability(self, capability: str) -> list[str]:
        """List operators that have a specific capability (legacy method).

        Args:
            capability: The capability to filter by.

        Returns:
            List of operator names with the specified capability.
        """
        # For backward compatibility, check both new capabilities and old-style string list
        result = []
        for name, meta in self._metadata.items():
            # Check new TaskCapability
            found = False
            if isinstance(meta.capabilities, list):
                for cap in meta.capabilities:
                    if hasattr(cap, 'task') and cap.task == capability:
                        result.append(name)
                        found = True
                        break
                    elif isinstance(cap, str) and cap == capability:
                        result.append(name)
                        found = True
                        break
        return result

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