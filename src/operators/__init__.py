"""DICOM Platform Operators."""
from .base import (
  DICOMReader,
  MetaExtractor,
  USPreprocess,
  ModelOperator,
  MeasurementOperator,
  ReportGenerator,
)
from .batch import (
  BatchDirectoryScanner,
  BatchProcessor,
  BatchResultAggregator,
  BatchReportGenerator,
)
from .dicomweb_client import DICOMWebClient, create_orthanc_client
from .dicomweb_operator import DICOMWebOperator, DICOMWebStoreOperator
from .onnx_runner import ONNXRunner
from .carotid_plaque import CarotidPlaqueDetector
from .deidentifier import DICOMDeidentifier, DeidAuditLogger

__all__ = [
  "DICOMReader",
  "MetaExtractor",
  "USPreprocess",
  "ModelOperator",
  "MeasurementOperator",
  "ReportGenerator",
  "BatchDirectoryScanner",
  "BatchProcessor",
  "BatchResultAggregator",
  "BatchReportGenerator",
  "ONNXRunner",
  "DICOMWebClient",
  "create_orthanc_client",
  "DICOMWebOperator",
  "DICOMWebStoreOperator",
  "CarotidPlaqueDetector",
  "DICOMDeidentifier",
  "DeidAuditLogger",
  "BUILTIN_OPERATORS",
]

# List of all builtin operators for auto-registration
BUILTIN_OPERATORS = [
  DICOMReader,
  MetaExtractor,
  USPreprocess,
  ModelOperator,
  MeasurementOperator,
  ReportGenerator,
  CarotidPlaqueDetector,
  BatchDirectoryScanner,
  BatchProcessor,
  BatchResultAggregator,
  BatchReportGenerator,
  DICOMDeidentifier,
]