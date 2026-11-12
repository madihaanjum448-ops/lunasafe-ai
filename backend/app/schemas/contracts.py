
"""Shared request and response contracts for LunaSafe AI."""

import math
from enum import Enum
from typing import List, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


# ---------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------

class HazardClass(str, Enum):
    safe = "safe"
    caution = "caution"
    unsafe = "unsafe"


CLASS_LABELS = {
    HazardClass.safe: "Safe candidate",
    HazardClass.caution: "Caution",
    HazardClass.unsafe: "Unsafe candidate",
}


class MeasurementMethod(str, Enum):
    shadow_geometry = "shadow_geometry"
    shadow = "shadow_geometry"
    diameter_fallback = "diameter_fallback"
    unavailable = "unavailable"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    none = "none"


class ShadowQuality(str, Enum):
    good = "good"
    fair = "fair"
    poor = "poor"


# ---------------------------------------------------------------------
# IMAGE INFORMATION
# ---------------------------------------------------------------------

class ImageInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = "image"
    width: int = Field(gt=0)
    height: int = Field(gt=0)

    pixel_scale_m: Optional[float] = Field(default=None, gt=0)
    sun_elevation_deg: Optional[float] = Field(
        default=None, ge=0, le=90
    )
    incidence_angle_deg: Optional[float] = Field(
        default=None, ge=0, le=180
    )

    projection: Optional[str] = None
    crs: Optional[str] = None
    geotransform: Optional[List[float]] = None
    metadata_source: str = "unknown"


# ---------------------------------------------------------------------
# BOULDER DETECTIONS
# ---------------------------------------------------------------------

class Detection(BaseModel):
    id: int
    bbox: List[float] = Field(min_length=4, max_length=4)
    confidence: float = Field(ge=0, le=1)

    size_m: Optional[float] = Field(default=None, gt=0)
    class_name: str = "boulder"


class DetectionsFile(BaseModel):
    image: ImageInfo
    detections: List[Detection] = Field(default_factory=list)


# ---------------------------------------------------------------------
# RECALL CORRECTION
# ---------------------------------------------------------------------

class RecallBin(BaseModel):
    bin_min_m: float = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices(
            "bin_min_m", "min_diameter_m"
        ),
    )

    bin_max_m: Optional[float] = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices(
            "bin_max_m", "max_diameter_m"
        ),
    )

    recall: float = Field(ge=0, le=1)
    precision: Optional[float] = Field(default=None, ge=0, le=1)
    n_gt: Optional[int] = Field(default=None, ge=0)


class RecallFile(BaseModel):
    bins: List[RecallBin] = Field(default_factory=list)


# ---------------------------------------------------------------------
# MEASUREMENTS
# ---------------------------------------------------------------------

class Measurement(BaseModel):
    detection_id: int

    diameter_m: Optional[float] = Field(default=None, ge=0)
    diameter_uncertainty_m: Optional[float] = Field(
        default=None, ge=0
    )

    height_m: Optional[float] = Field(default=None, ge=0)
    height_uncertainty_m: Optional[float] = Field(
        default=None, ge=0
    )

    shadow_length_px: Optional[float] = Field(
        default=None, ge=0
    )

    method: MeasurementMethod = MeasurementMethod.unavailable
    confidence: Confidence = Confidence.none

    shadow_quality: Optional[ShadowQuality] = None
    is_hazardous: Optional[bool] = None
    warnings: List[str] = Field(default_factory=list)


class MeasurementsFile(BaseModel):
    image: ImageInfo

    hazard_height_threshold_m: float = Field(gt=0)

    measurements: List[Measurement] = Field(
        default_factory=list
    )

    warnings: List[str] = Field(default_factory=list)

    height_validated: bool = False
    reference_count: Optional[int] = None
    height_mae_m: Optional[float] = None
    height_bias_m: Optional[float] = None


# ---------------------------------------------------------------------
# HAZARD GRID
# ---------------------------------------------------------------------

class HazardCell(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    row: int = Field(ge=0)
    col: int = Field(ge=0)

    p_hazard: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=1)

    class_: HazardClass = Field(alias="class")

    raw_boulder_count: int = Field(default=0, ge=0)

    corrected_boulder_count: float = Field(
        default=0, ge=0
    )

    hazardous_boulder_count: float = Field(
        default=0, ge=0
    )

    largest_boulder_m: Optional[float] = Field(
        default=None, ge=0
    )

    rho_h_per_m2: float = Field(default=0, ge=0)
    density: float = Field(default=0, ge=0)
    cell_area_m2: float = Field(default=0, ge=0)

    slope_deg: Optional[float] = Field(
        default=None, ge=0, le=90
    )

    # Allowed values: pass, fail, not_assessed.
    slope_gate: Optional[str] = None

    recall_corrected: bool = False

    explanation: str = ""

    reasons: List[str] = Field(default_factory=list)
    missing_inputs: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(
        default_factory=list,
        description="Cell-specific warnings (e.g. low-count parametric resampling).",
    )

    # Frontend-compatible names.
    # These remain optional until their calculations are implemented.
    probability: Optional[float] = Field(
        default=None, ge=0, le=1
    )

    interval_low: Optional[float] = Field(
        default=None, ge=0, le=1
    )

    interval_high: Optional[float] = Field(
        default=None, ge=0, le=1
    )

    label: Optional[str] = None

    raw_count: Optional[int] = Field(
        default=None, ge=0
    )

    corrected_count: Optional[float] = Field(
        default=None, ge=0
    )

    largest_height_m: Optional[float] = Field(
        default=None, ge=0
    )

    largest_height_method: Optional[str] = Field(
        default=None,
        description="Measurement method for the largest detected height (shadow_geometry, diameter_fallback, or none).",
    )


class HazardGridFile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    image: ImageInfo

    rows: int = Field(gt=0)
    cols: int = Field(gt=0)

    lander_footprint_diameter_m: Optional[float] = Field(
        default=None, gt=0
    )

    lander_footprint_area_m2: Optional[float] = Field(
        default=None, gt=0
    )

    cells: List[HazardCell] = Field(
        default_factory=list,
        validation_alias=AliasChoices(
            "cells", "hazard_cells"
        ),
        serialization_alias="hazard_cells",
    )

    warnings: List[str] = Field(default_factory=list)

    is_mock: bool = False

    disclaimer: str = (
        "LunaSafe AI is a research prototype for lunar landing "
        "hazard screening. Results are not flight-certified and "
        "do not guarantee a safe landing."
    )

    @property
    def hazard_cells(self) -> List[HazardCell]:
        return self.cells


# ---------------------------------------------------------------------
# ANALYSIS CONFIGURATION
# ---------------------------------------------------------------------

class AnalysisConfig(BaseModel):
    grid_rows: int = Field(default=8, ge=1)
    grid_cols: int = Field(default=8, ge=1)

    lander_footprint_diameter_m: float = Field(
        default=10.0, gt=0
    )

    hazard_height_threshold_m: float = Field(
        default=0.5, gt=0
    )

    slope_gate_deg: float = Field(
        default=10.0, ge=0, le=90
    )

    caution_p_hazard: float = Field(
        default=0.1, ge=0, le=1
    )

    unsafe_p_hazard: float = Field(
        default=0.3, ge=0, le=1
    )

    detection_confidence_min: float = Field(
        default=0.5, ge=0, le=1
    )

    apply_recall_correction: bool = False

    recall_floor: float = Field(
        default=0.2,
        gt=0,
        le=1.0,
        description="Minimum recall floor to avoid extreme weights (1/recall). Bins with 0 < recall < recall_floor are clamped to this floor.",
    )

    shadow_height_min_sun_elevation_deg: float = Field(
        default=5.0, gt=0, le=90
    )

    shadow_height_max_sun_elevation_deg: float = Field(
        default=80.0, gt=0, le=90
    )

    pixel_uncertainty_px: float = Field(
        default=1.0, ge=0
    )

    sun_elevation_uncertainty_deg: float = Field(
        default=0.0,
        ge=0.0,
        le=90.0,
        description="PLACEHOLDER / Proposal (unconfirmed): Uncertainty in Sun elevation angle in degrees. Propagated into shadow-based height uncertainty. Default 0.0.",
    )

    bootstrap_n: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Number of bootstrap replicates for estimating uncertainty intervals.",
    )

    bootstrap_ci: float = Field(
        default=0.90,
        gt=0,
        lt=1.0,
        description="Confidence level for bootstrap intervals (default 0.90 for 90% CI).",
    )

    bootstrap_seed: Optional[int] = Field(
        default=42,
        description="Random seed for bootstrap reproducibility. Set to None for unseeded randomness.",
    )

    slope_margin_deg: float = Field(
        default=0.0,
        ge=0.0,
        le=90.0,
        description="PLACEHOLDER / Proposal (unconfirmed): Safety margin below slope_gate_deg. Passing cells with slope > (slope_gate_deg - slope_margin_deg) are downgraded to Caution.",
    )

    use_interval_upper_bound: bool = Field(
        default=False,
        description="PLACEHOLDER / Proposal (unconfirmed): When True, Safe candidates whose interval_high >= unsafe_p_hazard are downgraded to Caution.",
    )

    slope_statistic: str = Field(
        default="max",
        description="Aggregation statistic for DEM slope grid reduction: 'max' (conservative default) or 'mean'.",
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> "AnalysisConfig":
        if not (0.0 <= self.caution_p_hazard <= 1.0):
            raise ValueError(
                f"caution_p_hazard ({self.caution_p_hazard}) must be between 0.0 and 1.0."
            )
        if not (0.0 <= self.unsafe_p_hazard <= 1.0):
            raise ValueError(
                f"unsafe_p_hazard ({self.unsafe_p_hazard}) must be between 0.0 and 1.0."
            )
        if self.caution_p_hazard >= self.unsafe_p_hazard:
            raise ValueError(
                f"caution_p_hazard ({self.caution_p_hazard}) must be strictly less than "
                f"unsafe_p_hazard ({self.unsafe_p_hazard})."
            )
        if self.slope_statistic not in ("max", "mean"):
            raise ValueError(
                f"slope_statistic must be 'max' or 'mean', got '{self.slope_statistic}'."
            )
        return self

    @property
    def confidence_min(self) -> float:
        return self.detection_confidence_min

    @property
    def caution_probability_threshold(self) -> float:
        return self.caution_p_hazard

    @property
    def unsafe_probability_threshold(self) -> float:
        return self.unsafe_p_hazard

    @property
    def hazard_boulder_height_m(self) -> float:
        return self.hazard_height_threshold_m

    @property
    def lander_footprint_area_m2(self) -> float:
        return math.pi * (
            self.lander_footprint_diameter_m / 2
        ) ** 2

    @property
    def slope_threshold_deg(self) -> float:
        return self.slope_gate_deg
