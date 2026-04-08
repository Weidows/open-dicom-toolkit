"""DICOM Platform Core - Operator and Registry."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from .task_capability import TaskCapability


@dataclass
class OperatorMeta:
    """Metadata for an Operator."""

    name: str  # "carotid_plaque_seg"
    display_name: str = ""  # "颈动脉斑块分割"
    version: str = "1.0.0"
    description: str = ""

    # Capabilities - structured task definitions
    capabilities: list[TaskCapability] = field(default_factory=list)

    # Backward compatible schemas
    input_schema: dict[str, str] = field(default_factory=dict)
    output_schema: dict[str, str] = field(default_factory=dict)

    # Resources
    resource_requirements: dict[str, Any] = field(default_factory=dict)

    # Source
    source: str = "builtin"  # "builtin", "pip"
    package: Optional[str] = None  # "dicom-plugin-carotid-seg" or "src.operators"

    # Dependencies
    dependencies: dict[str, str] = field(default_factory=dict)  # {"onnxruntime": ">=1.16"}

    # Entry point
    entry_point: Optional[str] = None  # "dicom_platform.plugins.carotid_seg"


class OperatorBase(ABC):
    """Base class for all Operators in the DICOM platform."""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def run(self, ctx: dict) -> dict:
        """Execute the operator on the given context.

        Args:
            ctx: Context dictionary containing input artifacts and metadata.

        Returns:
            Updated context with operator outputs.
        """
        raise NotImplementedError