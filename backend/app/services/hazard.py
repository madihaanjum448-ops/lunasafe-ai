
"""
LunaSafe AI - Boulder hazard assessment service.

Calculates:
    P(hazard) = 1 - exp(-rho_h * A)

where:
    rho_h = hazardous boulder density (boulders / m²)
    A     = circular lander footprint area (m²)

The slope gate is evaluated independently from the
Poisson footprint hazard probability.

Important limitations:
- Diameter-fallback heights are provisional assumptions.
- Fallback heights are never treated as confirmed physical heights.
- Only shadow-based height measurements determine hazardous status.
- Unknown heights prevent a Safe candidate classification.
- Missing slope data prevents a Safe candidate classification.
- Recall correction is applied when a valid size-bin recall exists.
- This is a research prototype, not a flight-certified system.
"""

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.schemas.contracts import (
    CLASS_LABELS,
    AnalysisConfig,
    Detection,
    HazardCell,
    HazardClass,
    HazardGridFile,
    ImageInfo,
    Measurement,
    MeasurementMethod,
    RecallFile,
)
from app.services.classification import classify_cell, explain_cell


# ================================================================
# 1. FOOTPRINT AREA AND POISSON PROBABILITY
# ================================================================

def footprint_area_m2(diameter_m: float) -> float:
    """Calculate the area of a circular lander footprint."""

    if not math.isfinite(diameter_m) or diameter_m <= 0:
        raise ValueError(
            "Lander footprint diameter must be positive."
        )

    return math.pi * (diameter_m / 2.0) ** 2


def poisson_hazard_probability(
    rho_h_per_m2: float,
    area_m2: float,
) -> float:
    """Calculate the probability of at least one hazardous boulder."""

    if not math.isfinite(rho_h_per_m2) or rho_h_per_m2 < 0:
        raise ValueError(
            "Hazardous boulder density must be non-negative."
        )

    if not math.isfinite(area_m2) or area_m2 <= 0:
        raise ValueError(
            "Footprint area must be positive."
        )

    probability = 1.0 - math.exp(-rho_h_per_m2 * area_m2)

    return max(0.0, min(1.0, probability))


def suggest_grid_dimensions(
    image_width: int,
    image_height: int,
    pixel_scale_m: float,
    footprint_diameter_m: float,
) -> Tuple[int, int]:
    """
    Suggest grid (rows, cols) so that each grid cell dimension approximately
    matches the lander footprint diameter, avoiding probability dilution
    while keeping cells large enough to encompass a landing attempt.

    Formula:
        cols = max(1, round((image_width * pixel_scale_m) / footprint_diameter_m))
        rows = max(1, round((image_height * pixel_scale_m) / footprint_diameter_m))

    Returns:
        (rows, cols)
    """
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Image dimensions must be positive.")
    if not math.isfinite(pixel_scale_m) or pixel_scale_m <= 0:
        raise ValueError("Pixel scale must be a positive finite number.")
    if not math.isfinite(footprint_diameter_m) or footprint_diameter_m <= 0:
        raise ValueError("Footprint diameter must be a positive finite number.")

    width_m = image_width * pixel_scale_m
    height_m = image_height * pixel_scale_m

    cols = max(1, int(round(width_m / footprint_diameter_m)))
    rows = max(1, int(round(height_m / footprint_diameter_m)))

    return rows, cols


# ================================================================
# 2. RECALL LOOKUP
# ================================================================

def _recall_for(
    diameter_m: Optional[float],
    recall: Optional[RecallFile],
) -> Optional[float]:
    """Find the recall value corresponding to a boulder diameter."""

    if recall is None or diameter_m is None:
        return None

    if not math.isfinite(diameter_m) or diameter_m < 0:
        return None

    for bin_data in recall.bins:
        lower = bin_data.bin_min_m

        upper = (
            bin_data.bin_max_m
            if bin_data.bin_max_m is not None
            else float("inf")
        )

        if lower <= diameter_m < upper:
            if 0 < bin_data.recall <= 1:
                return bin_data.recall

            return None

    return None


def _corrected_count(
    diameter_m: Optional[float],
    recall: Optional[RecallFile],
    recall_floor: float = 0.2,
) -> Tuple[float, bool, bool]:
    """
    Return the recall-adjusted contribution of one hazardous boulder.

    Returns:
        (weight, was_corrected, was_capped)

    If no valid recall bin exists or recall is 0, retain raw contribution of 1.0 (uncorrected).
    If 0 < recall < recall_floor, clamp recall to recall_floor to prevent weight explosion.
    """

    recall_value = _recall_for(diameter_m, recall)

    if recall_value is None or recall_value <= 0:
        return 1.0, False, False

    was_capped = False
    effective_recall = recall_value
    if effective_recall < recall_floor:
        effective_recall = recall_floor
        was_capped = True

    return 1.0 / effective_recall, True, was_capped


def compute_bootstrap_interval(
    cell_detections: List[Detection],
    cell_measurements: List[Optional[Measurement]],
    cell_area_m2: float,
    footprint_area_m2: float,
    corrected_hazardous: float,
    p_hazard: float,
    config: AnalysisConfig,
    recall: Optional[RecallFile],
    rng: np.random.Generator,
) -> Tuple[Optional[float], Optional[float], List[str], List[str]]:
    """
    Compute bootstrap uncertainty interval [interval_low, interval_high] for a cell.

    Returns:
        (interval_low, interval_high, cell_warnings, missing_inputs)

    Rules:
    - If cell has 0 detections: interval is [0.0, 0.0].
    - If cell has detections but NO genuine shadow-measured heights (fallback only):
      interval is (None, None) and missing_inputs records that heights are unmeasured.
    - If cell has < 5 detections: parametric Poisson(corrected_hazardous) resampling is used
      to avoid bootstrap collapse on small samples. A cell warning is generated.
    - If cell has >= 5 detections:
      (a) for each measured detection, draw height ~ Normal(height_m, height_uncertainty_m)
          and re-decide hazardous vs not (height >= hazard_height_threshold_m);
      (b) resample cell's detections with replacement;
      (c) apply recall weights (with recall_floor cap);
      (d) recompute rho and P across bootstrap replicates and take percentile interval.
    - Guarantees interval_low <= p_hazard <= interval_high.
    """
    cell_warnings: List[str] = []
    missing_inputs: List[str] = []

    if len(cell_detections) == 0:
        return 0.0, 0.0, cell_warnings, missing_inputs

    has_shadow = any(
        m is not None
        and m.method == MeasurementMethod.shadow_geometry
        and m.height_m is not None
        for m in cell_measurements
    )
    if not has_shadow:
        missing_inputs.append(
            "uncertainty interval unavailable: boulder heights are unmeasured fallback assumptions"
        )
        return None, None, cell_warnings, missing_inputs

    alpha_low = (1.0 - config.bootstrap_ci) / 2.0 * 100.0
    alpha_high = (1.0 + config.bootstrap_ci) / 2.0 * 100.0
    b_reps = config.bootstrap_n

    if len(cell_detections) < 5:
        # Parametric Poisson resampling for low counts (< 5 detections)
        k_samples = rng.poisson(lam=corrected_hazardous, size=b_reps)
        rho_samples = k_samples / cell_area_m2
        p_samples = 1.0 - np.exp(-rho_samples * footprint_area_m2)
        p_low = float(np.percentile(p_samples, alpha_low))
        p_high = float(np.percentile(p_samples, alpha_high))
        cell_warnings.append(
            f"Low detection count ({len(cell_detections)} < 5): uncertainty interval "
            f"estimated via parametric Poisson({corrected_hazardous:.2f}) resampling."
        )
    else:
        # Non-parametric bootstrap with height measurement uncertainty
        m_count = len(cell_detections)
        mu = np.zeros(m_count, dtype=float)
        sigma = np.zeros(m_count, dtype=float)
        weights = np.zeros(m_count, dtype=float)

        for j in range(m_count):
            meas = cell_measurements[j]
            if (
                meas is not None
                and meas.method == MeasurementMethod.shadow_geometry
                and meas.height_m is not None
            ):
                mu[j] = meas.height_m
                sigma[j] = (
                    meas.height_uncertainty_m
                    if (
                        meas.height_uncertainty_m is not None
                        and meas.height_uncertainty_m > 0
                    )
                    else 0.0
                )
                if config.apply_recall_correction and recall is not None:
                    w, _, _ = _corrected_count(
                        meas.diameter_m, recall, recall_floor=config.recall_floor
                    )
                    weights[j] = w
                else:
                    weights[j] = 1.0
            else:
                mu[j] = -1.0
                sigma[j] = 0.0
                weights[j] = 0.0

        if np.any(sigma > 0):
            heights_reps = rng.normal(loc=mu, scale=sigma, size=(b_reps, m_count))
        else:
            heights_reps = np.broadcast_to(mu, (b_reps, m_count))

        is_haz = heights_reps >= config.hazard_height_threshold_m
        haz_weights = is_haz * weights

        resample_idx = rng.integers(0, m_count, size=(b_reps, m_count))
        resampled_w = np.take_along_axis(haz_weights, resample_idx, axis=1)
        k_boot = np.sum(resampled_w, axis=1)
        rho_boot = k_boot / cell_area_m2
        p_boot = 1.0 - np.exp(-rho_boot * footprint_area_m2)

        p_low = float(np.percentile(p_boot, alpha_low))
        p_high = float(np.percentile(p_boot, alpha_high))

    interval_low = round(max(0.0, min(p_low, p_hazard)), 4)
    interval_high = round(min(1.0, max(p_high, p_hazard)), 4)
    if interval_low > p_hazard:
        interval_low = p_hazard
    if interval_high < p_hazard:
        interval_high = p_hazard

    return interval_low, interval_high, cell_warnings, missing_inputs


# ================================================================
# 3. MAIN HAZARD GRID FUNCTION
# ================================================================

def build_hazard_grid(
    image: ImageInfo,
    detections: List[Detection],
    measurements: List[Measurement],
    config: AnalysisConfig,
    slope_by_cell: Optional[List[List[Optional[float]]]] = None,
    recall: Optional[RecallFile] = None,
    is_mock: bool = False,
) -> HazardGridFile:
    """
    Build the hazard assessment grid.

    Each cell contains:
    - Detected boulder count
    - Confirmed raw hazardous boulder count
    - Recall-adjusted hazardous count
    - Hazardous boulder density
    - Poisson footprint hazard probability
    - Independent slope-gate result
    - Safe / Caution / Unsafe candidate classification
    - Explanation and missing-input information

    Diameter-fallback heights are never used to determine
    whether a boulder is hazardous.
    """

    warnings: List[str] = []

    # ------------------------------------------------------------
    # STEP 1: Validate image dimensions and pixel scale
    # ------------------------------------------------------------

    if image.width <= 0 or image.height <= 0:
        raise ValueError(
            "Image width and height must be positive."
        )

    if image.pixel_scale_m is None:
        raise ValueError(
            "pixel_scale_m is required to calculate areas and densities."
        )

    if (
        not math.isfinite(image.pixel_scale_m)
        or image.pixel_scale_m <= 0
    ):
        raise ValueError(
            "Pixel scale must be a positive finite value."
        )

    rows = config.grid_rows
    cols = config.grid_cols

    if rows <= 0 or cols <= 0:
        raise ValueError(
            "Grid rows and columns must be positive."
        )

    if rows > image.height or cols > image.width:
        raise ValueError(
            "Grid dimensions cannot exceed image pixel dimensions."
        )

    cell_w_px = image.width / cols
    cell_h_px = image.height / rows

    if cell_w_px <= 0 or cell_h_px <= 0:
        raise ValueError(
            "Grid cell dimensions must be positive."
        )

    cell_area = (
        cell_w_px
        * cell_h_px
        * image.pixel_scale_m ** 2
    )

    if not math.isfinite(cell_area) or cell_area <= 0:
        raise ValueError(
            "Calculated grid cell area is invalid."
        )

    footprint_area = footprint_area_m2(
        config.lander_footprint_diameter_m
    )

    if cell_area < footprint_area:
        warnings.append(
            f"Grid cell area ({cell_area:.1f} m2) is smaller "
            f"than the lander footprint ({footprint_area:.1f} m2). "
            "Consider using a coarser grid."
        )
    elif cell_area > 10.0 * footprint_area:
        warnings.append(
            f"Grid cell area ({cell_area:.1f} m2) is more than 10x "
            f"the lander footprint area ({footprint_area:.1f} m2). "
            "Large cells dilute boulder density and may underestimate "
            "localized hazard probability; consider using a finer grid."
        )

    if slope_by_cell is not None:
        slope_rows = len(slope_by_cell)
        slope_cols = (
            len(slope_by_cell[0])
            if (slope_rows > 0 and isinstance(slope_by_cell[0], list))
            else 0
        )
        dims_match = (slope_rows == rows) and all(
            isinstance(r, list) and len(r) == cols for r in slope_by_cell
        )
        if not dims_match:
            warnings.append(
                f"Slope grid dimensions ({slope_rows}x{slope_cols}) differ from "
                f"hazard grid dimensions ({rows}x{cols}); mismatched cells have slope not assessed."
            )

    # ------------------------------------------------------------
    # STEP 2: Prepare measurement lookup
    # ------------------------------------------------------------

    measurement_by_id: Dict[int, Measurement] = {
        measurement.detection_id: measurement
        for measurement in measurements
    }

    minimum_confidence = config.detection_confidence_min

    # ------------------------------------------------------------
    # STEP 3: Assign detections to grid cells
    # ------------------------------------------------------------

    buckets: Dict[tuple, list] = {}
    clipped_edge_count = 0

    for detection in detections:

        if detection.confidence < minimum_confidence:
            continue

        if len(detection.bbox) != 4:
            warnings.append(
                f"Detection {detection.id} has an invalid "
                "bounding box and was excluded."
            )
            continue

        x1, y1, x2, y2 = detection.bbox

        if x2 <= x1 or y2 <= y1:
            warnings.append(
                f"Detection {detection.id} has an invalid "
                "bounding box (non-positive width or height) and was excluded."
            )
            continue

        # Exclude detections that lie completely outside the image bounds
        if x2 <= 0 or x1 >= image.width or y2 <= 0 or y1 >= image.height:
            warnings.append(
                f"Detection {detection.id} is entirely outside the image bounds "
                "and was excluded."
            )
            continue

        # Handle detections cut by the image edge by clipping them to image bounds
        is_cut = (x1 < 0 or y1 < 0 or x2 > image.width or y2 > image.height)
        if is_cut:
            cx1 = max(0.0, float(x1))
            cy1 = max(0.0, float(y1))
            cx2 = min(float(image.width), float(x2))
            cy2 = min(float(image.height), float(y2))
            if cx2 <= cx1 or cy2 <= cy1:
                warnings.append(
                    f"Detection {detection.id} has zero area after clipping and was excluded."
                )
                continue
            clipped_edge_count += 1
            center_x = (cx1 + cx2) / 2.0
            center_y = (cy1 + cy2) / 2.0
        else:
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0

        col = min(int(center_x / cell_w_px), cols - 1)
        row = min(int(center_y / cell_h_px), rows - 1)

        buckets.setdefault((row, col), []).append(detection)

    if clipped_edge_count > 0:
        warnings.append(
            f"{clipped_edge_count} boulder detection(s) were cut by the image edge "
            "and were clipped to image bounds; physical measurements may be truncated."
        )

    # ------------------------------------------------------------
    # STEP 4: Calculate each grid cell
    # ------------------------------------------------------------

    cells: List[HazardCell] = []

    uncorrected_bins = 0
    capped_bins = 0
    any_fallback = False
    low_count_cells = 0
    rng = np.random.default_rng(config.bootstrap_seed)

    for row in range(rows):

        for col in range(cols):

            cell_detections = buckets.get((row, col), [])

            cell_measurements = [
                measurement_by_id.get(detection.id)
                for detection in cell_detections
            ]

            # ----------------------------------------------------
            # 4A. Calculate detected boulder sizes
            # ----------------------------------------------------

            diameters = [
                measurement.diameter_m
                for measurement in cell_measurements
                if measurement is not None
                and measurement.diameter_m is not None
            ]

            largest_boulder = (
                max(diameters)
                if diameters
                else None
            )

            # Determine largest height and measurement method
            measurements_with_height = [
                m
                for m in cell_measurements
                if m is not None and m.height_m is not None
            ]

            if measurements_with_height:
                m_largest = max(
                    measurements_with_height, key=lambda m: m.height_m
                )
                largest_height = m_largest.height_m
                if m_largest.method == MeasurementMethod.shadow_geometry:
                    largest_height_method = "shadow_geometry"
                elif m_largest.method == MeasurementMethod.diameter_fallback:
                    largest_height_method = "diameter_fallback"
                else:
                    largest_height_method = "none"
            else:
                largest_height = None
                largest_height_method = "none"

            # ----------------------------------------------------
            # 4B. Count confirmed hazardous boulders
            # ----------------------------------------------------

            raw_hazardous = 0
            corrected_hazardous = 0.0

            unknown_height = 0
            fallback_in_cell = False
            cell_recall_corrected = False

            for measurement in cell_measurements:

                if measurement is None:
                    unknown_height += 1
                    continue

                # Diameter fallback is NOT a confirmed height.
                if (
                    measurement.method
                    == MeasurementMethod.diameter_fallback
                ):
                    fallback_in_cell = True
                    any_fallback = True
                    unknown_height += 1
                    continue

                # Unavailable measurement cannot establish hazard status.
                if (
                    measurement.method
                    == MeasurementMethod.unavailable
                ):
                    unknown_height += 1
                    continue

                # Only shadow geometry can establish hazardous status.
                if (
                    measurement.method
                    != MeasurementMethod.shadow_geometry
                ):
                    unknown_height += 1
                    continue

                if measurement.height_m is None:
                    unknown_height += 1
                    continue

                if measurement.is_hazardous is None:
                    unknown_height += 1
                    continue

                if not measurement.is_hazardous:
                    continue

                raw_hazardous += 1

                if config.apply_recall_correction and recall is not None:

                    contribution, was_corrected, was_capped = _corrected_count(
                        measurement.diameter_m,
                        recall,
                        recall_floor=config.recall_floor,
                    )

                    corrected_hazardous += contribution

                    if was_corrected:
                        cell_recall_corrected = True
                    else:
                        uncorrected_bins += 1

                    if was_capped:
                        capped_bins += 1

                else:
                    corrected_hazardous += 1.0

            # ----------------------------------------------------
            # 4C. Calculate density and probability
            # ----------------------------------------------------

            rho_h = corrected_hazardous / cell_area

            probability = poisson_hazard_probability(
                rho_h,
                footprint_area,
            )

            # ----------------------------------------------------
            # 4D. Evaluate slope independently
            # ----------------------------------------------------

            slope = None
            slope_gate = "not_assessed"

            if (
                slope_by_cell is not None
                and row < len(slope_by_cell)
                and col < len(slope_by_cell[row])
            ):

                slope_value = slope_by_cell[row][col]

                if slope_value is not None:

                    try:
                        slope_value = float(slope_value)
                    except (TypeError, ValueError):
                        slope_value = float("nan")

                    if (
                        math.isfinite(slope_value)
                        and 0 <= slope_value <= 90
                    ):

                        slope = slope_value

                        slope_gate = (
                            "pass"
                            if slope <= config.slope_gate_deg
                            else "fail"
                        )

                    else:
                        warnings.append(
                            f"Invalid slope value at cell "
                            f"({row}, {col}); slope was not assessed."
                        )

            # ----------------------------------------------------
            # 4E. Identify missing and uncertain inputs
            # ----------------------------------------------------

            reasons: List[str] = []
            missing: List[str] = []

            if unknown_height > 0:
                missing.append(
                    f"height unknown for {unknown_height} boulder(s)"
                )

            if fallback_in_cell:
                missing.append(
                    "some heights are provisional diameter-based "
                    "assumptions and were excluded from hazard counts"
                )

            if slope_gate == "not_assessed":
                missing.append(
                    "slope not assessed (no valid DEM slope)"
                )

            # ----------------------------------------------------
            # 4F. Bootstrap uncertainty interval
            # ----------------------------------------------------

            interval_low, interval_high, boot_warnings, boot_missing = (
                compute_bootstrap_interval(
                    cell_detections=cell_detections,
                    cell_measurements=cell_measurements,
                    cell_area_m2=cell_area,
                    footprint_area_m2=footprint_area,
                    corrected_hazardous=corrected_hazardous,
                    p_hazard=probability,
                    config=config,
                    recall=recall,
                    rng=rng,
                )
            )
            if boot_warnings:
                low_count_cells += 1
            missing.extend(boot_missing)
            cell_warnings = list(boot_warnings)

            # ----------------------------------------------------
            # 4G. Classification rules (pure classification service)
            # ----------------------------------------------------

            classification, reasons = classify_cell(
                p_hazard=probability,
                slope_gate=slope_gate,
                unknown_height_count=unknown_height,
                fallback_in_cell=fallback_in_cell,
                config=config,
                slope_deg=slope,
                interval_high=interval_high,
            )

            # ----------------------------------------------------
            # 4H. Generate explanation
            # ----------------------------------------------------

            explanation = explain_cell(
                classification=classification,
                probability=probability,
                hazardous_count=raw_hazardous,
                corrected_count=corrected_hazardous,
                total_count=len(cell_detections),
                slope=slope,
                slope_gate=slope_gate,
                config=config,
                missing=missing,
                reasons=reasons,
            )

            # ----------------------------------------------------
            # 4J. Store cell result
            # ----------------------------------------------------

            probability_value = round(probability, 4)
            corrected_value = round(corrected_hazardous, 4)

            cells.append(
                HazardCell(
                    row=row,
                    col=col,

                    score=probability_value,
                    p_hazard=probability_value,

                    **{"class": classification},

                    raw_boulder_count=len(cell_detections),

                    corrected_boulder_count=corrected_value,

                    hazardous_boulder_count=raw_hazardous,

                    largest_boulder_m=largest_boulder,

                    rho_h_per_m2=rho_h,
                    density=round(rho_h * 100, 3),
                    cell_area_m2=round(cell_area, 2),

                    slope_deg=slope,
                    slope_gate=slope_gate,

                    recall_corrected=(
                        config.apply_recall_correction
                        and cell_recall_corrected
                    ),

                    explanation=explanation,
                    reasons=reasons,
                    missing_inputs=missing,

                    # Frontend-compatible fields.
                    probability=probability_value,
                    interval_low=interval_low,
                    interval_high=interval_high,
                    label=CLASS_LABELS[classification],
                    raw_count=len(cell_detections),
                    corrected_count=corrected_value,
                    largest_height_m=largest_height,
                    largest_height_method=largest_height_method,
                    warnings=cell_warnings,
                )
            )

    # ------------------------------------------------------------
    # STEP 5: Add grid-level warnings
    # ------------------------------------------------------------

    if config.apply_recall_correction and recall is None:
        warnings.append(
            "Recall correction requested but no recall.json "
            "was supplied; counts are uncorrected."
        )

    if capped_bins > 0:
        warnings.append(
            f"Recall floor ({config.recall_floor}) applied to {capped_bins} boulder(s) "
            f"to prevent weight explosion (weight capped at {1.0 / config.recall_floor:.1f})."
        )

    if low_count_cells > 0:
        warnings.append(
            f"Parametric Poisson resampling was used for uncertainty intervals in "
            f"{low_count_cells} cell(s) with < 5 detections."
        )

    if uncorrected_bins > 0:
        warnings.append(
            f"{uncorrected_bins} hazardous boulder(s) had no "
            "matching valid recall bin and were left uncorrected."
        )

    if slope_by_cell is None:
        warnings.append(
            "slope gate not assessed: no DEM/slope supplied. "
            "No cell can be labelled a Safe candidate."
        )

    if any_fallback:
        warnings.append(
            "Some heights use the diameter-based fallback "
            "assumption. These provisional values were excluded "
            "from confirmed hazardous-boulder counts and must not "
            "be interpreted as physical height measurements."
        )

    if image.sun_elevation_deg is None:
        warnings.append(
            "Sun elevation unavailable: shadow-based heights "
            "could not be calculated."
        )

    # ------------------------------------------------------------
    # STEP 6: Return hazard grid
    # ------------------------------------------------------------

    return HazardGridFile(
        image=image,
        rows=rows,
        cols=cols,
        lander_footprint_diameter_m=(
            config.lander_footprint_diameter_m
        ),
        lander_footprint_area_m2=round(
            footprint_area,
            3,
        ),
        is_mock=is_mock,
        hazard_cells=cells,
        warnings=warnings,
    )


# ================================================================
# 5. HUMAN-READABLE CELL EXPLANATION
# ================================================================

_explain = explain_cell
