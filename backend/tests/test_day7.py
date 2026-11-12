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
