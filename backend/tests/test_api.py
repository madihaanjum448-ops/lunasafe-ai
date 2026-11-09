
import io

import numpy as np
from PIL import Image
from PIL.TiffImagePlugin import ImageFileDirectory_v2

from tests.conftest import MOCK_IMAGE, make_image_bytes


# ---------------- system ----------------
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_default_config(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    assert r.json()["grid_rows"] == 8


def test_cors_allows_vite_origin(client):
    r = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ---------------- upload ----------------
def test_upload_png_without_metadata_warns_and_does_not_invent(client):
    r = client.post(
        "/api/upload",
        files={"file": ("a.png", make_image_bytes("PNG"), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["image"]["pixel_scale_m"] is None
    assert body["image"]["sun_elevation_deg"] is None
    assert set(body["missing_metadata"]) == {
        "pixel_scale_m",
        "sun_elevation_deg",
        "projection",
    }
    assert body["can_measure_diameter"] is False
    assert any("Pixel scale unavailable" in w for w in body["warnings"])


def test_upload_with_user_supplied_metadata(client):
    r = client.post(
        "/api/upload",
        files={"file": ("a.png", make_image_bytes("PNG"), "image/png")},
        data={"pixel_scale_m": "0.5", "sun_elevation_deg": "30"},
    )
    body = r.json()
    assert body["image"]["pixel_scale_m"] == 0.5
    assert body["can_measure_height_from_shadow"] is True
    assert "user_supplied" in body["image"]["metadata_source"]


def test_upload_rejects_bad_sun_elevation(client):
    r = client.post(
        "/api/upload",
        files={"file": ("a.png", make_image_bytes("PNG"), "image/png")},
        data={"sun_elevation_deg": "95"},
    )
    assert r.status_code == 422


def test_upload_empty_file(client):
    r = client.post(
        "/api/upload",
        files={"file": ("a.png", b"", "image/png")},
    )
    assert r.status_code == 400


def test_upload_corrupt_file(client):
    r = client.post(
        "/api/upload",
        files={"file": ("a.png", b"not an image", "image/png")},
    )
    assert r.status_code == 400


def test_upload_unsupported_format(client):
    r = client.post(
        "/api/upload",
        files={"file": ("a.gif", make_image_bytes("GIF"), "image/gif")},
    )
    assert r.status_code == 415


def test_upload_too_many_pixels(client):
    # 8193 x 1 is tiny on disk but exceeds the width limit
    r = client.post(
        "/api/upload",
        files={"file": ("a.png", make_image_bytes("PNG", (8193, 1)), "image/png")},
    )
    assert r.status_code == 422


def _geotiff_bytes(model_type: int, pixel_size: float) -> bytes:
    ifd = ImageFileDirectory_v2()
    ifd.tagtype[33550] = 12
    ifd[33550] = (pixel_size, pixel_size, 0.0)
    ifd.tagtype[33922] = 12
    ifd[33922] = (0.0, 0.0, 0.0, 1000.0, 2000.0, 0.0)
    ifd.tagtype[34735] = 3
    # header (1,1,0,nkeys) then keys: GTModelType, ProjLinearUnits(metre)
    ifd[34735] = (1, 1, 0, 2, 1024, 0, 1, model_type, 3076, 0, 1, 9001)
    buf = io.BytesIO()
    Image.new("L", (32, 32), 0).save(buf, format="TIFF", tiffinfo=ifd)
    return buf.getvalue()


def test_upload_geotiff_projected_metres_reads_scale(client):
    r = client.post(
        "/api/upload",
        files={"file": ("a.tif", _geotiff_bytes(1, 1.5), "image/tiff")},
    )
    assert r.status_code == 200
    assert r.json()["image"]["pixel_scale_m"] == 1.5
    assert r.json()["image"]["metadata_source"] == "geotiff"


def test_upload_geotiff_geographic_does_not_claim_metres(client):
    r = client.post(
        "/api/upload",
        files={"file": ("a.tif", _geotiff_bytes(2, 0.0001), "image/tiff")},
    )
    body = r.json()
    assert body["image"]["pixel_scale_m"] is None
    assert any("degrees" in w for w in body["warnings"])


# ---------------- measurement ----------------
def test_shadow_height_math(client):
    # shadow 10 px * 0.5 m/px = 5 m
    # tan(30 deg)=0.57735 -> height = 2.887 m
    body = {
        "image": MOCK_IMAGE,
        "detections": [
            {"id": 1, "bbox": [0, 0, 8, 6], "confidence": 0.9}
        ],
        "shadow_lengths_px": {"1": 10},
    }
    m = client.post("/api/measure", json=body).json()["measurements"][0]
    assert m["method"] == "shadow_geometry"
    assert abs(m["height_m"] - 2.887) < 0.01
    assert m["diameter_m"] == 4.0
    assert m["confidence"] == "high"


def test_measure_fallback_is_low_confidence_and_labelled(client):
    body = {
        "image": MOCK_IMAGE,
        "detections": [
            {"id": 1, "bbox": [0, 0, 8, 8], "confidence": 0.9}
        ],
    }
    m = client.post("/api/measure", json=body).json()["measurements"][0]
    assert m["method"] == "diameter_fallback" and m["confidence"] == "low"
    assert any("ASSUMPTION" in w for w in m["warnings"])


def test_measure_without_sun_but_with_shadow_uses_fallback(client):
    img = {**MOCK_IMAGE, "sun_elevation_deg": None}
    body = {
        "image": img,
        "detections": [
            {"id": 1, "bbox": [0, 0, 8, 8], "confidence": 0.9}
        ],
        "shadow_lengths_px": {"1": 5},
    }
    m = client.post("/api/measure", json=body).json()["measurements"][0]
    assert m["method"] == "diameter_fallback"


def test_measure_without_pixel_scale_computes_nothing(client):
    img = {**MOCK_IMAGE, "pixel_scale_m": None}
    body = {
        "image": img,
        "detections": [
            {"id": 1, "bbox": [0, 0, 8, 8], "confidence": 0.9}
        ],
    }
    m = client.post("/api/measure", json=body).json()["measurements"][0]
    assert m["method"] == "unavailable"
    assert m["diameter_m"] is None
    assert m["height_m"] is None


def test_detection_accepts_float_bboxes(client):
    req = {
        "image": MOCK_IMAGE,
        "detections": [
            {
                "id": 1,
                "bbox": [10.5, 20.3, 30.7, 40.9],
                "confidence": 0.95,
            }
        ],
        "shadow_lengths_px": {"1": 15.2},
    }
    r = client.post("/api/measure", json=req)
    assert r.status_code == 200
    meas = r.json()["measurements"][0]
    # width = 30.7 - 10.5 = 20.2; height = 40.9 - 20.3 = 20.6. Longer side is 20.6 px.
    # At 0.5 m/px, diameter = 20.6 * 0.5 = 10.3 m.
    assert round(meas["diameter_m"], 2) == 10.3
    assert meas["method"] == "shadow_geometry"

    r_an = client.post("/api/analyze", json=req)
    assert r_an.status_code == 200
    body = r_an.json()
    assert body["detections"][0]["bbox"] == [10.5, 20.3, 30.7, 40.9]
    assert body["detections"][0]["size_m"] is not None


# ---------------- hazard ----------------
def test_poisson_formula():
    from app.services.hazard import footprint_area_m2, poisson_hazard_probability
    import math

    assert poisson_hazard_probability(0, 78.5) == 0
    assert abs(
        poisson_hazard_probability(0.01, 100) - (1 - math.exp(-1))
    ) < 1e-12
    assert abs(footprint_area_m2(10) - math.pi * 25) < 1e-9


def _dense_dets(n, x0=10, y0=10):
    # Detections packed into one cell.
    # Hazard classification must use shadow-derived heights, not fallback heights.
    return [
        {
            "id": i + 1,
            "bbox": [
                x0 + i % 5 * 10,
                y0 + i // 5 * 10,
                x0 + i % 5 * 10 + 8,
                y0 + i // 5 * 10 + 8,
            ],
            "confidence": 0.9,
        }
        for i in range(n)
    ]


def test_hazard_grid_slope_not_assessed_never_safe(client):
    r = client.post(
        "/api/hazard-grid",
        json={
            "image": MOCK_IMAGE,
            "detections": [],
            "is_mock": True,
            "config": {"grid_rows": 2, "grid_cols": 2},
        },
    )
    assert r.status_code == 200
    body = r.json()
    cell = body["hazard_cells"][0]
    assert cell["p_hazard"] == 0
    assert cell["class"] == "caution"
    assert "downgraded_slope_not_assessed" in cell["reasons"]
    assert body["is_mock"] is True
    assert any("slope gate not assessed" in w for w in body["warnings"])


def test_hazard_grid_safe_with_slope_pass_and_unsafe_with_boulders(client):
    # 100x100 px image at 0.5 m/px, 2x2 grid.
    # Each cell is 50x50 px = 625 m2.
    #
    # 25 detections are placed in cell (0,0).
    # Each has a 10 px shadow:
    # height = 10 * 0.5 * tan(30 degrees) = 2.887 m.
    # This is an actual shadow-derived height above the 0.5 m threshold.
    #
    # rho_h = 25/625 = 0.04 /m2.
    # A = pi*5^2 = 78.54 m2.
    # P = 1-exp(-0.04*78.54) ~= 0.9567 -> unsafe.
    img = {**MOCK_IMAGE, "width": 100, "height": 100}

    dets = [
        {
            "id": i + 1,
            "bbox": [
                5 + (i % 5) * 9,
                5 + (i // 5) * 9,
                11 + (i % 5) * 9,
                11 + (i // 5) * 9,
            ],
            "confidence": 0.9,
        }
        for i in range(25)
    ]

    shadow_lengths_px = {str(d["id"]): 10 for d in dets}

    body = {
        "image": img,
        "detections": dets,
        "shadow_lengths_px": shadow_lengths_px,
        "slope_by_cell": [[2.0, 2.0], [2.0, 2.0]],
        "config": {"grid_rows": 2, "grid_cols": 2},
    }

    response = client.post("/api/hazard-grid", json=body)
    assert response.status_code == 200

    cells = {
        (c["row"], c["col"]): c
        for c in response.json()["hazard_cells"]
    }

    assert cells[(1, 1)]["class"] == "safe"
    assert cells[(1, 1)]["slope_gate"] == "pass"
    assert cells[(0, 0)]["class"] == "unsafe"
    assert abs(cells[(0, 0)]["p_hazard"] - 0.9567) < 0.01
    assert cells[(0, 0)]["p_hazard"] == cells[(0, 0)]["score"]


def test_slope_gate_failure_overrides_clean_boulders(client):
    body = {
        "image": MOCK_IMAGE,
        "detections": [],
        "slope_by_cell": [[25.0, 1.0], [1.0, 1.0]],
        "config": {"grid_rows": 2, "grid_cols": 2},
    }
    cells = {
        (c["row"], c["col"]): c
        for c in client.post("/api/hazard-grid", json=body).json()["hazard_cells"]
    }
    assert cells[(0, 0)]["class"] == "unsafe"
    assert cells[(0, 0)]["p_hazard"] == 0
    assert "slope_gate_failed" in cells[(0, 0)]["reasons"]


def test_recall_correction_raises_probability(client):
    dets = _dense_dets(3)

    # Supply real shadow measurements so these detections qualify as
    # confirmed hazardous boulders rather than diameter-only fallbacks.
    shadow_lengths_px = {str(d["id"]): 10 for d in dets}

    base = {
        "image": MOCK_IMAGE,
        "detections": dets,
        "shadow_lengths_px": shadow_lengths_px,
        "slope_by_cell": [[1, 1], [1, 1]],
        "config": {"grid_rows": 2, "grid_cols": 2},
    }

    recall = {
        "is_mock": True,
        "bins": [
            {
                "min_diameter_m": 0,
                "max_diameter_m": None,
                "recall": 0.5,
            }
        ],
    }

    p0 = client.post("/api/hazard-grid", json=base).json()["hazard_cells"][0]["p_hazard"]

    cfg = {
        "grid_rows": 2,
        "grid_cols": 2,
        "apply_recall_correction": True,
    }

    response = client.post(
        "/api/hazard-grid",
        json={**base, "config": cfg, "recall": recall},
    )
    assert response.status_code == 200

    p1 = response.json()["hazard_cells"][0]
    assert p1["p_hazard"] > p0
    assert p1["recall_corrected"] is True


def test_hazard_requires_pixel_scale(client):
    img = {**MOCK_IMAGE, "pixel_scale_m": None}
    r = client.post(
        "/api/hazard-grid",
        json={"image": img, "detections": []},
    )
    assert r.status_code == 422


def test_grid_cell_large_area_warning_and_helper(client):
    from app.services.hazard import suggest_grid_dimensions

    # 1. Helper suggests fine enough grid
    # 1000x1000 px, 0.5 m/px = 500x500 m. Footprint 10m -> 50x50 grid cells of 10x10 m.
    rows, cols = suggest_grid_dimensions(1000, 1000, 0.5, 10.0)
    assert rows == 50
    assert cols == 50

    # 2. Default 8x8 on 1000x1000 image with 0.5 m/px gives cell area 3906.25 m^2 > 10 * 78.54 m^2
    r = client.post(
        "/api/hazard-grid",
        json={
            "image": MOCK_IMAGE,  # 1000x1000, 0.5 m/px
            "detections": [],
            "config": {"grid_rows": 8, "grid_cols": 8},
        },
    )
    assert r.status_code == 200
    warnings = r.json()["warnings"]
    assert any("more than 10x the lander footprint area" in w for w in warnings)


def test_slope_grid_dimension_mismatch_warning(client):
    # Hazard grid configured as 4x4, but slope_by_cell supplied as 2x2
    r = client.post(
        "/api/hazard-grid",
        json={
            "image": {**MOCK_IMAGE, "width": 100, "height": 100},
            "detections": [],
            "config": {"grid_rows": 4, "grid_cols": 4},
            "slope_by_cell": [[2.0, 2.0], [2.0, 2.0]],
        },
    )
    assert r.status_code == 200
    body = r.json()
    warnings = body["warnings"]
    assert any("differ from hazard grid dimensions" in w for w in warnings)


def test_analyze_fills_size_m_and_returns_frontend_keys(client):
    body = {
        "image": MOCK_IMAGE,
        "detections": [
            {
                "id": 1,
                "bbox": [0, 0, 8, 8],
                "confidence": 0.9,
                "size_m": None,
            }
        ],
    }
    out = client.post("/api/analyze", json=body).json()
    assert {"image", "detections", "hazard_cells", "warnings"} <= set(out)
    assert out["detections"][0]["size_m"] == 4.0
    assert "class" in out["hazard_cells"][0]


# ---------------- slope ----------------
def test_slope_flat_and_ramp():
    from app.services.slope import compute_slope_deg

    flat = compute_slope_deg(np.zeros((10, 10)), 5.0)
    assert np.allclose(flat, 0)

    # ramp rising 1 m per 1 m cell in x -> 45 degrees
    ramp = np.tile(np.arange(10, dtype=float), (10, 1))
    s = compute_slope_deg(ramp, 1.0)
    assert np.allclose(s[2:-2, 2:-2], 45.0, atol=1e-6)


def test_slope_endpoint(client):
    ramp = np.tile(np.arange(16, dtype=float), (16, 1))
    buf = io.BytesIO()
    np.save(buf, ramp)

    r = client.post(
        "/api/slope",
        files={"dem_file": ("d.npy", buf.getvalue(), "application/octet-stream")},
        data={"cell_size_m": "1", "rows": "2", "cols": "2"},
    )
    assert r.status_code == 200
    assert abs(r.json()["slope_by_cell"][0][0] - 45.0) < 1e-6


def test_slope_endpoint_bad_file(client):
    r = client.post(
        "/api/slope",
        files={"dem_file": ("d.npy", b"junk", "application/octet-stream")},
        data={"cell_size_m": "1"},
    )
    assert r.status_code == 422


# ---------------- edge cases ----------------
def test_detection_outside_image_bounds(client):
    req = {
        "image": {**MOCK_IMAGE, "width": 100, "height": 100},
        "detections": [
            {"id": 1, "bbox": [-50, 10, -10, 30], "confidence": 0.9},
            {"id": 2, "bbox": [120, 20, 150, 40], "confidence": 0.9},
            {"id": 3, "bbox": [10, -50, 30, -10], "confidence": 0.9},
            {"id": 4, "bbox": [10, 120, 30, 150], "confidence": 0.9},
            {"id": 5, "bbox": [20, 20, 10, 10], "confidence": 0.9},  # inverted bbox x2 <= x1
        ],
        "config": {"grid_rows": 2, "grid_cols": 2},
    }
    r = client.post("/api/hazard-grid", json=req)
    assert r.status_code == 200
    body = r.json()
    warnings = body["warnings"]
    assert any("entirely outside the image bounds" in w for w in warnings)
    total_boulders = sum(c["raw_boulder_count"] for c in body["hazard_cells"])
    assert total_boulders == 0


def test_detection_edge_cut_clipping(client):
    req = {
        "image": {**MOCK_IMAGE, "width": 100, "height": 100},
        "detections": [
            {"id": 1, "bbox": [-10, 10, 20, 30], "confidence": 0.9},  # cut on left
            {"id": 2, "bbox": [80, 20, 120, 40], "confidence": 0.9},  # cut on right
            {"id": 3, "bbox": [10, -15, 30, 40], "confidence": 0.9},  # cut on top
            {"id": 4, "bbox": [10, 80, 30, 115], "confidence": 0.9},  # cut on bottom
        ],
        "config": {"grid_rows": 2, "grid_cols": 2},
    }
    r = client.post("/api/hazard-grid", json=req)
    assert r.status_code == 200
    body = r.json()
    warnings = body["warnings"]
    assert any("cut by the image edge and were clipped" in w for w in warnings)
    total_boulders = sum(c["raw_boulder_count"] for c in body["hazard_cells"])
    assert total_boulders == 4


def test_poisson_hand_computed_and_monotonicity():
    import math
    from app.services.hazard import footprint_area_m2, poisson_hazard_probability

    a_cell = 100.0
    d_footprint = 10.0
    a_fp = footprint_area_m2(d_footprint)

    # 0, 1, 2, 4 boulders hand computation
    # k=0
    assert poisson_hazard_probability(0.0 / a_cell, a_fp) == 0.0
    # k=1: rho = 0.01 -> 1 - exp(-0.01 * 25*pi) ~= 0.544068
    p1 = poisson_hazard_probability(1.0 / a_cell, a_fp)
    assert abs(p1 - (1.0 - math.exp(-0.01 * 25 * math.pi))) < 1e-6
    assert abs(p1 - 0.544068) < 1e-4

    # k=2: rho = 0.02 -> 1 - exp(-0.02 * 25*pi) ~= 0.792120
    p2 = poisson_hazard_probability(2.0 / a_cell, a_fp)
    assert abs(p2 - 0.7921) < 1e-4

    # k=4: rho = 0.04 -> 1 - exp(-0.04 * 25*pi) ~= 0.956786
    p4 = poisson_hazard_probability(4.0 / a_cell, a_fp)
    assert abs(p4 - 0.9568) < 1e-4

    # Monotonicity in rho
    rhos = [0.0, 0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 10.0]
    p_rhos = [poisson_hazard_probability(r, a_fp) for r in rhos]
    for i in range(len(p_rhos) - 1):
        assert p_rhos[i] <= p_rhos[i + 1]

    # Monotonicity in A
    areas = [10.0, 50.0, 78.54, 100.0, 500.0]
    p_areas = [poisson_hazard_probability(0.02, a) for a in areas]
    for i in range(len(p_areas) - 1):
        assert p_areas[i] <= p_areas[i + 1]

    # Probability bounds in [0, 1]
    assert 0.0 <= poisson_hazard_probability(0.0, 10.0) <= 1.0
    assert 0.0 <= poisson_hazard_probability(100.0, 1000.0) <= 1.0


def test_detection_on_cell_boundary(client):
    # 100x100 px image, 2x2 grid -> boundary at x=50, y=50.
    # Detection centered exactly at (x=50.0, y=25.0) -> falls into cell (row=0, col=1)
    req = {
        "image": {**MOCK_IMAGE, "width": 100, "height": 100},
        "detections": [
            {"id": 1, "bbox": [45.0, 20.0, 55.0, 30.0], "confidence": 0.9},
        ],
        "shadow_lengths_px": {"1": 10.0},
        "config": {"grid_rows": 2, "grid_cols": 2},
    }
    r = client.post("/api/hazard-grid", json=req)
    assert r.status_code == 200
    body = r.json()
    cells = {(c["row"], c["col"]): c for c in body["hazard_cells"]}
    assert cells[(0, 1)]["raw_boulder_count"] == 1
    assert cells[(0, 0)]["raw_boulder_count"] == 0


def test_recall_bin_edges_and_zero_bin(client):
    from app.services.hazard import _recall_for
    from app.schemas.contracts import RecallBin, RecallFile

    recall_obj = RecallFile(
        bins=[
            RecallBin(bin_min_m=1.0, bin_max_m=2.0, recall=0.5),
            RecallBin(bin_min_m=2.0, bin_max_m=3.0, recall=0.8),
            RecallBin(bin_min_m=3.0, bin_max_m=4.0, recall=0.0),  # recall=0 bin
        ]
    )

    # Below all bins
    assert _recall_for(0.99, recall_obj) is None
    # Lower edge of bin 0 (inclusive)
    assert _recall_for(1.0, recall_obj) == 0.5
    # Interior of bin 0
    assert _recall_for(1.5, recall_obj) == 0.5
    # Upper edge of bin 0 (exclusive) / lower edge of bin 1 (inclusive)
    assert _recall_for(2.0, recall_obj) == 0.8
    # Interior of bin 1
    assert _recall_for(2.5, recall_obj) == 0.8
    # Recall=0 bin should return None (not usable / prevents ZeroDivisionError)
    assert _recall_for(3.5, recall_obj) is None

    # Test through /api/hazard-grid with recall=0 bin
    req = {
        "image": {**MOCK_IMAGE, "width": 100, "height": 100},
        "detections": [
            {"id": 1, "bbox": [10, 10, 17, 17], "confidence": 0.9},  # 7px * 0.5 = 3.5m -> in recall=0 bin
        ],
        "shadow_lengths_px": {"1": 10.0},
        "config": {"grid_rows": 2, "grid_cols": 2, "apply_recall_correction": True},
        "recall": {
            "bins": [
                {"min_diameter_m": 3.0, "max_diameter_m": 4.0, "recall": 0.0}
            ]
        },
    }
    r = client.post("/api/hazard-grid", json=req)
    assert r.status_code == 200
    cell = r.json()["hazard_cells"][0]
    # Recall was 0, so correction could not be applied; count remains raw 1
    assert cell["corrected_boulder_count"] == 1.0
    assert cell["recall_corrected"] is False


def test_nan_inf_inputs_raise_or_handled(client):
    import math
    import pytest
    from app.services.hazard import (
        footprint_area_m2,
        poisson_hazard_probability,
        suggest_grid_dimensions,
    )
    from app.services.measurement import height_from_shadow

    # 1. Scientific math helpers reject NaN/inf
    with pytest.raises(ValueError, match="must be positive"):
        footprint_area_m2(float("nan"))
    with pytest.raises(ValueError, match="must be positive"):
        footprint_area_m2(float("inf"))

    with pytest.raises(ValueError, match="must be non-negative"):
        poisson_hazard_probability(float("nan"), 100.0)
    with pytest.raises(ValueError, match="must be positive"):
        poisson_hazard_probability(0.1, float("inf"))

    with pytest.raises(ValueError, match="positive finite"):
        suggest_grid_dimensions(100, 100, float("nan"), 10.0)
    with pytest.raises(ValueError, match="positive finite"):
        suggest_grid_dimensions(100, 100, 0.5, float("inf"))

    with pytest.raises(ValueError, match="must be finite"):
        height_from_shadow(float("nan"), 0.5, 30.0)
    with pytest.raises(ValueError, match="must be finite"):
        height_from_shadow(10.0, float("inf"), 30.0)

    # 2. Hazard grid service with NaN and Inf in slope_by_cell handles them safely
    from app.services.hazard import build_hazard_grid
    from app.schemas.contracts import AnalysisConfig, ImageInfo

    img_info = ImageInfo(**{**MOCK_IMAGE, "width": 100, "height": 100})
    grid_nan = build_hazard_grid(
        image=img_info,
        detections=[],
        measurements=[],
        config=AnalysisConfig(grid_rows=2, grid_cols=2),
        slope_by_cell=[[float("nan"), 5.0], [float("inf"), 5.0]],
    )
    cell_00 = [c for c in grid_nan.cells if c.row == 0 and c.col == 0][0]
    assert cell_00.slope_gate == "not_assessed"
    cell_10 = [c for c in grid_nan.cells if c.row == 1 and c.col == 0][0]
    assert cell_10.slope_gate == "not_assessed"
    assert any("Invalid slope value" in w for w in grid_nan.warnings)
