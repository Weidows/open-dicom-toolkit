"""Tests for OperatorBase and Registry."""
import pytest
from dataclasses import dataclass


class TestOperatorBase:
    """Test the OperatorBase abstract class."""

    def test_operator_has_required_metadata(self):
        """Operator must have name, version, capabilities."""
        from src.core.operator import OperatorBase

        # Abstract class - cannot instantiate directly
        with pytest.raises(TypeError):
            OperatorBase()

    def test_operator_subclass_has_metadata(self):
        """Concrete operator must define metadata fields."""
        from src.core.operator import OperatorBase, OperatorMeta

        meta = OperatorMeta(
            name="test_operator",
            version="1.0.0",
            capabilities=["segmentation"],
            input_schema={"image": "ndarray"},
            output_schema={"mask": "ndarray"},
        )

        assert meta.name == "test_operator"
        assert meta.version == "1.0.0"
        assert "segmentation" in meta.capabilities
        assert meta.input_schema == {"image": "ndarray"}
        assert meta.output_schema == {"mask": "ndarray"}

    def test_operator_subclass_implements_run(self):
        """Operator subclass must implement run method."""
        from src.core.operator import OperatorBase, OperatorMeta

        class DummyOperator(OperatorBase):
            def __init__(self, config: dict):
                self.config = config

            def run(self, ctx: dict) -> dict:
                ctx["result"] = "processed"
                return ctx

        operator = DummyOperator({})
        result = operator.run({})

        assert result["result"] == "processed"


class TestRegistry:
    """Test the Registry plugin system."""

    def test_registry_can_register_operator(self):
        """Registry should allow registering operators."""
        from src.core.registry import Registry
        from src.core.operator import OperatorBase, OperatorMeta

        class DummyOperator(OperatorBase):
            def __init__(self, config: dict):
                self.config = config

            def run(self, ctx: dict) -> dict:
                return ctx

        registry = Registry()
        registry.register(DummyOperator, OperatorMeta(
            name="dummy",
            version="1.0.0",
            capabilities=["test"],
            input_schema={},
            output_schema={},
        ))

        assert "dummy" in registry.list_operators()

    def test_registry_list_by_capability(self):
        """Registry should filter operators by capability."""
        from src.core.registry import Registry
        from src.core.operator import OperatorBase, OperatorMeta

        class SegmentationOp(OperatorBase):
            def __init__(self, config: dict):
                pass

            def run(self, ctx: dict) -> dict:
                return ctx

        class DetectionOp(OperatorBase):
            def __init__(self, config: dict):
                pass

            def run(self, ctx: dict) -> dict:
                return ctx

        registry = Registry()
        registry.register(SegmentationOp, OperatorMeta(
            name="seg",
            version="1.0.0",
            capabilities=["segmentation"],
            input_schema={},
            output_schema={},
        ))
        registry.register(DetectionOp, OperatorMeta(
            name="det",
            version="1.0.0",
            capabilities=["detection"],
            input_schema={},
            output_schema={},
        ))

        seg_ops = registry.list_by_capability("segmentation")
        assert "seg" in seg_ops
        assert "det" not in seg_ops

    def test_registry_get_operator(self):
        """Registry should instantiate operators by name."""
        from src.core.registry import Registry
        from src.core.operator import OperatorBase, OperatorMeta

        class MyOperator(OperatorBase):
            def __init__(self, config: dict):
                self.config = config

            def run(self, ctx: dict) -> dict:
                return ctx

        registry = Registry()
        registry.register(MyOperator, OperatorMeta(
            name="my_op",
            version="1.0.0",
            capabilities=["test"],
            input_schema={},
            output_schema={},
        ))

        operator = registry.get("my_op", {"param": "value"})
        assert operator.config == {"param": "value"}

    def test_registry_get_nonexistent_raises(self):
        """Getting non-existent operator should raise KeyError."""
        from src.core.registry import Registry

        registry = Registry()
        with pytest.raises(KeyError):
            registry.get("nonexistent", {})