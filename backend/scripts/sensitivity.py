#!/usr/bin/env python3
"""
Parameter sensitivity analysis script for LunaSafe AI.

Sweeps key parameters:
1. Lander footprint diameter (e.g. 6, 8, 10, 12, 15 m)
2. Hazard boulder height threshold (e.g. 0.3, 0.4, 0.5, 0.6, 0.8 m)
3. Recall scaling factor (e.g. 0.7, 0.85, 1.0, 1.15, 1.3, capped at 1.0)

Outputs:
- results/sensitivity/sensitivity.csv
- results/sensitivity/sensitivity.json (including run manifest)

Ensures deterministic execution via fixed seed.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings, get_settings
from app.schemas.contracts import (
    AnalysisConfig,
    Detection,
    HazardClass,
    RecallBin,
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
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_git_commit_hash() -> str:
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


def scale_recall(base_recall: Optional[RecallFile], scale_factor: float) -> Optional[RecallFile]:
    if base_recall is None:
        return None
    scaled_bins: List[RecallBin] = []
    for b in base_recall.bins:
        new_rec = min(1.0, max(0.0, b.recall * scale_factor))
        scaled_bins.append(
            RecallBin(
                bin_min_m=b.bin_min_m,
                bin_max_m=b.bin_max_m,
                recall=new_rec,
                precision=b.precision,
                n_gt=b.n_gt,
            )
        )
    return RecallFile(bins=scaled_bins)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run sensitivity sweep on landing hazard parameters."
    )
    parser.add_argument("--image", required=True, type=Path, help="Path to optical image")
    parser.add_argument("--detections", required=True, type=Path, help="Path to detections JSON")
    parser.add_argument("--shadows", type=Path, default=None, help="Path to shadow lengths JSON")
    parser.add_argument("--quality", type=Path, default=None, help="Path to shadow quality JSON")
    parser.add_argument("--recall", type=Path, default=None, help="Path to recall JSON")
    parser.add_argument("--dem", type=Path, default=None, help="Path to DEM .npy")
    parser.add_argument("--dem-cell-size", type=float, default=None, help="DEM cell size in metres")
    parser.add_argument("--pixel-scale", type=float, default=None, help="Pixel scale override")
    parser.add_argument("--sun-elevation", type=float, default=None, help="Sun elevation override")
    parser.add_argument("--out-dir", type=Path, default=BACKEND_DIR / "results" / "sensitivity", help="Output directory")
    parser.add_argument("--allow-mock", action="store_true", help="Allow synthetic/mock inputs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for bootstrap reproducibility")
    return parser.parse_args()


def run_sensitivity(args: argparse.Namespace) -> int:
    settings = get_settings()

    if not args.image.exists() or not args.detections.exists():
        print("Error: Image and detections files must exist.", file=sys.stderr)
        return 1

    input_hashes: Dict[str, str] = {
        "image": compute_sha256(args.image),
        "detections": compute_sha256(args.detections),
    }

    # Load detections
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
        print("Error: Detections must be JSON list or object with detections", file=sys.stderr)
        return 1

    if is_mock and not args.allow_mock:
        print(
            "ERROR: Detections are marked mock/synthetic (is_mock=True). "
            "Refusing to run sensitivity sweep without --allow-mock.",
            file=sys.stderr,
        )
        return 1

    detections = [Detection.model_validate(d) for d in raw_list]

    # Ingest image
    with open(args.image, "rb") as f:
        img_bytes = f.read()

    info, _ = metadata_svc.process_upload(
        img_bytes,
        filename=args.image.name,
        settings=settings,
        pixel_scale_m=args.pixel_scale,
        sun_elevation_deg=args.sun_elevation,
    )

    if info.pixel_scale_m is None:
        print("Error: pixel_scale_m is required for physical footprint calculation.", file=sys.stderr)
        return 1

    # Load optional shadows and quality
    shadow_dict: Dict[int, float] = {}
    if args.shadows and args.shadows.exists():
        input_hashes["shadows"] = compute_sha256(args.shadows)
        with open(args.shadows, "r", encoding="utf-8") as f:
            raw_s = json.load(f)
            if isinstance(raw_s, dict):
                shadow_dict = {int(k): float(v) for k, v in raw_s.items()}

    quality_dict: Optional[Dict[int, str]] = None
    if args.quality and args.quality.exists():
        input_hashes["quality"] = compute_sha256(args.quality)
        with open(args.quality, "r", encoding="utf-8") as f:
            raw_q = json.load(f)
            if isinstance(raw_q, dict):
                quality_dict = {int(k): str(v) for k, v in raw_q.items()}

    # Load optional base recall
    base_recall: Optional[RecallFile] = None
    if args.recall and args.recall.exists():
        input_hashes["recall"] = compute_sha256(args.recall)
        with open(args.recall, "r", encoding="utf-8") as f:
            raw_rec = json.load(f)
            base_recall = RecallFile.model_validate(raw_rec)

    # Baseline configuration
    baseline_cfg = AnalysisConfig(
        lander_footprint_diameter_m=10.0,
        hazard_height_threshold_m=0.5,
        slope_gate_deg=10.0,
        caution_p_hazard=0.10,
        unsafe_p_hazard=0.30,
        bootstrap_seed=args.seed,
        apply_recall_correction=(base_recall is not None),
    )

    # Load optional DEM
    slope_by_cell = None
    if args.dem and args.dem.exists():
        input_hashes["dem"] = compute_sha256(args.dem)
        if args.dem_cell_size and args.dem_cell_size > 0:
            dem_arr = np.load(args.dem, allow_pickle=False)
            slope_raster = slope_svc.compute_slope_deg(dem_arr, args.dem_cell_size)
            slope_by_cell = slope_svc.slope_by_grid_cell(
                slope_raster, baseline_cfg.grid_rows, baseline_cfg.grid_cols, "max"
            )

    # 1. Run baseline
    base_meas = measurement_svc.measure_detections(
        info, detections, baseline_cfg, shadow_dict, shadow_quality=quality_dict
    )
    base_grid = hazard_svc.build_hazard_grid(
        info, detections, base_meas.measurements, baseline_cfg,
        slope_by_cell=slope_by_cell, recall=base_recall, is_mock=is_mock
    )

    baseline_classes = [c.class_.value for c in base_grid.cells]
    baseline_p = [c.p_hazard for c in base_grid.cells]

    base_safe = sum(1 for c in baseline_classes if c == HazardClass.safe.value)
    base_caution = sum(1 for c in baseline_classes if c == HazardClass.caution.value)
    base_unsafe = sum(1 for c in baseline_classes if c == HazardClass.unsafe.value)

    # Define sweep sets
    footprint_values = [6.0, 8.0, 10.0, 12.0, 15.0]
    height_values = [0.3, 0.4, 0.5, 0.6, 0.8]
    recall_scale_values = [0.70, 0.85, 1.0, 1.15, 1.30]

    # Collect runs: (param_varied, footprint, height, recall_scale)
    runs_to_eval = [
        ("baseline", 10.0, 0.5, 1.0)
    ]

    for d in footprint_values:
        if d != 10.0:
            runs_to_eval.append(("footprint_diameter_m", d, 0.5, 1.0))

    for h in height_values:
        if h != 0.5:
            runs_to_eval.append(("hazard_height_threshold_m", 10.0, h, 1.0))

    for s in recall_scale_values:
        if s != 1.0:
            runs_to_eval.append(("recall_scale", 10.0, 0.5, s))

    results: List[Dict[str, Any]] = []

    for param_name, d_m, h_m, r_scale in runs_to_eval:
        cfg = AnalysisConfig(
            lander_footprint_diameter_m=d_m,
            hazard_height_threshold_m=h_m,
            slope_gate_deg=10.0,
            caution_p_hazard=0.10,
            unsafe_p_hazard=0.30,
            bootstrap_seed=args.seed,
            apply_recall_correction=(base_recall is not None),
        )

        cur_recall = scale_recall(base_recall, r_scale) if base_recall else None

        meas = measurement_svc.measure_detections(
            info, detections, cfg, shadow_dict, shadow_quality=quality_dict
        )
        grid = hazard_svc.build_hazard_grid(
            info, detections, meas.measurements, cfg,
            slope_by_cell=slope_by_cell, recall=cur_recall, is_mock=is_mock
        )

        classes = [c.class_.value for c in grid.cells]
        p_vals = [c.p_hazard for c in grid.cells]

        safe_cnt = sum(1 for c in classes if c == HazardClass.safe.value)
        caution_cnt = sum(1 for c in classes if c == HazardClass.caution.value)
        unsafe_cnt = sum(1 for c in classes if c == HazardClass.unsafe.value)

        mean_p = float(np.mean(p_vals)) if p_vals else 0.0
        max_p = float(np.max(p_vals)) if p_vals else 0.0

        # Count cells whose class differs from baseline
        diff_count = sum(1 for i in range(len(classes)) if classes[i] != baseline_classes[i])

        results.append({
            "parameter_varied": param_name,
            "footprint_diameter_m": d_m,
            "hazard_height_threshold_m": h_m,
            "recall_scale": r_scale,
            "safe_count": safe_cnt,
            "caution_count": caution_cnt,
            "unsafe_count": unsafe_cnt,
            "mean_p_hazard": round(mean_p, 4),
            "max_p_hazard": round(max_p, 4),
            "class_diff_from_baseline": diff_count,
        })

    # Write CSV
    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / "sensitivity.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "parameter_varied",
            "footprint_diameter_m",
            "hazard_height_threshold_m",
            "recall_scale",
            "safe_count",
            "caution_count",
            "unsafe_count",
            "mean_p_hazard",
            "max_p_hazard",
            "class_diff_from_baseline",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    # Write JSON with manifest
    json_path = args.out_dir / "sensitivity.json"
    payload = {
        "manifest": {
            "git_commit_hash": get_git_commit_hash(),
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "input_files_sha256": input_hashes,
            "baseline_config": baseline_cfg.model_dump(mode="json"),
            "seed": args.seed,
            "is_mock": is_mock,
            "unconfirmed_placeholders": UNCONFIRMED_PLACEHOLDERS,
        },
        "baseline": {
            "safe_count": base_safe,
            "caution_count": base_caution,
            "unsafe_count": base_unsafe,
            "mean_p_hazard": round(float(np.mean(baseline_p)), 4),
            "max_p_hazard": round(float(np.max(baseline_p)), 4),
        },
        "sweep_results": results,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[SUCCESS] Sensitivity analysis finished.")
    print(f"  CSV: {csv_path}")
    print(f"  JSON: {json_path}")
    print(f"  Total runs evaluated: {len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(run_sensitivity(parse_args()))
