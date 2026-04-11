"""Batch processing operators for DICOM files."""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

try:
  import numpy as np
except ImportError:
  np = None

from src.core import OperatorBase, OperatorMeta, TaskCapability

logger = logging.getLogger(__name__)


class BatchDirectoryScanner(OperatorBase):
  """Scan directory for DICOM files."""

  name = "batch_directory_scanner"
  version = "0.1.0"
  capabilities = ["batch", "scan", "directory"]
  input_schema = {"directory": "str"}
  output_schema = {"file_list": "list", "total_count": "int"}

  task_capability = TaskCapability(
    task="batch",
    target="scan",
    target_region="directory",
    input_format="path",
    output_formats=["file_list"],
  )

  def run(self, ctx: dict) -> dict:
    """Scan directory for DICOM files.

    Args:
      ctx: Should contain 'directory' key.

    Returns:
      ctx with 'file_list' and 'total_count'.
    """
    directory = ctx.get("directory")
    if not directory:
      ctx["error"] = "No directory provided"
      ctx["file_list"] = []
      ctx["total_count"] = 0
      return ctx

    if not os.path.exists(directory):
      ctx["error"] = f"Directory not found: {directory}"
      ctx["file_list"] = []
      ctx["total_count"] = 0
      return ctx

    # Recursively find all .dcm files
    try:
      dcm_files = sorted(Path(directory).rglob("*.dcm"))
      file_list = [str(f) for f in dcm_files]

      ctx["file_list"] = file_list
      ctx["total_count"] = len(file_list)
      logger.info(f"Found {len(file_list)} DICOM files in {directory}")

    except Exception as e:
      ctx["error"] = f"Failed to scan directory: {e}"
      ctx["file_list"] = []
      ctx["total_count"] = 0

    return ctx


class BatchProcessor(OperatorBase):
  """Process multiple DICOM files in batch."""

  name = "batch_processor"
  version = "0.1.0"
  capabilities = ["batch", "process", "parallel"]
  input_schema = {"file_list": "list", "workflow": "dict"}
  output_schema = {"results": "list", "success_count": "int", "failure_count": "int"}

  def __init__(self, config: dict):
    super().__init__(config)
    self.max_workers = config.get("max_workers", 4)
    self.progress_callback = config.get("progress_callback")
    self._stop_flag = False

  def stop(self):
    """Stop batch processing."""
    self._stop_flag = True

  def run(self, ctx: dict) -> dict:
    """Process multiple DICOM files.

    Args:
      ctx: Should contain 'file_list' and optionally 'workflow'.

    Returns:
      ctx with 'results', 'success_count', 'failure_count'.
    """
    file_list = ctx.get("file_list", [])
    workflow = ctx.get("workflow", None)

    if not file_list:
      ctx["results"] = []
      ctx["success_count"] = 0
      ctx["failure_count"] = 0
      return ctx

    results = []
    success_count = 0
    failure_count = 0

    # If no workflow defined, just read files
    if workflow is None:
      results = self._process_simple_batch(file_list, ctx)
    else:
      results = self._process_workflow_batch(file_list, workflow, ctx)

    # Count successes and failures
    for r in results:
      if r.get("error"):
        failure_count += 1
      else:
        success_count += 1

    ctx["results"] = results
    ctx["success_count"] = success_count
    ctx["failure_count"] = failure_count
    ctx["total_processed"] = len(file_list)

    logger.info(f"Batch processing complete: {success_count} succeeded, {failure_count} failed")

    return ctx

  def _process_simple_batch(self, file_list: List[str], ctx: dict) -> List[dict]:
    """Process files with simple read operation."""
    results = []

    # Import here to avoid circular imports
    from src.executor.executor import WorkflowExecutor

    # Simple workflow for reading
    read_workflow = {
      "nodes": [
        {"id": "reader", "type": "dicom_reader", "params": {}},
        {"id": "extractor", "type": "meta_extractor", "params": {}},
      ],
      "edges": [["reader", "extractor"]],
    }

    total = len(file_list)
    for i, file_path in enumerate(file_list):
      if self._stop_flag:
        logger.info("Batch processing stopped by user")
        break

      start_time = time.time()
      result = {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
      }

      try:
        executor = WorkflowExecutor(read_workflow)
        output = executor.execute({"path": file_path})

        if output.get("error"):
          result["error"] = output["error"]
        else:
          result["image"] = output.get("image")
          result["meta"] = output.get("meta", {})
          result["extracted_meta"] = output.get("extracted_meta", {})

      except Exception as e:
        result["error"] = str(e)

      result["processing_time"] = time.time() - start_time
      results.append(result)

      # Progress callback
      if self.progress_callback:
        self.progress_callback(i + 1, total, result)

      # Log progress
      logger.info(f"Processed {i + 1}/{total}: {os.path.basename(file_path)}")

    return results

  def _process_workflow_batch(self, file_list: List[str], workflow: dict, ctx: dict) -> List[dict]:
    """Process files with custom workflow in parallel."""
    results = []
    total = len(file_list)

    def process_single(file_path: str, index: int) -> dict:
      if self._stop_flag:
        return {"file_path": file_path, "error": "Stopped by user", "index": index}

      start_time = time.time()
      result = {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "index": index,
      }

      try:
        from src.executor.executor import WorkflowExecutor
        executor = WorkflowExecutor(workflow)
        output = executor.execute({"path": file_path})
        result.update(output)

      except Exception as e:
        result["error"] = str(e)

      result["processing_time"] = time.time() - start_time

      # Progress callback
      if self.progress_callback:
        self.progress_callback(index + 1, total, result)

      logger.info(f"Processed {index + 1}/{total}: {os.path.basename(file_path)}")

      return result

    # Process in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
      futures = {
        executor.submit(process_single, fp, i): fp
        for i, fp in enumerate(file_list)
      }

      for future in as_completed(futures):
        if self._stop_flag:
          # Cancel remaining futures
          for f in futures:
            f.cancel()
          break

        try:
          result = future.result()
          results.append(result)
        except Exception as e:
          file_path = futures[future]
          results.append({
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "error": str(e),
            "processing_time": 0,
          })

    # Sort results by index to maintain order
    results.sort(key=lambda x: x.get("index", 0))

    return results


class BatchResultAggregator(OperatorBase):
  """Aggregate batch processing results."""

  name = "batch_result_aggregator"
  version = "0.1.0"
  capabilities = ["batch", "aggregate", "report"]
  input_schema = {"results": "list"}
  output_schema = {"aggregated_report": "dict", "statistics": "dict"}

  task_capability = TaskCapability(
    task="batch",
    target="aggregate",
    target_region="results",
    input_format="results_list",
    output_formats=["report", "statistics"],
  )

  def run(self, ctx: dict) -> dict:
    """Aggregate batch processing results.

    Args:
      ctx: Should contain 'results' from BatchProcessor.

    Returns:
      ctx with 'aggregated_report' and 'statistics'.
    """
    results = ctx.get("results", [])

    if not results:
      ctx["aggregated_report"] = {
        "total_files": 0,
        "successful": 0,
        "failed": 0,
        "findings": [],
      }
      ctx["statistics"] = {}
      return ctx

    # Calculate statistics
    successful = [r for r in results if not r.get("error")]
    failed = [r for r in results if r.get("error")]

    processing_times = [r.get("processing_time", 0) for r in results if r.get("processing_time")]
    avg_time = sum(processing_times) / len(processing_times) if processing_times else 0
    total_time = sum(processing_times)

    # Collect all findings/detections
    all_findings = []
    all_measurements = []

    for r in results:
      # Collect detections
      if "detections" in r:
        for det in r.get("detections", []):
          det["source_file"] = r.get("file_name", "")
          all_findings.append(det)

      # Collect measurements
      if "measurements" in r:
        for m in r.get("measurements", []):
          m["source_file"] = r.get("file_name", "")
          all_measurements.append(m)

    # Build aggregated report
    aggregated_report = {
      "total_files": len(results),
      "successful": len(successful),
      "failed": len(failed),
      "success_rate": len(successful) / len(results) if results else 0,
      "findings": all_findings,
      "measurements": all_measurements,
      "failed_files": [
        {"file": r.get("file_name", ""), "error": r.get("error", "")}
        for r in failed
      ],
    }

    # Build statistics
    statistics = {
      "total_processing_time": total_time,
      "average_processing_time": avg_time,
      "min_processing_time": min(processing_times) if processing_times else 0,
      "max_processing_time": max(processing_times) if processing_times else 0,
      "total_findings": len(all_findings),
      "total_measurements": len(all_measurements),
    }

    ctx["aggregated_report"] = aggregated_report
    ctx["statistics"] = statistics

    logger.info(
      f"Aggregated {len(results)} results: {len(successful)} successful, "
      f"{len(failed)} failed, {len(all_findings)} findings"
    )

    return ctx


class BatchReportGenerator(OperatorBase):
  """Generate batch processing reports."""

  name = "batch_report_generator"
  version = "0.1.0"
  capabilities = ["batch", "report", "export"]
  input_schema = {"aggregated_report": "dict", "statistics": "dict", "output_format": "str"}
  output_schema = {"report_file": "str", "report_content": "dict"}

  def run(self, ctx: dict) -> dict:
    """Generate batch processing report.

    Args:
      ctx: Contains 'aggregated_report' and 'statistics'.

    Returns:
      ctx with 'report_file' and 'report_content'.
    """
    aggregated_report = ctx.get("aggregated_report", {})
    statistics = ctx.get("statistics", {})
    output_format = ctx.get("output_format", "json")

    # Generate report content
    report_content = {
      "summary": {
        "total_files": aggregated_report.get("total_files", 0),
        "successful": aggregated_report.get("successful", 0),
        "failed": aggregated_report.get("failed", 0),
        "success_rate": aggregated_report.get("success_rate", 0),
      },
      "statistics": statistics,
      "findings": aggregated_report.get("findings", []),
      "measurements": aggregated_report.get("measurements", []),
      "failed_files": aggregated_report.get("failed_files", []),
    }

    ctx["report_content"] = report_content

    # Save to file if output_dir specified
    output_dir = ctx.get("output_dir", "output")
    if output_dir:
      os.makedirs(output_dir, exist_ok=True)

      if output_format == "json":
        import json
        report_file = os.path.join(output_dir, "batch_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
          json.dump(report_content, f, indent=2, ensure_ascii=False)
        ctx["report_file"] = report_file

      elif output_format == "csv":
        import csv
        report_file = os.path.join(output_dir, "batch_report.csv")

        # Flatten findings to CSV
        findings = aggregated_report.get("findings", [])
        if findings:
          fieldnames = list(findings[0].keys()) if findings else []
          with open(report_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(findings)
        else:
          # Empty CSV
          with open(report_file, "w", encoding="utf-8") as f:
            f.write("No findings\n")
        ctx["report_file"] = report_file

      logger.info(f"Batch report saved to {report_file}")

    return ctx