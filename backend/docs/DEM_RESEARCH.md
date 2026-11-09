# Lunar site and DEM research (Day 2)

**How to read this file.** Section 1 = findings taken from sources I actually retrieved (listed at the end).
Section 2 = my inferences. Section 3 = decisions still open. **No dataset was downloaded** and
**no slope result here has been validated** – the backend sandbox could not reach these data hosts, and
nothing was run on real lunar data.

## 1. Verified findings (from retrieved sources)

**LOLA 5 m/pixel south-pole DEMs**
- The LOLA PDS node (MIT, imbrium.mit.edu) hosts adjusted 5 m/px LOLA DEMs of many south-pole regions of interest, with slope maps and error maps, plus a larger 5 m/px DEM covering 87–90°S.
- NASA PGDA `LOLA_5mpp` provides, per candidate site, 5 m/pix GeoTIFFs in south-polar stereographic X/Y metres (MOON_ME frame, DE421): `*_surf.tif` (height), `*_ldec.tif` (LOLA return count), `*_toterr.tif` (height uncertainty), `*_slp.tif` (slope, degrees), `*_slperr.tif` (slope uncertainty). The page lists Site01 "Connecting ridge" and Site04 "Shackleton rim"; the Barker et al. paper covers Sites 1, 4, 7 and 11.
- Quoted uncertainty for these improved models: height RMS about 0.30–0.50 m and **slope RMS about 1.5–2.5°** (Barker et al. 2021 abstract, Planetary & Space Science, doi:10.1016/j.pss.2020.105119).
- At 5 m/pix only about 10% of pixels near the pole contain a LOLA measurement; the rest are interpolated. A laser spot footprint is about 5 m, so 5 m/pix is the practical minimum.

**Global LOLA/Kaguya product**
- SLDEM2015 (LOLA + Kaguya Terrain Camera) is a global map with better than 60 m/pixel resolution; slope and azimuth maps derived from it are also archived on the LOLA PDS node.

**LROC NAC imagery (the likely input image)**
- NAC scale is 0.5 m/pixel at 50 km altitude; NAC-based map products span roughly 0.5–2.0 m/px.
- A single NAC product is about 5,000 samples wide and up to 52,224 lines (104,448 in summed mode). **This exceeds the frontend/backend 8192×8192 limit, so images must be cropped or tiled before upload.**
- PDS/LROC product labels list resolution, **incidence angle**, emission angle, phase angle, sub-solar azimuth and corner latitudes/longitudes. This is where pixel scale and sun angle should be read from.
- Polar NAC images are binned for light level; one USGS report quotes 1.0–1.3 m resolution for the polar images it used.

**NAC-stereo DEMs at non-polar sites**
- DLR/TUB publish NAC-stereo DEMs and ortho-images for landing sites; the Apollo 17 DEM is 1.5 m/pixel, tied to LOLA heights, with stated forward-intersection accuracy of ±0.8 to ±3.6 m.

## 2. Inferences (mine, not verified in a source)
- Incidence angle is measured from the local vertical, so on flat ground **sun elevation ≈ 90° − incidence**. The backend stores this as `incidence_angle_deg` only when the user supplies the sun elevation; it never derives elevation silently.
- A slope uncertainty of 1.5–2.5° is large against a gate near 10°. Slopes within about 2.5° of the gate should be treated as uncertain (a "margin" rule is **not implemented**).
- 5 m DEM cells are smaller than a ~10 m lander footprint, so per-cell *maximum* slope (`slope_by_grid_cell`, default `max`) is the conservative reduction.
- Using LOLA GeoTIFFs with an NAC image requires reprojecting/aligning them to the image. That needs GDAL/rasterio, which is **not** in `requirements.txt`.

## 3. Pending decisions
| Item | Status |
|---|---|
| Final site | **Not decided.** Needs PRD / Member 4. Proposed for discussion: LOLA Site 01 (south pole) because DEM, slope and slope-error files are all documented; fallback idea: a non-polar site with an NAC-stereo DEM (e.g. Apollo 17). |
| Boulder ground truth at the chosen site | Not researched. |
| Exact LROC NAC product IDs for the site | Not selected. |
| Slope gate threshold (placeholder 10°) | Must come from the PRD. |
| Georeferenced DEM alignment | Not implemented. |

## 4. Slope feasibility and fallback
- **Feasible** for the south-pole sites: slope maps already exist (`*_slp.tif`), so the pipeline needs only alignment + per-cell reduction. For a site with only a height DEM, `app/services/slope.py` computes Horn slope (unit-tested on a flat plane and a 45° ramp only).
- **Implemented fallback:** with no DEM, `slope_gate = "not_assessed"` and **no cell may be called a Safe candidate** (downgraded to Caution, with a warning). Slope can also be provided manually as a rows×cols grid.

## Sources retrieved
- LOLA PDS Data Node: https://imbrium.mit.edu/
- PGDA LOLA 5 m/pix README: https://core2.gsfc.nasa.gov/PGDA/LOLA_5mpp/README and https://core2.gsfc.nasa.gov/PGDA/LOLA_5mpp
- Barker et al. 2021 (NTRS): https://ntrs.nasa.gov/citations/20205009660
- Barker, SIW22 abstract (fill factor / artifacts): https://seal.ae.gatech.edu/sites/default/files/2022-10/SIW22-23.pdf
- LROC CDR NAC product description (ODE): https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/LROC/CDR/CDRNAC.htm
- LROC product label examples: https://data.lroc.im-ldi.com/lroc/view_lroc/LRO-L-LROC-2-EDR-V1.0/M157275053LE
- LROC NAC ROI mosaics: https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_ROI_HUMBOLT_LOA
- DLR/TUB LROC site DEMs: https://europlanet.dlr.de/LROC/index.html
- USGS V&V report on NAC south-pole DEM: astrogeology.usgs.gov (usgs_vv_report_nlsi_lunar_south_pole_20130412.pdf)
