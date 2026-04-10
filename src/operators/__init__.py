"""DICOM Platform Operators."""
from .base import (
    DICOMReader,
    MetaExtractor,
    USPreprocess,
    ModelOperator,
    MeasurementOperator,
    ReportGenerator,
)
from .dicomweb_client import DICOMWebClient, create_orthanc_client
from .dicomweb_operator import DICOMWebOperator, DICOMWebStoreOperator
from .onnx_runner import ONNXRunner
from .carotid_plaque import CarotidPlaqueDetector

__all__ = [
    "DICOMReader",
    "MetaExtractor",
    "USPreprocess",
    "ModelOperator",
    "MeasurementOperator",
    "ReportGenerator",
    "ONNXRunner",
    "DICOMWebClient",
    "create_orthanc_client",
    "DICOMWebOperator",
    "DICOMWebStoreOperator",
    "CarotidPlaqueDetector",
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
]