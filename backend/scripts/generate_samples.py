"""
Generate samples/*.json by calling the REAL API with MOCK input data.

Everything this script feeds in is synthetic (fixed random seed) and is marked
is_mock=true. It exists so Members 1/3/4 can see the exact JSON shapes.
Run from the backend folder:   python scripts/generate_samples.py
"""
import json
import math
import random
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.main import app

OUT = Path(__file__).resolve().parent.parent / "samples"
OUT.mkdir(exist_ok=True)
random.seed(42)

SCALE, SUN = 0.5, 30.0  # MOCK metadata
IMAGE = {"id": "mock_img_001", "width": 1000, "height": 1000, "pixel_scale_m": SCALE,
         "sun_elevation_deg": SUN, "incidence_angle_deg": 90 - SUN, "projection": "MOCK (not a real projection)",
         "metadata_source": "mock"}

# 40 synthetic boulders: some clustered top-right, the rest scattered
dets, shadows = [], {}
for i in range(1, 41):
    if i <= 18:
        cx, cy = random.gauss(800, 60), random.gauss(200, 60)
    else:
        cx, cy = random.uniform(20, 980), random.uniform(20, 980)
    cx, cy = min(max(cx, 20), 980), min(max(cy, 20), 980)
    side = random.randint(4, 12)  # px  -> 2..6 m at 0.5 m/px
    dets.append({"id": i, "bbox": [int(cx), int(cy), int(cx) + side, int(cy) + side],
                 "confidence": round(random.uniform(0.5, 0.97), 2), "size_m": None, "class_name": "boulder"})
    if i % 4 != 0:  # a quarter have no shadow measurement -> exercises the fallback
        h = side * SCALE * random.uniform(0.2, 0.7)
        shadows[str(i)] = round(h / math.tan(math.radians(SUN)) / SCALE, 1)

recall = {"is_mock": True, "validation_site": "MOCK - no real validation done",
          "bins": [{"min_diameter_m": 0, "max_diameter_m": 2, "recall": 0.5, "n_ground_truth": None},
                   {"min_diameter_m": 2, "max_diameter_m": 4, "recall": 0.75, "n_ground_truth": None},
                   {"min_diameter_m": 4, "max_diameter_m": None, "recall": 0.9, "n_ground_truth": None}],
          "notes": "Invented numbers for format testing only."}
slope = [[round(random.uniform(1, 8), 1) for _ in range(4)] for _ in range(4)]
slope[0][3] = 14.2  # one steep cell, mock

client = TestClient(app)
cfg = client.get("/api/config").json()
cfg.update({"grid_rows": 4, "grid_cols": 4, "apply_recall_correction": True})

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2))
    print("wrote", name)

save("config.json", cfg)
save("detections.json", {"image": IMAGE, "model_name": "MOCK", "model_version": None, "is_mock": True, "detections": dets})
save("recall.json", recall)
req = {"image": IMAGE, "detections": dets, "shadow_lengths_px": shadows, "config": cfg}
save("measurements.json", client.post("/api/measure", json=req).json())
req.update({"slope_by_cell": slope, "recall": recall, "is_mock": True})
save("analyze_request.json", req)
save("hazard_grid.json", client.post("/api/hazard-grid", json=req).json())
save("analyze_response.json", client.post("/api/analyze", json=req).json())
