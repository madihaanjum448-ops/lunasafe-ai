# Backend architecture

```
Image ──► /api/upload ──► metadata.py ──► ImageInfo (+warnings; nulls where unknown)
Member 1 detections ─┐
shadow lengths (opt) ┤
                     ├► measurement.py ──► measurements.json
ImageInfo ───────────┘            │
recall.json (opt) ────────────────┤
slope grid (opt, from slope.py) ──┴► hazard.py ──► hazard_grid.json ──► frontend
```
Routes only parse requests; all logic is in `app/services/`.

## Rules the code follows
1. **No invented values.** Missing pixel scale / sun elevation / projection stay `null` and produce warnings.
2. **Height from shadow:** `height = shadow_length_m × tan(sun_elevation)`; uncertainty = ±1 px shadow error × tan(e). Sun-angle error is *not* included (stated in output warnings).
3. **Fallback:** if shadow length or sun elevation is missing, height = diameter × 0.5 — a labelled **assumption** (`method: diameter_fallback`, `confidence: low`). The 0.5 ratio is NOT a verified value (`FALLBACK_HEIGHT_TO_DIAMETER_RATIO` in `measurement.py`). If pixel scale is missing nothing is computed (`method: unavailable`).
4. **Hazard (per grid cell):** `P = 1 − exp(−ρ_h · A)`, `ρ_h` = hazardous boulders ÷ cell area (m²), `A = π(d/2)²` for the lander footprint. A boulder counts as hazardous if height ≥ `hazard_height_threshold_m`. Optional recall correction counts each hazardous boulder as `1/recall(size bin)`.
5. **Slope gate is separate.** Slope never alters `p_hazard`. Rules: gate `fail` → Unsafe; else `p ≥ unsafe_p_hazard` → Unsafe; `p ≥ caution_p_hazard` → Caution; else Safe candidate. **A cell cannot be a Safe candidate if slope was not assessed** (downgraded to Caution, reason `downgraded_slope_not_assessed`).
6. Every cell carries `explanation`, `reasons` (machine-readable) and `missing_inputs`.
7. The frontend field `score` is kept but equals `p_hazard` (a probability, not a weighted score).

## Contracts (full models in `app/schemas/contracts.py`; examples in `samples/`)
Units: px, metres, degrees, boulders/m² unless stated. `null` = unknown. New fields are optional so the current frontend still works.

| File | Producer | Key fields |
|---|---|---|
| `detections.json` | Member 1 | `image{id,width,height,pixel_scale_m?,sun_elevation_deg?,projection?}`, `detections[{id, bbox[x1,y1,x2,y2], confidence 0–1, size_m?}]`, `is_mock` |
| `recall.json` | Member 1 / 4 | `bins[{min_diameter_m, max_diameter_m?, recall 0–1, n_ground_truth?}]`, `validation_site`, `is_mock` |
| `measurements.json` | Member 2 | per detection: `diameter_m`, `diameter_uncertainty_m`, `height_m`, `height_uncertainty_m`, `method`, `confidence`, `is_hazardous`, `warnings` |
| `hazard_grid.json` | Member 2 | `rows, cols, lander_footprint_*`, `hazard_cells[{row,col,score,p_hazard,interval_low,interval_high,class,label,raw_count,corrected_count,hazardous_boulder_count,largest_boulder_m,largest_height_m,largest_height_method,density,rho_h_per_m2,slope_deg,slope_gate,explanation,reasons,missing_inputs,warnings}]`, `warnings`, `disclaimer` |
| `config.json` | Member 2 | grid size, footprint diameter, hazard height, slope gate, class thresholds, recall switch, recall_floor, sun-elevation limits, bootstrap_n, bootstrap_ci, bootstrap_seed, slope_margin_deg, use_interval_upper_bound, slope_statistic |

`class` values: `safe` ("Safe candidate"), `caution`, `unsafe` ("Unsafe candidate").
`density` is hazardous boulders per **100 m²** (what the frontend label says); `rho_h_per_m2` is the raw value.

## Day 5 Statistical Pipeline & Uncertainty Intervals

### 1. Footprint Hazard Probability (FR-05)
$$P(\text{hazard}) = 1 - \exp(-\rho_h \cdot A)$$
- $A = \pi (d_{\text{footprint}} / 2)^2$ (e.g. $78.54\text{ m}^2$ for $d = 10\text{ m}$).
- $\rho_h = k_{\text{corr}} / A_{\text{cell}}$, where $A_{\text{cell}}$ is in $\text{m}^2$ derived from `pixel_scale_m`.
- Bounding boxes cut by the image edge are clipped to image boundaries with a warning count, rather than dropped.

### 2. Recall Correction (FR-06)
- Boulder weight $w_i = \min(1 / \text{recall}(\text{bin}_i), 1 / \text{recall\_floor})$.
- Default `recall_floor = 0.2` prevents weight explosion in low-recall bins.
- Bins missing or with recall 0 leave boulders uncorrected ($w_i = 1.0$) with an explicit warning.
- Raw count and corrected count are both reported in each `HazardCell`.

### 3. Bootstrap Uncertainty Interval & Parametric Fallback
- For cells with $\ge 5$ detections:
  1. For each replicate $b \in [1, B]$: draw height $\tilde{h}_i \sim \mathcal{N}(h_i, \sigma_{h,i}^2)$ for shadow-measured detections and evaluate $\tilde{h}_i \ge \text{threshold}$.
  2. Resample the cell's detections with replacement.
  3. Apply size-dependent recall weights.
  4. Compute $\tilde{\rho}_h$ and $\tilde{P}_b = 1 - \exp(-\tilde{\rho}_h \cdot A)$.
  5. Calculate empirical percentile interval $[P_{\alpha/2}, P_{1-\alpha/2}]$ (default 90% CI with $B=1000$ replicates, seed 42).
- **Low-count parametric Poisson fallback (< 5 detections):**
  - *Problem:* Bootstrapping 0–4 detections with replacement collapses into degenerate or misleadingly narrow intervals (e.g., drawing from 1 detection produces identical counts with zero variance, falsely claiming high certainty).
  - *Solution:* For cells with $< 5$ detections, we sample count $k \sim \text{Poisson}(\lambda = k_{\text{corr}})$ across replicates.
  - *PRD Confirmation Notice:* **This parametric Poisson fallback is flagged for team confirmation against PRD v2.0 Section 6.**
- Guarantee: `interval_low <= p_hazard <= interval_high` is enforced.
- If boulder heights are fallback assumptions only (no shadow geometry), the interval is set to `null` and flagged in `missing_inputs`.

## Day 5 outputs for Member 3/4

### For Member 3 (Frontend Integration)
- `HazardCell` fields now ready for the detail/explanation drawer:
  - `interval_low` & `interval_high`: Float bounds for the 90% hazard probability CI (e.g., `0.0111 [0.0, 0.0248]`).
  - `largest_height_method`: `"shadow_geometry"` | `"diameter_fallback"` | `"none"`.
  - `largest_height_m`: Height of the tallest boulder in the cell (or null if unassessed).
  - `raw_count`: Raw detected boulder count in the cell.
  - `corrected_count`: Recall-weighted boulder count.
  - `warnings`: Array of cell-specific caveats (e.g., parametric Poisson sampling notice).

### For Member 4 (Presentation & Slide Formulas)
- **Probability model:** Spatial Poisson point process of hazardous obstacles intersecting lander circular footprint:
  $$P(\text{collision}) = 1 - e^{-\rho_h A}$$
- **Recall adjustment:** Corrects for observational detection bias:
  $$\rho_h = \frac{1}{A_{\text{cell}}} \sum_{i \in \text{haz}} \min\left(\frac{1}{R(d_i)}, \frac{1}{R_{\text{floor}}}\right)$$
- **Monte Carlo / Bootstrap confidence:**
  Joint propagation of shadow measurement uncertainty ($\sigma_h \approx \pm 1\text{ px} \cdot \tan\theta$) and spatial shot noise via $B=1000$ vectorised replicates under 0.1 s.

## Day 6 Classification & End-to-End Pipeline (FR-07, FR-08, Gate 3)

### 1. Classification Engine (`app/services/classification.py`)
Classification logic is extracted into a pure, testable function `classify_cell(...)` following strict precedence:
1. `slope_gate == "fail"` $\to$ **Unsafe candidate** (`"slope_gate_failed"`). Absolute hard-stop: overrides $P = 0$.
2. $P(\text{hazard}) \ge \text{unsafe\_p\_hazard}$ ($30\%$) $\to$ **Unsafe candidate** (`"p_hazard_at_or_above_unsafe_threshold"`).
3. $P(\text{hazard}) \ge \text{caution\_p\_hazard}$ ($10\%$) $\to$ **Caution candidate** (`"p_hazard_at_or_above_caution_threshold"`).
4. Otherwise $\to$ provisional **Safe candidate** (`"p_hazard_below_caution_threshold"`).
5. **Mandatory Safety Downgrades** on provisional Safe candidates:
   - `slope_gate == "not_assessed"` $\to$ **Caution** (`"downgraded_slope_not_assessed"`). A cell lacking slope data can never be certified as Safe.
   - `unknown_height_count > 0` $\to$ **Caution** (`"downgraded_height_unknown"`).
   - `fallback_in_cell is True` $\to$ **Caution** (`"downgraded_fallback_height"`). Provisional height assumptions cannot certify a Safe touchdown zone.
   - `slope_margin_deg > 0.0`: A passing cell whose slope is within the configured margin of the gate ($\text{slope} > \text{gate} - \text{margin}$) is downgraded to **Caution** (`"slope_within_margin_of_gate"`). Default is `0.0` (off).
   - `use_interval_upper_bound is True`: A Safe candidate whose 90% CI upper bound $\ge \text{unsafe\_p\_hazard}$ is downgraded to **Caution** (`"interval_reaches_unsafe_threshold"`). Default is `False` (off).

**Boundary Rules:**
- $P$ exactly equal to a threshold falls in the higher risk category ($P = 0.30 \implies \text{Unsafe}$; $P = 0.10 \implies \text{Caution}$).
- Slope exactly equal to the slope gate passes ($\text{slope} \le \text{slope\_gate\_deg}$).

**Configuration Validation:**
- In `AnalysisConfig`: `caution_p_hazard < unsafe_p_hazard` is strictly enforced via a Pydantic `model_validator`. Any request specifying $\text{caution} \ge \text{unsafe}$ or out-of-range probabilities is rejected with HTTP 422.

### 2. Slope Layer and Gate (FR-07)
- Slope is purely a separate gate and is never used to alter $P(\text{hazard})$.
- The DEM slope grid is calculated with the exact same rows $\times$ cols as `AnalysisConfig` to ensure spatial alignment.
- Aggregation statistic: supports `"max"` (conservative default) or `"mean"` via `AnalysisConfig.slope_statistic`.
- When no DEM is supplied, `slope_gate` evaluates to `"not_assessed"` across all cells, forcing all otherwise-safe cells into `Caution` with grid-level warnings.

### 3. End-to-End Pipeline Endpoint (`POST /api/pipeline`)
Provides a single unified multipart entry point:
- Optical image file upload (`image`).
- Optional metadata overrides (`pixel_scale_m`, `sun_elevation_deg`, `projection`).
- Bounding-box detections JSON (as string or file).
- Optional shadow lengths JSON, recall curve JSON, config JSON.
- Optional DEM elevation raster (`.npy`) and `dem_cell_size_m`.
- Response model (`PipelineResponse`):
  `image`, `detections` (with physical `size_m` filled), `measurements`, `hazard_cells` (with probabilities, intervals, classifications, and rule-based explanations), `warnings`, `disclaimer`, `is_mock`.

### 4. Day 6 / Gate 3 Status
- **Gate 3 Criteria:** One image runs through the full pipeline from upload to hazard map with probability, bootstrap interval, slope gate (or explicit missing marker), and rule-based explanations.
- **Verification Status:** **PASS** (demonstrated across 51 automated tests).
- **Honest Provenance & Limitations:**
  - Demonstrated end-to-end on synthetic images, mock detector outputs, and synthetic DEM rasters (`is_mock: True`).
  - Real LROC NAC optical images and high-resolution stereo DEMs have not yet been downloaded or coregistered.
  - Thresholds ($0.5\text{ m}$ height, $10.0^\circ$ slope gate, $10\% / 30\%$ class boundaries) remain engineering working defaults / placeholders awaiting PRD v2.0 sign-off from Member 4.

## Day 7 Additions

### 1. Height Estimation with Propagated Uncertainty (FR-04)
- **Analytical Uncertainty Propagation:**
  $$\sigma_h^2 = (\tan(e) \cdot \sigma_L)^2 + (L \cdot \sec^2(e) \cdot \sigma_{e,\text{rad}})^2$$
  where $L = \text{shadow\_length\_m} = s_{\text{px}} \cdot \text{pixel\_scale\_m}$, $e = \text{sun\_elevation\_rad}$, $\sigma_L = \text{pixel\_uncertainty\_px} \cdot \text{pixel\_scale\_m}$, and $\sigma_{e,\text{rad}} = \text{radians}(\sigma_e)$.
  Controlled by `AnalysisConfig.sun_elevation_uncertainty_deg` (default 0.0 deg for backward compatibility; unconfirmed proposal).
  When $\sigma_e = 0$, the formula simplifies identically to the previous $\sigma_h = \tan(e) \sigma_L$.
- **Shadow Quality Assessment (`ShadowQuality`):**
  - `"good"`: standard shadow geometry confidence (high if detection confidence $\ge 0.8$ and Sun elevation reliable).
  - `"fair"`: confidence capped at `medium` (cannot be `high`).
  - `"poor"`: height cannot establish confirmed hazard status (`is_hazardous = None`, confidence `low`). Treated as an unmeasured/unknown height in `hazard.py` (excluded from raw and corrected hazardous boulder counts, triggers caution downgrade).
- **Ground-Truth Height Reference Validation:**
  - Optional `reference_heights_m` dictionary by detection ID in `measure_detections` and `MeasureRequest`.
  - Computes Mean Absolute Error ($MAE$) and Bias ($h_{\text{est}} - h_{\text{ref}}$) across matching measured detections.
  - Stamps `height_validated = True` with `reference_count = n`, `height_mae_m`, and `height_bias_m`.
  - When reference heights are missing, `height_validated = False` and explicitly warns: *"Heights are unvalidated: no reference height set."*

### 2. Known-Site Execution Pipeline (`scripts/run_known_site.py`)
- CLI runner that ingests image, detections, optional shadows, shadow quality, recall curve, DEM, and configuration.
- Calls identical backend services as `POST /api/pipeline` without logic duplication.
- Enforces strict mock refusal: if `detections.is_mock == True`, refuses to run unless `--allow-mock` is explicitly supplied.
- Produces 4 audit-trail files in `--out`:
  1. `measurements.json`: serialized `MeasurementsFile` with uncertainties and quality flags.
  2. `hazard_grid.json`: serialized `HazardGridFile` with cell probabilities, intervals, and classifications.
  3. `summary.json`: summary statistics (class counts, exclusion reasons, methods, slope status, warnings).
  4. `run_manifest.json`: reproducibility manifest with git commit hash, SHA-256 hashes of all input files, config used, seed, UTC timestamp, mock flag, and unconfirmed PRD placeholders.

### 3. Global Boulder Map Comparison (`scripts/compare_global_map.py`)
- Compares pipeline hazard grid against published global boulder reference data.
- Supports two input formats:
  - Point CSV (`lon, lat` or `x, y`, `diameter`).
  - Density raster (`.npy` array or GeoTIFF).
- Enforces strict georeferencing: uses image `geotransform` and CRS from `ImageInfo`. If geotransform is missing, refuses to guess coordinates and exits with a clear error.
- Computes:
  - Spearman rank correlation ($r_s$) across grid cells with bootstrap confidence interval (deterministic seed).
  - Total count ratio ($\sum k_{\text{pipeline}} / \sum k_{\text{ref}}$).
  - Per-size-bin comparison against reference diameters.
  - Warns of spatial resolution mismatch between global product and high-resolution optical imagery.
- Uses configurable criteria in `scripts/comparison_config.json` with clearly marked placeholders.

### 4. Parameter Sensitivity Analysis (`scripts/sensitivity.py`)
- Sweeps three primary pipeline variables:
  1. Lander footprint diameter ($6, 8, 10, 12, 15\text{ m}$)
  2. Hazard height threshold ($0.3, 0.4, 0.5, 0.6, 0.8\text{ m}$)
  3. Detector recall scaling factor ($\times 0.70, \times 0.85, \times 1.0, \times 1.15, \times 1.30$, capped at 1.0)
- Outputs `results/sensitivity/sensitivity.csv` and `sensitivity.json` with manifest metadata.
- Guarantees:
  - Baseline row matches default pipeline execution.
  - Larger footprint diameter mathematically never lowers $P(\text{hazard})$ for any cell ($\frac{\partial P}{\partial A} \ge 0$).

## How to Reproduce a Run

```powershell
# 1. Run known-site pipeline with synthetic fixtures
python backend/scripts/run_known_site.py `
  --image backend/tests/fixtures/known_site/image.png `
  --detections backend/tests/fixtures/known_site/detections_mock.json `
  --shadows backend/tests/fixtures/known_site/shadows.json `
  --quality backend/tests/fixtures/known_site/quality.json `
  --dem backend/tests/fixtures/known_site/dem.npy `
  --dem-cell-size 2.5 `
  --recall backend/tests/fixtures/known_site/recall.json `
  --pixel-scale 0.5 `
  --sun-elevation 30.0 `
  --allow-mock `
  --out backend/results/known_site

# 2. Compare against reference boulder map
python backend/scripts/compare_global_map.py `
  --hazard-grid backend/tests/fixtures/comparison/hazard_grid_geo.json `
  --reference backend/tests/fixtures/comparison/reference_boulders.csv `
  --ref-resolution-m 5.0 `
  --out backend/results/comparison/report.json

# 3. Run parameter sensitivity sweep
python backend/scripts/sensitivity.py `
  --image backend/tests/fixtures/known_site/image.png `
  --detections backend/tests/fixtures/known_site/detections_mock.json `
  --shadows backend/tests/fixtures/known_site/shadows.json `
  --quality backend/tests/fixtures/known_site/quality.json `
  --dem backend/tests/fixtures/known_site/dem.npy `
  --dem-cell-size 2.5 `
  --recall backend/tests/fixtures/known_site/recall.json `
  --pixel-scale 0.5 `
  --sun-elevation 30.0 `
  --allow-mock `
  --out-dir backend/results/sensitivity
```

## Known limits
- Shadow *measurement* (finding shadow length in the image) is not implemented; the API takes `shadow_lengths_px` as input. Someone must supply it (Member 1's model or a later step).
- Flat-ground assumption in the shadow formula; local slope makes heights wrong. Uncertainty does not cover this.
- Boulder ↔ cell assignment uses the bbox centre. Cells smaller than the lander footprint trigger a warning.
- DEM alignment is assumed, not computed (see `DEM_RESEARCH.md`).
- Global boulder map comparison requires projected/geographic geotransform on the target image.
