<!-- AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi) -->
# Format of the pre-generated data (`apps/web/public/data/`)

The internal map reads **static files**, no API and no login. They are built by
`python -m src.data.snapshots` ([how to run it](../src/data/README.md#snapshots-for-the-internal-map)) and published with
the front end. Do not edit them by hand: run the generator again. Physical values only (units below); no
recommendations or classes.

JSON Schemas of every file are in [`data-format/`](data-format/); the test `tests/test_snapshots.py` validates the
generator output against them. The shape of the series follows the `Timeseries` schema of the API contract
(`feat/ravi-api-contract`, not merged): `time`, `values{VARIABLE: number|null}`, units in `variables`.

## Files

```text
apps/web/public/data/
├── index.json                  # start here: regions, sources, files, warnings
├── sergipe/
│   ├── points.geojson          # grid points on land (id, lat, lon)
│   ├── pilots.geojson          # the two named pilot places
│   ├── power.json              # series per point and pilot
│   ├── gldas.json  imerg.json  smap.json  viirs.json
│   └── srtm.json               # terrain per point and pilot (no time)
└── nordeste/
    ├── points.geojson
    └── power.json  gldas.json  imerg.json  smap.json  viirs.json  srtm.json
```

Load `index.json` first and follow `files` (paths are relative to `index.json`). A source with `status: "failed"`
has no files; the reason is in `warnings`. Everything is UTF-8; numbers are rounded (1 to 3 decimals).

## `index.json` (`index.schema.json`)

| Field | Meaning |
|---|---|
| `format_version` | `1`. Bumped when a field changes meaning |
| `generated_at` | UTC time of the run |
| `regions[]` | `id`, `name`, `bbox [W,S,E,N]`, `spacing_deg` of the grid, `points` (on land), `points_file`, `pilots`, `pilots_file` (or `null`) |
| `sources[]` | `id`, `name`, `provider`, `nasa` (bool), `kind` (`timeseries` or `static`), `status`, `resolution`, `temporal_resolution`, `aggregation`, `variables[{name,long_name,unit}]`, `latest_date`, `period{start,end}`, `attribution{dataset,doi,url,notice}`, `files{region: path}` |
| `warnings[]` | `source`, `code` (`source_failed` or `partial_data`), `message`: read these before trusting a source |

`attribution` must be shown next to the data (the project README lists every dataset with its DOI). `latest_date` is the
newest date the source offered in that run; `period` is what the files contain.

## `<region>/points.geojson` and `pilots.geojson`

GeoJSON `FeatureCollection` of `Point` features, coordinates `[lon, lat]`. Each feature has `id` (the key used in all
other files) and `properties.lat/lon`. Grid ids are `SE001`, `NE001`... (north to south, west to east; the numbers have
gaps where open water points were dropped). Pilots have the id of the place and `name`, `zone`, `state`, `radius_km`.

Grid points stand for the box `lat/lon ± spacing/2` (Sergipe 0.25°, Nordeste 1°); a pilot stands for the square of
half-side `radius_km` (5 km) around it. Only points on land are listed (a point is on land when the GLDAS land model
has a value there). Pilots are always kept.

## `<region>/<source>.json` (`series.schema.json`)

```json
{
  "source": "power",
  "region": "sergipe",
  "variables": [{"name": "T2M", "long_name": "Air temperature at 2 m (daily mean)", "unit": "°C"}],
  "aggregation": "nearest_cell",
  "resolution": "0.5° x 0.625° (MERRA-2), 1° (CERES solar)",
  "period": {"start": "2026-10-09", "end": "2026-11-07"},
  "attribution": {"dataset": "...", "doi": null, "url": "https://power.larc.nasa.gov/", "notice": null},
  "points": {
    "SE001": [{"time": "2026-10-09", "values": {"T2M": 27.4}}, {"time": "2026-10-10", "values": {"T2M": null}}]
  }
}
```

- `points` maps a point or pilot id to its series, ascending by `time`. A point with no valid value at all is absent.
- `values[VARIABLE]` is `null` when there is no valid value at that time (satellite gap, cloud, no coverage).
- Dates where no point has any value are not published, so `period` can be shorter than the requested span.
- `time` is `YYYY-MM-DD`: the day for daily data, the first day of the month for GLDAS monthly, the first day of the
  composite for NDVI.
- `aggregation`: `nearest_cell` (POWER: the model cell that holds the point), `cell_mean` (mean of the valid grid cells
  inside the point's box; the nearest cell if the box is smaller than a cell), `window_mean` (mean of the valid
  pixels inside the box).

## `<region>/srtm.json` (`static.schema.json`)

Same header, but `points` maps an id to `{variable: value}` with no time: `elevation_m`, `slope_mean_deg`,
`slope_mean_pct`, all computed at 30 m inside **5 km of the point** (the box of a pilot; for the 1° grid it describes the
terrain around the point, not the whole cell).

## Sources, variables and units

| Source (`id`) | Variables (unit) | Resolution | Time step | Window of a default run |
|---|---|---|---|---|
| `power` NASA POWER | `T2M`, `T2M_MAX`, `T2M_MIN` (°C), `PRECTOTCORR` (mm/day), `ALLSKY_SFC_SW_DWN` (MJ/m²/day), `GWETROOT` (fraction 0-1), derived `ET0_FAO56` (mm/day), `WATER_BALANCE` (mm/day) | 0.5° x 0.625° (solar 1°) | daily | last 30 days, ending 7 days before the run (POWER latency) |
| `gldas` GLDAS Noah (monthly) | `SoilMoi0_10cm_inst`, `SoilMoi10_40cm_inst` (kg/m² = mm of water), `Rainf_f_tavg` (mm/day, monthly mean) | 0.25° | monthly | last 6 months available (GLDAS 2.1 ends 2026-07) |
| `imerg` GPM IMERG Late | `precipitation` (mm/day) | 0.1° | daily | last 30 days available |
| `smap` SMAP enhanced | `soil_moisture` (m³/m³, 6 a.m. pass; values outside 0.02-0.5 are dropped, as in the toolkit) | 9 km | daily, gaps between orbits | last 30 days available |
| `viirs` VIIRS NDVI | `NDVI` (dimensionless, -1 to 1; no cloud or quality mask) | 500 m | one 16-day composite every 16 days | composites within 60 days of the newest |
| `srtm` NASADEM | `elevation_m` (m), `slope_mean_deg` (°), `slope_mean_pct` (%) | 30 m | static | - |

`ET0_FAO56` is the FAO-56 Penman-Monteith reference evapotranspiration computed per point from the POWER inputs of its
cell (`T2M_MAX`, `T2M_MIN`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN`), the point's latitude and the SRTM elevation.
`WATER_BALANCE = PRECTOTCORR - ET0_FAO56`. Both are `null` where an input is missing. `RH2M` and `WS2M` are used but
not published.

## Size and regeneration

All files together stay under **5 MB** (the generator stops with a clear message otherwise). Change the window, the
regions or the spacing with the generator flags and read the numbers in
[`src/data/README.md`](../src/data/README.md#snapshots-for-the-internal-map).
