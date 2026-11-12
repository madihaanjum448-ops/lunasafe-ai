import cv2
import numpy as np
import pytest

from ml.src.shadow_extraction import ShadowCandidateExtractor


def create_synthetic_image(path):
    """Create a bright boulder with a dark elongated region nearby."""
    image = np.full((120, 120), 180, dtype=np.uint8)

    # Simulated bright boulder
    cv2.circle(image, (50, 60), 8, 230, -1)

    # Simulated elongated dark region
    cv2.ellipse(image, (68, 60), (3, 9), 0, 0, 360, 40, -1)

    assert cv2.imwrite(str(path), image)


def valid_detection():
    return {
        "id": 1,
        "polygon": [
            [42, 52],
            [58, 52],
            [58, 68],
            [42, 68],
        ],
        "bbox": [42, 52, 58, 68],
    }


def test_extract_finds_and_ranks_candidates(tmp_path):
    image_path = tmp_path / "synthetic.png"
    create_synthetic_image(image_path)

    extractor = ShadowCandidateExtractor()
    result = extractor.extract(image_path, valid_detection())

    assert result["detection_id"] == 1
    assert result["status"] == "needs_manual_review"
    assert result["measurement_available"] is False
    assert result["shadow_measurement_status"] == "unavailable"
    assert result["confidence"] is None
    assert result["shadow_length_px"] is None
    assert result["physical_height_m"] is None

    assert len(result["candidates"]) > 0

    scores = [
        candidate["ranking_score"]
        for candidate in result["candidates"]
    ]

    assert all(isinstance(score, (int, float)) for score in scores)
    assert scores == sorted(scores, reverse=True)

    for candidate in result["candidates"]:
        assert candidate["confidence"] is None
        assert candidate["area_px"] > 0


def test_invalid_polygon_returns_unavailable(tmp_path):
    image_path = tmp_path / "synthetic.png"
    create_synthetic_image(image_path)

    detection = valid_detection()
    detection["polygon"] = [[50, 50], [55, 55]]

    extractor = ShadowCandidateExtractor()
    result = extractor.extract(image_path, detection)

    assert result["status"] == "unavailable"
    assert result["reason"] == "Invalid boulder polygon"
    assert result["candidates"] == []
    assert result["measurement_available"] is False


def test_missing_image_raises_file_not_found():
    extractor = ShadowCandidateExtractor()

    with pytest.raises(FileNotFoundError):
        extractor.extract(
            "nonexistent_image.png",
            valid_detection(),
        )
