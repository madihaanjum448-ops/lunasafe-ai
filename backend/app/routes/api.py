"""All API endpoints. Routes stay thin: the logic lives in app/services."""
import io
import json
from typing import Dict, List, Optional

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.config import Settings, get_settings
from app.schemas.contracts import (
    AnalysisConfig,
    Detection,
    HazardGridFile,
    MeasurementsFile,
    RecallFile,
)
from app.schemas.requests import (
    AnalyzeResponse,
    HazardGridRequest,
    MeasureRequest,
    PipelineResponse,
    UploadResponse,
)
from app.services import hazard as hazard_svc
from app.services import measurement as measurement_svc
from app.services import metadata as metadata_svc
from app.services import slope as slope_svc
from app.services.metadata import ImageValidationError

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
    return measurement_svc.measure_detections(
        req.image,
        req.detections,
        _config(req.config, settings),
        req.shadow_lengths_px,
        shadow_quality=req.shadow_quality,
        reference_heights_m=req.reference_heights_m,
    )


@router.post("/hazard-grid", response_model=HazardGridFile, tags=["analysis"])
def hazard_grid(req: HazardGridRequest, settings: Settings = Depends(get_settings)):
    """hazard_grid.json: Poisson footprint probability per cell + separate slope gate."""
    cfg = _config(req.config, settings)
    meas = measurement_svc.measure_detections(
        req.image,
        req.detections,
        cfg,
        req.shadow_lengths_px,
        shadow_quality=req.shadow_quality,
    )
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
    meas = measurement_svc.measure_detections(
        req.image,
        req.detections,
        cfg,
        req.shadow_lengths_px,
        shadow_quality=req.shadow_quality,
    )
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


@router.post("/pipeline", response_model=PipelineResponse, tags=["pipeline"])
async def run_pipeline(
    image: Optional[UploadFile] = File(None, description="Lunar optical image file (PNG, JPEG, TIFF, WEBP)"),
    image_file: Optional[UploadFile] = File(None, description="Alias for image file"),
    file: Optional[UploadFile] = File(None, description="Alias for image file"),
    pixel_scale_m: Optional[float] = Form(None, description="Metres per pixel from product label / metadata"),
    sun_elevation_deg: Optional[float] = Form(None, description="Sun elevation angle in degrees"),
    projection: Optional[str] = Form(None, description="Cartographic projection description"),
    detections: Optional[str] = Form(None, description="Detections as JSON string or upload detections_file"),
    detections_file: Optional[UploadFile] = File(None, description="Detections as uploaded JSON file"),
    shadow_lengths_px: Optional[str] = Form(None, description="Shadow lengths JSON string or upload shadow_lengths_file"),
    shadow_lengths_file: Optional[UploadFile] = File(None, description="Shadow lengths as uploaded JSON file"),
    shadow_quality: Optional[str] = Form(None, description="Shadow quality JSON string or upload shadow_quality_file"),
    shadow_quality_file: Optional[UploadFile] = File(None, description="Shadow quality as uploaded JSON file"),
    recall: Optional[str] = Form(None, description="RecallFile as JSON string or upload recall_file"),
    recall_file: Optional[UploadFile] = File(None, description="RecallFile as uploaded JSON file"),
    config: Optional[str] = Form(None, description="AnalysisConfig as JSON string or upload config_file"),
    config_file: Optional[UploadFile] = File(None, description="AnalysisConfig as uploaded JSON file"),
    dem_file: Optional[UploadFile] = File(None, description=".npy 2-D elevation array in metres"),
    dem_cell_size_m: Optional[float] = Form(None, description="DEM cell size in metres"),
    is_mock: Optional[bool] = Form(False, description="Flag indicating mock/synthetic inputs"),
    settings: Settings = Depends(get_settings),
):
    """
    End-to-end pipeline (FR-07, FR-08, Gate 3):
    Upload image + metadata -> Measure boulders -> Build slope grid from DEM (if supplied) ->
    Hazard probability & bootstrap intervals -> Classification -> Comprehensive output.
    """
    img = image or image_file or file
    if img is None:
        raise HTTPException(status_code=422, detail="Image file is required.")

    # 1. Parse config first to know grid dimensions
    cfg_data = None
    if config is not None and config.strip():
        try:
            cfg_data = json.loads(config)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON in config: {e}")
    elif config_file is not None:
        raw_cfg = await config_file.read()
        if raw_cfg.strip():
            try:
                cfg_data = json.loads(raw_cfg.decode("utf-8"))
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid JSON in config_file: {e}")

    if cfg_data is not None:
        try:
            cfg = AnalysisConfig(**cfg_data)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid config parameters: {e}")
    else:
        cfg = _config(None, settings)

    # 2. Ingest and validate image
    raw_img = await img.read()
    try:
        info, upload_warnings = metadata_svc.process_upload(
            raw_img,
            img.filename or "upload",
            settings,
            pixel_scale_m=pixel_scale_m,
            sun_elevation_deg=sun_elevation_deg,
            projection=projection,
        )
    except ImageValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    if info.pixel_scale_m is None:
        raise HTTPException(
            status_code=422,
            detail="pixel_scale_m is required to calculate areas, densities, and physical measurements.",
        )

    # 3. Parse detections
    dets_raw = None
    if detections is not None and detections.strip():
        try:
            dets_raw = json.loads(detections)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON in detections: {e}")
    elif detections_file is not None:
        raw_det_bytes = await detections_file.read()
        if raw_det_bytes.strip():
            try:
                dets_raw = json.loads(raw_det_bytes.decode("utf-8"))
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid JSON in detections_file: {e}")

    if dets_raw is None:
        raise HTTPException(status_code=422, detail="detections (as JSON string or uploaded file) is required.")

    mock_flag = bool(is_mock)
    if isinstance(dets_raw, dict):
        if dets_raw.get("is_mock") is True:
            mock_flag = True
        raw_list = dets_raw.get("detections", [])
    elif isinstance(dets_raw, list):
        raw_list = dets_raw
    else:
        raise HTTPException(
            status_code=422,
            detail="Detections JSON must be a list or a dictionary containing 'detections'.",
        )

    try:
        detections_list = [Detection.model_validate(d) for d in raw_list]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid detection data: {e}")

    # 4. Parse shadow lengths
    shadow_dict: Dict[int, float] = {}
    shadows_raw = None
    if shadow_lengths_px is not None and shadow_lengths_px.strip():
        try:
            shadows_raw = json.loads(shadow_lengths_px)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON in shadow_lengths_px: {e}")
    elif shadow_lengths_file is not None:
        raw_sh_bytes = await shadow_lengths_file.read()
        if raw_sh_bytes.strip():
            try:
                shadows_raw = json.loads(raw_sh_bytes.decode("utf-8"))
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid JSON in shadow_lengths_file: {e}")

    if shadows_raw is not None:
        if not isinstance(shadows_raw, dict):
            raise HTTPException(
                status_code=422,
                detail="shadow_lengths_px must be a dictionary mapping detection IDs to pixel lengths.",
            )
        for k, v in shadows_raw.items():
            try:
                k_int = int(k)
                v_flt = float(v)
                shadow_dict[k_int] = v_flt
            except (ValueError, TypeError):
                raise HTTPException(status_code=422, detail=f"Invalid shadow length entry: {k}: {v}")

        # Check for mismatched detection IDs
        det_ids = {d.id for d in detections_list}
        mismatched = set(shadow_dict.keys()) - det_ids
        if mismatched:
            raise HTTPException(
                status_code=422,
                detail=f"shadow_lengths_px contains unknown detection ID(s): {sorted(list(mismatched))}",
            )

    # 4b. Parse shadow quality
    shadow_quality_dict: Optional[Dict[int, str]] = None
    sq_raw = None
    if shadow_quality is not None and shadow_quality.strip():
        try:
            sq_raw = json.loads(shadow_quality)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON in shadow_quality: {e}")
    elif shadow_quality_file is not None:
        raw_sq_bytes = await shadow_quality_file.read()
        if raw_sq_bytes.strip():
            try:
                sq_raw = json.loads(raw_sq_bytes.decode("utf-8"))
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid JSON in shadow_quality_file: {e}")

    if sq_raw is not None:
        if not isinstance(sq_raw, dict):
            raise HTTPException(
                status_code=422,
                detail="shadow_quality must be a dictionary mapping detection IDs to quality strings.",
            )
        shadow_quality_dict = {}
        for k, v in sq_raw.items():
            try:
                k_int = int(k)
                shadow_quality_dict[k_int] = str(v)
            except (ValueError, TypeError):
                raise HTTPException(status_code=422, detail=f"Invalid shadow quality entry: {k}: {v}")

    # 5. Parse recall
    recall_obj = None
    recall_raw = None
    if recall is not None and recall.strip():
        try:
            recall_raw = json.loads(recall)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON in recall: {e}")
    elif recall_file is not None:
        raw_rec_bytes = await recall_file.read()
        if raw_rec_bytes.strip():
            try:
                recall_raw = json.loads(raw_rec_bytes.decode("utf-8"))
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid JSON in recall_file: {e}")

    if recall_raw is not None:
        try:
            recall_obj = RecallFile.model_validate(recall_raw)
            if recall_obj.is_mock:
                mock_flag = True
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid recall table data: {e}")

    # 6. Parse DEM and compute slope grid
    slope_by_cell = None
    dem_warnings: List[str] = []
    if dem_file is not None:
        raw_dem = await dem_file.read()
        if raw_dem:
            if dem_cell_size_m is None or dem_cell_size_m <= 0:
                raise HTTPException(
                    status_code=422,
                    detail="dem_cell_size_m must be provided and > 0 when dem_file is supplied.",
                )
            try:
                dem_array = np.load(io.BytesIO(raw_dem), allow_pickle=False)
                slope_raster = slope_svc.compute_slope_deg(dem_array, dem_cell_size_m)
                slope_by_cell = slope_svc.slope_by_grid_cell(
                    slope_raster, cfg.grid_rows, cfg.grid_cols, cfg.slope_statistic
                )
                dem_warnings.append(
                    "Assumes the DEM footprint equals the image footprint (no georeferenced alignment yet)."
                )
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Could not read or compute slope from DEM: {e}")

    # 7. Measurements
    meas = measurement_svc.measure_detections(
        info, detections_list, cfg, shadow_dict, shadow_quality=shadow_quality_dict
    )

    # 8. Hazard grid & classification
    try:
        grid = hazard_svc.build_hazard_grid(
            info,
            detections_list,
            meas.measurements,
            cfg,
            slope_by_cell=slope_by_cell,
            recall=recall_obj,
            is_mock=mock_flag,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    by_id = {m.detection_id: m for m in meas.measurements}
    filled_dets = []
    for d in detections_list:
        m = by_id.get(d.id)
        if d.size_m is None and m and m.diameter_m is not None:
            d = d.model_copy(update={"size_m": m.diameter_m})
        filled_dets.append(d)

    combined_warnings = upload_warnings + meas.warnings + dem_warnings + grid.warnings

    return PipelineResponse(
        image=info,
        detections=filled_dets,
        measurements=meas.measurements,
        hazard_cells=grid.hazard_cells,
        warnings=combined_warnings,
        is_mock=mock_flag,
    )
