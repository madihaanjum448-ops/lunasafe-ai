import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_shadow_key_string_error():
    payload = {
        "image": {"id": "img1", "width": 100, "height": 100, "pixel_scale_m": 0.5, "sun_elevation_deg": 30},
        "detections": [
            {"id": 1, "bbox": [10, 10, 30, 30], "confidence": 0.9},
        ],
        "shadow_lengths_px": {"1": 5.0},  # string key instead of int
    }
    response = client.post("/api/measure", json=payload)
    assert response.status_code == 422
    assert "shadow_lengths_px keys" in response.json().get("detail", "").lower()
