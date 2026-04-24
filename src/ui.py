"""Gradio UI for DICOM analysis."""

import logging
from pathlib import Path

from src.executor.executor import execute_workflow
from src.planner.planner import PlanningAgent

logger = logging.getLogger(__name__)


def _format_report(report: dict | str) -> str:
  """Format analysis report as markdown."""
  if isinstance(report, dict):
    lines = []
    for k, v in report.items():
      if isinstance(v, dict):
        lines.append(f"**{k}**:")
        for sk, sv in v.items():
          lines.append(f"  - {sk}: {sv}")
      else:
        lines.append(f"**{k}**: {v}")
    return "\n\n".join(lines)
  return str(report)


def analyze_dicom(file_path: str, instruction: str, model_path: str | None = None) -> str:
  """Analyze DICOM file and return report as markdown.

  Args:
    file_path: Path to uploaded DICOM file.
    instruction: Natural language analysis instruction.
    model_path: Optional path to ONNX model.

  Returns:
    Formatted analysis report.
  """
  if not file_path:
    return "Please upload a DICOM file."

  try:
    agent = PlanningAgent({})
    workflow = agent.plan(instruction)

    initial_ctx = {"path": file_path}
    if model_path and model_path.strip():
      initial_ctx["model_path"] = model_path.strip()

    result = execute_workflow(workflow, initial_ctx)
    report = result.get("report", result)

    return _format_report(report)
  except Exception as e:
    logger.exception("Analysis failed")
    return f"**Error**: {e}"


def create_ui(model_path: str | None = None) -> "gr.Blocks":
  """Create Gradio UI for DICOM analysis.

  Args:
    model_path: Default model path from config.

  Returns:
    Gradio Blocks application.
  """
  try:
    import gradio as gr
  except ImportError:
    raise ImportError("gradio is required for UI. Install with: uv pip install gradio")

  with gr.Blocks(title="DICOM Agent Toolkit") as demo:
    gr.Markdown("# DICOM Agent Toolkit")
    gr.Markdown("Upload a DICOM file and provide an analysis instruction.")

    with gr.Row():
      with gr.Column(scale=1):
        file_input = gr.File(
          label="DICOM File",
          file_types=[".dcm"],
        )
        instruction = gr.Textbox(
          label="Instruction",
          value="Analyze this DICOM study",
          lines=2,
        )
        model_path_input = gr.Textbox(
          label="Model Path (optional)",
          value=model_path or "",
          lines=1,
        )
        submit_btn = gr.Button("Analyze", variant="primary")

      with gr.Column(scale=2):
        output = gr.Markdown(label="Analysis Result")

    submit_btn.click(
      fn=analyze_dicom,
      inputs=[file_input, instruction, model_path_input],
      outputs=output,
    )

  return demo
