#!/usr/bin/env python3
"""
Global boulder map comparison script for LunaSafe AI.

Compares pipeline hazard-grid boulder counts/densities against a reference
published global boulder map product (either CSV of detected boulders or density raster).

Maps reference data onto the hazard grid cells using image geotransform/CRS.
Refuses to guess coordinates if georeference is missing.

Outputs:
- Number of cells compared
- Spearman rank correlation with bootstrap CI (fixed seed)
- Total count ratio
- Per-size-bin comparison (if size available)
- Spatial resolution mismatch limitation note
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure backend directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def compute_ranks(x: np.ndarray) -> np.ndarray:
    """Compute fractional average ranks for 1-D array x."""
    order = np.argsort(x)
    ranks = np.empty(len(x), dtype=float)
    ranks[order] = np.arange(len(x), dtype=float) + 1.0

    # Adjust for tied values
    unique_vals, counts = np.unique(x, return_counts=True)
    for val, count in zip(unique_vals, counts):
        if count > 1:
            indices = np.where(x == val)[0]
            ranks[indices] = np.mean(ranks[indices])
    return ranks


def spearman_rank_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Compute Spearman rank correlation coefficient r_s."""
    if len(x) < 2:
        return 0.0
    rx = compute_ranks(x)
    ry = compute_ranks(y)
    std_rx = np.std(rx)
    std_ry = np.std(ry)
    if std_rx == 0.0 or std_ry == 0.0:
        return 0.0
    corr = np.corrcoef(rx, ry)[0, 1]
    return float(corr) if math.isfinite(corr) else 0.0


def bootstrap_spearman_ci(
    x: np.ndarray,
    y: np.ndarray,
    n_boot: int = 1000,
    ci: float = 0.90,
    seed: int = 42,
) -> Tuple[float, float]:
    """Compute bootstrap percentile confidence interval for Spearman r_s."""
    n = len(x)
    if n < 3:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    boot_vals = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_vals[i] = spearman_rank_correlation(x[idx], y[idx])
    alpha = (1.0 - ci) / 2.0 * 100.0
    low = float(np.percentile(boot_vals, alpha))
    high = float(np.percentile(boot_vals, 100.0 - alpha))
    return low, high


def load_hazard_grid(grid_path: Path) -> Dict[str, Any]:
    with open(grid_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_reference_csv(csv_path: Path) -> List[Dict[str, float]]:
    """
    Load reference boulder detections from CSV.
    Supported coordinate headers: (x, y) or (lon, lat) or (longitude, latitude).
    Supported size headers: diameter, diameter_m, size, size_m.
    """
    records: List[Dict[str, float]] = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
            x_val = None
            y_val = None
            for x_key in ["x", "lon", "longitude"]:
                if x_key in clean_row:
                    try:
                        x_val = float(clean_row[x_key])
                        break
                    except ValueError:
                        pass
            for y_key in ["y", "lat", "latitude"]:
                if y_key in clean_row:
                    try:
                        y_val = float(clean_row[y_key])
                        break
                    except ValueError:
                        pass
            diam_val = None
            for d_key in ["diameter", "diameter_m", "size", "size_m"]:
                if d_key in clean_row:
                    try:
                        diam_val = float(clean_row[d_key])
                        break
                    except ValueError:
                        pass

            if x_val is not None and y_val is not None:
                records.append({"x": x_val, "y": y_val, "diameter_m": diam_val})
    return records


def map_csv_to_cells(
    records: List[Dict[str, float]],
    geotransform: List[float],
    width_px: int,
    height_px: int,
    rows: int,
    cols: int,
) -> Tuple[np.ndarray, List[float]]:
    """
    Map point coordinates into row, col bins using image geotransform.
    x_geo = gt[0] + x_px * gt[1]
    y_geo = gt[3] + y_px * gt[5]
    """
    gt_x0, px_w, _, gt_y0, _, px_h = geotransform
    cell_w_px = width_px / cols
    cell_h_px = height_px / rows

    ref_counts = np.zeros((rows, cols), dtype=float)
    ref_diameters: List[float] = []

    for rec in records:
        x_geo = rec["x"]
        y_geo = rec["y"]
        x_px = (x_geo - gt_x0) / px_w
        y_px = (y_geo - gt_y0) / px_h

        if 0 <= x_px < width_px and 0 <= y_px < height_px:
            c = min(int(x_px // cell_w_px), cols - 1)
            r = min(int(y_px // cell_h_px), rows - 1)
            ref_counts[r, c] += 1.0
            if rec.get("diameter_m") is not None:
                ref_diameters.append(rec["diameter_m"])

    return ref_counts, ref_diameters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare LunaSafe hazard grid with published global boulder map."
    )
    parser.add_argument("--hazard-grid", required=True, type=Path, help="Path to hazard_grid.json")
    parser.add_argument("--reference", required=True, type=Path, help="Path to reference CSV or .npy raster")
    parser.add_argument("--ref-type", choices=["csv", "raster"], default=None, help="Type of reference file")
    parser.add_argument(
        "--config",
        type=Path,
        default=SCRIPT_DIR / "comparison_config.json",
        help="Path to comparison criteria configuration JSON",
    )
    parser.add_argument("--ref-resolution-m", type=float, default=None, help="Reference map resolution in metres")
    parser.add_argument(
        "--out",
        type=Path,
        default=BACKEND_DIR / "results" / "comparison" / "comparison_report.json",
        help="Output JSON path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.hazard_grid.exists():
        print(f"Error: Hazard grid file not found: {args.hazard_grid}", file=sys.stderr)
        return 1
    if not args.reference.exists():
        print(f"Error: Reference file not found: {args.reference}", file=sys.stderr)
        return 1

    # Load comparison config
    if args.config.exists():
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {
            "min_cells_required": 8,
            "spearman_correlation_threshold": 0.60,
            "count_ratio_bounds": [0.5, 2.0],
            "bootstrap_ci": 0.90,
            "bootstrap_reps": 1000,
            "bootstrap_seed": 42,
            "size_bins_m": [
                {"name": "small", "min_m": 0.0, "max_m": 2.0},
                {"name": "medium", "min_m": 2.0, "max_m": 5.0},
                {"name": "large", "min_m": 5.0, "max_m": None},
            ],
        }

    grid_data = load_hazard_grid(args.hazard_grid)
    image_info = grid_data.get("image", {})
    geotransform = image_info.get("geotransform")

    # STRICT REQUIREMENT: "If no georeference exists, stop with a clear error; do not guess coordinates."
    if not geotransform or len(geotransform) < 6:
        print(
            "ERROR: ImageInfo lacks georeference (geotransform is None or invalid). "
            "Cannot map global reference data without valid georeferencing. "
            "Coordinate guessing is strictly prohibited.",
            file=sys.stderr,
        )
        return 1

    rows = grid_data.get("rows", 8)
    cols = grid_data.get("cols", 8)
    width_px = image_info.get("width", 1024)
    height_px = image_info.get("height", 1024)
    pixel_scale_m = image_info.get("pixel_scale_m", 1.0)
    is_mock = grid_data.get("is_mock", False)

    cells = grid_data.get("hazard_cells") or grid_data.get("cells") or []
    if not cells:
        print("Error: Hazard grid contains no cells.", file=sys.stderr)
        return 1

    pipeline_densities = np.zeros((rows, cols), dtype=float)
    pipeline_counts = np.zeros((rows, cols), dtype=float)
    for c in cells:
        r = c["row"]
        col = c["col"]
        # Use corrected count if available, otherwise raw
        cnt = c.get("corrected_boulder_count") or c.get("corrected_count") or c.get("raw_boulder_count", 0.0)
        dens = c.get("rho_h_per_m2") or c.get("density") or 0.0
        pipeline_counts[r, col] = float(cnt)
        pipeline_densities[r, col] = float(dens)

    # Determine reference type
    ref_type = args.ref_type
    if not ref_type:
        ext = args.reference.suffix.lower()
        if ext in (".csv", ".txt"):
            ref_type = "csv"
        elif ext in (".npy", ".npz", ".tif", ".tiff"):
            ref_type = "raster"
        else:
            ref_type = "csv"

    ref_diameters: List[float] = []

    if ref_type == "csv":
        ref_records = load_reference_csv(args.reference)
        ref_counts, ref_diameters = map_csv_to_cells(
            ref_records, geotransform, width_px, height_px, rows, cols
        )
        # Compute cell area to get reference density
        cell_area_m2 = (width_px * pixel_scale_m / cols) * (height_px * pixel_scale_m / rows)
        ref_densities = ref_counts / cell_area_m2
    else:
        # Raster reference
        ref_arr = np.load(args.reference, allow_pickle=False)
        if ref_arr.shape == (rows, cols):
            ref_densities = ref_arr.astype(float)
            ref_counts = ref_arr.astype(float)
        else:
            # Block-reduce
            r_factor = ref_arr.shape[0] // rows
            c_factor = ref_arr.shape[1] // cols
            if r_factor >= 1 and c_factor >= 1:
                trimmed = ref_arr[: rows * r_factor, : cols * c_factor]
                reshaped = trimmed.reshape(rows, r_factor, cols, c_factor)
                ref_densities = reshaped.mean(axis=(1, 3))
                ref_counts = reshaped.sum(axis=(1, 3))
            else:
                print(f"Error: Reference raster shape {ref_arr.shape} is incompatible with grid ({rows}, {cols})", file=sys.stderr)
                return 1

    # Flatten for correlation
    p_flat = pipeline_densities.flatten()
    r_flat = ref_densities.flatten()
    n_cells = len(p_flat)

    # Compute Spearman rank correlation with bootstrap CI
    r_s = spearman_rank_correlation(p_flat, r_flat)
    ci_low, ci_high = bootstrap_spearman_ci(
        p_flat,
        r_flat,
        n_boot=cfg.get("bootstrap_reps", 1000),
        ci=cfg.get("bootstrap_ci", 0.90),
        seed=cfg.get("bootstrap_seed", 42),
    )

    tot_pipeline = float(np.sum(pipeline_counts))
    tot_ref = float(np.sum(ref_counts))
    count_ratio = float(tot_pipeline / tot_ref) if tot_ref > 0 else (1.0 if tot_pipeline == 0 else float("inf"))

    # Size-bin comparison (where reference diameters exist)
    size_bin_results = []
    if ref_diameters:
        bins_cfg = cfg.get("size_bins_m", [])
        for b in bins_cfg:
            b_name = b["name"]
            min_m = b["min_m"]
            max_m = b["max_m"]
            ref_in_bin = sum(
                1 for d in ref_diameters
                if d >= min_m and (max_m is None or d < max_m)
            )
            size_bin_results.append({
                "bin_name": b_name,
                "min_m": min_m,
                "max_m": max_m,
                "reference_count": ref_in_bin,
            })

    # Resolution mismatch limitation note
    res_ref = args.ref_resolution_m if args.ref_resolution_m is not None else "unspecified"
    res_mismatch_warning = (
        f"Resolution mismatch: Reference dataset resolution ({res_ref} m) differs from "
        f"optical image resolution ({pixel_scale_m:.2f} m/px). Sub-resolution boulders in the "
        f"global map cannot be matched one-to-one with high-resolution optical detections."
    )

    # Evaluation against placeholders
    criteria_corr = cfg.get("spearman_correlation_threshold", 0.60)
    corr_met = bool(r_s >= criteria_corr)
    ratio_bounds = cfg.get("count_ratio_bounds", [0.5, 2.0])
    ratio_met = bool(ratio_bounds[0] <= count_ratio <= ratio_bounds[1])

    report = {
        "is_mock": is_mock,
        "n_cells_compared": n_cells,
        "spearman_rank_correlation": round(r_s, 4),
        "spearman_bootstrap_ci_90": [round(ci_low, 4), round(ci_high, 4)],
        "pipeline_total_boulders": round(tot_pipeline, 2),
        "reference_total_boulders": round(tot_ref, 2),
        "total_count_ratio": round(count_ratio, 4),
        "per_size_bin_comparison": size_bin_results,
        "resolution_comparison": {
            "imagery_gsd_m": pixel_scale_m,
            "reference_resolution_m": res_ref,
            "limitation": res_mismatch_warning,
        },
        "evaluation_against_placeholders": {
            "correlation_threshold": criteria_corr,
            "correlation_met": corr_met,
            "count_ratio_bounds": ratio_bounds,
            "count_ratio_met": ratio_met,
            "note": "Evaluation criteria are PLACEHOLDERS from Member 4 protocol.",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[SUCCESS] Global map comparison finished. Report: {args.out}")
    print(f"  Compared cells: {n_cells}")
    print(f"  Spearman r_s: {r_s:.4f} (90% CI: [{ci_low:.4f}, {ci_high:.4f}])")
    print(f"  Total count ratio: {count_ratio:.4f} (pipeline: {tot_pipeline:.1f}, ref: {tot_ref:.1f})")
    print(f"  [LIMITATION] {res_mismatch_warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
