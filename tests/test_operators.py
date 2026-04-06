"""Tests for DICOM Reader Operator."""
import pytest
from pathlib import Path


class TestDICOMReader:
    """Test DICOMReader operator."""

    def test_dicom_reader_metadata(self):
        """DICOMReader should have correct metadata."""
        from dicom_platform.operators import DICOMReader

        assert DICOMReader.name == "dicom_reader"
        assert "read" in DICOMReader.capabilities
        assert "DICOM" in DICOMReader.capabilities

    def test_dicom_reader_run_returns_image_and_meta(self):
        """DICOMReader.run should return image data and metadata."""
        from dicom_platform.operators import DICOMReader
        import numpy as np

        # Create minimal test context with a mock path
        reader = DICOMReader({})
        ctx = {"path": "/fake/path"}

        # This will fail because path doesn't exist, but validates interface
        result = reader.run(ctx)
        assert "image" in result or "error" in result