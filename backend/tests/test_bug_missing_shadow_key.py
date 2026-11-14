import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_missing_shadow_length_error():
    payload = {
        "image": {"id": "img1", "width": 100, "height": 100, "pixel_scale_m": 0.5, "sun_elevation_deg": 30},
        "detections": [
            {"id": 1, "bbox": [10, 10, 30, 30], "confidence": 0.9},
            {"id": 2, "bbox": [40, 40, 60, 60], "confidence": 0.85},
        ],
        "shadow_lengths_px": {"1": 5.0},  # detection 2 missing
    }
    response = client.post("/api/measure", json=payload)
    assert response.status_code == 422
    assert "missing shadow length" in response.json().get("detail", "").lower()
