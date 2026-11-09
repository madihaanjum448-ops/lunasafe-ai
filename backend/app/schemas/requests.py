
"""
LunaSafe AI - API request and response schemas.

These models define the data exchanged between the frontend
and FastAPI backend.

Detailed scientific data structures are defined in contracts.py.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.contracts import (
    AnalysisConfig,
    Detection,
    HazardCell,
    ImageInfo,
    Measurement,
    RecallFile,
)


# ---------------------------------------------------------
# 1. Image upload response
# ---------------------------------------------------------

class UploadResponse(BaseModel):
    """Response returned after uploading and validating an image."""

    image: ImageInfo

    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings generated during image validation.",
    )

    missing_metadata: List[str] = Field(
        default_factory=list,
        description=(
            "Missing metadata fields: pixel_scale_m, "
            "sun_elevation_deg or projection."
        ),
    )

    can_measure_diameter: bool = Field(
        description=(
            "True when a valid pixel scale is available "
            "for converting pixels into metres."
        ),
    )

    can_measure_height_from_shadow: bool = Field(
        description=(
            "True when valid pixel scale and Sun elevation "
            "are available for shadow-based height estimation."
        ),
    )


# ---------------------------------------------------------
# 2. Boulder measurement request
# ---------------------------------------------------------

class MeasureRequest(BaseModel):
    """Request to measure detected boulders."""

    image: ImageInfo

    detections: List[Detection] = Field(
        description="Boulder detections produced by the AI model.",
    )

    shadow_lengths_px: Dict[int, float] = Field(
        default_factory=dict,
        description=(
            "Mapping of detection ID to measured shadow length "
            "in pixels. Optional."
        ),
    )

    config: Optional[AnalysisConfig] = Field(
        default=None,
        description=(
            "Optional analysis configuration. "
            "Backend defaults are used when omitted."
        ),
    )


# ---------------------------------------------------------
# 3. Hazard grid request
# ---------------------------------------------------------

class HazardGridRequest(BaseModel):
    """Request to calculate the lunar landing hazard grid."""

    image: ImageInfo

    detections: List[Detection] = Field(
        description="Boulder detections associated with the image.",
    )

    shadow_lengths_px: Dict[int, float] = Field(
        default_factory=dict,
        description=(
            "Mapping of detection ID to shadow length in pixels."
        ),
    )

    config: Optional[AnalysisConfig] = Field(
        default=None,
        description="Optional hazard analysis configuration.",
    )

    slope_by_cell: Optional[List[List[Optional[float]]]] = Field(
        default=None,
        description=(
            "Slope values in degrees arranged as a rows x cols grid. "
            "Normally generated using the /api/slope endpoint."
        ),
    )

    recall: Optional[RecallFile] = Field(
        default=None,
        description=(
            "Optional detector recall values grouped by "
            "boulder diameter bin. Used for recall correction."
        ),
    )

    is_mock: bool = Field(
        default=False,
        description=(
            "True when the supplied detections or analysis "
            "inputs are demonstration or test data."
        ),
    )


# ---------------------------------------------------------
# 4. Complete analysis response
# ---------------------------------------------------------

class AnalyzeResponse(BaseModel):
    """
    Complete analysis response returned to the frontend.

    The structure is compatible with the frontend's
    sampleResult.json response format.
    """

    image: ImageInfo

    detections: List[Detection] = Field(
        description="Detected boulders in the uploaded image.",
    )

    measurements: List[Measurement] = Field(
        description="Diameter and height measurements.",
    )

    hazard_cells: List[HazardCell] = Field(
        description=(
            "Grid-cell hazard probabilities, classifications, "
            "slope information and explanations."
        ),
    )

    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings and limitations associated with the analysis.",
    )

    is_mock: bool = Field(
        default=False,
        description="Indicates whether the result uses mock data.",
    )
