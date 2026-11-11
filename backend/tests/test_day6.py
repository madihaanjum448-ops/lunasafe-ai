"""
LunaSafe AI - Day 6 tests: classification (FR-08), slope gate (FR-07), and end-to-end pipeline.
"""
import io
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.schemas.contracts import AnalysisConfig, HazardClass
from app.services.classification import classify_cell, explain_cell


@pytest.fixture
def client():
    return TestClient(app)


def _make_png_bytes(width=100, height=100):
    buf = io.BytesIO()
    img = Image.new("L", (width, height), color=128)
    img.save(buf, format="PNG")
    return buf.getvalue()


# =====================================================================
# 1. CLASSIFICATION TRUTH TABLE & BOUNDARIES (FR-08)
# =====================================================================

def test_classification_truth_table_precedence():
    cfg = AnalysisConfig(caution_p_hazard=0.10, unsafe_p_hazard=0.30, slope_gate_deg=10.0)

    # 1. Slope gate fail -> Unsafe (overrides zero or low probability)
    cls1, r1 = classify_cell(
        p_hazard=0.0, slope_gate="fail", unknown_height_count=0, fallback_in_cell=False, config=cfg
    )
    assert cls1 == HazardClass.unsafe
    assert r1 == ["slope_gate_failed"]

    # 2. Probability >= unsafe threshold -> Unsafe
    cls2, r2 = classify_cell(
        p_hazard=0.35, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False, config=cfg
    )
    assert cls2 == HazardClass.unsafe
    assert r2 == ["p_hazard_at_or_above_unsafe_threshold"]

    # Exact boundary: p == unsafe threshold -> Unsafe
    cls2_bound, r2_bound = classify_cell(
        p_hazard=0.30, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False, config=cfg
    )
    assert cls2_bound == HazardClass.unsafe
    assert r2_bound == ["p_hazard_at_or_above_unsafe_threshold"]

    # 3. Probability >= caution threshold -> Caution
    cls3, r3 = classify_cell(
        p_hazard=0.20, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False, config=cfg
    )
    assert cls3 == HazardClass.caution
    assert r3 == ["p_hazard_at_or_above_caution_threshold"]

    # Exact boundary: p == caution threshold -> Caution
    cls3_bound, r3_bound = classify_cell(
        p_hazard=0.10, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False, config=cfg
    )
    assert cls3_bound == HazardClass.caution
    assert r3_bound == ["p_hazard_at_or_above_caution_threshold"]

    # 4. Otherwise Safe candidate
    cls4, r4 = classify_cell(
        p_hazard=0.05, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False, config=cfg
    )
    assert cls4 == HazardClass.safe
    assert r4 == ["p_hazard_below_caution_threshold"]


def test_classification_downgrades():
    cfg = AnalysisConfig(caution_p_hazard=0.10, unsafe_p_hazard=0.30, slope_gate_deg=10.0)

    # Slope not assessed -> downgraded from Safe to Caution
    c_slope, r_slope = classify_cell(
        p_hazard=0.02, slope_gate="not_assessed", unknown_height_count=0, fallback_in_cell=False, config=cfg
    )
    assert c_slope == HazardClass.caution
    assert "downgraded_slope_not_assessed" in r_slope

    # Height unknown -> downgraded from Safe to Caution
    c_unk, r_unk = classify_cell(
        p_hazard=0.02, slope_gate="pass", unknown_height_count=2, fallback_in_cell=False, config=cfg
    )
    assert c_unk == HazardClass.caution
    assert "downgraded_height_unknown" in r_unk

    # Fallback in cell -> downgraded from Safe to Caution
    c_fb, r_fb = classify_cell(
        p_hazard=0.02, slope_gate="pass", unknown_height_count=0, fallback_in_cell=True, config=cfg
    )
    assert c_fb == HazardClass.caution
    assert "downgraded_fallback_height" in r_fb


def test_classification_optional_proposals():
    # 1. slope_margin_deg (default 0.0 is off)
    cfg_default = AnalysisConfig(slope_gate_deg=10.0, slope_margin_deg=0.0)
    c_def, r_def = classify_cell(
        p_hazard=0.02, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False,
        config=cfg_default, slope_deg=9.0
    )
    assert c_def == HazardClass.safe
    assert "slope_within_margin_of_gate" not in r_def

    # When slope_margin_deg = 2.0: gate is 10.0, margin is [8.0, 10.0]
    cfg_margin = AnalysisConfig(slope_gate_deg=10.0, slope_margin_deg=2.0)
    # Slope 7.5 deg is below 8.0 deg -> Safe
    c_safe, _ = classify_cell(
        p_hazard=0.02, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False,
        config=cfg_margin, slope_deg=7.5
    )
    assert c_safe == HazardClass.safe

    # Slope 8.5 deg is within margin -> Caution
    c_marg, r_marg = classify_cell(
        p_hazard=0.02, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False,
        config=cfg_margin, slope_deg=8.5
    )
    assert c_marg == HazardClass.caution
    assert "slope_within_margin_of_gate" in r_marg

    # 2. use_interval_upper_bound (default False is off)
    cfg_int_off = AnalysisConfig(unsafe_p_hazard=0.30, use_interval_upper_bound=False)
    c_ioff, r_ioff = classify_cell(
        p_hazard=0.02, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False,
        config=cfg_int_off, interval_high=0.35
    )
    assert c_ioff == HazardClass.safe
    assert "interval_reaches_unsafe_threshold" not in r_ioff

    # When use_interval_upper_bound = True: interval_high >= 0.30 -> Caution
    cfg_int_on = AnalysisConfig(unsafe_p_hazard=0.30, use_interval_upper_bound=True)
    c_ion, r_ion = classify_cell(
        p_hazard=0.02, slope_gate="pass", unknown_height_count=0, fallback_in_cell=False,
        config=cfg_int_on, interval_high=0.35
    )
    assert c_ion == HazardClass.caution
    assert "interval_reaches_unsafe_threshold" in r_ion


def test_explanation_states_decision_rule():
    cfg = AnalysisConfig()
    exp_slope = explain_cell(
        classification=HazardClass.unsafe,
        probability=0.0,
        hazardous_count=0,
        corrected_count=0,
        total_count=0,
        slope=15.0,
        slope_gate="fail",
        config=cfg,
        missing=[],
        reasons=["slope_gate_failed"],
    )
    assert "slope gate hard-stop" in exp_slope

    exp_p = explain_cell(
        classification=HazardClass.unsafe,
        probability=0.45,
        hazardous_count=5,
        corrected_count=5,
        total_count=5,
        slope=2.0,
        slope_gate="pass",
        config=cfg,
        missing=[],
        reasons=["p_hazard_at_or_above_unsafe_threshold"],
    )
    assert "meets or exceeds the 30% unsafe threshold" in exp_p


# =====================================================================
# 2. CONFIG VALIDATION & API CONFIG (FR-08)
# =====================================================================

def test_config_validator_rejects_caution_ge_unsafe():
    # caution >= unsafe must raise ValueError
    with pytest.raises(ValueError, match="caution_p_hazard .* must be strictly less than unsafe_p_hazard"):
        AnalysisConfig(caution_p_hazard=0.30, unsafe_p_hazard=0.30)

    with pytest.raises(ValueError, match="caution_p_hazard .* must be strictly less than unsafe_p_hazard"):
        AnalysisConfig(caution_p_hazard=0.40, unsafe_p_hazard=0.20)


def test_config_api_endpoint_and_threshold_changes(client):
    # GET /api/config returns default config with new fields
    r = client.get("/api/config")
    assert r.status_code == 200
    cfg_res = r.json()
    assert "slope_margin_deg" in cfg_res
    assert "use_interval_upper_bound" in cfg_res
    assert "slope_statistic" in cfg_res

    # Invalid config posted to hazard-grid returns 422
    bad_req = {
        "image": {"id": "test", "width": 100, "height": 100, "pixel_scale_m": 0.5, "sun_elevation_deg": 30.0},
        "detections": [],
        "config": {"caution_p_hazard": 0.40, "unsafe_p_hazard": 0.20},
    }
    r_bad = client.post("/api/hazard-grid", json=bad_req)
    assert r_bad.status_code == 422
    assert "caution_p_hazard" in r_bad.text


# =====================================================================
# 3. END-TO-END PIPELINE ENDPOINT (FR-07, FR-08, Gate 3)
# =====================================================================

def test_pipeline_complete_flow_with_dem(client):
    img_bytes = _make_png_bytes(200, 200)

    # Create 2x2 ramp DEM: row 0 is flat (0 slope), row 1 is steep ramp
    dem_arr = np.zeros((20, 20), dtype=float)
    dem_arr[10:, :] = np.arange(10, dtype=float).reshape(-1, 1) * 0.4
    dem_buf = io.BytesIO()
    np.save(dem_buf, dem_arr)

    dets_json = json.dumps([
        {"id": 1, "bbox": [20, 20, 26, 26], "confidence": 0.95},  # cell (0, 0)
    ])
    shadows_json = json.dumps({"1": 10.0})
    cfg_json = json.dumps({"grid_rows": 2, "grid_cols": 2, "slope_gate_deg": 10.0})

    files = {
        "image": ("lunar.png", img_bytes, "image/png"),
        "dem_file": ("dem.npy", dem_buf.getvalue(), "application/octet-stream"),
    }
    data = {
        "pixel_scale_m": "0.50",
        "sun_elevation_deg": "30.0",
        "detections": dets_json,
        "shadow_lengths_px": shadows_json,
        "config": cfg_json,
        "dem_cell_size_m": "1.0",
    }

    r = client.post("/api/pipeline", files=files, data=data)
    assert r.status_code == 200
    res = r.json()

    assert {"image", "detections", "measurements", "hazard_cells", "warnings", "disclaimer", "is_mock"} <= set(res)
    assert len(res["hazard_cells"]) == 4

    # Row 0 cells: flat slope -> slope_gate == pass
    c00 = [c for c in res["hazard_cells"] if c["row"] == 0 and c["col"] == 0][0]
    assert c00["slope_gate"] == "pass"
    assert c00["interval_low"] is not None and c00["interval_high"] is not None
    assert c00["interval_low"] <= c00["p_hazard"] <= c00["interval_high"]

    # Row 1 cells: steep slope -> slope_gate == fail -> Unsafe
    c10 = [c for c in res["hazard_cells"] if c["row"] == 1 and c["col"] == 0][0]
    assert c10["slope_gate"] == "fail"
    assert c10["class"] == "unsafe"
    assert "slope_gate_failed" in c10["reasons"]


def test_pipeline_without_dem_produces_no_safe_cells(client):
    img_bytes = _make_png_bytes(100, 100)
    dets_json = json.dumps([])  # 0 boulders
    cfg_json = json.dumps({"grid_rows": 2, "grid_cols": 2})

    files = {
        "image": ("lunar.png", img_bytes, "image/png"),
    }
    data = {
        "pixel_scale_m": "0.50",
        "sun_elevation_deg": "30.0",
        "detections": dets_json,
        "config": cfg_json,
    }

    r = client.post("/api/pipeline", files=files, data=data)
    assert r.status_code == 200
    res = r.json()

    # Without DEM, slope_gate must be not_assessed and NO cell can be Safe
    for cell in res["hazard_cells"]:
        assert cell["slope_gate"] == "not_assessed"
        assert cell["class"] != "safe"
        assert "downgraded_slope_not_assessed" in cell["reasons"]

    assert any("slope gate not assessed" in w for w in res["warnings"])


def test_pipeline_without_sun_angle_labels_fallback_no_confirmed_hazards(client):
    img_bytes = _make_png_bytes(100, 100)
    dets_json = json.dumps([
        {"id": 1, "bbox": [10, 10, 20, 20], "confidence": 0.95},
    ])
    cfg_json = json.dumps({"grid_rows": 2, "grid_cols": 2})

    files = {
        "image": ("lunar.png", img_bytes, "image/png"),
    }
    data = {
        "pixel_scale_m": "0.50",
        # sun_elevation_deg omitted!
        "detections": dets_json,
        "config": cfg_json,
    }

    r = client.post("/api/pipeline", files=files, data=data)
    assert r.status_code == 200
    res = r.json()

    # Measurement must be fallback and low confidence
    meas = res["measurements"][0]
    assert meas["method"] == "diameter_fallback"
    assert meas["confidence"] == "low"
    assert meas["is_hazardous"] is None

    # Fallback boulders are excluded from confirmed hazardous counts
    c00 = [c for c in res["hazard_cells"] if c["row"] == 0 and c["col"] == 0][0]
    assert c00["hazardous_boulder_count"] == 0.0
    assert c00["p_hazard"] == 0.0
    assert c00["largest_height_method"] == "diameter_fallback"


def test_pipeline_error_handling(client):
    img_bytes = _make_png_bytes(100, 100)

    # 1. Bad JSON in detections -> 422
    r_bad_det = client.post(
        "/api/pipeline",
        files={"image": ("lunar.png", img_bytes, "image/png")},
        data={"pixel_scale_m": "0.5", "detections": "{bad json"},
    )
    assert r_bad_det.status_code == 422
    assert "Invalid JSON in detections" in r_bad_det.text

    # 2. Mismatched detection ID in shadow lengths -> 422
    r_mismatch = client.post(
        "/api/pipeline",
        files={"image": ("lunar.png", img_bytes, "image/png")},
        data={
            "pixel_scale_m": "0.5",
            "detections": json.dumps([{"id": 1, "bbox": [10, 10, 20, 20], "confidence": 0.9}]),
            "shadow_lengths_px": json.dumps({"999": 15.0}),  # unknown ID 999
        },
    )
    assert r_mismatch.status_code == 422
    assert "unknown detection ID" in r_mismatch.text

    # 3. Missing pixel scale on non-GeoTIFF -> 422
    r_no_scale = client.post(
        "/api/pipeline",
        files={"image": ("lunar.png", img_bytes, "image/png")},
        data={"detections": json.dumps([])},
    )
    assert r_no_scale.status_code == 422
    assert "pixel_scale_m is required" in r_no_scale.text
