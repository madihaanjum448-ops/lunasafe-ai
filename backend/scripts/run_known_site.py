#!/usr/bin/env python3
"""
Known-site runner for LunaSafe AI.

Executes the landing-hazard screening pipeline on an optical image,
detections, shadow measurements, DEM elevation raster, and recall table.
Calls identical service functions to the /api/pipeline endpoint (no duplicate logic).

Writes to --out:
- measurements.json
- hazard_grid.json
- summary.json
- run_manifest.json
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend directory to sys.path so 'app.*' imports resolve cleanly
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
from app.core.config import Settings, get_settings
from app.schemas.contracts import (
    AnalysisConfig,
    Detection,
    HazardClass,
    RecallFile,
)
from app.services import hazard as hazard_svc
from app.services import measurement as measurement_svc
from app.services import metadata as metadata_svc
from app.services import slope as slope_svc

UNCONFIRMED_PLACEHOLDERS = [
    "hazard_height_threshold_m: 0.5m is unconfirmed (PRD v2.0 placeholder).",
    "slope_gate_deg: 10.0 deg is unconfirmed (PRD v2.0 placeholder).",
    "caution_p_hazard: 0.10 is unconfirmed (PRD v2.0 placeholder).",
    "unsafe_p_hazard: 0.30 is unconfirmed (PRD v2.0 placeholder).",
    "fallback_height_to_diameter_ratio: 0.5 is an assumption (not scientifically verified).",
    "slope_margin_deg: 0.0 deg is a proposal only.",
    "use_interval_upper_bound: false is a proposal only.",
    "sun_elevation_uncertainty_deg: 0.0 deg is a proposal only.",
]


def compute_sha256(filepath: Path) -> str:
    """Compute hex SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_git_commit_hash() -> str:
    """Retrieve the current git commit hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run LunaSafe AI hazard pipeline on a known site image."
    )
    parser.add_argument("--image", required=True, type=Path, help="Path to lunar optical image.")
    parser.add_argument("--detections", required=True, type=Path, help="Path to detections JSON file.")
    parser.add_argument("--shadows", type=Path, default=None, help="Path to shadow lengths JSON file.")
    parser.add_argument("--quality", type=Path, default=None, help="Path to shadow quality JSON file.")
    parser.add_argument("--recall", type=Path, default=None, help="Path to detector recall JSON file.")
    parser.add_argument("--dem", type=Path, default=None, help="Path to DEM .npy elevation raster.")
    parser.add_argument("--dem-cell-size", type=float, default=None, help="DEM cell size in metres.")
    parser.add_argument("--config", type=Path, default=None, help="Path to custom AnalysisConfig JSON file.")
    parser.add_argument("--pixel-scale", type=float, default=None, help="Override image pixel scale in m/px.")
    parser.add_argument("--sun-elevation", type=float, default=None, help="Override Sun elevation in degrees.")
    parser.add_argument("--projection", type=str, default=None, help="Override image projection.")
    parser.add_argument("--reference-heights", type=Path, default=None, help="Optional JSON of ground-truth heights.")
    parser.add_argument("--out", type=Path, default=BACKEND_DIR / "results" / "known_site", help="Output directory.")
    parser.add_argument("--allow-mock", action="store_true", help="Allow running on synthetic/mock inputs.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    return parser.parse_args()


def run_pipeline_known_site(args: argparse.Namespace) -> int:
    settings = get_settings()

    # 1. Verify required image and detections exist
    if not args.image.exists():
        print(f"Error: Image file not found: {args.image}", file=sys.stderr)
        return 1
    if not args.detections.exists():
        print(f"Error: Detections file not found: {args.detections}", file=sys.stderr)
        return 1

    input_hashes: Dict[str, str] = {
        "image": compute_sha256(args.image),
        "detections": compute_sha256(args.detections),
    }

    # 2. Parse detections and check is_mock
    with open(args.detections, "r", encoding="utf-8") as f:
        dets_raw = json.load(f)

    is_mock = False
    if isinstance(dets_raw, dict):
        if dets_raw.get("is_mock") is True:
            is_mock = True
        raw_list = dets_raw.get("detections", [])
    elif isinstance(dets_raw, list):
        raw_list = dets_raw
    else:
        print("Error: Detections file must be a JSON array or object with 'detections'", file=sys.stderr)
        return 1

    if is_mock and not args.allow_mock:
        print(
            "ERROR: Detections file is marked as mock/synthetic (is_mock=True). "
            "Refusing to run without explicit --allow-mock flag.",
            file=sys.stderr,
        )
        return 1

    if is_mock:
        print("[WARNING] Running on synthetic/mock data (--allow-mock is active). All outputs stamped is_mock=True.")

    detections = [Detection.model_validate(d) for d in raw_list]

    # 3. Parse config
    if args.config and args.config.exists():
        input_hashes["config"] = compute_sha256(args.config)
        with open(args.config, "r", encoding="utf-8") as f:
            cfg_dict = json.load(f)
        cfg = AnalysisConfig.model_validate(cfg_dict)
    else:
        cfg = AnalysisConfig(
            lander_footprint_diameter_m=settings.lander_footprint_diameter_m,
            hazard_height_threshold_m=settings.hazard_boulder_height_m,
            slope_gate_deg=settings.slope_gate_deg,
            bootstrap_seed=args.seed,
        )

    # 4. Ingest and validate image metadata
    with open(args.image, "rb") as f:
        img_bytes = f.read()

    info, upload_warnings = metadata_svc.process_upload(
        img_bytes,
        filename=args.image.name,
        settings=settings,
        pixel_scale_m=args.pixel_scale,
        sun_elevation_deg=args.sun_elevation,
        projection=args.projection,
    )

    if info.pixel_scale_m is None:
        print("Error: pixel_scale_m is required for physical measurements and areas.", file=sys.stderr)
        return 1

    # 5. Parse shadow lengths
    shadow_dict: Dict[int, float] = {}
    if args.shadows and args.shadows.exists():
        input_hashes["shadows"] = compute_sha256(args.shadows)
        with open(args.shadows, "r", encoding="utf-8") as f:
            raw_s = json.load(f)
        if isinstance(raw_s, dict):
            for k, v in raw_s.items():
                try:
                    shadow_dict[int(k)] = float(v)
                except (ValueError, TypeError):
                    pass

    # 6. Parse shadow quality
    quality_dict: Optional[Dict[int, str]] = None
    if args.quality and args.quality.exists():
        input_hashes["quality"] = compute_sha256(args.quality)
        with open(args.quality, "r", encoding="utf-8") as f:
            raw_q = json.load(f)
        if isinstance(raw_q, dict):
            quality_dict = {int(k): str(v) for k, v in raw_q.items()}

    # 7. Parse reference heights (optional)
    ref_heights: Optional[Dict[int, float]] = None
    if args.reference_heights and args.reference_heights.exists():
        input_hashes["reference_heights"] = compute_sha256(args.reference_heights)
        with open(args.reference_heights, "r", encoding="utf-8") as f:
            raw_r = json.load(f)
        if isinstance(raw_r, dict):
            ref_heights = {int(k): float(v) for k, v in raw_r.items()}

    # 8. Parse recall table
    recall_obj = None
    if args.recall and args.recall.exists():
        input_hashes["recall"] = compute_sha256(args.recall)
        with open(args.recall, "r", encoding="utf-8") as f:
            raw_rec = json.load(f)
        recall_obj = RecallFile.model_validate(raw_rec)
        if getattr(recall_obj, "is_mock", False):
            is_mock = True

    # 9. Compute measurements
    meas_file = measurement_svc.measure_detections(
        info,
        detections,
        cfg,
        shadow_lengths_px=shadow_dict,
        shadow_quality=quality_dict,
        reference_heights_m=ref_heights,
    )

    # 10. Parse DEM and compute slope grid
    slope_by_cell = None
    dem_warnings: List[str] = []
    slope_assessed = False
    if args.dem and args.dem.exists():
        input_hashes["dem"] = compute_sha256(args.dem)
        if args.dem_cell_size is None or args.dem_cell_size <= 0:
            print("Error: --dem-cell-size must be provided and > 0 when --dem is supplied.", file=sys.stderr)
            return 1
        dem_array = np.load(args.dem, allow_pickle=False)
        slope_raster = slope_svc.compute_slope_deg(dem_array, args.dem_cell_size)
        slope_by_cell = slope_svc.slope_by_grid_cell(
            slope_raster, cfg.grid_rows, cfg.grid_cols, cfg.slope_statistic
        )
        dem_warnings.append(
            "Assumes the DEM footprint equals the image footprint (no georeferenced alignment yet)."
        )
        slope_assessed = True

    # 11. Build hazard grid
    grid = hazard_svc.build_hazard_grid(
        info,
        detections,
        meas_file.measurements,
        cfg,
        slope_by_cell=slope_by_cell,
        recall=recall_obj,
        is_mock=is_mock,
    )

    combined_warnings = upload_warnings + meas_file.warnings + dem_warnings + grid.warnings

    # 12. Create output directory
    args.out.mkdir(parents=True, exist_ok=True)

    # Write measurements.json
    meas_out = meas_file.model_dump(mode="json")
    if is_mock:
        meas_out["is_mock"] = True
    with open(args.out / "measurements.json", "w", encoding="utf-8") as f:
        json.dump(meas_out, f, indent=2)

    # Write hazard_grid.json
    grid_out = grid.model_dump(mode="json")
    with open(args.out / "hazard_grid.json", "w", encoding="utf-8") as f:
        json.dump(grid_out, f, indent=2)

    # Compute summary counts
    class_counts = {
        HazardClass.safe.value: 0,
        HazardClass.caution.value: 0,
        HazardClass.unsafe.value: 0,
    }
    cells_passed = 0
    cells_failed = 0
    cells_not_assessed = 0

    for c in grid.cells:
        class_counts[c.class_.value] += 1
        if c.slope_gate == "pass":
            cells_passed += 1
        elif c.slope_gate == "fail":
            cells_failed += 1
        else:
            cells_not_assessed += 1

    method_counts = {"shadow_geometry": 0, "diameter_fallback": 0, "unavailable": 0}
    quality_counts = {"good": 0, "fair": 0, "poor": 0, "unspecified": 0}

    for m in meas_file.measurements:
        method_counts[m.method.value] = method_counts.get(m.method.value, 0) + 1
        if m.shadow_quality is not None:
            quality_counts[m.shadow_quality.value] = quality_counts.get(m.shadow_quality.value, 0) + 1
        else:
            quality_counts["unspecified"] += 1

    summary = {
        "is_mock": is_mock,
        "total_cells": len(grid.cells),
        "class_counts": class_counts,
        "detections_summary": {
            "total_detections": len(detections),
            "used_detections": len(detections),
            "excluded_detections": 0,
            "exclusion_reasons": {},
        },
        "heights_by_method": method_counts,
        "shadow_quality_counts": quality_counts,
        "slope_availability": {
            "assessed": slope_assessed,
            "dem_file": str(args.dem.name) if args.dem else None,
            "dem_cell_size_m": args.dem_cell_size,
            "slope_gate_deg": cfg.slope_gate_deg,
            "cells_passed": cells_passed,
            "cells_failed": cells_failed,
            "cells_not_assessed": cells_not_assessed,
        },
        "warnings": combined_warnings,
    }

    with open(args.out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Write run_manifest.json
    manifest = {
        "git_commit_hash": get_git_commit_hash(),
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "input_files_sha256": input_hashes,
        "config_used": cfg.model_dump(mode="json"),
        "seed": args.seed,
        "is_mock": is_mock,
        "unconfirmed_placeholders": UNCONFIRMED_PLACEHOLDERS,
    }

    with open(args.out / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[SUCCESS] Pipeline completed. Outputs written to {args.out}")
    print(f"  Cells summary: {class_counts}")
    print(f"  Slope assessed: {slope_assessed} (pass={cells_passed}, fail={cells_failed}, not_assessed={cells_not_assessed})")
    print(f"  Heights by method: {method_counts}")
    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline_known_site(parse_args()))
