
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
        if not 0 <= confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1.")

        if not 0 <= iou <= 1:
            raise ValueError("IoU must be between 0 and 1.")

        if (
            isinstance(image_size, bool)
            or not isinstance(image_size, int)
            or image_size <= 0
        ):
            raise ValueError("Image size must be a positive integer.")

        self.model_path = Path(model_path)
        self.confidence = confidence
        self.iou = iou
        self.tile_nms_iou = 0.5
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

        if pixel_scale_m is not None and pixel_scale_m <= 0:
            raise ValueError("Pixel scale must be positive.")

        if sun_elevation_deg is not None and not 0 <= sun_elevation_deg <= 90:
            raise ValueError("Sun elevation must be between 0 and 90 degrees.")

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

    def predict_tiled(
        self,
        image_path: str | Path,
        tile_size: int = 1024,
        overlap: float = 0.2,
        confidence: float | None = None,
        pixel_scale_m: float | None = None,
        sun_elevation_deg: float | None = None,
        projection: str | None = None,
    ) -> dict[str, Any]:
        """Run segmentation on overlapping tiles and merge detections."""

        if isinstance(tile_size, bool) or not isinstance(tile_size, int) or tile_size <= 0:
            raise ValueError("Tile size must be a positive integer.")

        if not 0 <= overlap < 1:
            raise ValueError("Overlap must be between 0 (inclusive) and 1 (exclusive).")

        if pixel_scale_m is not None and pixel_scale_m <= 0:
            raise ValueError("Pixel scale must be positive.")

        if sun_elevation_deg is not None and not 0 <= sun_elevation_deg <= 90:
            raise ValueError("Sun elevation must be between 0 and 90 degrees.")

        threshold = confidence if confidence is not None else self.confidence
        if not 0 <= threshold <= 1:
            raise ValueError("Confidence must be between 0 and 1.")

        image_path = Path(image_path)
        if not image_path.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")

        height, width = image.shape[:2]
        stride = max(1, int(tile_size * (1 - overlap)))

        def tile_starts(length: int) -> list[int]:
            if length <= tile_size:
                return [0]

            starts = [0]
            while starts[-1] + tile_size < length:
                starts.append(starts[-1] + stride)

            return starts

        candidates = []

        for y0 in tile_starts(height):
            for x0 in tile_starts(width):
                tile = image[
                    y0:min(y0 + tile_size, height),
                    x0:min(x0 + tile_size, width)
                ]

                result = self.model.predict(
                    source=tile,
                    imgsz=self.image_size,
                    conf=threshold,
                    iou=self.iou,
                    device=self.device,
                    verbose=False,
                )[0]

                if result.boxes is None:
                    continue

                for index, box in enumerate(result.boxes):
                    local_box = box.xyxy[0].cpu().numpy().tolist()
                    score = float(box.conf[0].cpu().item())
                    class_id = int(box.cls[0].cpu().item())

                    x1 = max(0.0, float(local_box[0]) + x0)
                    y1 = max(0.0, float(local_box[1]) + y0)
                    x2 = min(float(width), float(local_box[2]) + x0)
                    y2 = min(float(height), float(local_box[3]) + y0)

                    if x2 <= x1 or y2 <= y1:
                        continue

                    polygon = []
                    if result.masks is not None and index < len(result.masks.xy):
                        polygon = [
                            [
                                round(float(point[0]) + x0, 2),
                                round(float(point[1]) + y0, 2),
                            ]
                            for point in result.masks.xy[index]
                        ]

                    candidates.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": score,
                        "class_name": self.model.names[class_id],
                        "polygon": polygon,
                    })

        # Greedy class-aware non-maximum suppression.
        candidates.sort(key=lambda item: item["confidence"], reverse=True)
        kept = []

        for candidate in candidates:
            x1, y1, x2, y2 = candidate["bbox"]
            duplicate = False

            for existing in kept:
                if candidate["class_name"] != existing["class_name"]:
                    continue

                a1, b1, a2, b2 = existing["bbox"]

                intersection_width = max(0.0, min(x2, a2) - max(x1, a1))
                intersection_height = max(0.0, min(y2, b2) - max(y1, b1))
                intersection = intersection_width * intersection_height

                area_candidate = (x2 - x1) * (y2 - y1)
                area_existing = (a2 - a1) * (b2 - b1)
                union = area_candidate + area_existing - intersection

                iou = intersection / union if union > 0 else 0.0

                if iou > self.tile_nms_iou:
                    duplicate = True
                    break

            if not duplicate:
                kept.append(candidate)

        detections = []

        for index, candidate in enumerate(kept, start=1):
            detections.append({
                "id": index,
                "bbox": [round(value, 2) for value in candidate["bbox"]],
                "confidence": round(candidate["confidence"], 5),
                "size_m": None,
                "class_name": candidate["class_name"],
                "polygon": candidate["polygon"],
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
