# Handover & Audit Summary – Member 2 (Backend / Geospatial)

## Test Environment Verification Note
- **Environment**: Windows 11 (win32), Python 3.15.1, pytest 9.2.0, pluggy 1.7.0.
- **Verification execution**: Virtual environment created at `backend/.venv`, all dependencies from `requirements.txt` installed.
- **Real test suite result**: **51 passed, 1 warning in 1.09s**.
  - All 26 original unit and integration tests passed.
  - 7 edge-case and hardening tests (float bboxes, grid dilution warnings, helper, slope mismatch, boundary centers, zero recall bins, NaN/inf inputs) passed.
  - 8 Day 5 tests covering recall correction caps, largest height method, edge-clipped bboxes, Poisson hand-computations, zero-boulder bootstrap, fallback uncertainty intervals, CI reproducibility & bracketing, and 64-cell performance (<0.1s) passed.
  - 10 new Day 6 tests covering classification truth tables, threshold boundary rules, downgrade reasons, optional slope margin & interval upper-bound proposals, Pydantic threshold validator (caution < unsafe), end-to-end multipart pipeline execution with/without DEM and sun angle, and 4xx error handling passed.

---

## 1. Plan Verification Audit Table

| Day | Item | Status | Evidence |
|---|---|---|---|
| **Day 1** | FastAPI skeleton runs (`uvicorn app.main:app`), `/api/health` and `/docs` accessible | **PASS** | `app/main.py:12-45`, `app/routes/api.py:32-35`. Verified live with uvicorn test: `/api/health` returned HTTP 200 `{"status":"ok","app":"LunaSafe AI Backend","version":"0.1.0"}` and `/docs` returned HTTP 200 (length 1018). |
| **Day 1** | Five JSON contracts exist with valid samples in `samples/` | **PASS** | `app/schemas/contracts.py`: `DetectionsFile` (L85), `RecallFile` (L116), `MeasurementsFile` (L148), `HazardGridFile` (L236), `AnalysisConfig` (L279). All sample files in `samples/` (`detections.json`, `recall.json`, `measurements.json`, `hazard_grid.json`, `config.json`, `analyze_request.json`, `analyze_response.json`) validated against Pydantic models. |
| **Day 1** | CORS configured for Vite dev server (`http://localhost:5173`, `http://127.0.0.1:5173`) | **PASS** | `app/core/config.py:13,27-28`, `app/main.py:21-26`. Preflight options tested and confirmed in `tests/test_api.py:23-32` (`test_cors_allows_vite_origin`). |
| **Day 2** | Metadata extraction & validation (pixel scale, sun elevation, projection) | **PASS** | `app/services/metadata.py:170-330,479-572`. GeoTIFF projected CRS tags parsed; user overrides validated; out-of-range sun elevations (>80° or <5°) flagged with warnings. |
| **Day 2** | Missing metadata remains `None` with explicit warnings (never invented) | **PASS** | `app/services/metadata.py:574-617`, `app/routes/api.py:57-64`. Tested in `tests/test_api.py:35-50` (`test_upload_png_without_metadata_warns_and_does_not_invent`). |
| **Day 2** | Image file integrity checks (empty, corrupt, unsupported formats, size/pixel limits) | **PASS** | `app/services/metadata.py:378-466`. Rejects empty (HTTP 400), corrupt (HTTP 400), non-PNG/JPEG/TIFF/WEBP (HTTP 415), >50 MB (HTTP 413), >8192x8192 px (HTTP 422). Tested in `tests/test_api.py:58-106`. |
| **Day 2** | DEM research & global-map coverage | **PARTIAL** | Documented in `docs/DEM_RESEARCH.md:1-56`. Unconfirmed: no real lunar DEMs downloaded; no landing site finalized; automated georeferenced DEM-to-image alignment not implemented; Horn slope algorithm tested only on synthetic numpy arrays; slope uncertainty margin rule (1.5–2.5° RMS error) not implemented; LROC NAC tile/crop not implemented. |
| **Day 3** | Pixel-to-metre conversion and diameter from longer bbox side | **PASS** | `app/services/measurement.py:39-68` (`diameter_from_bbox`: `side_px = max(x2 - x1, y2 - y1)`, `diameter_m = side_px * scale`). Tested in `tests/test_api.py:168-182`. |
| **Day 3** | Analysis grid assignment | **PASS** | `app/services/hazard.py:272-277`. Bounding box centers mapped to grid cells via `min(int(center / cell_px), dim - 1)`. Tested in `tests/test_api.py:228-273`. |
| **Day 3** | Unit tests on mock detections | **PASS** | `tests/test_api.py:210-387` and `tests/conftest.py:21-25` (`MOCK_IMAGE`). Detections marked `is_mock` remain synthetic and are never described as ML predictions. |
| **Day 4** | Height from shadow geometry ($h = s_m \cdot \tan\theta$) with hand-computed values | **PASS** | `app/services/measurement.py:71-122` (`height_from_shadow`). Tested in `tests/test_api.py:133-146` (`test_shadow_height_math`). Independent scratch script recomputation matches expected values. |
| **Day 4** | Fallback height ($0.5 \times \text{diameter}$) labelled low confidence, excluded from confirmed hazard counts | **PASS** | `app/services/measurement.py:305-328` (method `diameter_fallback`, confidence `low`, `is_hazardous = None`). `app/services/hazard.py:350-358` skips fallback from `raw_hazardous` and adds explanatory warnings. Tested in `tests/test_api.py:149-182`. |

---

## 2. Independent Hand Recomputation (Scratch Script)

Script path: `<brain>/scratch/recompute.py`

### Formula:
$$\text{Lander footprint Area } A_{fp} = \pi \left(\frac{d_{fp}}{2}\right)^2 = \pi \times 5^2 \approx 78.5398\text{ m}^2$$
$$\rho_h = \frac{k}{A_{cell}} = \frac{k}{100\text{ m}^2}$$
$$P(\text{hazard}) = 1 - \exp(-\rho_h \cdot A_{fp}) = 1 - \exp\left(-\frac{k \cdot \pi}{4}\right)$$

### Execution Output:
```text
=== Independent Hand Recomputation: Poisson P(hazard) ===
Parameters: cell_area = 100 m^2, lander footprint diameter = 10 m
k = 0 boulders: rho = 0.0000/m^2, A_fp = 78.5398 m^2 -> P = 0.0000 (raw: 0.000000)
k = 2 boulders: rho = 0.0200/m^2, A_fp = 78.5398 m^2 -> P = 0.7921 (raw: 0.792120)
k = 4 boulders: rho = 0.0400/m^2, A_fp = 78.5398 m^2 -> P = 0.9568 (raw: 0.956786)

=== Independent Hand Recomputation: Shadow Height ===
Inputs: shadow = 10.0 px, scale = 0.5 m/px, sun_elevation = 30.0 deg
shadow_m = 5.00 m, tan(30.0 deg) = 0.577350
height = 2.8868 m (+/- 0.2887 m)
```
Matches expected theoretical values: $0$, $0.7921$, and $0.9568$.

---

## 3. Issues Fixed and Commit Log

1. **`588300e` fix: accept float bboxes**
   - Changed `Detection.bbox` from `List[int]` to `List[float]` in `app/schemas/contracts.py`.
   - Updated `diameter_from_bbox` type hint in `app/services/measurement.py`.
   - Verified that `hazard.py` cell assignment calculations seamlessly handle float coordinates.
   - Added `test_detection_accepts_float_bboxes` in `tests/test_api.py`.

2. **`48b449b` feat: grid-size and slope-grid warnings**
   - Added warning in `app/services/hazard.py` when grid cell area $> 10 \times$ lander footprint area ($A_{cell} > 10 \cdot A_{fp}$) to alert against probability dilution.
   - Implemented and exposed `suggest_grid_dimensions(image_width, image_height, pixel_scale_m, footprint_diameter_m)` helper in `app/services/hazard.py`.
   - Added dimension check in `app/services/hazard.py` that raises a warning if `slope_by_cell` dimensions differ from $(rows \times cols)$.
   - Added `test_grid_cell_large_area_warning_and_helper` and `test_slope_grid_dimension_mismatch_warning` in `tests/test_api.py`.

3. **`1060d70` test: edge cases**
   - Added `test_detection_outside_image_bounds`: verifies out-of-bound bboxes are safely excluded with warnings and 0 hazard count.
   - Added `test_detection_on_cell_boundary`: verifies bboxes centered exactly on cell boundaries assign cleanly without index errors.
   - Added `test_recall_bin_edges_and_zero_bin`: tests lower-inclusive and upper-exclusive bin boundaries and ensures `recall=0.0` bins fall back to uncorrected count $1.0$ without division-by-zero errors.
   - Added `test_nan_inf_inputs_raise_or_handled`: verifies scientific functions raise `ValueError` on NaN/inf and API gracefully marks invalid slope values.

4. **`2a24111` chore: repo hygiene**
   - Added `pytest_results.txt` to `backend/.gitignore` to prevent committing absolute local paths.
   - Moved `create_dem.py` to `backend/scripts/create_dem.py` and updated output path.
   - Moved `test_dem.npy` to `backend/tests/fixtures/test_dem.npy`.
   - Confirmed no `.env`, `uploads/`, personal paths, or tokens are staged or tracked.

5. **`docs: verification report`**
   - Updated `backend/HANDOVER.md` with complete verification audit, real test results, and PR metadata.
   - Maintained original `backend/docs/HANDOFF.md`.

---

## 4. Day 5 Implementation & Verification Log
Branch: `member2/day5-footprint-recall-interval`

1. **`c07470a` feat(hazard): footprint probability audit and edge clipping**
   - Explicitly derived and validated density area in $\text{m}^2$ from `pixel_scale_m`.
   - Handled bounding boxes cut by image edges: coordinates are clipped to image boundaries with warnings incremented rather than dropping the detections.
   - Verified monotonicity in density $\rho$ and footprint area $A$, probability bounds within $[0, 1]$, and hand-computed Poisson probabilities for $k \in \{0, 1, 2, 4\}$.

2. **`f3dbc8d` feat(recall): recall weighting cap and largest height method**
   - Implemented recall bins $[min, max)$ with `None` max indicating $+\infty$.
   - Prevented division-by-zero for bins with recall 0 or missing; boulders remain uncorrected with explicit warnings.
   - Added `recall_floor = 0.2` cap in `AnalysisConfig` to bound weights to $\le 5.0$, adding grid warnings when the floor triggers.
   - Added `largest_height_method` (`shadow_geometry` / `diameter_fallback` / `none`) to `HazardCell` for frontend explanation card.

3. **`41faacb` feat(interval): bootstrap uncertainty interval**
   - Added `bootstrap_n` (1000), `bootstrap_ci` (0.90), `bootstrap_seed` (42) to `AnalysisConfig`.
   - Vectorised NumPy Monte Carlo resampling evaluating height perturbation $\sim \mathcal{N}(h, \sigma_h^2)$ and detection resampling with replacement.
   - For cells with $< 5$ detections, implemented parametric Poisson($\lambda = k_{\text{corr}}$) resampling to prevent bootstrap interval collapse (flagged for team confirmation against PRD v2.0 Section 6).
   - If heights are fallback-only, uncertainty interval returns `None` with explanatory `missing_inputs`.
   - 64 cells evaluated in $< 0.1\text{ s}$ (far below 2 s requirement).

---

## 5. Day 6 Implementation & Gate 3 Log
Branch: `member2/day6-classification-pipeline`

1. **`13d3263` refactor(classification): extract classify_cell and explain_cell**
   - Extracted cell classification into pure, stateless functions in `app/services/classification.py`.
   - Preserved strict precedence: (1) slope gate fail -> Unsafe hard-stop; (2) P >= unsafe -> Unsafe; (3) P >= caution -> Caution; (4) Safe candidate; (5) Safe downgraded to Caution if slope not assessed, height unknown, or height provisional fallback.
   - Refactored `hazard.py` to use `classification.py` and evaluate bootstrap intervals prior to classification.

2. **`f8a1746` feat(config): configurable classification thresholds, slope margin, and validator**
   - Added Pydantic `model_validator` on `AnalysisConfig` enforcing `caution_p_hazard < unsafe_p_hazard` (both in $[0, 1]$) returning HTTP 422 if violated.
   - Added optional proposal fields: `slope_margin_deg` (default 0.0) and `use_interval_upper_bound` (default False).
   - Added `slope_statistic` supporting `"max"` (conservative default) and `"mean"`.

3. **`6824e1d` feat(pipeline): end-to-end multipart pipeline endpoint with honest missing inputs**
   - Implemented `POST /api/pipeline` taking multipart image, metadata overrides, detections (file or string), optional shadows, recall, config, and optional DEM raster (.npy).
   - Returns complete `PipelineResponse` with image metadata, measured detections (`size_m`), measurements, hazard cells, aggregated warnings, disclaimer, and `is_mock` flag.
   - Implemented honest missing input handling: missing sun angle -> fallback heights excluded from hazard counts; missing DEM -> slope not assessed, no safe cells; missing pixel scale -> HTTP 422; mismatched shadow detection IDs -> HTTP 422.

4. **`36bec69` test(day6): classification truth table, threshold validation, and end-to-end pipeline tests**
   - 10 new tests in `tests/test_day6.py` covering all classification paths, boundary values, proposals, threshold validator, and pipeline multipart flows.

---

## 6. Unconfirmed Placeholders vs PRD v2.0
The following values remain placeholders in `app/core/config.py` and `app/schemas/contracts.py` as PRD v2.0 was not provided:
- **Lander footprint diameter**: `10.0 m` (`lander_footprint_diameter_m`)
- **Hazardous boulder height threshold**: `0.5 m` (`hazard_boulder_height_m`)
- **Slope gate angle**: `10.0 deg` (`slope_gate_deg`)
- **Caution / Unsafe P(hazard) class thresholds**: `10%` (`0.10`) / `30%` (`0.30`)
- **Fallback height-to-diameter ratio**: `0.5` (`FALLBACK_HEIGHT_TO_DIAMETER_RATIO` in `app/services/measurement.py`)
- **Default grid resolution**: `8x8` (`grid_rows`, `grid_cols`)
- **Recall floor cap**: `0.2` (`recall_floor` in `app/schemas/contracts.py`)
- **Parametric Poisson fallback for < 5 detections**: Flagged for team confirmation against PRD v2.0 Section 6.
- **Slope margin and interval upper bound**: Proposals flagged for team review.

---

## 7. Dependencies Blocked on Other Members
- **Blocked on Member 1 (ML / Detection)**:
  - Real boulder detection model weights (YOLOv8-seg).
  - Detector output format `[x1, y1, x2, y2]` with confidence scores for cropped lunar images.
  - Empirical validation recall table (`recall.json`). (All outputs remain `is_mock: True` / `recall: placeholder` until received).
  - Optical shadow segmentation to generate `shadow_lengths_px` without user manual input.
- **Blocked on Member 4 (Scientific Validation / PRD v2.0)**:
  - Formal sign-off on PRD v2.0 threshold values ($0.5\text{ m}$ height, $10.0^\circ$ slope gate, $10\% / 30\%$ class boundaries).
  - Lunar landing site selection coordinates and real LROC/LOLA DEM data products.
