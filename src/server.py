"""FastAPI server for DICOM analysis."""
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.planner import PlanningAgent
from src.executor import execute_workflow

from fastapi_radar import Radar
from sqlalchemy import create_engine

app = FastAPI(
    title="DICOM Agent Toolkit API",
    description="AI Agent-driven DICOM medical imaging analysis",
    version="0.1.0",
)
engine = create_engine("sqlite:///./app.db")

# Full monitoring with SQL query tracking
radar = Radar(app, db_engine=engine)
radar.create_tables()

class AnalyzeRequest(BaseModel):
    """Analysis request."""

    instruction: str = "Analyze this DICOM study"
    model_path: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Analysis response."""

    report: dict
    workflow: dict
    metadata: dict


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "DICOM Agent Toolkit API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_dicom(
    file: UploadFile = File(...),
    instruction: str = "Analyze this DICOM study",
    model_path: Optional[str] = None,
):
    """Analyze a DICOM file.

    Args:
        file: DICOM file upload.
        instruction: Natural language instruction.
        model_path: Optional path to ONNX model.

    Returns:
        Analysis report and workflow.
    """
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dcm") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Plan workflow
        agent = PlanningAgent({})
        workflow = agent.plan(instruction)

        # Execute
        initial_ctx = {"path": tmp_path}
        if model_path:
            initial_ctx["model_path"] = model_path

        result = execute_workflow(workflow, initial_ctx)

        return AnalyzeResponse(
            report=result.get("report", {}),
            workflow=workflow,
            metadata={
                "instruction": instruction,
                "file_size": len(content),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/plan")
async def plan_workflow(instruction: str):
    """Generate workflow from instruction.

    Args:
        instruction: Natural language instruction.

    Returns:
        Workflow definition.
    """
    agent = PlanningAgent({})
    workflow = agent.plan(instruction)
    return {"workflow": workflow, "yaml": agent.to_yaml(workflow)}


@app.get("/operators")
async def list_operators():
    """List available operators."""
    from src.core import get_registry

    registry = get_registry()
    operators = []

    for name in registry.list_operators():
        meta = registry.get_metadata(name)
        operators.append({
            "name": meta.name,
            "version": meta.version,
            "description": meta.description,
            "input_schema": meta.input_schema,
            "output_schema": meta.output_schema,
        })

    return {"operators": operators}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
