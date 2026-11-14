<!-- AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi) -->
# `apps/api`: data API (contract)

A small read-only HTTP API over the NASA data toolkit in [`src/data`](../../src/data/README.md): ask for a **source**, a **point**, a **radius** and a **period**, get a JSON time series back. It is an internal tool for looking at the data on a map; it does not decide the product.

**Status: contract only.** This folder has the specification and mock responses. The FastAPI implementation (issue #16) comes in a second PR and must follow [`openapi.yaml`](openapi.yaml).

## Files

| File | What |
|---|---|
| [`openapi.yaml`](openapi.yaml) | OpenAPI 3.1 contract: `GET /health`, `GET /sources`, `GET /timeseries`, error format, limits, CORS |
| [`examples/health.json`](examples/health.json) | `GET /health` |
| [`examples/sources.json`](examples/sources.json) | `GET /sources`: the eight sources, with variables, units and limits |
| [`examples/timeseries_power_aracaju.json`](examples/timeseries_power_aracaju.json) | POWER, 3 variables, Aracaju, 30 days. Real values from `data/sample/power_aracaju_2025.csv` |
| [`examples/timeseries_imerg.json`](examples/timeseries_imerg.json) | IMERG daily precipitation, 10 km box. Real values (cell mean from the toolkit's output) |
| [`examples/timeseries_smap.json`](examples/timeseries_smap.json) | SMAP soil moisture with `null` gap days. **Illustrative values** (no SMAP file was downloaded for the whole month), realistic shape |
| [`examples/error_422.json`](examples/error_422.json) | The error body (`no_data`) |

## Using the mocks (front end)

Every example is valid against the matching schema in `openapi.yaml`, so you can import it as is:

```ts
import sources from "../../api/examples/sources.json";
import power from "../../api/examples/timeseries_power_aracaju.json";
```

Or serve them statically and point the app at that URL while the real API does not exist. Things the UI must handle, all present in the examples: `null` values (gaps), `warnings`, `cells_used`/`cells_valid`, `attribution` (always show it), `nasa: false` for Sentinel-2 (never call it NASA data) and the error body `{"error": {"code", "message"}}`.

## Main decisions

- **Aggregation:** `cell_mean` (mean of the grid cells in the box), `nearest_cell` (box smaller than a cell, `radius_km=0`, or POWER, which is a point API), `window_mean` (raster sources).
- **Raster sources** (MODIS, VIIRS, HLS, Sentinel-2) are accepted by `/timeseries` and return the **window mean per acquisition date**; no pixels. Dates with no valid pixel are `null`; no date at all gives `422 no_data`. Radius is capped at 10 km for HLS and Sentinel-2.
- **Limits:** `lat` -89..89, `lon` -180..180, `radius_km` 0..50, and a maximum period per source (`max_period_days`: 366 POWER and IMERG, 31 GLDAS and SMAP, 183 MODIS and VIIRS, 92 HLS and Sentinel-2).
- **Errors:** `400 invalid_parameter`, `404 unknown_source`, `422 no_data`, `502 upstream_error`, `504 upstream_timeout`, plus `503 server_not_configured` (Earthdata credentials missing on the server) and `500 internal_error`. Always JSON.
- **CORS:** allowed origins come from `API_CORS_ORIGINS` (comma-separated); default `http://localhost:5173`.
- **No login on the API.** Earthdata credentials stay on the server (`~/.netrc`), never in a request, response or the repo.

## Validate the contract

No dependency is added to the project. The spec is checked with a throwaway tool, and each example was validated against its schema in `components.schemas` with `jsonschema` (draft 2020-12, formats enforced):

```bash
uvx openapi-spec-validator apps/api/openapi.yaml
```
