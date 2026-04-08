"""CLI tool for DICOM analysis."""
import argparse
import json
import sys
from pathlib import Path

from src.planner import PlanningAgent
from src.executor import execute_workflow


def analyze(
    input_path: str,
    instruction: str = "Analyze this DICOM study",
    model_path: str = None,
    output: str = None,
) -> dict:
    """Analyze DICOM files using natural language instruction.

    Args:
        input_path: Path to DICOM file or directory.
        instruction: Natural language instruction.
        model_path: Optional path to ONNX model.
        output: Optional output file path.

    Returns:
        Analysis result dictionary.
    """
    # Plan workflow
    agent = PlanningAgent({})
    workflow = agent.plan(instruction)

    # Add model path if provided
    initial_ctx = {"path": input_path}
    if model_path:
        initial_ctx["model_path"] = model_path

    # Execute
    result = execute_workflow(workflow, initial_ctx)

    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DICOM Agent Toolkit - AI-driven DICOM analysis"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze DICOM files")
    analyze_parser.add_argument("input", help="Path to DICOM file or directory")
    analyze_parser.add_argument(
        "-i", "--instruction", default="Analyze this DICOM study",
        help="Natural language instruction"
    )
    analyze_parser.add_argument(
        "-m", "--model", help="Path to ONNX model file"
    )
    analyze_parser.add_argument(
        "-o", "--output", help="Output file path (JSON)"
    )
    analyze_parser.add_argument(
        "-y", "--yaml", action="store_true", help="Output workflow as YAML"
    )

    # Server command
    server_parser = subparsers.add_parser("server", help="Start API server")
    server_parser.add_argument(
        "--host", default="0.0.0.0", help="Server host"
    )
    server_parser.add_argument(
        "--port", type=int, default=8000, help="Server port"
    )

    args = parser.parse_args()

    if args.command == "analyze":
        # Output YAML if requested
        if getattr(args, "yaml", False):
            agent = PlanningAgent({})
            workflow = agent.plan(args.instruction)
            print(agent.to_yaml(workflow))
            return

        # Run analysis
        result = analyze(
            input_path=args.input,
            instruction=args.instruction,
            model_path=args.model,
        )

        # Output
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2, default=str))
            print(f"Results saved to {args.output}")
        else:
            print(json.dumps(result.get("report", result), indent=2, default=str))

    elif args.command == "server":
        try:
            import uvicorn
        except ImportError:
            print("Error: uvicorn not installed. Run: pip install uvicorn")
            sys.exit(1)

        from src.server import app
        uvicorn.run(app, host=args.host, port=args.port)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()