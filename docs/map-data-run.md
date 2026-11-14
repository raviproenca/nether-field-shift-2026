<!-- AI-assisted: generated with Antigravity (Gemini 3.8 Flash), reviewed by Ignição & Periélio -->
# Map Data Snapshot Run (#18)

This document records the data provenance, coverage, gaps, validation results, and reproducibility for the static map snapshot files published in `apps/web/public/data/`.

## 1. Overview and Manifest

- **Generation Timestamp**: `2026-11-14T18:48:13Z` (`index.json` format_version: 1)
- **Total Payload Size**: 2,382,791 bytes (2.38 MB; 2.27 MiB), strictly below the 5.0 MB maximum budget.
- **Regions**:
  - `sergipe`: 55 land grid points (SE001–SE061, with gaps, 0.25° grid, water points masked by GLDAS land model) + 2 pilot sites = 57 points total.
  - `nordeste`: 196 land grid points (NE001–NE248, with gaps, 1.0° grid, water points masked by GLDAS land model).
- **Pilot Sites (Sergipe)**:
  - `sergipe_agreste_itabaiana`: [-37.425, -10.685], radius 5.0 km, Agreste zone.
  - `sergipe_semiarido_ns_gloria`: [-37.420, -10.218], radius 5.0 km, Semiárido zone.

### File List

| Path | Format | Size (bytes) | Description |
|---|---|---|---|
| `apps/web/public/data/index.json` | JSON | 5,728 | Manifest, metadata, attributions, file pointers, warnings |
| `apps/web/public/data/sergipe/points.geojson` | GeoJSON | 7,839 | 55 grid point coordinates and IDs |
| `apps/web/public/data/sergipe/pilots.geojson` | GeoJSON | 590 | 2 pilot sites with metadata |
| `apps/web/public/data/sergipe/gldas.json` | JSON | 37,527 | GLDAS monthly series (57 points, 6 months) |
| `apps/web/public/data/sergipe/srtm.json` | JSON | 4,845 | NASADEM elevation & slope (57 points) |
| `apps/web/public/data/sergipe/power.json` | JSON | 296,498 | NASA POWER meteorology & ET0/water balance (57 points, 30 days) |
| `apps/web/public/data/sergipe/imerg.json` | JSON | 91,744 | GPM IMERG Late precipitation (57 points, 30 days) |
| `apps/web/public/data/sergipe/smap.json` | JSON | 86,367 | SMAP morning soil moisture (56 points with data, 28 days) |
| `apps/web/public/data/sergipe/viirs.json` | JSON | 11,550 | VIIRS 16-day NDVI (57 points, 4 composites) |
| `apps/web/public/data/nordeste/points.geojson` | GeoJSON | 27,283 | 196 grid point coordinates and IDs |
| `apps/web/public/data/nordeste/gldas.json` | JSON | 127,348 | GLDAS monthly series (196 points, 6 months) |
| `apps/web/public/data/nordeste/srtm.json` | JSON | 15,065 | NASADEM elevation & slope (196 points) |
| `apps/web/public/data/nordeste/power.json` | JSON | 1,016,330 | NASA POWER meteorology & ET0/water balance (196 points, 30 days) |
| `apps/web/public/data/nordeste/imerg.json` | JSON | 314,650 | GPM IMERG Late precipitation (196 points, 30 days) |
| `apps/web/public/data/nordeste/smap.json` | JSON | 301,004 | SMAP morning soil moisture (196 points, 28 days) |
| `apps/web/public/data/nordeste/viirs.json` | JSON | 38,423 | VIIRS 16-day NDVI (196 points, 4 composites) |

## 2. Source Coverage, Provenance and Latency

| Source ID | Name & Product | Provider | Status | Temporal Range | Latest Date | Aggregation | Variables & Units |
|---|---|---|---|---|---|---|---|
| `gldas` | GLDAS Noah V2.1 (`GLDAS_NOAH025_M`) | NASA GSFC GES DISC | `ok` | 2026-02-01 to 2026-07-01 (6 months) | 2026-07-01 | `cell_mean` (0.25°) | `SoilMoi0_10cm_inst` (kg/m²), `SoilMoi10_40cm_inst` (kg/m²), `Rainf_f_tavg` (mm/day) |
| `srtm` | NASADEM Merged DEM V001 (`NASADEM_HGT`) | NASA JPL / Planetary Computer | `ok` | Static (2000-02) | N/A | `window_mean` (30 m in 5 km radius) | `elevation_m` (m), `slope_mean_deg` (°), `slope_mean_pct` (%) |
| `power` | NASA POWER Daily API (MERRA-2 + CERES SYN1deg) | NASA Langley Research Center | `ok` | 2026-10-09 to 2026-11-07 (30 days) | 2026-11-07 | `nearest_cell` (0.5° x 0.625°) | `T2M`, `T2M_MAX`, `T2M_MIN` (°C), `PRECTOTCORR` (mm/day), `ALLSKY_SFC_SW_DWN` (MJ/m²/day), `GWETROOT` (0-1), derived `ET0_FAO56` (mm/day), derived `WATER_BALANCE` (mm/day) |
| `imerg` | GPM IMERG Late Precipitation L3 V07 (`GPM_3IMERGDL`) | NASA GSFC GES DISC | `ok` | 2026-10-15 to 2026-11-13 (30 days) | 2026-11-13 | `cell_mean` (0.1°) | `precipitation` (mm/day) |
| `smap` | SMAP Enhanced L3 Radiometer 9 km V006 (`SPL3SMP_E`) | NASA NSIDC DAAC | `ok` | 2026-10-13 to 2026-11-12 (28 days) | 2026-11-12 | `cell_mean` (9 km EASE-2) | `soil_moisture` (m³/m³) |
| `viirs` | VIIRS Vegetation Indices 16-Day 500m V002 (`VNP13A1`) | NASA LP DAAC | `ok` | 2026-09-06 to 2026-10-24 (4 composites) | 2026-10-24 | `window_mean` (500 m sinusoidal) | `NDVI` (dimensionless -1..1) |

## 3. Data Integrity & Gaps Analysis

1. **GLDAS Latency**:
   - The newest monthly timestamp in this run is `2026-07-01`; this does not establish a permanent end of the collection. Six monthly timestamps are published.
   - Nordeste has 12 null readings. The exported files alone do not establish the cause of each missing value.
2. **POWER Latency**:
   - The generator deliberately applies a seven-day lag (ends `2026-11-07`); this is not a measurement of the service’s latest available date. There are 171 null scalar values in Sergipe and 618 in Nordeste.
   - Derived `ET0_FAO56` and `WATER_BALANCE` correctly incorporate NASADEM elevation and FAO-56 Penman-Monteith physics.
3. **IMERG**:
   - 100% complete daily series with 0 nulls across all 57 Sergipe and 196 Nordeste points.
4. **SMAP Orbital Gaps**:
   - SMAP has a 2–3 day orbital revisit interval. Days between orbits naturally produce `null` values for points not covered by the swath.
   - The generator masks values outside 0.02–0.50 m³/m³ and fill values. This range filter is not a full retrieval-quality assessment.
   - Sergipe point `SE061` has no valid exported SMAP readings and is omitted from this source. The other 54 grid points and both pilots have 11–15 valid dates each. The files contain 28 distinct dates spanning October 13–November 12; dates empty everywhere are omitted. There are 889 null scalar values in Sergipe and 3,043 in Nordeste. Orbit coverage and the value filter can both contribute; these files do not identify each null’s cause.
5. **VIIRS NDVI**:
   - 4 composites (Sept 6, Sept 22, Oct 8, Oct 24, 2026) fully populated (0 nulls) across all points and pilots.
6. **Pilots Validation**:
   - `sergipe_agreste_itabaiana` and `sergipe_semiarido_ns_gloria` are 100% present across all sources and files.
   - NASADEM terrain: Itabaiana (Agreste) elevation = 181.7 m (slope 2.73° / 4.77%); Nossa Senhora da Glória (Semiárido) elevation = 249.2 m (slope 4.21° / 7.39%).
   - VIIRS NDVI (Oct 24): Itabaiana = 0.387; Glória = 0.313.
7. **Schema & Value Checks**:
   - Strict validation with `Draft202012Validator` against all schemas in `docs/data-format/` passed with 0 errors.
   - No `NaN`, `Infinity`, or non-finite constants present in JSON files.
   - `index.json` records no source failures or fetch warnings (`warnings: []`). This does not imply complete observations, full spatial coverage, or independently verified scientific quality. VIIRS NDVI has no cloud/quality mask, as documented in the format contract.

## 4. Reproducibility

The existing generated WIP was retained after validation; no regeneration or new download was performed during this package. The original invocation log was not retained in this handoff. This equivalent command uses the documented settings and fixes the reference date. Service updates can still change the results, and `generated_at` changes on a new run. Existing caches (`data/cache/`, 5.1 MB) and raw tiles (`data/raw/`, 1.1 GB) were present locally; cache presence alone does not independently certify every measurement. Product IDs, attribution URLs and DOIs are preserved in `index.json` and credited with data-use policies in the repository README.

```bash
source .venv/bin/activate
# Use the existing normal Earthdata configuration; do not inspect credentials.
python -m src.data.snapshots \
  --regions sergipe,nordeste \
  --spacing sergipe=0.25 --spacing nordeste=1 \
  --sources gldas,srtm,power,imerg,smap,viirs \
  --today 2026-11-14 \
  --days 30 \
  --gldas-months 6 \
  --ndvi-days 60 \
  --max-mb 5 \
  --workers 4 \
  --out apps/web/public/data
```

## 5. Potential Risks & Operational Notes

- **Network / Wi-Fi**: The snapshot files require only static HTTP requests to the hosting site. Live basemap and NASA GIBS layers still need their external services; this package does not guarantee offline map operation or zero runtime risk.
- **Payload Budget**: At 2.38 MB (2.27 MiB), the snapshot payload is below the 5 MB package budget. Publication uses the existing Cloudflare Pages workflow. Public deployment and smoke verification remain pending an authorized merge.
- **HLS / S2 / Open-Meteo**: Explicitly excluded per contract and architectural decisions.
