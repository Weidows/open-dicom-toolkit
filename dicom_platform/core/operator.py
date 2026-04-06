"""DICOM Platform Core - Operator and Registry."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperatorMeta:
    """Metadata for an Operator."""
    name: str
    version: str
    capabilities: list[str]
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    description: str = ""
    resource_requirements: dict[str, Any] = field(default_factory=dict)


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