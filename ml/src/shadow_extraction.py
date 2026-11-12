from pathlib import Path
from typing import Any

import cv2
import numpy as np


class ShadowCandidateExtractor:
    """
    Experimental dark-region candidate extractor.

    Candidates are ranked using darkness, area, distance from
    the boulder polygon, and contour-based elongation.

    Ranking scores are heuristic, not shadow probabilities.
    All candidates require manual review.

    Physical shadow measurements remain unavailable until
    shadow endpoints and their association are verified.
    """

    def __init__(
        self,
        search_radius: int = 30,
        min_area: int = 3,
        max_area: int = 500,
        darkness_threshold: float = 12.0,
    ):
        self.search_radius = search_radius
        self.min_area = min_area
        self.max_area = max_area
        self.darkness_threshold = darkness_threshold

    def extract(
        self,
        image_path: str | Path,
        detection: dict[str, Any],
    ) -> dict[str, Any]:

        image_path = Path(image_path)

        if not image_path.is_file():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        image = cv2.imread(
            str(image_path),
            cv2.IMREAD_GRAYSCALE,
        )

        if image is None:
            raise ValueError(
                f"Could not read image: {image_path}"
            )

        height, width = image.shape
        detection_id = detection["id"]

        polygon = np.asarray(
            detection["polygon"],
            dtype=np.float32,
        )

        if (
            polygon.ndim != 2
            or polygon.shape[0] < 3
            or polygon.shape[1] != 2
            or not np.isfinite(polygon).all()
        ):
            return self._unavailable(
                detection_id,
                "Invalid boulder polygon",
            )

        x1, y1, x2, y2 = detection["bbox"]

        left = max(0, int(x1) - self.search_radius)
        top = max(0, int(y1) - self.search_radius)
        right = min(width, int(x2) + self.search_radius)
        bottom = min(height, int(y2) + self.search_radius)

        crop = image[top:bottom, left:right]

        if crop.size == 0:
            return self._unavailable(
                detection_id,
                "Empty search region",
            )

        # Create boulder mask in crop coordinates.
        boulder_mask = np.zeros(
            crop.shape,
            dtype=np.uint8,
        )

        local_polygon = polygon.copy()
        local_polygon[:, 0] -= left
        local_polygon[:, 1] -= top

        cv2.fillPoly(
            boulder_mask,
            [local_polygon.astype(np.int32)],
            255,
        )

        # Exclude boulder and surrounding margin.
        exclusion_size = 3

        kernel = np.ones(
            (
                exclusion_size * 2 + 1,
                exclusion_size * 2 + 1,
            ),
            dtype=np.uint8,
        )

        exclusion_mask = cv2.dilate(
            boulder_mask,
            kernel,
            iterations=1,
        )

        search_mask = np.where(
            exclusion_mask == 0,
            255,
            0,
        ).astype(np.uint8)

        # Estimate local terrain brightness.
        background = cv2.GaussianBlur(
            crop,
            (0, 0),
            sigmaX=7,
            sigmaY=7,
        )

        darkness = (
            background.astype(np.float32)
            - crop.astype(np.float32)
        )

        candidate_mask = (
            (darkness >= self.darkness_threshold)
            & (search_mask > 0)
        ).astype(np.uint8) * 255

        candidate_mask = cv2.morphologyEx(
            candidate_mask,
            cv2.MORPH_CLOSE,
            np.ones((3, 3), dtype=np.uint8),
        )

        count, labels, stats, centroids = (
            cv2.connectedComponentsWithStats(
                candidate_mask,
                connectivity=8,
            )
        )

        candidates = []
        polygon_contour = polygon.reshape((-1, 1, 2))

        for label in range(1, count):
            x, y, w, h, area = stats[label]

            if not self.min_area <= area <= self.max_area:
                continue

            component_mask = (
                labels[y:y + h, x:x + w] == label
            ).astype(np.uint8)

            contours, _ = cv2.findContours(
                component_mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )

            if not contours:
                continue

            contour = max(
                contours,
                key=cv2.contourArea,
            )

            rect = cv2.minAreaRect(contour)
            rect_width, rect_height = rect[1]

            if min(rect_width, rect_height) <= 0:
                aspect_ratio = 1.0
            else:
                aspect_ratio = (
                    max(rect_width, rect_height)
                    / min(rect_width, rect_height)
                )

            center_x, center_y = centroids[label]

            global_x = float(center_x + left)
            global_y = float(center_y + top)

            signed_distance = cv2.pointPolygonTest(
                polygon_contour,
                (global_x, global_y),
                True,
            )

            distance_from_boulder_px = max(
                0.0,
                -float(signed_distance),
            )

            mean_darkness = float(
                darkness[labels == label].mean()
            )

            candidates.append({
                "bbox": [
                    int(x + left),
                    int(y + top),
                    int(x + w + left),
                    int(y + h + top),
                ],
                "centroid": [
                    round(global_x, 2),
                    round(global_y, 2),
                ],
                "area_px": int(area),
                "mean_darkness": round(mean_darkness, 2),
                "distance_from_boulder_px": round(
                    distance_from_boulder_px,
                    2,
                ),
                "aspect_ratio": round(
                    float(aspect_ratio),
                    2,
                ),
                "ranking_score": None,
                "confidence": None,
            })

        # Heuristic candidate ranking.
        for candidate in candidates:
            darkness_score = np.clip(
                candidate["mean_darkness"] / 50.0,
                0.0,
                1.0,
            )

            area_score = np.clip(
                candidate["area_px"] / 300.0,
                0.0,
                1.0,
            )

            distance_score = 1.0 - np.clip(
                candidate["distance_from_boulder_px"]
                / (self.search_radius * 2),
                0.0,
                1.0,
            )

            shape_score = np.clip(
                (candidate["aspect_ratio"] - 1.0) / 4.0,
                0.0,
                1.0,
            )

            candidate["ranking_score"] = round(
                0.30 * darkness_score
                + 0.25 * area_score
                + 0.25 * distance_score
                + 0.20 * shape_score,
                4,
            )

        candidates.sort(
            key=lambda item: item["ranking_score"],
            reverse=True,
        )

        status = (
            "needs_manual_review"
            if candidates
            else "unavailable"
        )

        reason = (
            "Dark-region candidates found. "
            "Ranking is heuristic; shadow association "
            "and endpoints are not verified."
            if candidates
            else "No suitable dark-region candidates found."
        )

        return {
            "detection_id": detection_id,
            "status": status,
            "reason": reason,
            "measurement_available": False,
            "shadow_measurement_status": "unavailable",
            "shadow_start": None,
            "shadow_tip": None,
            "shadow_length_px": None,
            "confidence": None,
            "candidates": candidates,
            "physical_height_m": None,
        }

    @staticmethod
    def _unavailable(
        detection_id: int,
        reason: str,
    ) -> dict[str, Any]:

        return {
            "detection_id": detection_id,
            "status": "unavailable",
            "reason": reason,
            "measurement_available": False,
            "shadow_measurement_status": "unavailable",
            "shadow_start": None,
            "shadow_tip": None,
            "shadow_length_px": None,
            "confidence": None,
            "candidates": [],
            "physical_height_m": None,
        }
