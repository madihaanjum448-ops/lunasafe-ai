
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
) -> Tuple[float, bool]:
    """
    Return the recall-adjusted contribution of one hazardous boulder.

    If no valid recall bin exists, retain the raw contribution of 1.
    """

    recall_value = _recall_for(diameter_m, recall)

    if recall_value is None:
        return 1.0, False

    return 1.0 / recall_value, True


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

        if (
            x2 <= x1
            or y2 <= y1
            or x1 < 0
            or y1 < 0
            or x2 > image.width
            or y2 > image.height
        ):
            warnings.append(
                f"Detection {detection.id} has an invalid or "
                "out-of-image bounding box and was excluded."
            )
            continue

        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0

        col = min(int(center_x / cell_w_px), cols - 1)
        row = min(int(center_y / cell_h_px), rows - 1)

        buckets.setdefault((row, col), []).append(detection)

    # ------------------------------------------------------------
    # STEP 4: Calculate each grid cell
    # ------------------------------------------------------------

    cells: List[HazardCell] = []

    uncorrected_bins = 0
    any_fallback = False

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

            # Only genuine shadow-geometry heights are eligible.
            measured_heights = [
                measurement.height_m
                for measurement in cell_measurements
                if measurement is not None
                and measurement.method
                == MeasurementMethod.shadow_geometry
                and measurement.height_m is not None
            ]

            largest_height = (
                max(measured_heights)
                if measured_heights
                else None
            )

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

                if config.apply_recall_correction:

                    contribution, was_corrected = _corrected_count(
                        measurement.diameter_m,
                        recall,
                    )

                    corrected_hazardous += contribution

                    if was_corrected:
                        cell_recall_corrected = True
                    else:
                        uncorrected_bins += 1

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
            # 4F. Classification rules
            # ----------------------------------------------------

            if slope_gate == "fail":

                classification = HazardClass.unsafe
                reasons.append("slope_gate_failed")

            elif probability >= config.unsafe_p_hazard:

                classification = HazardClass.unsafe
                reasons.append(
                    "p_hazard_at_or_above_unsafe_threshold"
                )

            elif probability >= config.caution_p_hazard:

                classification = HazardClass.caution
                reasons.append(
                    "p_hazard_at_or_above_caution_threshold"
                )

            else:

                classification = HazardClass.safe
                reasons.append(
                    "p_hazard_below_caution_threshold"
                )

            # ----------------------------------------------------
            # 4G. Prevent unsupported Safe classifications
            # ----------------------------------------------------

            if (
                classification == HazardClass.safe
                and slope_gate == "not_assessed"
            ):
                classification = HazardClass.caution
                reasons.append(
                    "downgraded_slope_not_assessed"
                )

            if (
                classification == HazardClass.safe
                and unknown_height > 0
            ):
                classification = HazardClass.caution
                reasons.append(
                    "downgraded_height_unknown"
                )

            if (
                classification == HazardClass.safe
                and fallback_in_cell
            ):
                classification = HazardClass.caution
                reasons.append(
                    "downgraded_fallback_height"
                )

            # ----------------------------------------------------
            # 4H. Generate explanation
            # ----------------------------------------------------

            explanation = _explain(
                classification=classification,
                probability=probability,
                hazardous_count=raw_hazardous,
                corrected_count=corrected_hazardous,
                total_count=len(cell_detections),
                slope=slope,
                slope_gate=slope_gate,
                config=config,
                missing=missing,
            )

            # ----------------------------------------------------
            # 4I. Store cell result
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
                    interval_low=None,
                    interval_high=None,
                    label=CLASS_LABELS[classification],
                    raw_count=len(cell_detections),
                    corrected_count=corrected_value,
                    largest_height_m=largest_height,
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

def _explain(
    classification,
    probability,
    hazardous_count,
    corrected_count,
    total_count,
    slope,
    slope_gate,
    config,
    missing,
) -> str:
    """Generate a human-readable explanation for a grid cell."""

    label = CLASS_LABELS[classification]

    parts = [
        (
            f"{label}: P(hazard) = {probability:.1%} "
            f"for a {config.lander_footprint_diameter_m:g} m "
            f"footprint. There are {hazardous_count} confirmed "
            f"hazardous boulders among {total_count} detected boulders."
        )
    ]

    if config.apply_recall_correction:
        parts.append(
            f"The recall-adjusted hazardous count is "
            f"{corrected_count:.2f}."
        )

    if slope_gate == "fail":
        parts.append(
            f"Slope {slope:.1f} degrees exceeds the "
            f"{config.slope_gate_deg:g} degree slope gate."
        )

    elif slope_gate == "pass":
        parts.append(
            f"Slope {slope:.1f} degrees is within the "
            f"{config.slope_gate_deg:g} degree slope gate."
        )

    else:
        parts.append("Slope was not assessed.")

    if missing:
        parts.append(
            "Missing/uncertain inputs: "
            + "; ".join(missing)
            + "."
        )

    return " ".join(parts)
