"""LLM Planner - Convert natural language to workflow."""
import yaml
from typing import Any

from src.core import get_registry
from src.operators import (
    DICOMReader,
    MetaExtractor,
    USPreprocess,
    ModelOperator,
    MeasurementOperator,
    ReportGenerator,
)


# Register operators for planning
def _register_default_operators():
    """Register default operators for capability matching."""
    registry = get_registry()

    operators = [
        (DICOMReader, "read DICOM files from path"),
        (MetaExtractor, "extract metadata from DICOM"),
        (USPreprocess, "preprocess ultrasound images"),
        (ModelOperator, "run model inference for segmentation or detection"),
        (MeasurementOperator, "compute measurements from predictions"),
        (ReportGenerator, "generate analysis reports"),
    ]

    for op_cls, desc in operators:
        from src.core import OperatorMeta
        meta = OperatorMeta(
            name=op_cls.name,
            version=op_cls.version,
            capabilities=op_cls.capabilities,
            input_schema=op_cls.input_schema,
            output_schema=op_cls.output_schema,
            description=desc,
        )
        registry.register(op_cls, meta)


_register_default_operators()


class PlanningAgent:
    """Agent that converts natural language instructions to workflow plans."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.registry = get_registry()

    def list_capabilities(self) -> list[str]:
        """List all available capabilities from registered operators."""
        capabilities = set()
        for name in self.registry.list_operators():
            meta = self.registry.get_metadata(name)
            capabilities.update(meta.capabilities)
        return sorted(capabilities)

    def plan(self, instruction: str) -> dict:
        """Generate a workflow from natural language instruction.

        Args:
            instruction: Natural language description of the task.

        Returns:
            Workflow dictionary with nodes and edges.
        """
        instruction_lower = instruction.lower()

        # Build workflow based on keywords
        nodes = []
        edges = []
        node_id = 0

        # Always start with DICOMReader
        read_id = f"node_{node_id}"
        nodes.append({"id": read_id, "type": "dicom_reader", "params": {}})
        node_id += 1

        # Add MetaExtractor
        meta_id = f"node_{node_id}"
        nodes.append({"id": meta_id, "type": "meta_extractor", "params": {}})
        edges.append([read_id, meta_id])
        node_id += 1

        # Add preprocessing if needed
        if any(k in instruction_lower for k in ["超声", "ultrasound", "us", "图像", "image"]):
            pre_id = f"node_{node_id}"
            nodes.append({"id": pre_id, "type": "us_preprocess", "params": {}})
            edges.append([meta_id, pre_id])
            node_id += 1
            prev_node = pre_id
        else:
            prev_node = meta_id

        # Add model operator for segmentation/detection
        if any(k in instruction_lower for k in ["分割", "segment", "检测", "detect", "找", "find", "肿块", "lesion", "病灶"]):
            model_id = f"node_{node_id}"
            nodes.append({"id": model_id, "type": "model_operator", "params": {}})
            edges.append([prev_node, model_id])
            node_id += 1

            # Add postprocess/measurement
            measure_id = f"node_{node_id}"
            nodes.append({"id": measure_id, "type": "measurement_operator", "params": {}})
            edges.append([model_id, measure_id])
            node_id += 1
            final_node = measure_id
        else:
            final_node = prev_node

        # Always add report generator
        report_id = f"node_{node_id}"
        nodes.append({"id": report_id, "type": "report_generator", "params": {}})
        edges.append([final_node, report_id])

        return {
            "name": "generated_workflow",
            "nodes": nodes,
            "edges": edges,
        }

    def to_yaml(self, workflow: dict) -> str:
        """Convert workflow to YAML string.

        Args:
            workflow: Workflow dictionary.

        Returns:
            YAML string representation.
        """
        return yaml.dump(workflow, default_flow_style=False, sort_keys=False)