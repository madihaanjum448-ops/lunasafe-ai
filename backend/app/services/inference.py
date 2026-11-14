'''Inference service for Member 2.

This module loads a YOLO segmentation checkpoint (provided by Member 1) and runs
inference on an uploaded image. If the checkpoint is missing or the `ultralytics`
package is not installed, a clear HTTPException is raised so the API reports the
problem to the client.

The function `run_inference` returns a list of detection dictionaries matching the
`Detection` schema used throughout the backend.
'''  

import io
import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException

# Lazy import – the ultralytics package may not be present in test environments.
def _load_model() -> Any:
    """Load the YOLO model from a checkpoint.

    The checkpoint location is taken from the environment variable
    `LUNA_YOLO_CHECKPOINT` or defaults to ``models/member1_checkpoint.pt``
    relative to the repository root.
    """
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="ultralytics package not installed; cannot perform inference.",
        ) from exc

    checkpoint_path = os.getenv(
        "LUNA_YOLO_CHECKPOINT",
        str(Path(__file__).parents[3] / "models" / "member1_checkpoint.pt"),
    )
    if not Path(checkpoint_path).exists():
        raise HTTPException(
            status_code=500,
            detail=f"YOLO checkpoint not found at {checkpoint_path}.",
        )
    return YOLO(checkpoint_path)

# Cache the loaded model for subsequent calls.
_MODEL: Any | None = None

def _get_model() -> Any:
    global MODEL
    if MODEL is None:
        MODEL = _load_model()
    return MODEL

def run_inference(image_bytes: bytes) -> List[Dict[str, Any]]:
    """Run inference on raw image bytes.

    Returns a list of dictionaries with keys:
        id, bbox (x1, y1, x2, y2), confidence, class_name, polygon (optional).
    """
    model = _get_model()
    # The ultralytics model accepts a file‑like object.
    img = io.BytesIO(image_bytes)
    results = model(img)
    detections: List[Dict[str, Any]] = []
    det_id = 0
    for r in results:
        if getattr(r, "boxes", None) is None:
            continue
        boxes = r.boxes.xyxy.tolist()
        confidences = r.boxes.conf.tolist()
        for box, conf in zip(boxes, confidences):
            detection: Dict[str, Any] = {
                "id": det_id,
                "bbox": box,
                "confidence": conf,
                "class_name": "boulder",
                "polygon": None,
            }
            # If segmentation masks are present, convert the first mask to a polygon‑like list.
            if getattr(r, "masks", None) is not None and r.masks.data is not None:
                try:
                    # r.masks.data shape: (N, H, W). Use the first mask.
                    mask_array = r.masks.data[0].cpu().numpy()
                    detection["polygon"] = mask_array.tolist()
                except Exception:
                    # Silently ignore mask conversion errors – the detection remains valid.
                    pass
            detections.append(detection)
            det_id += 1
    return detections
