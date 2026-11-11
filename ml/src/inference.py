
from pathlib import Path
from typing import Any

import cv2
from ultralytics import YOLO


# Resolve model path relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = (
    PROJECT_ROOT / "ml" / "models" / "lunasafe_yolov8n_seg_best.pt"
)


class LunaSafeInference:
    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        confidence: float = 0.25,
        iou: float = 0.7,
        image_size: int = 640,
        device: str | int = "cpu",
    ):
        self.model_path = Path(model_path)
        self.confidence = confidence
        self.iou = iou
        self.image_size = image_size
        self.device = device

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Model checkpoint not found: {self.model_path}"
            )

        self.model = YOLO(str(self.model_path))

        if self.model.task != "segment":
            raise ValueError("Expected an instance segmentation model.")

    def predict(
        self,
        image_path: str | Path,
        confidence: float | None = None,
        pixel_scale_m: float | None = None,
        sun_elevation_deg: float | None = None,
        projection: str | None = None,
    ) -> dict[str, Any]:

        image_path = Path(image_path)

        if not image_path.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")

        original_image = cv2.imread(str(image_path))

        if original_image is None:
            raise ValueError(f"Could not read image: {image_path}")

        height, width = original_image.shape[:2]

        threshold = (
            confidence if confidence is not None else self.confidence
        )

        if not 0 <= threshold <= 1:
            raise ValueError("Confidence must be between 0 and 1.")

        result = self.model.predict(
            source=str(image_path),
            imgsz=self.image_size,
            conf=threshold,
            iou=self.iou,
            device=self.device,
            verbose=False,
        )[0]

        detections = []

        if result.boxes is not None:
            for index, box in enumerate(result.boxes):

                bbox = box.xyxy[0].cpu().numpy().tolist()
                score = float(box.conf[0].cpu().item())
                class_id = int(box.cls[0].cpu().item())

                polygon = []

                if result.masks is not None:
                    polygon = result.masks.xy[index].tolist()

                detections.append({
                    "id": index + 1,
                    "bbox": [
                        round(float(value), 2)
                        for value in bbox
                    ],
                    "confidence": round(score, 5),
                    "size_m": None,
                    "class_name": self.model.names[class_id],
                    "polygon": [
                        [
                            round(float(point[0]), 2),
                            round(float(point[1]), 2),
                        ]
                        for point in polygon
                    ],
                })

        return {
            "image": {
                "id": image_path.stem,
                "width": width,
                "height": height,
                "pixel_scale_m": pixel_scale_m,
                "sun_elevation_deg": sun_elevation_deg,
                "projection": projection,
            },
            "detections": detections,
            "model_name": "YOLOv8n-seg",
            "is_mock": False,
        }
