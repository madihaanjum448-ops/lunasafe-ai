"""
Tests for Member 2 Day 7:
- Propagated shadow uncertainty (FR-04)
- Shadow quality flags ('good', 'fair', 'poor')
- Height validation against reference heights
"""
import math
import pytest
from app.schemas.contracts import (
    AnalysisConfig,
    Confidence,
    Detection,
    HazardClass,
    ImageInfo,
    MeasurementMethod,
    ShadowQuality,
)
from app.services.measurement import height_from_shadow, measure_detections
from app.services.hazard import build_hazard_grid


def test_height_uncertainty_hand_computed_and_backward_compatibility():
    # Test parameters:
    # shadow_length_px = 10.0, pixel_scale_m = 0.5 -> L = 5.0 m
    # sun_elevation_deg = 30 deg -> tan(30 deg) = 1/sqrt(3) ~= 0.577350269
    # pixel_uncertainty_px = 1.0 -> sigma_L = 0.5 m
    # Case 1: sigma_e = 0.0 deg
    h, sigma_h = height_from_shadow(
        shadow_length_px=10.0,
        pixel_scale_m=0.5,
        sun_elevation_deg=30.0,
        pixel_uncertainty_px=1.0,
        sun_elevation_uncertainty_deg=0.0,
    )
    expected_h = 5.0 * math.tan(math.radians(30.0))
    expected_sigma_h_zero = 0.5 * math.tan(math.radians(30.0))
    assert math.isclose(h, expected_h, rel_tol=1e-6)
    assert math.isclose(sigma_h, expected_sigma_h_zero, rel_tol=1e-6)

    # Case 2: sigma_e = 1.0 deg
    # term_L = 0.5 * tan(30 deg) ~= 0.288675135
    # sec(30 deg) = 2/sqrt(3), sec^2(30 deg) = 4/3
    # sigma_e_rad = 1.0 * pi / 180 ~= 0.0174532925
    # term_e = 5.0 * (4/3) * (pi / 180) ~= 0.116355283
    # sigma_h = sqrt(term_L^2 + term_e^2) ~= sqrt(0.083333333 + 0.013538552) ~= 0.311242486
    h2, sigma_h2 = height_from_shadow(
        shadow_length_px=10.0,
        pixel_scale_m=0.5,
        sun_elevation_deg=30.0,
        pixel_uncertainty_px=1.0,
        sun_elevation_uncertainty_deg=1.0,
    )
    term_L = 0.5 * math.tan(math.radians(30.0))
    term_e = 5.0 * (1.0 / math.cos(math.radians(30.0))) ** 2 * math.radians(1.0)
    expected_sigma_h2 = math.sqrt(term_L ** 2 + term_e ** 2)
    assert math.isclose(h2, expected_h, rel_tol=1e-6)
    assert math.isclose(sigma_h2, expected_sigma_h2, rel_tol=1e-6)
    assert sigma_h2 > sigma_h  # Monotonic increase


def test_height_uncertainty_monotonicity():
    # As sun_elevation_uncertainty increases, sigma_h must strictly increase
    sigmas = []
    for deg in [0.0, 0.5, 1.0, 2.0, 5.0]:
        _, sigma_h = height_from_shadow(
            shadow_length_px=12.0,
            pixel_scale_m=0.5,
            sun_elevation_deg=25.0,
            pixel_uncertainty_px=1.0,
            sun_elevation_uncertainty_deg=deg,
        )
        sigmas.append(sigma_h)
    assert sigmas == sorted(sigmas)
    assert len(set(sigmas)) == len(sigmas)


def test_shadow_quality_flags_in_measurement():
    image = ImageInfo(width=100, height=100, pixel_scale_m=0.5, sun_elevation_deg=30.0)
    dets = [
        Detection(id=1, bbox=[10, 10, 20, 20], confidence=0.9),  # good
        Detection(id=2, bbox=[30, 30, 40, 40], confidence=0.9),  # fair -> cap at medium
        Detection(id=3, bbox=[50, 50, 60, 60], confidence=0.9),  # poor -> low confidence, is_hazardous None
    ]
    cfg = AnalysisConfig(hazard_height_threshold_m=0.5)
    shadows = {1: 10.0, 2: 10.0, 3: 10.0}
    quality = {1: "good", 2: "fair", 3: "poor"}

    meas_file = measure_detections(image, dets, cfg, shadows, shadow_quality=quality)
    meas = {m.detection_id: m for m in meas_file.measurements}

    # Good
    assert meas[1].confidence == Confidence.high
    assert meas[1].is_hazardous is True
    assert meas[1].shadow_quality == ShadowQuality.good

    # Fair
    assert meas[2].confidence == Confidence.medium  # Capped from high to medium
    assert meas[2].is_hazardous is True
    assert meas[2].shadow_quality == ShadowQuality.fair

    # Poor
    assert meas[3].confidence == Confidence.low
    assert meas[3].is_hazardous is None  # Excluded from confirmed hazard status
    assert meas[3].shadow_quality == ShadowQuality.poor
    assert any("poor" in w.lower() for w in meas[3].warnings)


def test_poor_shadow_quality_excluded_from_hazard_counts():
    image = ImageInfo(width=100, height=100, pixel_scale_m=0.5, sun_elevation_deg=30.0)
    # Cell 0,0 containing only one detection with poor shadow quality
    dets = [Detection(id=1, bbox=[10, 10, 20, 20], confidence=0.9)]
    cfg = AnalysisConfig(hazard_height_threshold_m=0.5, grid_rows=2, grid_cols=2)
    shadows = {1: 20.0}  # Tall boulder (~5.7m), but poor shadow
    quality = {1: "poor"}

    meas_file = measure_detections(image, dets, cfg, shadows, shadow_quality=quality)
    slope_by_cell = [[5.0, 5.0], [5.0, 5.0]]  # Slope passes

    grid = build_hazard_grid(image, dets, meas_file.measurements, cfg, slope_by_cell=slope_by_cell)
    cell = grid.hazard_cells[0]

    # Boulder must be excluded from hazardous count
    assert cell.hazardous_boulder_count == 0
    assert cell.raw_boulder_count == 1
    assert cell.p_hazard == 0.0
    # Because height is unconfirmed (poor shadow), safe is downgraded to caution
    assert cell.class_ == HazardClass.caution
    assert "downgraded_height_unknown" in cell.reasons


def test_reference_heights_validation_metrics():
    image = ImageInfo(width=100, height=100, pixel_scale_m=0.5, sun_elevation_deg=30.0)
    dets = [
        Detection(id=1, bbox=[10, 10, 20, 20], confidence=0.9),
        Detection(id=2, bbox=[30, 30, 40, 40], confidence=0.9),
    ]
    cfg = AnalysisConfig()
    shadows = {1: 10.0, 2: 15.0}  # Heights ~= 2.887m and 4.330m

    # Case 1: No reference set
    m1 = measure_detections(image, dets, cfg, shadows)
    assert m1.height_validated is False
    assert m1.reference_count is None
    assert any("unvalidated" in w.lower() for w in m1.warnings)

    # Case 2: Reference set provided
    # Let reference for 1 be 3.0m (diff = 2.887 - 3.0 = -0.113)
    # Let reference for 2 be 4.0m (diff = 4.330 - 4.0 = +0.330)
    refs = {1: 3.0, 2: 4.0}
    m2 = measure_detections(image, dets, cfg, shadows, reference_heights_m=refs)
    assert m2.height_validated is True
    assert m2.reference_count == 2
    assert m2.height_mae_m is not None
    assert m2.height_bias_m is not None
    # Check MAE and Bias math
    h1 = m2.measurements[0].height_m
    h2 = m2.measurements[1].height_m
    expected_mae = round((abs(h1 - 3.0) + abs(h2 - 4.0)) / 2.0, 4)
    expected_bias = round(((h1 - 3.0) + (h2 - 4.0)) / 2.0, 4)
    assert m2.height_mae_m == expected_mae
    assert m2.height_bias_m == expected_bias


def test_known_site_runner_mock_refusal_and_execution(tmp_path):
    from pathlib import Path
    import subprocess
    import json
    import sys

    fixtures_dir = Path("backend/tests/fixtures/known_site")
    image_path = fixtures_dir / "image.png"
    mock_dets = fixtures_dir / "detections_mock.json"
    real_format_dets = fixtures_dir / "detections.json"
    shadows_path = fixtures_dir / "shadows.json"
    quality_path = fixtures_dir / "quality.json"
    dem_path = fixtures_dir / "dem.npy"
    recall_path = fixtures_dir / "recall.json"

    # 1. Refusal on mock data without --allow-mock
    res_refusal = subprocess.run(
        [
            sys.executable,
            "backend/scripts/run_known_site.py",
            "--image", str(image_path),
            "--detections", str(mock_dets),
            "--pixel-scale", "0.5",
            "--sun-elevation", "30.0",
            "--out", str(tmp_path / "out_refusal"),
        ],
        capture_output=True,
        text=True,
    )
    assert res_refusal.returncode == 1
    assert "Refusing to run without explicit --allow-mock" in res_refusal.stderr

    # 2. Execution with --allow-mock
    out_dir = tmp_path / "out_allowed"
    res_allowed = subprocess.run(
        [
            sys.executable,
            "backend/scripts/run_known_site.py",
            "--image", str(image_path),
            "--detections", str(mock_dets),
            "--shadows", str(shadows_path),
            "--quality", str(quality_path),
            "--dem", str(dem_path),
            "--dem-cell-size", "2.5",
            "--recall", str(recall_path),
            "--pixel-scale", "0.5",
            "--sun-elevation", "30.0",
            "--allow-mock",
            "--out", str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res_allowed.returncode == 0
    assert (out_dir / "measurements.json").exists()
    assert (out_dir / "hazard_grid.json").exists()
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "run_manifest.json").exists()

    with open(out_dir / "run_manifest.json") as f:
        manifest = json.load(f)
    assert manifest["is_mock"] is True
    assert "image" in manifest["input_files_sha256"]
    assert "git_commit_hash" in manifest
    assert len(manifest["unconfirmed_placeholders"]) > 0

    with open(out_dir / "summary.json") as f:
        summary = json.load(f)
    assert summary["is_mock"] is True
    assert summary["slope_availability"]["assessed"] is True
    assert summary["detections_summary"]["total_detections"] == 3


def test_compare_global_map_script(tmp_path):
    from pathlib import Path
    import subprocess
    import json
    import sys
    import numpy as np

    comp_fixtures = Path("backend/tests/fixtures/comparison")
    grid_geo = comp_fixtures / "hazard_grid_geo.json"
    ref_csv = comp_fixtures / "reference_boulders.csv"

    # 1. Missing georeference check
    no_geo_grid = tmp_path / "no_geo_grid.json"
    with open(grid_geo) as f:
        data = json.load(f)
    data["image"]["geotransform"] = None
    with open(no_geo_grid, "w") as f:
        json.dump(data, f)

    res_no_geo = subprocess.run(
        [
            sys.executable,
            "backend/scripts/compare_global_map.py",
            "--hazard-grid", str(no_geo_grid),
            "--reference", str(ref_csv),
            "--out", str(tmp_path / "rep1.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert res_no_geo.returncode == 1
    assert "Cannot map global reference data without valid georeferencing" in res_no_geo.stderr

    # 2. Valid CSV comparison
    rep_csv = tmp_path / "rep_csv.json"
    res_csv = subprocess.run(
        [
            sys.executable,
            "backend/scripts/compare_global_map.py",
            "--hazard-grid", str(grid_geo),
            "--reference", str(ref_csv),
            "--ref-resolution-m", "5.0",
            "--out", str(rep_csv),
        ],
        capture_output=True,
        text=True,
    )
    assert res_csv.returncode == 0
    with open(rep_csv) as f:
        rep = json.load(f)
    assert rep["n_cells_compared"] == 16
    assert rep["spearman_rank_correlation"] > 0.95
    assert "Resolution mismatch" in rep["resolution_comparison"]["limitation"]
    assert "correlation_met" in rep["evaluation_against_placeholders"]

    # 3. Valid raster (.npy) comparison
    ref_raster = tmp_path / "ref_raster.npy"
    np.save(ref_raster, np.ones((4, 4), dtype=float) * 0.1)
    rep_raster = tmp_path / "rep_raster.json"
    res_raster = subprocess.run(
        [
            sys.executable,
            "backend/scripts/compare_global_map.py",
            "--hazard-grid", str(grid_geo),
            "--reference", str(ref_raster),
            "--ref-type", "raster",
            "--out", str(rep_raster),
        ],
        capture_output=True,
        text=True,
    )
    assert res_raster.returncode == 0
    with open(rep_raster) as f:
        rep_r = json.load(f)
    assert rep_r["n_cells_compared"] == 16


def test_sensitivity_script_execution_and_monotonicity(tmp_path):
    from pathlib import Path
    import subprocess
    import json
    import csv
    import sys

    fixtures_dir = Path("backend/tests/fixtures/known_site")
    image_path = fixtures_dir / "image.png"
    mock_dets = fixtures_dir / "detections_mock.json"
    shadows_path = fixtures_dir / "shadows.json"
    quality_path = fixtures_dir / "quality.json"
    dem_path = fixtures_dir / "dem.npy"
    recall_path = fixtures_dir / "recall.json"
    out_dir = tmp_path / "sensitivity_out"

    # 1. Refusal on mock data without --allow-mock
    res_ref = subprocess.run(
        [
            sys.executable,
            "backend/scripts/sensitivity.py",
            "--image", str(image_path),
            "--detections", str(mock_dets),
            "--pixel-scale", "0.5",
            "--sun-elevation", "30.0",
            "--out-dir", str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res_ref.returncode == 1
    assert "Refusing to run sensitivity sweep without --allow-mock" in res_ref.stderr

    # 2. Execution with --allow-mock
    res_run = subprocess.run(
        [
            sys.executable,
            "backend/scripts/sensitivity.py",
            "--image", str(image_path),
            "--detections", str(mock_dets),
            "--shadows", str(shadows_path),
            "--quality", str(quality_path),
            "--dem", str(dem_path),
            "--dem-cell-size", "2.5",
            "--recall", str(recall_path),
            "--pixel-scale", "0.5",
            "--sun-elevation", "30.0",
            "--allow-mock",
            "--out-dir", str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res_run.returncode == 0
    assert (out_dir / "sensitivity.csv").exists()
    assert (out_dir / "sensitivity.json").exists()

    # Read CSV results
    rows = []
    with open(out_dir / "sensitivity.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    # 3. Check baseline row exists and class_diff_from_baseline is 0
    baseline_row = [r for r in rows if r["parameter_varied"] == "baseline"][0]
    assert int(baseline_row["class_diff_from_baseline"]) == 0
    assert float(baseline_row["footprint_diameter_m"]) == 10.0

    # 4. Check larger footprint never lowers p_hazard
    footprint_rows = [
        r for r in rows if r["parameter_varied"] in ("baseline", "footprint_diameter_m")
    ]
    footprint_rows.sort(key=lambda r: float(r["footprint_diameter_m"]))
    prev_max_p = 0.0
    for r in footprint_rows:
        cur_max_p = float(r["max_p_hazard"])
        assert cur_max_p >= prev_max_p  # Monotonic increase
        prev_max_p = cur_max_p



