# Operators Module

## Overview
Built-in operators for DICOM processing pipeline.

## Available Operators

### DICOMReader

Read DICOM files from path.

```python
from src.operators import DICOMReader

reader = DICOMReader({})
ctx = {"path": "/path/to/dicom/or/folder"}
result = reader.run(ctx)
# result["image"] = numpy array
# result["meta"] = DICOM metadata dict
```

**Capabilities:** `read`, `DICOM`

**Input:**
| Field | Type | Description |
|-------|------|-------------|
| `path` | str | Path to DICOM file or directory |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| `image` | ndarray | Image data (None if not implemented) |
| `meta` | dict | Metadata including modality, pixel_spacing, etc. |

---

### MetaExtractor

Extract metadata from DICOM files.

```python
from src.operators import MetaExtractor

extractor = MetaExtractor({})
ctx = {
    "meta": {"modality": "CT", "pixel_spacing": [0.5, 0.5]}
}
result = extractor.run(ctx)
# result["extracted_meta"] = {...}
```

**Capabilities:** `metadata`, `extract`

**Input:**
| Field | Type | Description |
|-------|------|-------------|
| `image` | ndarray | Image data |
| `meta` | dict | Raw DICOM metadata |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| `extracted_meta` | dict | Extracted fields (PixelSpacing, ImageOrientation, etc.) |

---

### USPreprocess

Preprocess ultrasound images.

```python
from src.operators import USPreprocess

preprocessor = USPreprocess({})
ctx = {
    "image": image_array,
    "extracted_meta": {"pixel_spacing": [0.5, 0.5]}
}
result = preprocessor.run(ctx)
# result["preprocessed_image"] = processed_image
```

**Capabilities:** `preprocess`, `ultrasound`

**Input:**
| Field | Type | Description |
|-------|------|-------------|
| `image` | ndarray | Input ultrasound image |
| `extracted_meta` | dict | Image metadata |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| `preprocessed_image` | ndarray | Preprocessed image |

---

### ModelOperator

Run model inference (segmentation/detection).

```python
from src.operators import ModelOperator

model = ModelOperator({"model": "my_seg_model"})
ctx = {
    "preprocessed_image": image_array,
}
result = model.run(ctx)
# result["predictions"] = mask
# result["probabilities"] = confidence scores
```

**Capabilities:** `inference`, `model`, `segmentation`, `detection`

**Input:**
| Field | Type | Description |
|-------|------|-------------|
| `preprocessed_image` | ndarray | Preprocessed input image |
| `model` | str | (optional) Model name from config |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| `predictions` | ndarray | Segmentation mask or detection boxes |
| `probabilities` | ndarray | Confidence scores |

---

### MeasurementOperator

Compute measurements from segmentation results.

```python
from src.operators import MeasurementOperator

measurer = MeasurementOperator({})
ctx = {
    "predictions": mask_array,
    "extracted_meta": {"pixel_spacing": [0.5, 0.5]}
}
result = measurer.run(ctx)
# result["measurements"] = [{"area_mm2": 123.4, "diameter_mm": 12.5}, ...]
```

**Capabilities:** `measurement`, `quantification`

**Input:**
| Field | Type | Description |
|-------|------|-------------|
| `predictions` | ndarray | Segmentation mask |
| `extracted_meta` | dict | Pixel spacing for physical units |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| `measurements` | list[dict] | List of measurements (area, volume, diameter) |

---

### ReportGenerator

Generate structured analysis reports.

```python
from src.operators import ReportGenerator

generator = ReportGenerator({})
ctx = {
    "measurements": [{"area_mm2": 123.4}],
    "extracted_meta": {"modality": "CT"}
}
result = generator.run(ctx)
# result["report"] = {...}
```

**Capabilities:** `report`, `output`

**Input:**
| Field | Type | Description |
|-------|------|-------------|
| `measurements` | list[dict] | Measurement results |
| `extracted_meta` | dict | Image metadata |

**Output:**
| Field | Type | Description |
|-------|------|-------------|
| `report` | dict | Structured report (summary, measurements, metadata) |

---

## Using with Registry

```python
from src.core import get_registry

registry = get_registry()

# List all operators
print(registry.list_operators())
# ['dicom_reader', 'meta_extractor', 'us_preprocess', ...]

# Get by capability
segmentation_ops = registry.list_by_capability("segmentation")

# Instantiate
op = registry.get("dicom_reader", {})
```