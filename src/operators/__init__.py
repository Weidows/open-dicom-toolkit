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
]