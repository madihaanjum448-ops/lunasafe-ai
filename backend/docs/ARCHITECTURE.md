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
| `hazard_grid.json` | Member 2 | `rows, cols, lander_footprint_*`, `hazard_cells[{row,col,score,p_hazard,class,boulder_count,hazardous_boulder_count,largest_boulder_m,density,rho_h_per_m2,slope_deg,slope_gate,explanation,reasons,missing_inputs}]`, `warnings`, `disclaimer` |
| `config.json` | Member 2 | grid size, footprint diameter, hazard height, slope gate, class thresholds, recall switch, sun-elevation limits |

`class` values: `safe` ("Safe candidate"), `caution`, `unsafe` ("Unsafe candidate").
`density` is hazardous boulders per **100 m²** (what the frontend label says); `rho_h_per_m2` is the raw value.

## Known limits
- Shadow *measurement* (finding shadow length in the image) is not implemented; the API takes `shadow_lengths_px` as input. Someone must supply it (Member 1's model or a later step).
- Flat-ground assumption in the shadow formula; local slope makes heights wrong. Uncertainty does not cover this.
- Boulder ↔ cell assignment uses the bbox centre. Cells smaller than the lander footprint trigger a warning.
- DEM alignment is assumed, not computed (see `DEM_RESEARCH.md`).
