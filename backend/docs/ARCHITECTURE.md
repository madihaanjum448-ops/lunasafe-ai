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
| `config.json` | Member 2 | grid size, footprint diameter, hazard height, slope gate, class thresholds, recall switch, recall_floor, sun-elevation limits, bootstrap_n, bootstrap_ci, bootstrap_seed |

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

## Known limits
- Shadow *measurement* (finding shadow length in the image) is not implemented; the API takes `shadow_lengths_px` as input. Someone must supply it (Member 1's model or a later step).
- Flat-ground assumption in the shadow formula; local slope makes heights wrong. Uncertainty does not cover this.
- Boulder ↔ cell assignment uses the bbox centre. Cells smaller than the lander footprint trigger a warning.
- DEM alignment is assumed, not computed (see `DEM_RESEARCH.md`).
