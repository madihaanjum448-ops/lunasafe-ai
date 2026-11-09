import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def make_image_bytes(fmt="PNG", size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("L", size, 128).save(buf, format=fmt)
    return buf.getvalue()


# ---- MOCK TEST DATA (not real lunar data) ---------------------------------
MOCK_IMAGE = {
    "id": "mock_img", "width": 1000, "height": 1000,
    "pixel_scale_m": 0.5, "sun_elevation_deg": 30.0, "projection": "MOCK",
}
