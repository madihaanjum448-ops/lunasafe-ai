
"""
Boulder measurement service for LunaSafe AI.

Diameter:
    diameter = longer bounding-box side in pixels * pixel scale

Shadow-based height:
    height = shadow length in metres * tan(Sun elevation)

Assumptions and limitations:
- Shadow geometry assumes locally flat ground.
- Pixel uncertainty is propagated; Sun-angle and pixel-scale
  uncertainties are not included.
- If shadow geometry is unavailable, a diameter-based height
  fallback may be reported, but it is LOW confidence.
- A fallback height is NOT treated as a confirmed hazard measurement.
"""

import math
from typing import Dict, List, Optional

from app.schemas.contracts import (
    AnalysisConfig,
    Confidence,
    Detection,
    ImageInfo,
    Measurement,
    MeasurementMethod,
    MeasurementsFile,
    ShadowQuality,
)


# ASSUMPTION — not a verified scientific value.
# Confirm or replace using Member 4's research.
FALLBACK_HEIGHT_TO_DIAMETER_RATIO = 0.5


def diameter_from_bbox(
    bbox: List[float],
    pixel_scale_m: float,
) -> tuple[float, float]:
    """
    Calculate approximate boulder diameter from its bounding box.

    Returns:
        diameter_m: estimated diameter in metres
        uncertainty_m: estimated +/- uncertainty in metres

    Assumes an uncertainty of +/- 1 pixel.
    """
    if len(bbox) != 4:
        raise ValueError("Bounding box must contain exactly four coordinates.")

    x1, y1, x2, y2 = bbox

    if x2 <= x1 or y2 <= y1:
        raise ValueError("Bounding box must have positive width and height.")

    if not math.isfinite(pixel_scale_m) or pixel_scale_m <= 0:
        raise ValueError("Pixel scale must be a positive finite value.")

    side_px = max(x2 - x1, y2 - y1)

    diameter_m = side_px * pixel_scale_m
    uncertainty_m = pixel_scale_m

    return diameter_m, uncertainty_m


def height_from_shadow(
    shadow_length_px: float,
    pixel_scale_m: float,
    sun_elevation_deg: float,
    pixel_uncertainty_px: float = 1.0,
    sun_elevation_uncertainty_deg: float = 0.0,
) -> tuple[float, float]:
    """
    Estimate boulder height using shadow geometry and propagated uncertainty.

    Formula:
        height = shadow_length_m * tan(Sun elevation)
        sigma_h^2 = (tan(e) * sigma_L)^2 + (L * sec^2(e) * sigma_e_rad)^2

    Returns:
        height_m: estimated height in metres
        uncertainty_m: propagated uncertainty from shadow pixel and sun elevation error

    Assumes flat ground; pixel scale uncertainty is not included.
    """
    values = (
        shadow_length_px,
        pixel_scale_m,
        sun_elevation_deg,
        pixel_uncertainty_px,
        sun_elevation_uncertainty_deg,
    )

    if not all(math.isfinite(value) for value in values):
        raise ValueError("Shadow measurement inputs must be finite numbers.")

    if shadow_length_px <= 0:
        raise ValueError("Shadow length must be positive.")

    if pixel_scale_m <= 0:
        raise ValueError("Pixel scale must be positive.")

    if not 0 < sun_elevation_deg < 90:
        raise ValueError("Sun elevation must be between 0 and 90 degrees.")

    if pixel_uncertainty_px < 0:
        raise ValueError("Pixel uncertainty cannot be negative.")

    if sun_elevation_uncertainty_deg < 0:
        raise ValueError("Sun elevation uncertainty cannot be negative.")

    shadow_length_m = shadow_length_px * pixel_scale_m
    sun_angle_rad = math.radians(sun_elevation_deg)

    height_m = shadow_length_m * math.tan(sun_angle_rad)

    sigma_l = pixel_uncertainty_px * pixel_scale_m
    term_l = math.tan(sun_angle_rad) * sigma_l

    if sun_elevation_uncertainty_deg > 0:
        sigma_e_rad = math.radians(sun_elevation_uncertainty_deg)
        sec_e = 1.0 / math.cos(sun_angle_rad)
        term_e = shadow_length_m * (sec_e ** 2) * sigma_e_rad
        uncertainty_m = math.sqrt(term_l ** 2 + term_e ** 2)
    else:
        uncertainty_m = term_l

    return height_m, uncertainty_m


def measure_detections(
    image: ImageInfo,
    detections: List[Detection],
    config: AnalysisConfig,
    shadow_lengths_px: Optional[Dict[int, float]] = None,
    shadow_quality: Optional[Dict[int, str]] = None,
    reference_heights_m: Optional[Dict[int, float]] = None,
) -> MeasurementsFile:
    """
    Calculate diameter and height measurements for detected boulders.

    Missing pixel scale:
        No diameter or height can be calculated.

    Missing shadow length or Sun elevation:
        A low-confidence diameter-based height fallback is reported.

    Important:
        Fallback measurements are not marked as confirmed hazardous
        or non-hazardous. The hazard engine must preserve this distinction.
    """

    shadow_lengths_px = shadow_lengths_px or {}

    file_warnings: List[str] = []
    measurements: List[Measurement] = []

    scale = image.pixel_scale_m
    sun = image.sun_elevation_deg

    # ---------------------------------------------------------
    # Validate image metadata
    # ---------------------------------------------------------

    if scale is None:
        file_warnings.append(
            "Pixel scale unavailable: diameters and heights cannot "
            "be converted into metres."
        )
    elif not math.isfinite(scale) or scale <= 0:
        file_warnings.append(
            "Invalid pixel scale: expected a positive finite value."
        )
        scale = None

    if sun is None:
        file_warnings.append(
            "Sun elevation unavailable: shadow-based heights "
            "cannot be calculated."
        )
    elif not math.isfinite(sun) or not 0 < sun < 90:
        file_warnings.append(
            "Invalid Sun elevation: expected an angle between "
            "0 and 90 degrees."
        )
        sun = None

    if sun is not None:
        file_warnings.append(
            "Shadow-based height measurement assumes locally flat ground."
        )
        if config.sun_elevation_uncertainty_deg > 0:
            file_warnings.append(
                "Reported uncertainty propagates pixel error and "
                "Sun-elevation uncertainty, but excludes pixel-scale uncertainty."
            )
        else:
            file_warnings.append(
                "Reported uncertainty excludes uncertainty in Sun elevation "
                "and pixel scale."
            )

    sun_is_reliable = (
        sun is not None
        and config.shadow_height_min_sun_elevation_deg
        <= sun
        <= config.shadow_height_max_sun_elevation_deg
    )

    if sun is not None and not sun_is_reliable:
        file_warnings.append(
            f"Sun elevation {sun} degrees is outside the configured "
            f"reliable range "
            f"[{config.shadow_height_min_sun_elevation_deg}, "
            f"{config.shadow_height_max_sun_elevation_deg}]. "
            "Shadow-based heights will have LOW confidence."
        )

    # ---------------------------------------------------------
    # Process each detected boulder
    # ---------------------------------------------------------

    for detection in detections:

        warnings: List[str] = []

        # Determine shadow quality
        quality_str: Optional[str] = None
        quality_enum: Optional[ShadowQuality] = None
        if shadow_quality:
            raw_q = shadow_quality.get(detection.id)
            if raw_q is not None:
                q_clean = str(raw_q).strip().lower()
                if q_clean in ("good", "fair", "poor"):
                    quality_str = q_clean
                    quality_enum = ShadowQuality(q_clean)
                else:
                    warnings.append(
                        f"Unrecognized shadow_quality '{raw_q}' for detection {detection.id}; ignored."
                    )

        # Without a valid pixel scale, no physical measurement is possible.
        if scale is None:
            measurements.append(
                Measurement(
                    detection_id=detection.id,
                    method=MeasurementMethod.unavailable,
                    confidence=Confidence.none,
                    shadow_quality=quality_enum,
                    warnings=[
                        "No valid pixel scale; cannot convert pixels "
                        "into metres."
                    ],
                )
            )
            continue

        # -----------------------------------------------------
        # Calculate diameter
        # -----------------------------------------------------

        try:
            diameter_m, diameter_uncertainty_m = diameter_from_bbox(
                detection.bbox,
                scale,
            )
        except ValueError as exc:
            measurements.append(
                Measurement(
                    detection_id=detection.id,
                    method=MeasurementMethod.unavailable,
                    confidence=Confidence.none,
                    shadow_quality=quality_enum,
                    warnings=[f"Diameter could not be calculated: {exc}"],
                )
            )
            continue

        # -----------------------------------------------------
        # Retrieve shadow measurement
        # -----------------------------------------------------

        shadow_px = shadow_lengths_px.get(detection.id)

        valid_shadow = (
            shadow_px is not None
            and isinstance(shadow_px, (int, float))
            and math.isfinite(shadow_px)
            and shadow_px > 0
        )

        # -----------------------------------------------------
        # Case 1: Shadow geometry is available
        # -----------------------------------------------------

        if valid_shadow and sun is not None:

            height_m, height_uncertainty_m = height_from_shadow(
                shadow_length_px=float(shadow_px),
                pixel_scale_m=scale,
                sun_elevation_deg=sun,
                pixel_uncertainty_px=config.pixel_uncertainty_px,
                sun_elevation_uncertainty_deg=config.sun_elevation_uncertainty_deg,
            )

            method = MeasurementMethod.shadow_geometry

            if sun_is_reliable:
                confidence = (
                    Confidence.high
                    if detection.confidence >= 0.8
                    else Confidence.medium
                )
            else:
                confidence = Confidence.low
                warnings.append(
                    "Sun elevation is outside the configured reliable "
                    "range; shadow-based height has LOW confidence."
                )

            # Shadow quality adjustments:
            # "poor" shadow quality: height is not used to establish hazard status
            # (treat as unknown height, reason recorded, confidence low).
            # "fair": confidence capped at medium.
            if quality_str == "poor":
                confidence = Confidence.low
                is_hazardous = None
                warnings.append(
                    "Shadow quality marked 'poor': height is unconfirmed and excluded from establishing hazard status."
                )
            elif quality_str == "fair":
                if confidence == Confidence.high:
                    confidence = Confidence.medium
                is_hazardous = (
                    height_m >= config.hazard_height_threshold_m
                )
            else:
                is_hazardous = (
                    height_m >= config.hazard_height_threshold_m
                )

        # -----------------------------------------------------
        # Case 2: Shadow geometry is unavailable
        # -----------------------------------------------------

        else:

            missing_inputs: List[str] = []

            if sun is None:
                missing_inputs.append("valid Sun elevation")

            if not valid_shadow:
                missing_inputs.append("valid shadow length")

            height_m = (
                diameter_m * FALLBACK_HEIGHT_TO_DIAMETER_RATIO
            )

            height_uncertainty_m = None

            method = MeasurementMethod.diameter_fallback
            confidence = Confidence.low

            warnings.append(
                f"Height is an ASSUMPTION using diameter x "
                f"{FALLBACK_HEIGHT_TO_DIAMETER_RATIO}. "
                f"Missing: {', '.join(missing_inputs)}."
            )

            warnings.append(
                "This fallback height is not a confirmed physical "
                "measurement and must not independently determine "
                "hazardous-boulder classification."
            )

            # Do not turn an assumed height into a confirmed hazard flag.
            is_hazardous = None

        # -----------------------------------------------------
        # Store result
        # -----------------------------------------------------

        measurements.append(
            Measurement(
                detection_id=detection.id,
                diameter_m=round(diameter_m, 3),
                diameter_uncertainty_m=round(
                    diameter_uncertainty_m, 3
                ),
                height_m=round(height_m, 3),
                height_uncertainty_m=(
                    round(height_uncertainty_m, 3)
                    if height_uncertainty_m is not None
                    else None
                ),
                shadow_length_px=(
                    float(shadow_px) if valid_shadow else None
                ),
                method=method,
                confidence=confidence,
                shadow_quality=quality_enum,
                is_hazardous=is_hazardous,
                warnings=warnings,
            )
        )

    # ---------------------------------------------------------
    # Validation against reference heights (if provided)
    # ---------------------------------------------------------

    height_validated = False
    reference_count: Optional[int] = None
    height_mae_m: Optional[float] = None
    height_bias_m: Optional[float] = None

    if reference_heights_m:
        meas_map = {m.detection_id: m for m in measurements}
        diffs: List[float] = []
        for d_id, ref_h in reference_heights_m.items():
            try:
                k_int = int(d_id)
            except (ValueError, TypeError):
                continue
            m = meas_map.get(k_int)
            if m is not None and m.height_m is not None:
                diffs.append(m.height_m - float(ref_h))

        if diffs:
            height_validated = True
            reference_count = len(diffs)
            height_mae_m = round(sum(abs(d) for d in diffs) / len(diffs), 4)
            height_bias_m = round(sum(diffs) / len(diffs), 4)
        else:
            file_warnings.append(
                "Heights are unvalidated: reference heights were provided but matched no measured detections."
            )
    else:
        file_warnings.append(
            "Heights are unvalidated: no reference height set."
        )

    # ---------------------------------------------------------
    # Return complete measurement response
    # ---------------------------------------------------------

    return MeasurementsFile(
        image=image,
        hazard_height_threshold_m=config.hazard_height_threshold_m,
        measurements=measurements,
        warnings=file_warnings,
        height_validated=height_validated,
        reference_count=reference_count,
        height_mae_m=height_mae_m,
        height_bias_m=height_bias_m,
    )
