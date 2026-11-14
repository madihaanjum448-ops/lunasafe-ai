import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_duplicate_detection_ids_fail():
    payload = {
        "image": {"id": "img1", "width": 100, "height": 100, "pixel_scale_m": 0.5},
        "detections": [
            {"id": 1, "bbox": [10, 10, 30, 30], "confidence": 0.9},
            {"id": 1, "bbox": [40, 40, 60, 60], "confidence": 0.8},
        ],
        "shadow_lengths_px": {"1": 5.0}
    }
    response = client.post("/api/measure", json=payload)
    assert response.status_code == 422
    assert "duplicate detection id" in response.json().get("detail", "").lower()
