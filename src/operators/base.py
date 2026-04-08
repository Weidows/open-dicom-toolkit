"""Base operators for DICOM processing."""
from typing import Any

from src.core import OperatorBase, OperatorMeta


class DICOMReader(OperatorBase):
    """Read DICOM files from path."""

    name = "dicom_reader"
    version = "0.1.0"
    capabilities = ["read", "DICOM"]
    input_schema = {"path": "str"}
    output_schema = {"image": "ndarray", "meta": "dict"}

    def run(self, ctx: dict) -> dict:
        """Read DICOM file(s) from path.

        Args:
            ctx: Must contain 'path' key with DICOM file or directory path.

        Returns:
            ctx with 'image' and 'meta' keys populated.
        """
        import os

        path = ctx.get("path")
        if not path:
            ctx["error"] = "No path provided"
            return ctx

        if not os.path.exists(path):
            ctx["error"] = f"Path not found: {path}"
            return ctx

        # TODO: Implement actual DICOM reading with pydicom
        # Placeholder implementation
        ctx["meta"] = {
            "path": path,
            "modality": "UNKNOWN",
            "pixel_spacing": None,
        }
        ctx["image"] = None

        return ctx


class MetaExtractor(OperatorBase):
    """Extract metadata from DICOM files."""

    name = "meta_extractor"
    version = "0.1.0"
    capabilities = ["metadata", "extract"]
    input_schema = {"image": "ndarray", "meta": "dict"}
    output_schema = {"extracted_meta": "dict"}

    def run(self, ctx: dict) -> dict:
        """Extract relevant metadata from DICOM.

        Args:
            ctx: Should contain 'meta' from DICOMReader.

        Returns:
            ctx with 'extracted_meta' containing pixel spacing, orientation, etc.
        """
        meta = ctx.get("meta", {})

        extracted = {
            "pixel_spacing": meta.get("pixel_spacing"),
            "image_orientation": meta.get("image_orientation"),
            "image_position": meta.get("image_position"),
            "modality": meta.get("modality"),
            "series_instance_uid": meta.get("series_instance_uid"),
            "sop_instance_uid": meta.get("sop_instance_uid"),
        }

        ctx["extracted_meta"] = extracted
        return ctx


class USPreprocess(OperatorBase):
    """Preprocess ultrasound images."""

    name = "us_preprocess"
    version = "0.1.0"
    capabilities = ["preprocess", "ultrasound"]
    input_schema = {"image": "ndarray", "extracted_meta": "dict"}
    output_schema = {"preprocessed_image": "ndarray"}

    def run(self, ctx: dict) -> dict:
        """Preprocess ultrasound image.

        Args:
            ctx: Contains 'image' and 'extracted_meta'.

        Returns:
            ctx with 'preprocessed_image'.
        """
        image = ctx.get("image")
        if image is None:
            ctx["preprocessed_image"] = None
            return ctx

        # TODO: Implement actual preprocessing
        # - Denoising
        # - Normalization
        # - Resize
        # - Frame sampling for cine
        ctx["preprocessed_image"] = image

        return ctx


class ModelOperator(OperatorBase):
    """Run model inference using ONNX Runtime."""

    name = "model_operator"
    version = "0.1.0"
    capabilities = ["inference", "model", "segmentation", "detection"]
    input_schema = {"preprocessed_image": "ndarray", "model_name": "str"}
    output_schema = {"predictions": "ndarray", "probabilities": "ndarray"}

    def __init__(self, config: dict):
        super().__init__(config)
        self.model_path = config.get("model_path")
        self.model_name = config.get("model", "default")
        self.target_size = config.get("target_size")  # (H, W)
        self.runner = None

    def _get_runner(self, model_path: str):
        """Get or create ONNX runner."""
        if self.runner is None or (hasattr(self.runner, 'model_path') and self.runner.model_path != model_path):
            from .onnx_runner import ONNXRunner
            self.runner = ONNXRunner(model_path).load()
        return self.runner

    def run(self, ctx: dict) -> dict:
        """Run model inference.

        Args:
            ctx: Contains 'preprocessed_image' and optionally 'model' or 'model_path'.

        Returns:
            ctx with 'predictions' and 'probabilities'.
        """
        image = ctx.get("preprocessed_image")
        if image is None:
            ctx["predictions"] = None
            ctx["probabilities"] = None
            return ctx

        # Get model path from context or config
        model_path = ctx.get("model_path", self.model_path)

        # Check if model path exists
        if not model_path:
            ctx["predictions"] = None
            ctx["probabilities"] = None
            ctx["model_error"] = "No model_path provided"
            return ctx

        try:
            runner = self._get_runner(model_path)

            # Preprocess
            original_size = (image.shape[1], image.shape[2]) if image.ndim == 3 else image.shape[:2]
            preprocessed = runner.preprocess(image, self.target_size)

            # Inference
            predictions, probabilities = runner.predict(preprocessed)

            # Postprocess
            ctx["predictions"] = runner.postprocess(predictions, original_size)
            ctx["probabilities"] = runner.postprocess(probabilities, original_size)
        except Exception as e:
            ctx["model_error"] = str(e)
            ctx["predictions"] = None
            ctx["probabilities"] = None

        return ctx


class MeasurementOperator(OperatorBase):
    """Compute measurements from segmentation results."""

    name = "measurement_operator"
    version = "0.1.0"
    capabilities = ["measurement", "quantification"]
    input_schema = {"predictions": "ndarray", "extracted_meta": "dict"}
    output_schema = {"measurements": "dict"}

    def run(self, ctx: dict) -> dict:
        """Compute measurements from predictions.

        Args:
            ctx: Contains 'predictions' mask and 'extracted_meta' for pixel spacing.

        Returns:
            ctx with 'measurements' containing areas, volumes, diameters, etc.
        """
        predictions = ctx.get("predictions")
        meta = ctx.get("extracted_meta", {})

        if predictions is None:
            ctx["measurements"] = []
            return ctx

        # TODO: Implement actual measurement calculations
        # - Connected components
        # - Area/volume calculation using pixel spacing
        # - Diameter estimation
        measurements = []

        ctx["measurements"] = measurements
        return ctx


class ReportGenerator(OperatorBase):
    """Generate analysis reports."""

    name = "report_generator"
    version = "0.1.0"
    capabilities = ["report", "output"]
    input_schema = {"measurements": "dict", "extracted_meta": "dict"}
    output_schema = {"report": "dict"}

    def run(self, ctx: dict) -> dict:
        """Generate structured report.

        Args:
            ctx: Contains 'measurements' and 'extracted_meta'.

        Returns:
            ctx with 'report' containing structured output.
        """
        measurements = ctx.get("measurements", [])
        meta = ctx.get("extracted_meta", {})

        # TODO: Implement actual report generation (DICOM SR / JSON)
        report = {
            "summary": {
                "total_findings": len(measurements) if measurements else 0,
            },
            "measurements": measurements,
            "metadata": meta,
        }

        ctx["report"] = report
        return ctx