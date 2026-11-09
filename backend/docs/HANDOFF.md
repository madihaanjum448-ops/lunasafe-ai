# Handoff – Member 2 (Backend / Geospatial)

## Important caveats
- **PRD v2.0, the Work Division doc and the Innovation Gap doc were not in the upload** (only `lunasafe-ai-main.zip`). Scope followed your written brief. "Day 1 / Day 2" below are mapped from the responsibilities you listed, not from the work-division text. Please compare against the PRD and fix any mismatch.
- **PLACEHOLDER values (not from the PRD):** lander footprint 10 m, hazardous height 0.5 m, slope gate 10°, caution/unsafe P(hazard) thresholds 10% / 30%, fallback height = 0.5 × diameter, 8×8 default grid.
- Tests were run on Linux with Python 3.12 (**26 passed**) and a live `uvicorn` smoke test (health, analyze, CORS preflight) was done. The Windows commands were **not run on Windows**.
- No real lunar data was used. Samples are synthetic and marked `is_mock`.

## Status
**Day 1 (foundation, upload, contracts)**
- [x] FastAPI app, routes/services/schemas/config, CORS, `/api/health`, validation + error handling
- [x] Upload validation (PNG/JPEG/TIFF/WEBP, <=50 MB, <=8192x8192, empty/corrupt), metadata extraction (GeoTIFF scale/CRS where present; user-supplied scale/sun/projection), warnings instead of invented values
- [x] Five documented contracts + mock samples (`samples/`)

**Day 2 (measurement, hazard, DEM)**
- [x] Diameter from pixel scale; height from shadow geometry with uncertainty; labelled low-confidence fallback
- [x] Poisson footprint hazard, separate slope gate, explanations, optional recall correction
- [x] Horn slope + per-cell reduction (unit-tested only on synthetic DEMs)
- [x] DEM / site research written up (`DEM_RESEARCH.md`) - nothing downloaded
- [ ] Final site selection, georeferenced DEM alignment, real-data validation

## Frontend facts worth telling Member 3
- The existing frontend only reads `image`, `detections`, `hazard_cells`, `warnings`; `/api/analyze` returns those plus extras.
- Its mock data is internally inconsistent: with `pixel_scale_m = 0.5` the mock bboxes (about 45-70 px) imply 22-35 m objects, but `size_m` says 1-5 m. Real data will not match the mock numbers.
- Mock `score` was an arbitrary number; the backend's `score` is now the Poisson probability.
- Metadata warning texts in `constants/metadata.js` match the backend's wording.

## Still depends on others
**Member 1:** real `detections.json` (bbox px, confidence) for cropped images; `recall.json`; ideally shadow lengths per boulder (`shadow_lengths_px`) or a shadow-segmentation step; confirm bbox format `[x1,y1,x2,y2]`.
**Member 3:** wire `client.js` into `MissionContext`; show `hazard_cells[].explanation/reasons/missing_inputs`, `p_hazard`, slope gate, `disclaimer`; label `is_mock` results; handle API errors; crop/tile tool for NAC images larger than 8192 px.
**Member 4:** choose the site and boulder ground truth; produce the real recall table; confirm PRD thresholds; decide a slope-uncertainty margin rule; validate heights/slopes against references.
**Team / PRD check:** footprint size, hazard height, slope gate, class thresholds, grid size; whether sun-angle uncertainty must enter height error.
