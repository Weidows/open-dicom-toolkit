"""Base operators for DICOM processing."""
from typing import Any

try:
    import pydicom
    import numpy as np
    from pydicom.dataset import Dataset
except ImportError:
    pydicom = None
    np = None
    Dataset = None

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
        from pathlib import Path

        path = ctx.get("path")
        if not path:
            ctx["error"] = "No path provided"
            return ctx

        if not os.path.exists(path):
            ctx["error"] = f"Path not found: {path}"
            return ctx

        if pydicom is None or np is None:
            ctx["error"] = "pydicom or numpy not installed"
            return ctx

        try:
            # If path is directory, find first .dcm file
            if os.path.isdir(path):
                dcm_files = sorted(Path(path).rglob("*.dcm"))
                if not dcm_files:
                    ctx["error"] = f"No .dcm files found in {path}"
                    return ctx
                path = str(dcm_files[0])

            # Read DICOM file
            ds = pydicom.dcmread(path)

            # Extract metadata
            meta = {
                "path": path,
                "modality": str(ds.get("Modality", "UNKNOWN")),
                "patient_id": str(ds.get("PatientID", "")),
                "study_instance_uid": str(ds.get("StudyInstanceUID", "")),
                "series_instance_uid": str(ds.get("SeriesInstanceUID", "")),
                "sop_instance_uid": str(ds.get("SOPInstanceUID", "")),
                "pixel_spacing": ds.get("PixelSpacing"),
                "image_orientation": ds.get("ImageOrientationPatient"),
                "image_position": ds.get("ImagePositionPatient"),
                "rows": ds.get("Rows"),
                "columns": ds.get("Columns"),
                "bits_allocated": ds.get("BitsAllocated"),
                "bits_stored": ds.get("BitsStored"),
                "photometric_interpretation": str(ds.get("PhotometricInterpretation", "")),
            }

            # Extract pixel data
            image = None
            if hasattr(ds, "pixel_array"):
                image = ds.pixel_array

                # Handle different photometric interpretations
                if meta.get("photometric_interpretation") == "MONOCHROME1":
                    # Invert for monochrome1
                    image = image.max() - image

            ctx["meta"] = meta
            ctx["image"] = image
            ctx["dicom_dataset"] = ds  # Keep original dataset for advanced access

        except Exception as e:
            ctx["error"] = f"Failed to read DICOM: {e}"
            ctx["image"] = None
            ctx["meta"] = {"path": path, "modality": "ERROR"}

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
    """Generate analysis reports (JSON and DICOM SR)."""

    name = "report_generator"
    version = "0.1.0"
    capabilities = ["report", "output", "DICOM_SR"]
    input_schema = {"measurements": "dict", "extracted_meta": "dict", "detections": "list"}
    output_schema = {"report": "dict", "sr_file": "str"}

    def run(self, ctx: dict) -> dict:
        """Generate structured report.

        Args:
            ctx: Contains 'measurements', 'extracted_meta', 'detections'.

        Returns:
            ctx with 'report' containing structured output.
            Optionally 'sr_file' if DICOM SR generation is requested.
        """
        measurements = ctx.get("measurements", [])
        meta = ctx.get("extracted_meta", {})
        detections = ctx.get("detections", [])
        generate_sr = ctx.get("generate_sr", False)

        # Generate JSON report
        report = {
            "summary": {
                "total_findings": len(measurements) if measurements else 0,
                "total_detections": len(detections) if detections else 0,
            },
            "measurements": measurements,
            "detections": detections,
            "metadata": meta,
        }

        ctx["report"] = report

        # Generate DICOM SR if requested
        if generate_sr:
            sr_file = self._generate_sr(ctx)
            ctx["sr_file"] = sr_file

        return ctx

    def _generate_sr(self, ctx: dict) -> str:
        """Generate DICOM SR file."""
        try:
            import pydicom
            from pydicom.dataset import Dataset, FileDataset
            from pydicom.uid import generate_uid, ExplicitVRLittleEndian
            from datetime import datetime
            from pydicom.sequence import Sequence
        except ImportError:
            ctx["error"] = "pydicom not installed, cannot generate SR"
            return None

        measurements = ctx.get("measurements", [])
        detections = ctx.get("detections", [])
        meta = ctx.get("extracted_meta", {})

        # Create file meta
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.88.11"
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        file_meta.ImplementationClassUID = generate_uid()

        # Create dataset
        sr = FileDataset(None, {}, file_meta=file_meta, preamble=b'\x00' * 128)
        sr.is_little_endian = True
        sr.is_implicit_VR = False

        # Basic attributes
        sr.SOPClassUID = file_meta.MediaStorageSOPClassUID
        sr.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID

        # Patient
        sr.PatientName = meta.get("patient_name", "Anonymous^Patient")
        sr.PatientID = meta.get("patient_id", "UNKNOWN")

        # Study
        sr.StudyDate = datetime.now().strftime("%Y%m%d")
        sr.StudyTime = datetime.now().strftime("%H%M%S")
        sr.StudyInstanceUID = meta.get("study_instance_uid", generate_uid())
        sr.StudyID = "1"

        # Series
        sr.SeriesDate = sr.StudyDate
        sr.SeriesTime = sr.StudyTime
        sr.SeriesInstanceUID = generate_uid()
        sr.SeriesNumber = 1
        sr.Modality = "SR"

        # Instance
        sr.InstanceNumber = "1"
        sr.InstanceCreationDate = sr.StudyDate
        sr.InstanceCreationTime = sr.StudyTime

        # Content
        sr.ValueType = "CONTAINER"
        sr.ConceptNameCodeSequence = [self._create_code("125100", "DCM", "Imaging Measurement Report")]
        sr.ContinuityOfContent = "SEPARATE"

        # Build content sequence
        content_items = []

        # Add summary
        summary_item = Dataset()
        summary_item.RelationshipType = "CONTAINS"
        summary_item.ValueType = "TEXT"
        summary_item.ConceptNameCodeSequence = [self._create_code("121401", "DCM", "Summary")]
        summary_item.TextValue = f"Total detections: {len(detections)}, Total measurements: {len(measurements)}"
        content_items.append(summary_item)

        # Add detections as findings
        for i, detection in enumerate(detections):
            finding_item = Dataset()
            finding_item.RelationshipType = "CONTAINS"
            finding_item.ValueType = "TEXT"

            label = detection.get("label", "Unknown")
            bbox = detection.get("bbox", [])
            score = detection.get("confidence", 0)

            finding_text = f"Finding {i+1}: {label}"
            if bbox:
                finding_text += f", Location: {bbox}"
            if score:
                finding_text += f", Confidence: {score:.2f}"

            finding_item.ConceptNameCodeSequence = [self._create_code("SCTID", "SCTID", label)]
            finding_item.TextValue = finding_text
            content_items.append(finding_item)

        sr.ContentSequence = Sequence(content_items)

        # Verification
        sr.IsComplete = True
        sr.IsFinal = True
        sr.VerificationFlag = "UNVERIFIED"

        # Save
        import os
        output_dir = ctx.get("output_dir", "output")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"sr_report_{sr.SOPInstanceUID}.dcm")

        sr.save_as(output_path, write_like_original=False)
        return output_path

    def _create_code(self, code_value: str, scheme: str, meaning: str) -> Dataset:
        """Create a code sequence item."""
        code = Dataset()
        code.CodeValue = code_value
        code.CodeSchemeDesignator = scheme
        code.CodeMeaning = meaning
        return code