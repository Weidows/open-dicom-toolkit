"""Tests for batch processing operators."""
import os
import tempfile
import pytest
from pathlib import Path

from src.operators.batch import (
  BatchDirectoryScanner,
  BatchProcessor,
  BatchResultAggregator,
  BatchReportGenerator,
)


class TestBatchDirectoryScanner:
  """Tests for BatchDirectoryScanner."""

  def test_scan_empty_directory(self):
    """Test scanning empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
      scanner = BatchDirectoryScanner({})
      ctx = scanner.run({"directory": tmpdir})

      assert ctx["total_count"] == 0
      assert ctx["file_list"] == []

  def test_scan_directory_with_files(self):
    """Test scanning directory with DICOM files."""
    with tempfile.TemporaryDirectory() as tmpdir:
      # Create some test files
      for i in range(3):
        file_path = os.path.join(tmpdir, f"test_{i}.dcm")
        with open(file_path, "w") as f:
          f.write("")

      scanner = BatchDirectoryScanner({})
      ctx = scanner.run({"directory": tmpdir})

      assert ctx["total_count"] == 3
      assert len(ctx["file_list"]) == 3
      assert all(f.endswith(".dcm") for f in ctx["file_list"])

  def test_scan_nonexistent_directory(self):
    """Test scanning nonexistent directory."""
    scanner = BatchDirectoryScanner({})
    ctx = scanner.run({"directory": "/nonexistent/path"})

    assert ctx.get("error") is not None
    assert ctx["total_count"] == 0


class TestBatchProcessor:
  """Tests for BatchProcessor."""

  def test_process_empty_file_list(self):
    """Test processing empty file list."""
    processor = BatchProcessor({})
    ctx = processor.run({"file_list": []})

    assert ctx["success_count"] == 0
    assert ctx["failure_count"] == 0
    assert ctx["results"] == []

  def test_process_nonexistent_files(self):
    """Test processing nonexistent files."""
    processor = BatchProcessor({})
    ctx = processor.run({
      "file_list": ["/nonexistent/file1.dcm", "/nonexistent/file2.dcm"],
    })

    assert ctx["success_count"] == 0
    assert ctx["failure_count"] == 2
    assert len(ctx["results"]) == 2

  def test_stop_flag(self):
    """Test stop flag functionality."""
    processor = BatchProcessor({})
    assert processor._stop_flag is False

    processor.stop()
    assert processor._stop_flag is True


class TestBatchResultAggregator:
  """Tests for BatchResultAggregator."""

  def test_aggregate_empty_results(self):
    """Test aggregating empty results."""
    aggregator = BatchResultAggregator({})
    ctx = aggregator.run({"results": []})

    assert ctx["aggregated_report"]["total_files"] == 0
    assert ctx["statistics"] == {}

  def test_aggregate_successful_results(self):
    """Test aggregating successful results."""
    results = [
      {"file_path": "/path/file1.dcm", "file_name": "file1.dcm",
       "processing_time": 1.5, "image": None, "meta": {}},
      {"file_path": "/path/file2.dcm", "file_name": "file2.dcm",
       "processing_time": 2.0, "image": None, "meta": {}},
    ]

    aggregator = BatchResultAggregator({})
    ctx = aggregator.run({"results": results})

    assert ctx["aggregated_report"]["total_files"] == 2
    assert ctx["aggregated_report"]["successful"] == 2
    assert ctx["aggregated_report"]["failed"] == 0
    assert ctx["aggregated_report"]["success_rate"] == 1.0
    assert ctx["statistics"]["average_processing_time"] == 1.75

  def test_aggregate_mixed_results(self):
    """Test aggregating mixed results (success and failure)."""
    results = [
      {"file_path": "/path/file1.dcm", "file_name": "file1.dcm",
       "processing_time": 1.5, "image": None},
      {"file_path": "/path/file2.dcm", "file_name": "file2.dcm",
       "processing_time": 2.0, "error": "Failed to read"},
    ]

    aggregator = BatchResultAggregator({})
    ctx = aggregator.run({"results": results})

    assert ctx["aggregated_report"]["total_files"] == 2
    assert ctx["aggregated_report"]["successful"] == 1
    assert ctx["aggregated_report"]["failed"] == 1
    assert len(ctx["aggregated_report"]["failed_files"]) == 1

  def test_aggregate_with_findings(self):
    """Test aggregating results with detections."""
    results = [
      {
        "file_path": "/path/file1.dcm",
        "file_name": "file1.dcm",
        "detections": [{"label": "plaque", "confidence": 0.9}],
        "processing_time": 1.5,
      },
      {
        "file_path": "/path/file2.dcm",
        "file_name": "file2.dcm",
        "processing_time": 2.0,
      },
    ]

    aggregator = BatchResultAggregator({})
    ctx = aggregator.run({"results": results})

    assert len(ctx["aggregated_report"]["findings"]) == 1
    assert ctx["statistics"]["total_findings"] == 1


class TestBatchReportGenerator:
  """Tests for BatchReportGenerator."""

  def test_generate_json_report(self):
    """Test generating JSON report."""
    with tempfile.TemporaryDirectory() as tmpdir:
      generator = BatchReportGenerator({})
      ctx = generator.run({
        "aggregated_report": {
          "total_files": 2,
          "successful": 2,
          "failed": 0,
          "success_rate": 1.0,
          "findings": [],
          "measurements": [],
          "failed_files": [],
        },
        "statistics": {"total_processing_time": 3.5},
        "output_format": "json",
        "output_dir": tmpdir,
      })

      assert ctx["report_file"] is not None
      assert ctx["report_file"].endswith(".json")
      assert os.path.exists(ctx["report_file"])

  def test_generate_csv_report(self):
    """Test generating CSV report."""
    with tempfile.TemporaryDirectory() as tmpdir:
      generator = BatchReportGenerator({})
      ctx = generator.run({
        "aggregated_report": {
          "total_files": 2,
          "successful": 2,
          "failed": 0,
          "success_rate": 1.0,
          "findings": [
            {"label": "plaque", "confidence": 0.9, "bbox": [1, 2, 3, 4]},
          ],
          "measurements": [],
          "failed_files": [],
        },
        "statistics": {"total_processing_time": 3.5},
        "output_format": "csv",
        "output_dir": tmpdir,
      })

      assert ctx["report_file"] is not None
      assert ctx["report_file"].endswith(".csv")
      assert os.path.exists(ctx["report_file"])