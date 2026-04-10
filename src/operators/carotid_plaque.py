"""Carotid plaque detection operator."""
import numpy as np
from typing import List, Dict, Any, Optional

from src.core import OperatorBase, OperatorMeta
from src.core.task_capability import TaskCapability


class CarotidPlaqueDetector(OperatorBase):
    """Detect carotid plaque in ultrasound images."""

    name = "carotid_plaque_detector"
    version = "0.1.0"
    capabilities = [
        "detection",
        "carotid",
        "plaque",
        "ultrasound",
        "vessel",
    ]
    input_schema = {
        "image": "ndarray",
        "meta": "dict",
    }
    output_schema = {
        "detections": "list",
        "plaque_masks": "list",
        "confidence_scores": "list",
    }

    # Define capability for plugin discovery
    task_capability = TaskCapability(
        task="detection",
        target="plaque",
        target_region="carotid",
        input_format="image_2d",
        output_formats=["bbox", "mask", "confidence"],
        model_framework="onnx",
        model_input_size=(512, 512),
        conditions={"modality": ["US"], "body_part": ["neck"]},
    )

    def __init__(self, config: dict):
        super().__init__(config)
        self.model_path = config.get("model_path")
        self.confidence_threshold = config.get("confidence_threshold", 0.5)
        self.runner = None

    def _get_runner(self):
        """Get ONNX model runner."""
        if self.runner is None:
            from .onnx_runner import ONNXRunner

            model_path = self.model_path or self._get_default_model_path()
            self.runner = ONNXRunner(model_path).load()
        return self.runner

    def _get_default_model_path(self) -> str:
        """Get default model path. Override to provide your own model."""
        # Default looking for model in common locations
        import os
        for path in [
            "models/carotid_plaque.onnx",
            "models/plaque_detector.onnx",
            "data/models/carotid_plaque.onnx",
        ]:
            if os.path.exists(path):
                return path
        return "models/carotid_plaque.onnx"

    def run(self, ctx: dict) -> dict:
        """Detect carotid plaque in ultrasound image.

        Args:
            ctx: Must contain 'image' (numpy array) and optionally 'meta'.

        Returns:
            ctx with detection results:
            - detections: List of dicts with bbox, label, score
            - plaque_masks: List of binary masks
            - confidence_scores: List of confidence scores
        """
        image = ctx.get("image")
        if image is None:
            ctx["error"] = "No image provided"
            ctx["detections"] = []
            return ctx

        try:
            # Preprocess
            processed = self._preprocess(image)

            # Run inference (or use demo mode)
            if self.model_path and self._model_exists():
                runner = self._get_runner()
                output = runner.inference(processed)
                predictions = self._postprocess(output, image.shape)
            else:
                # Demo mode: simple threshold-based detection
                predictions = self._demo_detection(image)

            # Extract results
            ctx["detections"] = predictions.get("detections", [])
            ctx["plaque_masks"] = predictions.get("masks", [])
            ctx["confidence_scores"] = predictions.get("scores", [])

            # Summary
            ctx["detection_summary"] = {
                "num_plaques": len(ctx["detections"]),
                "max_confidence": max(ctx["confidence_scores"]) if ctx["confidence_scores"] else 0,
                "has_plaque": len(ctx["detections"]) > 0,
            }

        except Exception as e:
            ctx["error"] = f"Plaque detection failed: {e}"
            ctx["detections"] = []
            ctx["plaque_masks"] = []

        return ctx

    def _model_exists(self) -> bool:
        """Check if model file exists."""
        import os
        if self.model_path:
            return os.path.exists(self.model_path)
        return False

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input."""
        import cv2

        # Handle different input formats
        # HWC (H, W, C) -> CHW
        if len(image.shape) == 3 and image.shape[2] <= 4:
            # Image is HWC format
            h, w, c = image.shape
            image = image.transpose(2, 0, 1)  # HWC -> CHW
        elif len(image.shape) == 2:
            # Grayscale
            image = np.stack([image] * 3, axis=0)
        elif len(image.shape) == 3 and image.shape[0] <= 4:
            # Already CHW format
            pass

        # Resize to model input size
        target_size = self.task_capability.model_input_size or (512, 512)
        image = cv2.resize(image.transpose(1, 2, 0), target_size).transpose(2, 0, 1)

        # Normalize
        image = image.astype(np.float32) / 255.0

        # Add batch dimension
        return np.expand_dims(image, axis=0)

    def _postprocess(self, output: np.ndarray, original_shape: tuple) -> dict:
        """Postprocess model output to detection results."""
        # This depends on model architecture
        # Assuming output is (1, 1, H, W) segmentation mask
        mask = output[0, 0]

        # Find connected components
        import cv2
        _, binary = cv2.threshold(mask, 0.5, 1, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(
            binary.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        detections = []
        masks = []
        scores = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)

            # Filter small detections
            if area < 100:
                continue

            # Get confidence from mask region
            roi = mask[y : y + h, x : x + w]
            score = float(roi.mean())

            if score < self.confidence_threshold:
                continue

            detections.append(
                {
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "label": "plaque",
                    "area_mm2": self._estimate_area(area),
                }
            )
            masks.append((binary * 255).astype(np.uint8))
            scores.append(score)

        return {"detections": detections, "masks": masks, "scores": scores}

    def _demo_detection(self, image: np.ndarray) -> dict:
        """Demo detection using simple thresholding."""
        import cv2

        # Normalize image
        if image.max() > 1:
            image = image.astype(np.float32) / 255.0

        # Simple edge/region detection
        gray = (image[0] * 255).astype(np.uint8) if len(image.shape) == 3 else (image * 255).astype(np.uint8)

        # Apply threshold to find bright regions (potential plaque)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections = []
        masks = []
        scores = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 200:  # Filter noise
                continue

            x, y, w, h = cv2.boundingRect(contour)

            # Simple confidence based on area
            score = min(0.9, 0.3 + area / 10000)

            detections.append(
                {
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "label": "plaque",
                    "area_mm2": self._estimate_area(area),
                }
            )

            mask = np.zeros_like(gray)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            masks.append(mask)
            scores.append(score)

        return {"detections": detections, "masks": masks, "scores": scores}

    def _estimate_area(self, pixel_area: int) -> float:
        """Estimate real area in mm² from pixel area."""
        # This requires pixel spacing from DICOM metadata
        # For demo, assume 0.1mm per pixel
        return pixel_area * 0.01


# Register operator metadata for auto-discovery
OPERATOR_META = OperatorMeta(
    name=CarotidPlaqueDetector.name,
    version=CarotidPlaqueDetector.version,
    capabilities=[CarotidPlaqueDetector.task_capability],
    input_schema=CarotidPlaqueDetector.input_schema,
    output_schema=CarotidPlaqueDetector.output_schema,
    description="Detect carotid plaque in ultrasound images using deep learning",
)