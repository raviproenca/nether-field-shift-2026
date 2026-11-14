<!-- AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi) -->
# `src/data`: NASA data toolkit

Download and clip NASA data to a region. It is infrastructure: it does not choose a variable or a use case for the team.

```bash
source .venv/bin/activate          # after the setup in the root README
python -m src.data <source> [region] --start YYYY-MM-DD --end YYYY-MM-DD --variable NAME [--out PATH]
```

Sources: `power`, `gldas`, `imerg`, `smap`, `modis`, `viirs`, `hls`.

## Region

| Flag | Meaning |
|---|---|
| (none) | Preset `sergipe` (-38.25,-11.57,-36.39,-9.51) |
| `--bbox sergipe` / `--bbox nordeste` | Presets (`nordeste` = -48.8,-18.4,-34.7,-1.0) |
| `--bbox W,S,E,N` | Free box in degrees, validated (W<E, S<N, lon within 180, lat within 90) |
| `--point LAT,LON --radius-km N` | Square box of half-side N km around a point: lat deg = km/111.32, lon deg = km/(111.32·cos(lat)) |

`--bbox` and `--point` are mutually exclusive. Negative values work without quotes (`--point -10.91,-37.07`).

## Examples

```bash
# POWER daily series for Aracaju (no login). Variables are POWER parameter names.
python -m src.data power --point -10.91,-37.07 --radius-km 1 --start 2025-01-01 --end 2025-12-31 \
  --variable T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN --out data/sample/power_aracaju_2025.csv

# How many granules exist? (no login, no download)
python -m src.data gldas --search-only --start 2025-01-01 --end 2025-01-31
python -m src.data hls --short-name HLSS30 --search-only --point -10.91,-37.07 --radius-km 5 --start 2025-01-01 --end 2025-01-31

# Needs Earthdata Login (run scripts/earthdata-login.sh once)
python -m src.data gldas --variable SoilMoi0_10cm_inst --start 2025-01-01 --end 2025-01-31
python -m src.data imerg --variable precipitation --start 2025-01-01 --end 2025-01-31 --out data/processed/rain.parquet
python -m src.data smap  --variable Soil_Moisture_Retrieval_Data_AM/soil_moisture --start 2025-01-01 --end 2025-01-31
python -m src.data modis --variable NDVI --start 2025-01-01 --end 2025-03-31          # one GeoTIFF per tile in data/processed/modis/
python -m src.data hls   --variable B04 --point -10.91,-37.07 --radius-km 2 --start 2025-01-01 --end 2025-01-31
```

`--variable` is always yours to choose: a POWER parameter list, a variable name inside the file, `group/variable` for SMAP, a band name for HLS (`B04`, `B8A`, `Fmask`) or a substring of the dataset name for MODIS/VIIRS (`NDVI`, `EVI`). `--short-name` and `--version` override the defaults below.

## Where files go

| Folder | Content | Git |
|---|---|---|
| `data/raw/<source>/` | Downloaded granules and cached POWER JSON | ignored |
| `data/processed/` | Clipped output (CSV, Parquet, GeoTIFF) | ignored |
| `data/sample/` | Small hand-picked samples (e.g. `power_aracaju_2025.csv`) | versioned |

Output of POWER, GLDAS, IMERG and SMAP is a table (`.csv` or `.parquet`; GLDAS/IMERG/SMAP long format `time, lat, lon, <variable>`). MODIS, VIIRS and HLS write one GeoTIFF per granule into the folder given by `--out` (default `data/processed/<source>/`). Use `--refresh` to ignore the POWER cache and `--download` to fetch whole GLDAS/IMERG files instead of lazy reads.

## What needs login

| Source | Login | How it is read |
|---|---|---|
| `power` | No | Public API, center point of the box. The regional endpoint needs at least a 2-degree range, so a box becomes its center point. Timeout 60 s, 3 attempts, `-999` becomes NaN |
| `gldas`, `imerg` | Earthdata Login | `earthaccess.open` (HTTPS range reads); only the box bytes are transferred. Hyrax OPeNDAP was not used (see note) |
| `smap` | Earthdata Login | Full `.h5` downloaded, clipped locally with its 2-D lat/lon arrays |
| `modis` | Earthdata Login | HDF4 tile downloaded, read with `pyhdf`, clipped locally |
| `viirs` | Earthdata Login | HDF5 tile downloaded, clipped locally |
| `hls` | Earthdata Login | Only the requested band GeoTIFF is downloaded, clipped locally |

Granule **search** never needs login. Without `~/.netrc` the download commands stop with `run scripts/earthdata-login.sh first`.

> **Not exercised against the real services:** the Earthdata download paths (GLDAS, IMERG, SMAP, MODIS, VIIRS, HLS) were not run because there are no credentials in this environment. Search, clipping (synthetic files in `tests/`) and the login error are tested. Expect to fix small details (variable names, SMAP group paths, VIIRS scale attributes) on the first real run. OPeNDAP via Hyrax would need `pydap` or `.dodsrc` setup that cannot be validated without login, so lazy HTTPS reads are used instead.

## Datasets, resolution and latest data (measured 2026-11-14, box = Sergipe preset)

Latest date = start of the most recent granule returned by the CMR search (POWER: last day with a valid value).

| Source | Default short_name (version) | Spatial resolution | Latest available |
|---|---|---|---|
| `power` | daily point API (v2.x) | 0.5° x 0.625° (MERRA-2 meteorology), 1° (CERES SYN1deg solar) | 2026-11-11 |
| `gldas` | `GLDAS_NOAH025_3H` (2.1) | 0.25° (~25 km), 3-hourly | 2026-07-31 |
| `imerg` | `GPM_3IMERGDL` (07, Late run) | 0.1° (~10 km), daily | 2026-11-12 |
| `imerg` (Final) | `GPM_3IMERGDF` (07) | 0.1° (~10 km), daily | 2025-09-30 (collection ended) |
| `smap` | `SPL3SMP_E` (006) | 9 km, daily | 2026-11-12 |
| `modis` | `MOD13Q1` (061) | 250 m, 16-day | 2026-10-16 (composite start) |
| `viirs` | `VNP13A1` (002) | 500 m, 8-day rolling 16-day | 2026-10-24 (composite start) |
| `hls` | `HLSL30` (2.0) | 30 m, Landsat | 2026-11-05 |
| `hls` | `HLSS30` (2.0) | 30 m, Sentinel-2 | 2026-11-05 |

Granules returned for Sergipe in 2025-01-01..2025-01-31: GLDAS 248, IMERG 31, SMAP 31, MODIS 6, VIIRS 12, HLSL30 61, HLSS30 72.

### Choices worth knowing

- **IMERG default is the Late run.** The Final run (`GPM_3IMERGDF`) ends on 2025-09-30 in CMR, so any 2026 request would be empty. Late has about one day of latency. Pass `--short-name GPM_3IMERGDF` for 2025 and earlier if you prefer the gauge-adjusted Final run.
- **MODIS is not discontinued and has no gaps.** Between 2025-01 and 2026-10 `MOD13Q1` has a composite every 16 days on both tiles covering Sergipe (h14v09, h14v10), with no gap. Terra and Aqua are far beyond their design life, though, so VIIRS is the continuity record.
- **MODIS or VIIRS?** Use `MOD13Q1` (250 m) when field-scale detail matters and the period is covered: it is the finest of the two. Use `VNP13A1` (500 m, new composite every 8 days, latest date 8 days newer) when you need the freshest data, denser time sampling, or a record that will keep going. `--short-name MYD13Q1` gives Aqua, offset by 8 days.
- **HLS is the only product near plot scale (30 m).** HLSL30 is Landsat, HLSS30 is Sentinel-2; use both for a 2-3 day revisit. Reflectance bands have a 0.0001 scale factor that the output does not apply (nodata `-9999` becomes NaN); multiply by 0.0001 yourself. MODIS/VIIRS output applies fill values and `scale_factor` when the file declares them.
