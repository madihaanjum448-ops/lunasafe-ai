"""All API endpoints. Routes stay thin: the logic lives in app/services."""
import io
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.config import Settings, get_settings
from app.schemas.contracts import AnalysisConfig, HazardGridFile, MeasurementsFile
from app.schemas.requests import (
    AnalyzeResponse, HazardGridRequest, MeasureRequest, UploadResponse,
)
from app.services import hazard as hazard_svc
from app.services import measurement as measurement_svc
from app.services import metadata as metadata_svc
from app.services import slope as slope_svc

router = APIRouter(prefix="/api")


def _config(req_config: Optional[AnalysisConfig], settings: Settings) -> AnalysisConfig:
    """Use the request's config, else defaults taken from environment settings."""
    if req_config is not None:
        return req_config
    return AnalysisConfig(
        lander_footprint_diameter_m=settings.lander_footprint_diameter_m,
        hazard_height_threshold_m=settings.hazard_boulder_height_m,
        slope_gate_deg=settings.slope_gate_deg,
    )


@router.get("/health", tags=["system"])
def health(settings: Settings = Depends(get_settings)):
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@router.get("/config", response_model=AnalysisConfig, tags=["system"])
def default_config(settings: Settings = Depends(get_settings)):
    """The default config.json. Values marked PLACEHOLDER must be confirmed against the PRD."""
    return _config(None, settings)


@router.post("/upload", response_model=UploadResponse, tags=["image"])
async def upload_image(
    file: UploadFile = File(...),
    pixel_scale_m: Optional[float] = Form(None, description="metres per pixel, from the product label"),
    sun_elevation_deg: Optional[float] = Form(None, description="solar elevation, degrees"),
    projection: Optional[str] = Form(None),
    settings: Settings = Depends(get_settings),
):
    """Validate an image, read what metadata exists, and report what is missing. Nothing is invented."""
    data = await file.read()
    info, warnings = metadata_svc.process_upload(
        data, file.filename or "upload", settings,
        pixel_scale_m=pixel_scale_m, sun_elevation_deg=sun_elevation_deg, projection=projection,
    )
    missing = [n for n, v in (("pixel_scale_m", info.pixel_scale_m),
                              ("sun_elevation_deg", info.sun_elevation_deg),
                              ("projection", info.projection)) if v is None]
    return UploadResponse(
        image=info, warnings=warnings, missing_metadata=missing,
        can_measure_diameter=info.pixel_scale_m is not None,
        can_measure_height_from_shadow=info.pixel_scale_m is not None and info.sun_elevation_deg is not None,
    )


@router.post("/measure", response_model=MeasurementsFile, tags=["analysis"])
def measure(req: MeasureRequest, settings: Settings = Depends(get_settings)):
    """measurements.json: diameter (pixel scale) and height (shadow geometry, with labelled fallback)."""
    return measurement_svc.measure_detections(req.image, req.detections, _config(req.config, settings), req.shadow_lengths_px)


@router.post("/hazard-grid", response_model=HazardGridFile, tags=["analysis"])
def hazard_grid(req: HazardGridRequest, settings: Settings = Depends(get_settings)):
    """hazard_grid.json: Poisson footprint probability per cell + separate slope gate."""
    cfg = _config(req.config, settings)
    meas = measurement_svc.measure_detections(req.image, req.detections, cfg, req.shadow_lengths_px)
    try:
        grid = hazard_svc.build_hazard_grid(req.image, req.detections, meas.measurements, cfg,
                                            slope_by_cell=req.slope_by_cell, recall=req.recall, is_mock=req.is_mock)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    grid.warnings = meas.warnings + grid.warnings
    return grid


@router.post("/analyze", response_model=AnalyzeResponse, response_model_by_alias=True, tags=["analysis"])
def analyze(req: HazardGridRequest, settings: Settings = Depends(get_settings)):
    """One call for the frontend: detections (size_m filled where possible) + measurements + hazard cells + warnings."""
    cfg = _config(req.config, settings)
    meas = measurement_svc.measure_detections(req.image, req.detections, cfg, req.shadow_lengths_px)
    try:
        grid = hazard_svc.build_hazard_grid(req.image, req.detections, meas.measurements, cfg,
                                            slope_by_cell=req.slope_by_cell, recall=req.recall, is_mock=req.is_mock)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    by_id = {m.detection_id: m for m in meas.measurements}
    dets = []
    for d in req.detections:
        m = by_id.get(d.id)
        if d.size_m is None and m and m.diameter_m is not None:
            d = d.model_copy(update={"size_m": m.diameter_m})
        dets.append(d)
    return AnalyzeResponse(image=req.image, detections=dets, measurements=meas.measurements,
                           hazard_cells=grid.hazard_cells, warnings=meas.warnings + grid.warnings, is_mock=req.is_mock)


@router.post("/slope", tags=["dem"])
async def slope_from_dem(
    dem_file: UploadFile = File(..., description=".npy 2-D elevation array in metres"),
    cell_size_m: float = Form(..., gt=0, description="DEM cell size in metres"),
    rows: int = Form(8, ge=1, le=64),
    cols: int = Form(8, ge=1, le=64),
):
    """
    Compute slope per grid cell from a DEM saved as .npy (metres).
    ASSUMES the DEM covers the same footprint as the image. Not validated against a published slope product.
    """
    raw = await dem_file.read()
    try:
        dem = np.load(io.BytesIO(raw), allow_pickle=False)
        slope = slope_svc.compute_slope_deg(dem, cell_size_m)
    except Exception as e:  # bad file or bad shape
        raise HTTPException(status_code=422, detail=f"Could not read DEM: {e}")
    return {
        "rows": rows, "cols": cols,
        "slope_by_cell": slope_svc.slope_by_grid_cell(slope, rows, cols, "max"),
        "statistic": "max slope inside each cell (conservative)",
        "warnings": ["Assumes the DEM footprint equals the image footprint (no georeferenced alignment yet)."],
    }
