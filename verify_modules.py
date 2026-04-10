"""Verify each module with real DICOM data."""
import sys
import os

# Fix Windows console encoding
os.environ["PYTHONIOENCODING"] = "utf-8"

# Test data path
DICOM_PATH = "data/20251015_100893_0001_20251016_114732235/Anonymous Anonymous Anonymous_20251015_100893_0001/DICOM/PAT00001/STU00001/SER00001/I0000001"


def test_dicom_reader():
    """Test 1: DICOM Reader"""
    print("\n" + "=" * 50)
    print("Test 1: DICOM Reader")
    print("=" * 50)

    from src.operators import DICOMReader

    op = DICOMReader({})
    result = op.run({"path": DICOM_PATH})

    success = result.get("image") is not None and "error" not in result
    print(f"  [PASS] DICOM read: {result.get('meta', {}).get('modality')}")
    print(f"  [PASS] Image loaded: {result.get('image') is not None}")
    print(f"  Status: {'PASS' if success else 'FAIL'}")
    return success


def test_meta_extractor():
    """Test 2: Metadata Extraction"""
    print("\n" + "=" * 50)
    print("Test 2: Metadata Extraction")
    print("=" * 50)

    from src.operators import DICOMReader, MetaExtractor

    # First read the DICOM
    reader = DICOMReader({})
    ctx = reader.run({"path": DICOM_PATH})

    # Then extract metadata
    op = MetaExtractor({})
    result = op.run(ctx)

    success = result.get("extracted_meta") is not None
    meta = result.get("extracted_meta", {})
    print(f"  [PASS] Modality: {meta.get('modality')}")
    print(f"  [INFO] Pixel Spacing: {meta.get('pixel_spacing')}")
    print(f"  Status: {'PASS' if success else 'FAIL'}")
    return success


def test_operators_registry():
    """Test 3: Registry and Plugin Discovery"""
    print("\n" + "=" * 50)
    print("Test 3: Registry & Plugin Discovery")
    print("=" * 50)

    from src.core import get_registry

    registry = get_registry()
    operators = registry.list_operators()

    print(f"  [PASS] Registered operators: {len(operators)}")
    for op in operators:
        print(f"    - {op}")

    # Test query methods
    detection = registry.list_by_task("detection")
    segmentation = registry.list_by_task("segmentation")
    print(f"  [INFO] Detection operators: {detection}")
    print(f"  [INFO] Segmentation operators: {segmentation}")

    success = len(operators) >= 6
    print(f"  Status: {'PASS' if success else 'FAIL'}")
    return success


def test_planner():
    """Test 4: LLM Planner"""
    print("\n" + "=" * 50)
    print("Test 4: LLM Planner")
    print("=" * 50)

    from src.planner import PlanningAgent

    agent = PlanningAgent({})

    # Test Chinese instruction
    wf = agent.plan("分析这个超声病例，找出斑块并测量最大径")
    nodes = wf.get("nodes", [])
    types = [n.get("type") for n in nodes]

    print(f"  [PASS] Workflow nodes: {len(nodes)}")
    print(f"  [INFO] Node types: {types}")

    # Test YAML output
    yaml_str = agent.to_yaml(wf)
    print(f"  [PASS] YAML output: {len(yaml_str)} chars")

    success = len(nodes) >= 4
    print(f"  Status: {'PASS' if success else 'FAIL'}")
    return success


def test_executor():
    """Test 5: Workflow Executor"""
    print("\n" + "=" * 50)
    print("Test 5: Workflow Executor")
    print("=" * 50)

    from src.planner import PlanningAgent
    from src.executor import execute_workflow

    # Create workflow
    agent = PlanningAgent({})
    wf = agent.plan("分析这个超声病例，找出斑块")

    # Execute
    result = execute_workflow(wf, {"path": DICOM_PATH})

    has_report = "report" in result
    print(f"  [PASS] Has report: {has_report}")
    if has_report:
        report = result["report"]
        print(f"  [INFO] Report keys: {list(report.keys())}")

    # Check for errors
    errors = [k for k in result.keys() if k.endswith("_error")]
    print(f"  [INFO] Errors: {errors}")

    success = has_report
    print(f"  Status: {'PASS' if success else 'FAIL'}")
    return success


def test_onnx_runner():
    """Test 6: ONNX Runner (basic)"""
    print("\n" + "=" * 50)
    print("Test 6: ONNX Runner (Import)")
    print("=" * 50)

    try:
        from src.operators import ONNXRunner
        import numpy as np

        # Test preprocessing without actual model
        runner = ONNXRunner.__new__(ONNXRunner)
        runner.model_path = "dummy.onnx"
        runner.providers = ["CPUExecutionProvider"]
        runner.session = None

        # Test preprocess
        img = np.random.rand(3, 224, 224).astype(np.float32)
        processed = runner.preprocess(img, (224, 224))

        print(f"  [PASS] ONNXRunner import: OK")
        print(f"  [PASS] Preprocess shape: {processed.shape}")

        success = processed.shape == (1, 3, 224, 224)
        print(f"  Status: {'PASS' if success else 'FAIL'}")
        return success
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_dicomweb_client():
    """Test 7: DICOMweb Client (import)"""
    print("\n" + "=" * 50)
    print("Test 7: DICOMweb Client (Import)")
    print("=" * 50)

    try:
        from src.operators import DICOMWebClient, create_orthanc_client

        # Just test import and instantiation
        client = create_orthanc_client("http://localhost:8042")
        print(f"  [PASS] DICOMWebClient import: OK")
        print(f"  [INFO] Base URL: {client.base_url}")

        success = True
        print(f"  Status: {'PASS' if success else 'FAIL'}")
        return success
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_cli():
    """Test 8: CLI (import)"""
    print("\n" + "=" * 50)
    print("Test 8: CLI (Import)")
    print("=" * 50)

    try:
        from src import cli

        print(f"  [PASS] CLI import: OK")
        success = True
        print(f"  Status: {'PASS' if success else 'FAIL'}")
        return success
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_server():
    """Test 9: API Server (import)"""
    print("\n" + "=" * 50)
    print("Test 9: API Server (Import)")
    print("=" * 50)

    try:
        from src import server

        print(f"  [PASS] Server import: OK")
        success = True
        print(f"  Status: {'PASS' if success else 'FAIL'}")
        return success
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 50)
    print("DICOM Agent Toolkit - Module Verification")
    print(f"Test data: {DICOM_PATH}")
    print("=" * 50)

    tests = [
        ("DICOM Reader", test_dicom_reader),
        ("Metadata Extraction", test_meta_extractor),
        ("Registry & Plugins", test_operators_registry),
        ("LLM Planner", test_planner),
        ("Workflow Executor", test_executor),
        ("ONNX Runner", test_onnx_runner),
        ("DICOMweb Client", test_dicomweb_client),
        ("CLI", test_cli),
        ("API Server", test_server),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"  [FAIL] Exception: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\nTotal: {passed}/{total} passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())