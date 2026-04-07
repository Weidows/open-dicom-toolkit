"""Tests for LLM Planner."""
import pytest


class TestPlanner:
    """Test the LLM Planner component."""

    def test_planner_has_capability_registry(self):
        """Planner should have access to operator capabilities."""
        from src.planner.planner import PlanningAgent

        agent = PlanningAgent({})
        # Should have access to capability registry
        capabilities = agent.list_capabilities()
        assert "read" in capabilities
        assert "segmentation" in capabilities or "inference" in capabilities

    def test_planner_generates_workflow_from_instruction(self):
        """Planner should generate workflow from natural language."""
        from src.planner.planner import PlanningAgent

        agent = PlanningAgent({})
        instruction = "请分析这个超声病例，找出肿块并测量最大径"

        workflow = agent.plan(instruction)

        assert "nodes" in workflow
        assert "edges" in workflow
        assert len(workflow["nodes"]) > 0

    def test_planner_includes_dicom_reader(self):
        """Workflow should include DICOMReader node."""
        from src.planner.planner import PlanningAgent

        agent = PlanningAgent({})
        workflow = agent.plan("分析这个DICOM文件")

        node_types = [n["type"] for n in workflow["nodes"]]
        assert "DICOMReader" in node_types

    def test_planner_output_has_valid_structure(self):
        """Workflow output should have valid node/edge structure."""
        from src.planner.planner import PlanningAgent

        agent = PlanningAgent({})
        workflow = agent.plan("做分割")

        # Each node should have id, type
        for node in workflow["nodes"]:
            assert "id" in node
            assert "type" in node

        # Edges should reference node ids
        for edge in workflow["edges"]:
            assert isinstance(edge, (list, tuple))
            assert len(edge) == 2

    def test_planner_selects_model_based_on_task(self):
        """Planner should select appropriate model based on task."""
        from src.planner.planner import PlanningAgent

        agent = PlanningAgent({})

        # Segmentation task -> should include model operator
        seg_workflow = agent.plan("分割这个图像")
        node_types = [n["type"] for n in seg_workflow["nodes"]]
        assert "ModelOperator" in node_types

        # Detection task -> should include model operator
        det_workflow = agent.plan("检测病灶")
        node_types = [n["type"] for n in det_workflow["nodes"]]
        assert "ModelOperator" in node_types

    def test_planner_to_yaml(self):
        """Planner should be able to output YAML."""
        from src.planner.planner import PlanningAgent

        agent = PlanningAgent({})
        workflow = agent.plan("分析")

        yaml_output = agent.to_yaml(workflow)
        assert "nodes:" in yaml_output
        assert "DICOMReader" in yaml_output