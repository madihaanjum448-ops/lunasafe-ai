"""
LunaSafe AI - Grid-cell hazard classification service (FR-08).

This module implements the pure classification decision rules and explanation
generator for analysis grid cells.

Precedence Rules:
-----------------
1. slope_gate == "fail" -> Unsafe candidate ("slope_gate_failed")
   A terrain slope exceeding the slope gate is an absolute hard-stop.
   The cell is immediately classified as Unsafe, regardless of boulder hazard
   probability (even if p_hazard == 0).

2. p_hazard >= unsafe_p_hazard -> Unsafe candidate ("p_hazard_at_or_above_unsafe_threshold")
   Hazard probability meets or exceeds the unsafe threshold (default 30%, PLACEHOLDER).

3. p_hazard >= caution_p_hazard -> Caution candidate ("p_hazard_at_or_above_caution_threshold")
   Hazard probability meets or exceeds the caution threshold (default 10%, PLACEHOLDER).

4. Otherwise -> Safe candidate ("p_hazard_below_caution_threshold")
   Hazard probability is below the caution threshold and slope has not failed.

5. Mandatory Safety Downgrades on Safe Candidates:
   A provisionally Safe candidate is downgraded to Caution if any of the following apply:
   - slope_gate == "not_assessed" ("downgraded_slope_not_assessed"):
     A cell lacking elevation / slope assessment can NEVER be certified as Safe.
   - unknown_height_count > 0 ("downgraded_height_unknown"):
     Detections exist whose heights could not be measured or estimated.
   - fallback_in_cell is True ("downgraded_fallback_height"):
     Provisional diameter-based fallback heights were used; unverified assumptions
     cannot certify a Safe landing zone.
   - slope_margin_deg > 0.0 ("slope_within_margin_of_gate"):
     Passing slope is within the configured safety margin of the slope gate
     (slope_deg > slope_gate_deg - slope_margin_deg).
   - use_interval_upper_bound is True ("interval_reaches_unsafe_threshold"):
     The 90% bootstrap uncertainty upper bound reaches the unsafe threshold
     (interval_high >= unsafe_p_hazard).

Boundary Rules:
---------------
- Probabilities equal to thresholds fall in the higher category:
  p == unsafe_p_hazard -> Unsafe; p == caution_p_hazard -> Caution.
- Slopes equal to the slope gate pass:
  slope <= slope_gate_deg -> pass.
"""

import math
from typing import List, Optional, Tuple

from app.schemas.contracts import CLASS_LABELS, AnalysisConfig, HazardClass


def classify_cell(
    p_hazard: float,
    slope_gate: str,
    unknown_height_count: int,
    fallback_in_cell: bool,
    config: AnalysisConfig,
    slope_deg: Optional[float] = None,
    interval_high: Optional[float] = None,
) -> Tuple[HazardClass, List[str]]:
    """
    Classify a single grid cell according to hazard probability and slope gate.

    Args:
        p_hazard:
            Poisson footprint collision probability in [0, 1].
        slope_gate:
            Slope assessment result: "pass", "fail", or "not_assessed".
        unknown_height_count:
            Number of detections in cell with completely unmeasured heights.
        fallback_in_cell:
            Whether any detection in cell relies on diameter-fallback height.
        config:
            AnalysisConfig instance containing threshold parameters.
        slope_deg:
            Optional evaluated slope in degrees for margin checks.
        interval_high:
            Optional upper bound of the bootstrap confidence interval.

    Returns:
        (classification, reasons)
        - classification: HazardClass.safe, HazardClass.caution, or HazardClass.unsafe.
        - reasons: List of machine-readable reason strings documenting the decision.
    """
    reasons: List[str] = []

    # 1. Slope gate hard-stop: slope failure always forces Unsafe
    if slope_gate == "fail":
        reasons.append("slope_gate_failed")
        return HazardClass.unsafe, reasons

    # 2. Probability exceeds or meets unsafe threshold
    if p_hazard >= config.unsafe_p_hazard:
        reasons.append("p_hazard_at_or_above_unsafe_threshold")
        return HazardClass.unsafe, reasons

    # 3. Probability exceeds or meets caution threshold
    if p_hazard >= config.caution_p_hazard:
        reasons.append("p_hazard_at_or_above_caution_threshold")
        return HazardClass.caution, reasons

    # 4. Provisionally Safe candidate
    classification = HazardClass.safe
    reasons.append("p_hazard_below_caution_threshold")

    # 5. Apply mandatory safety downgrades on provisional Safe candidates
    if slope_gate == "not_assessed":
        classification = HazardClass.caution
        reasons.append("downgraded_slope_not_assessed")

    if unknown_height_count > 0:
        classification = HazardClass.caution
        reasons.append("downgraded_height_unknown")

    if fallback_in_cell:
        classification = HazardClass.caution
        reasons.append("downgraded_fallback_height")

    # Optional safety margin below slope gate
    slope_margin = getattr(config, "slope_margin_deg", 0.0)
    if (
        slope_margin > 0.0
        and slope_gate == "pass"
        and slope_deg is not None
        and math.isfinite(slope_deg)
    ):
        if slope_deg > (config.slope_gate_deg - slope_margin):
            classification = HazardClass.caution
            reasons.append("slope_within_margin_of_gate")

    # Optional conservative upper-bound check
    use_interval = getattr(config, "use_interval_upper_bound", False)
    if (
        use_interval
        and interval_high is not None
        and math.isfinite(interval_high)
    ):
        if interval_high >= config.unsafe_p_hazard:
            classification = HazardClass.caution
            reasons.append("interval_reaches_unsafe_threshold")

    return classification, reasons


def explain_cell(
    classification: HazardClass,
    probability: float,
    hazardous_count: float,
    corrected_count: float,
    total_count: int,
    slope: Optional[float],
    slope_gate: str,
    config: AnalysisConfig,
    missing: List[str],
    reasons: Optional[List[str]] = None,
) -> str:
    """
    Generate a human-readable explanation for a grid cell stating which rule decided the class.
    """
    label = CLASS_LABELS[classification]
    reasons_list = reasons or []

    parts: List[str] = [
        (
            f"{label}: P(hazard) = {probability:.1%} "
            f"for a {config.lander_footprint_diameter_m:g} m footprint. "
            f"There are {hazardous_count:g} confirmed hazardous boulders "
            f"among {total_count} detected boulders."
        )
    ]

    if config.apply_recall_correction:
        parts.append(
            f"The recall-adjusted hazardous count is {corrected_count:.2f}."
        )

    if slope_gate == "fail":
        parts.append(
            f"Slope {slope:.1f} degrees exceeds the {config.slope_gate_deg:g} degree slope gate."
        )
    elif slope_gate == "pass":
        parts.append(
            f"Slope {slope:.1f} degrees is within the {config.slope_gate_deg:g} degree slope gate."
        )
    else:
        parts.append("Slope was not assessed.")

    # State the exact decision rule
    if "slope_gate_failed" in reasons_list:
        parts.append("Classified as Unsafe candidate by slope gate hard-stop.")
    elif "p_hazard_at_or_above_unsafe_threshold" in reasons_list:
        parts.append(
            f"Classified as Unsafe candidate because hazard probability ({probability:.1%}) "
            f"meets or exceeds the {config.unsafe_p_hazard:.0%} unsafe threshold."
        )
    elif "p_hazard_at_or_above_caution_threshold" in reasons_list:
        parts.append(
            f"Classified as Caution candidate because hazard probability ({probability:.1%}) "
            f"meets or exceeds the {config.caution_p_hazard:.0%} caution threshold."
        )
    else:
        downgrades = []
        if "downgraded_slope_not_assessed" in reasons_list:
            downgrades.append("slope was not assessed")
        if "downgraded_height_unknown" in reasons_list:
            downgrades.append("boulder heights are unknown")
        if "downgraded_fallback_height" in reasons_list:
            downgrades.append("boulder heights use provisional fallback assumptions")
        if "slope_within_margin_of_gate" in reasons_list:
            margin = getattr(config, "slope_margin_deg", 0.0)
            downgrades.append(
                f"slope ({slope:.1f}°) is within {margin:g}° margin of the slope gate"
            )
        if "interval_reaches_unsafe_threshold" in reasons_list:
            downgrades.append(
                f"uncertainty interval upper bound reaches the {config.unsafe_p_hazard:.0%} unsafe threshold"
            )

        if downgrades:
            parts.append(
                f"Downgraded from Safe to Caution candidate because {'; '.join(downgrades)}."
            )
        else:
            parts.append(
                f"Classified as Safe candidate because hazard probability ({probability:.1%}) "
                f"is below the {config.caution_p_hazard:.0%} caution threshold and slope passes."
            )

    if missing:
        parts.append("Missing/uncertain inputs: " + "; ".join(missing) + ".")

    return " ".join(parts)

