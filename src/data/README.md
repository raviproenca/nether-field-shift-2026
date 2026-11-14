<!-- AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi) -->
# `src/data`: NASA data toolkit

Download and clip NASA data to a region. It is infrastructure: it does not choose a variable or a use case for the team.

```bash
source .venv/bin/activate          # after the setup in the root README (requirements-dev.txt)
python -m src.data <source> [region] --start YYYY-MM-DD --end YYYY-MM-DD --variable NAME [--out PATH]
```

Sources: `power`, `gldas`, `imerg`, `smap`, `modis`, `viirs`, `hls` (NASA) and `planetary` (Sentinel-2, ESA/Copernicus, **not NASA**).

## Region

| Flag | Meaning |
|---|---|
| (none) | Preset `sergipe` (-38.25,-11.57,-36.39,-9.51) |
| `--bbox sergipe` / `--bbox nordeste` | Presets (`nordeste` = -48.8,-18.4,-34.7,-1.0) |
| `--bbox W,S,E,N` | Free box in degrees, validated (W<E, S<N, lon within 180, lat within 90) |
| `--point LAT,LON --radius-km N` | Square box of half-side N km around a point: lat deg = km/111.32, lon deg = km/(111.32·cos(lat)) |
| `--point LAT,LON` (POWER only) | POWER is a point API, so the point is used as is and no radius is needed |

`--bbox` and `--point` are mutually exclusive. Negative values work without quotes (`--point -10.91,-37.07`). `--radius-km` is required with `--point` for every source except `power`.

If the box is smaller than one cell of a GLDAS, IMERG or SMAP grid (e.g. `--radius-km 1` on GLDAS's 0.25° grid), the cell nearest to the box center is used and a `warning:` line is printed. A box outside the grid is still an error.

## Examples

```bash
# POWER daily series for Aracaju (no login). Variables are POWER parameter names.
python -m src.data power --point -10.91,-37.07 --start 2025-01-01 --end 2025-12-31 \
  --variable T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN --out data/sample/power_aracaju_2025.csv

# How many granules exist? (no login, no download)
python -m src.data gldas --search-only --start 2025-01-01 --end 2025-01-31
python -m src.data hls --short-name HLSS30 --search-only --point -10.91,-37.07 --radius-km 5 --start 2025-01-01 --end 2025-01-31

# Sentinel-2 L2A, 10 m, from the Microsoft Planetary Computer (no account, no key)
python -m src.data planetary --search-only --start 2025-01-01 --end 2025-01-31
python -m src.data planetary --variable B04 --point -10.91,-37.07 --radius-km 2 --start 2025-01-01 --end 2025-01-31 --max-cloud 20

# Needs Earthdata Login (run scripts/earthdata-login.sh once)
python -m src.data gldas --variable SoilMoi0_10cm_inst --start 2025-01-01 --end 2025-01-31
python -m src.data imerg --variable precipitation --start 2025-01-01 --end 2025-01-31 --out data/processed/rain.parquet
python -m src.data smap  --variable Soil_Moisture_Retrieval_Data_AM/soil_moisture --start 2025-01-01 --end 2025-01-31   # PM group: Soil_Moisture_Retrieval_Data_PM/soil_moisture_pm
python -m src.data modis --variable NDVI --start 2025-01-01 --end 2025-03-31          # one GeoTIFF per tile in data/processed/modis/
python -m src.data hls   --variable B04 --point -10.91,-37.07 --radius-km 2 --start 2025-01-01 --end 2025-01-31
```

`--variable` is always yours to choose: a POWER parameter list, a variable name inside the file, `group/variable` for SMAP, a band name for HLS (`B04`, `B8A`, `Fmask`) or a substring of the dataset name for MODIS/VIIRS (`NDVI`, `EVI`). `--short-name` and `--version` override the defaults below. Each source pins a default version (GLDAS 2.1, IMERG 07, SMAP 006, MOD13Q1 061, VNP13A1 002, HLS 2.0); it is used only with the default short_name, so pass `--version` yourself when you change `--short-name` to a product with another version scheme. For MODIS/VIIRS the text must match exactly one dataset in the tile (an exact name wins; otherwise an error lists the candidates).

## Where files go

| Folder | Content | Git |
|---|---|---|
| `data/raw/<source>/` | Downloaded granules (`--raw-dir`) | ignored |
| `data/cache/power/` | Cached POWER API responses (`--cache-dir`) | ignored |
| `data/processed/` | Clipped output (CSV, Parquet, GeoTIFF) | ignored |
| `data/sample/` | Small hand-picked samples (e.g. `power_aracaju_2025.csv`) | versioned |

Output of POWER, GLDAS, IMERG and SMAP is a table (`.csv` or `.parquet`; GLDAS/IMERG/SMAP long format `time, lat, lon, <variable>`). MODIS, VIIRS and HLS write one GeoTIFF per granule into the folder given by `--out` (default `data/processed/<source>/`). `--out` is checked before anything is searched or downloaded: `.csv` or `.parquet` for table sources, a folder for GeoTIFF sources. Use `--refresh` to ignore the POWER cache and `--download` to fetch whole GLDAS/IMERG files instead of lazy reads. Use `--keep-out-of-range` to keep GLDAS/IMERG/SMAP values outside the variable's declared valid range (see the SMAP note below).

## What needs login

| Source | Login | How it is read |
|---|---|---|
| `power` | No | Public API; the point itself, or the center of a box. The regional endpoint needs at least a 2-degree range, so a box becomes its center point. Timeout 60 s, 3 attempts, `-999` becomes NaN |
| `gldas`, `imerg` | Earthdata Login | `earthaccess.open` (HTTPS range reads); only the box bytes are transferred. Hyrax OPeNDAP was not used (see note) |
| `smap` | Earthdata Login | Full `.h5` downloaded, clipped locally with its 2-D lat/lon arrays |
| `modis` | Earthdata Login | HDF4 tile downloaded, read with `pyhdf`, clipped locally |
| `viirs` | Earthdata Login | HDF5 tile downloaded, clipped locally |
| `planetary` | No | STAC search (`pystac-client`), URLs signed by `planetary-computer`; only the box window of the cloud-optimized GeoTIFF is read over HTTP |
| `hls` | Earthdata Login | Only the requested band GeoTIFF is downloaded, clipped locally |

Granule **search** never needs login. Without `~/.netrc` the download commands stop with `run scripts/earthdata-login.sh first`.

> **Errors:** network, auth (HTTP 401/403), file and format failures while opening, downloading or reading data are reported as one `error:` line (HTTP status or error class plus a short text, never credentials or signed URLs), not as a traceback.

> **Tested with real files (2026-11-14):** SMAP, MODIS, VIIRS and HLS were downloaded and clipped for Sergipe; GLDAS and IMERG downloads have not been run yet. Notes from that run:
>
> - **SMAP** stores `-9999` in its 2-D `latitude`/`longitude` without declaring it. These holes are ignored; EASE-Grid 2.0 is clipped through its per-row latitudes and per-column longitudes. Values outside the variable's `valid_min`/`valid_max` (0.02-0.5 for soil moisture) are dropped by default, with one `warning: dropped N values outside valid_min/valid_max (0.02-0.5)` on stderr; fill values are always dropped. The real file has retrievals above 0.5 that are not fill: on 2025-01-10, 4.4% of the valid values over the Nordeste preset (544 of 12,340, up to 0.60) and 6.5% worldwide (up to 0.92). Pass `--keep-out-of-range` to keep them. A day can have no valid soil moisture over a small box (SMAP revisits every 2-3 days, so swaths leave gaps): the command then stops with a clear error (exit code 2) instead of writing an empty file. The PM group names its datasets with a `_pm` suffix (`Soil_Moisture_Retrieval_Data_PM/soil_moisture_pm`).
> - **MODIS (HDF4)** `scale_factor` above 1 (NDVI/EVI use 10000) means `(raw - add_offset) / scale_factor`; a factor of 1 or less (e.g. LST 0.02) and all **VIIRS (HDF5)** files use the CF rule `raw * scale_factor + add_offset`. Fill values (VIIRS has two) and `valid_range` are masked before scaling. 
> - **Output nodata per source:** MODIS and VIIRS GeoTIFFs are float64 with NaN as nodata (values already scaled); HLS GeoTIFFs keep the original int16 with nodata -9999 (reflectance scale factor 0.0001 not applied); SMAP, GLDAS and IMERG are tables, where empty cells are simply dropped.
> - OPeNDAP via Hyrax would need `pydap` or `.dodsrc` setup that cannot be validated here, so GLDAS/IMERG use lazy HTTPS reads instead.

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
| `planetary` | `sentinel-2-l2a` (Copernicus, not NASA) | 10 m (B02, B03, B04, B08), 20 m, 60 m | 2026-11-10 (point box) / 2026-11-12 (Sergipe box) |

Granules returned for Sergipe in 2025-01-01..2025-01-31: GLDAS 248, IMERG 31, SMAP 31, MODIS 6, VIIRS 12, HLSL30 61, HLSS30 72. Sentinel-2 L2A (Planetary Computer, same box and period): 11 items with cloud < 20%, 63 with any cloud.

### Choices worth knowing

- **IMERG default is the Late run.** The Final run (`GPM_3IMERGDF`) ends on 2025-09-30 in CMR, so any 2026 request would be empty. Late has about one day of latency. Pass `--short-name GPM_3IMERGDF` for 2025 and earlier if you prefer the gauge-adjusted Final run.
- **MODIS is not discontinued and has no gaps.** Between 2025-01 and 2026-10 `MOD13Q1` has a composite every 16 days on both tiles covering Sergipe (h14v09, h14v10), with no gap. Terra and Aqua are far beyond their design life, though, so VIIRS is the continuity record.
- **MODIS or VIIRS?** Use `MOD13Q1` (250 m) when field-scale detail matters and the period is covered: it is the finest of the two. Use `VNP13A1` (500 m, new composite every 8 days, latest date 8 days newer) when you need the freshest data, denser time sampling, or a record that will keep going. `--short-name MYD13Q1` gives Aqua, offset by 8 days.
- **HLS is the only product near plot scale (30 m).** HLSL30 is Landsat, HLSS30 is Sentinel-2; use both for a 2-3 day revisit. Reflectance bands have a 0.0001 scale factor that the output does not apply (nodata `-9999` becomes NaN); multiply by 0.0001 yourself. MODIS/VIIRS output applies fill values and `scale_factor` when the file declares them.

### `planetary` (Sentinel-2)

- Flags: `--collection` (default `sentinel-2-l2a`), `--max-cloud N` (default 20, query `eo:cloud_cover < N`; use `--max-cloud 100` for collections without cloud cover), `--variable` = asset name (`B04`, `B08`, `SCL`, `visual`). `--search-only` prints the item count in the period and the newest item over the box (any cloud, sorted by datetime descending).
- Size guard: before reading, the window is estimated (box in meters / asset resolution, capped by the tile size). Above `--max-pixels` (default 25 million per band and item) the command stops and asks for a smaller `--point/--radius-km`. A 2 km radius at 10 m is about 0.16 million pixels.
- Output: one GeoTIFF per item in `data/processed/planetary/` (`<item id>_<asset>.tif`), in the item's UTM CRS. The lat/lon box is reprojected before clipping and only that window is downloaded. Reflectance values are raw digital numbers (scale 0.0001; products after processing baseline 04.00 also carry an offset of -0.1, see the item's `raster:bands`). Keep boxes small: a 10 m raster of a whole state is huge.
- Real test (2026-11-14): `--point -10.91,-37.07 --radius-km 2`, `B04`, January 2025, cloud < 20% gave 2 items and two 404 x 401 pixel uint16 GeoTIFFs (EPSG:32724, 10 m, about 317 KiB each).
- Sentinel-2 is ESA/Copernicus data: credit "Contains modified Copernicus Sentinel data [year]". Use `hls` for the NASA 30 m alternative.

### IBGE SIDRA (Produção Agrícola Municipal), third-party data

Not NASA data. `python -m src.data.sidra` downloads any SIDRA table for all municipalities of one UF (default Sergipe, code 28) through the public API, no login. The table, variable and product codes are yours to choose (see [docs/research/brazil-data-sources.md](../../docs/research/brazil-data-sources.md)).

```bash
python -m src.data.sidra --table 5457 --variable 8331,216,214,112,215 --classification 782 \
  --categories 40112,40119,40122 --period "last 1" --out data/processed/pam_sergipe.csv
```

Output is a tidy CSV/Parquet (one row per municipality, variable, year and category) with `value` as a number (`-` becomes 0, `X`, `..` and `...` become NaN) and the raw text in `symbol`. One call may return at most 100,000 values; the connector stops with a clear error above that. Raw answers are cached in `data/cache/sidra/` (`--refresh` ignores the cache). The IBGE licence was not verified (see the research note): credit "Fonte: IBGE, Pesquisa Agrícola Municipal".
