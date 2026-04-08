"""Task Capability - Structured capability definition for plugins."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaskCapability:
    """Defines what a plugin can do - structured capability for matching."""

    # Task type
    task: str  # "detection", "segmentation", "classification", "measurement"
    target: str  # "carotid_plaque", "thyroid_nodule", "liver_mass"
    target_region: str  # "intima", "carotid_artery", "thyroid"

    # Input/Output
    input_format: str  # "image_2d", "image_3d", "cine"
    output_formats: list[str] = field(default_factory=list)  # ["bbox", "mask", "polygon", "confidence"]

    # Model Info
    model_framework: Optional[str] = None  # "onnx", "pytorch", "tensorrt"
    model_input_size: Optional[tuple[int, int]] = None  # (512, 512)

    # Constraints
    conditions: dict[str, list[str]] = field(default_factory=dict)  # {"modality": ["US"], "body_part": ["neck"]}

    def matches(self, task: str = None, target: str = None, modality: str = None) -> bool:
        """Check if this capability matches the given criteria."""
        if task and self.task != task:
            return False
        if target and self.target != target:
            return False
        if modality:
            supported_modalities = self.conditions.get("modality", [])
            if supported_modalities and modality not in supported_modalities:
                return False
        return True