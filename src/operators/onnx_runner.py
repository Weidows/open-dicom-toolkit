"""ONNX Model Runner for inference."""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class ONNXRunner:
    """Load and run ONNX models."""

    def __init__(self, model_path: str, providers: list[str] = None):
        """Initialize ONNX runtime session.

        Args:
            model_path: Path to .onnx model file.
            providers: List of execution providers (e.g., ['CPUExecutionProvider']).
        """
        self.model_path = Path(model_path)
        self.providers = providers or ["CPUExecutionProvider"]
        self.session = None
        self.input_name = None
        self.output_name = None

    def load(self) -> "ONNXRunner":
        """Load the ONNX model.

        Returns:
            Self for chaining.
        """
        try:
            import onnxruntime as ort

            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )

            self.session = ort.InferenceSession(
                str(self.model_path),
                sess_options=sess_options,
                providers=self.providers,
            )

            # Get input/output names
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name

            logger.info(f"Loaded ONNX model: {self.model_path}")
            return self
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise

    def preprocess(self, image: np.ndarray, target_size: tuple = None) -> np.ndarray:
        """Preprocess image for model input.

        Args:
            image: Input image (H, W, C) or (C, H, W).
            target_size: Target size (H, W) for resizing.

        Returns:
            Preprocessed image array ready for model.
        """
        # Convert to float32 and normalize to [0, 1]
        if image.dtype != np.float32:
            image = image.astype(np.float32)

        # Handle different channel orders
        if len(image.shape) == 3 and image.shape[2] <= 4:  # HWC
            image = np.transpose(image, (2, 0, 1))  # CHW

        # Normalize
        if image.max() > 1.0:
            image = image / 255.0

        # Resize if needed
        if target_size:
            try:
                import cv2

                # Resize each channel
                if image.ndim == 3:
                    channels = [cv2.resize(c, target_size, interpolation=cv2.INTER_LINEAR)
                               for c in image]
                    image = np.stack(channels, axis=0)
            except ImportError:
                from scipy.ndimage import zoom

                zoom_factors = (1, target_size[0] / image.shape[1], target_size[1] / image.shape[2])
                image = zoom(image, zoom_factors)

        # Add batch dimension
        image = np.expand_dims(image, axis=0)

        return image

    def predict(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Run inference on image.

        Args:
            image: Preprocessed image array.

        Returns:
            Tuple of (predictions, probabilities).
        """
        if self.session is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        # Run inference
        outputs = self.session.run([self.output_name], {self.input_name: image})
        output = outputs[0]

        # Handle different output formats
        if output.shape[1] > 1:  # Classification with multiple classes
            probabilities = self._softmax(output)
            predictions = np.argmax(probabilities, axis=1)
        else:  # Binary/segmentation
            probabilities = self._sigmoid(output)
            predictions = (probabilities > 0.5).astype(np.uint8)

        return predictions, probabilities

    def postprocess(self, output: np.ndarray, original_size: tuple) -> np.ndarray:
        """Postprocess model output to original image size.

        Args:
            output: Model output array.
            original_size: Original (H, W) size.

        Returns:
            Resized output.
        """
        try:
            import cv2

            output = np.squeeze(output)
            if output.ndim == 2:
                output = cv2.resize(output, original_size, interpolation=cv2.INTER_LINEAR)
            return output
        except ImportError:
            return np.squeeze(output)

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Compute softmax probabilities."""
        exp_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Compute sigmoid probabilities."""
        return 1 / (1 + np.exp(-x))

    @classmethod
    def from_pretrained(cls, model_name: str, cache_dir: str = None) -> "ONNXRunner":
        """Load model from pretrained models directory.

        Args:
            model_name: Name of the model file.
            cache_dir: Cache directory path.

        Returns:
            Loaded ONNXRunner instance.
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "dicom-agent-toolkit" / "models"
        else:
            cache_dir = Path(cache_dir)

        model_path = cache_dir / model_name

        if not model_path.exists():
            logger.warning(f"Model not found: {model_path}")

        return cls(str(model_path)).load()