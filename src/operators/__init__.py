"""DICOM Platform Operators."""
from .base import (
    DICOMReader,
    MetaExtractor,
    USPreprocess,
    ModelOperator,
    MeasurementOperator,
    ReportGenerator,
)

__all__ = [
    "DICOMReader",
    "MetaExtractor",
    "USPreprocess",
    "ModelOperator",
    "MeasurementOperator",
    "ReportGenerator",
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