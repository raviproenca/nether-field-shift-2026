# Crop Helper · Field Shift: Adapting Farms with NASA Data

**Crop Helper** is Team **Nether**'s decision-support dashboard for the [NASA Space Apps Challenge 2026](https://www.spaceappschallenge.org/), local event in **Aracaju, Brazil**.

**Challenge:** [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/)

**Current scope:** [docs/scope.md](docs/scope.md), the single source for what we deliver, in which order and what is out.

**Public app:** [crop-helper.pages.dev](https://crop-helper.pages.dev/) · **Published web code revision:** `37552552250d42a74f61a3a9ca1676a59a38693f` (2026-11-16; this is the deployed app commit, not the documentation revision).

Ravi confirmed on 2026-11-16 that the NASA Space Apps submission is complete. The current Pages build calls the product API on an Azure trial; that API is temporary and is not promised through the winners announcement. The repository also contains a demo-only build path that serves saved results without the API.

## What it is

**Decision support** for the technical professional who leads planting decisions in Sergipe, Brazil. It compares three rotation strategies (the current practice and two alternatives), checks the planting windows against the official ZARC zoning, and shows the source of every number. It does not predict the harvest or the yield.

**Known limit:** the ranking did not change across wet and dry years in the historical backtest: the same strategy ranked first in 45 of 45 tested seasons ([backtest record, PR #96](https://github.com/raviproenca/nether-field-shift-2026/pull/96)). Read the ranking as a structured comparison of options, not a forecast of how a season will turn out.

The dashboard keeps **last crop grown** separate from **intended crop**. Live requests send the last crop as `previous_crops` to the API. The static demo shows saved recommendations and states when the selected history was not applied; it does not claim to personalize saved results. Unknown or unsupported history does not receive a rotation score benefit or a pest-cycle claim.

ZARC is a check against published planting windows, not a guarantee that a crop or date is suitable. Recommendations use fixed rules and the supported crops (maize, beans and cassava); they are not yield probabilities or harvest predictions. The live API is on a time-limited Azure trial. If it is unavailable, live mode reports an error; it does not silently substitute a saved result.

## How to run

### Crop Helper web app

Requirements: Node.js 24 or newer. The default build uses saved demo data when `VITE_API_URL` is empty.

```bash
cd apps/web
npm ci
VITE_API_URL= npm run dev
```

To run against a local API, start the API as described below, then use `VITE_API_URL=http://localhost:8000 npm run dev`. For the live Azure trial endpoint, use `VITE_API_URL=https://field-shift-api.kindpebble-07cb9fe8.brazilsouth.azurecontainerapps.io npm run dev`. The URL is public configuration, not a credential. Never put a token or password in a `VITE_*` variable.

### API and data toolkit

Requirements: [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv venv -p 3.12 .venv && uv pip install -r requirements-dev.txt -r apps/api/requirements.txt
```

Run the API locally on loopback:

```bash
.venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

No Azure or Cloudflare resources are created by these local commands.

Data toolkit (details in [src/data/README.md](src/data/README.md)):

```bash
source .venv/bin/activate
# POWER needs no login
python -m src.data power --point -10.91,-37.07 --start 2025-01-01 --end 2025-12-31 \
  --variable T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN --out data/sample/power_aracaju_2025.csv
# Count granules without login
python -m src.data modis --search-only --start 2025-01-01 --end 2025-01-31
# Sentinel-2 (ESA, not NASA) from the Planetary Computer: no account
python -m src.data planetary --variable B04 --point -10.91,-37.07 --radius-km 2 --start 2025-01-01 --end 2025-01-31
# NASADEM / SRTM 30 m terrain elevation & slope (no account)
python -m src.data srtm --point -10.685,-37.425 --radius-km 5 --variable all --out data/processed/srtm
# Open-Meteo 15-day forecast with FAO-56 ET0 (no account)
python -m src.data open-meteo --point -10.685,-37.425 --forecast-days 15
# GLDAS, IMERG, SMAP, MODIS, VIIRS and HLS downloads need a free NASA Earthdata account:
scripts/earthdata-login.sh        # once; stores credentials in ~/.netrc, never in the repo
python -m src.data gldas --variable SoilMoi0_10cm_inst --start 2025-01-01 --end 2025-01-31
```

### Tests

```bash
# Web tests, lint and typecheck
cd apps/web
npm test
npm run lint
npm run typecheck

# Python tests that do not require live data services
cd ../..
.venv/bin/python -m pytest -m "not network"
```

Live data checks are separately marked: `.venv/bin/python -m pytest -m network`.

## NASA data used

The product uses NASA Earth science data alongside the third-party sources below. The table also preserves datasets available to the repository's data toolkit. NASA Earth science data are open: free to use and redistribute with attribution; see the [Earthdata data use guidance](https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance). The *License / policy* column links to each dataset's terms.

| Dataset | Page | DOI | License / policy |
|---|---|---|---|
| NASA POWER, daily point API (MERRA-2 + CERES SYN1deg) | [power.larc.nasa.gov](https://power.larc.nasa.gov/) | none | Open; own [referencing guide](https://power.larc.nasa.gov/docs/referencing/): cite the POWER project, the version and the access date |
| GLDAS Noah Land Surface Model L4 3-hourly 0.25° v2.1 (`GLDAS_NOAH025_3H`) | [GES DISC](https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_3H_2.1/summary) | [10.5067/E7TYRXPJKWOQ](https://doi.org/10.5067/E7TYRXPJKWOQ) | NASA open data, EOSDIS use guidance |
| GLDAS Noah Land Surface Model L4 monthly 0.25° v2.1 (`GLDAS_NOAH025_M`) | [GES DISC](https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_M_2.1/summary) | [10.5067/SXAVCZFAQLNO](https://doi.org/10.5067/SXAVCZFAQLNO) | NASA open data, EOSDIS use guidance |
| GPM IMERG Late Precipitation L3 1 day 0.1° v07 (`GPM_3IMERGDL`) | [GES DISC](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDL_07/summary) | [10.5067/GPM/IMERGDL/DAY/07](https://doi.org/10.5067/GPM/IMERGDL/DAY/07) | NASA open data, EOSDIS use guidance |
| GPM IMERG Final Precipitation L3 1 day 0.1° v07 (`GPM_3IMERGDF`, up to 2025-09-30) | [GES DISC](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary) | [10.5067/GPM/IMERGDF/DAY/07](https://doi.org/10.5067/GPM/IMERGDF/DAY/07) | NASA open data, EOSDIS use guidance |
| SMAP Enhanced L3 Radiometer Soil Moisture Daily 9 km v006 (`SPL3SMP_E`) | [NSIDC](https://nsidc.org/data/spl3smp_e/versions/6) | [10.5067/M20OXIZHY3RJ](https://doi.org/10.5067/M20OXIZHY3RJ) | Free and open; NSIDC asks for citation as on the dataset page |
| MODIS/Terra Vegetation Indices 16-Day L3 250 m v061 (`MOD13Q1`) | [LP DAAC](https://lpdaac.usgs.gov/products/mod13q1v061/) | [10.5067/MODIS/MOD13Q1.061](https://doi.org/10.5067/MODIS/MOD13Q1.061) | NASA open data, EOSDIS use guidance |
| VIIRS/NPP Vegetation Indices 16-Day L3 500 m v002 (`VNP13A1`) | [LP DAAC](https://lpdaac.usgs.gov/products/vnp13a1v002/) | [10.5067/VIIRS/VNP13A1.002](https://doi.org/10.5067/VIIRS/VNP13A1.002) | NASA open data, EOSDIS use guidance |
| HLS Landsat Surface Reflectance 30 m v2.0 (`HLSL30`) | [LP DAAC](https://lpdaac.usgs.gov/products/hlsl30v002/) | [10.5067/HLS/HLSL30.002](https://doi.org/10.5067/HLS/HLSL30.002) | NASA open data, EOSDIS use guidance |
| HLS Sentinel-2 Surface Reflectance 30 m v2.0 (`HLSS30`) | [LP DAAC](https://lpdaac.usgs.gov/products/hlss30v002/) | [10.5067/HLS/HLSS30.002](https://doi.org/10.5067/HLS/HLSS30.002) | NASA open data, EOSDIS use guidance |
| NASADEM Merged DEM Global 1 arc-second v001 (`NASADEM_HGT`, elevation and slope; read through the Microsoft Planetary Computer) | [Planetary Computer](https://planetarycomputer.microsoft.com/dataset/nasadem) | [10.5067/MEASURES/NASADEM/NASADEM_HGT.001](https://doi.org/10.5067/MEASURES/NASADEM/NASADEM_HGT.001) | NASA open data, EOSDIS use guidance. Service use: [Planetary Computer terms of use](https://planetarycomputer.microsoft.com/terms) |
| NASA GIBS (Global Imagery Browse Services), WMTS and WMS for EPSG:3857, shown live in the internal map (`apps/web/`) | [GIBS API](https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api) | none | NASA open data, EOSDIS use guidance; credited on the map as "Imagery: NASA GIBS / EOSDIS" |
| GIBS `VIIRS_NOAA20_CorrectedReflectance_TrueColor`, from VIIRS/JPSS1 L1B 375 m and 750 m swaths NRT v2.1 (`VJ102IMG_NRT`, `VJ103IMG_NRT`, `VJ102MOD_NRT`) | [CMR](https://cmr.earthdata.nasa.gov/search/concepts/C2208779826-LANCEMODIS.html) | [10.5067/VIIRS/VJ102IMG_NRT.021](https://doi.org/10.5067/VIIRS/VJ102IMG_NRT.021), [10.5067/VIIRS/VJ103IMG_NRT.021](https://doi.org/10.5067/VIIRS/VJ103IMG_NRT.021), [10.5067/VIIRS/VJ102MOD_NRT.021](https://doi.org/10.5067/VIIRS/VJ102MOD_NRT.021) | NASA open data, EOSDIS use guidance |
| GIBS `VIIRS_NOAA20_NDVI_8Day`, from VIIRS/JPSS1 Vegetation Indices 8-Day L3 500 m v2 (`VJ113A4N`) | [CMR](https://cmr.earthdata.nasa.gov/search/concepts/C3706771935-LANCEMODIS.html) | [10.5067/VIIRS/VJ113A4N.002](https://doi.org/10.5067/VIIRS/VJ113A4N.002) | NASA open data, EOSDIS use guidance |
| GIBS `VIIRS_NOAA20_Land_Surface_Temp_Day`, from VIIRS/JPSS1 Land Surface Temperature and Emissivity L2 750 m v2 (`VJ121_NRT`, `VJ121`) | [CMR](https://cmr.earthdata.nasa.gov/search/concepts/C2781382411-LANCEMODIS.html) | [10.5067/VIIRS/VJ121_NRT.002](https://doi.org/10.5067/VIIRS/VJ121_NRT.002) | NASA open data, EOSDIS use guidance |
| GIBS `SMAP_L4_Analyzed_Surface_Soil_Moisture`, from SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture Analysis Update v008 (`SPL4SMAU`) | [CMR](https://cmr.earthdata.nasa.gov/search/concepts/C3480440639-NSIDC_CPRD.html) | [10.5067/02LGW4DGJYRX](https://doi.org/10.5067/02LGW4DGJYRX) | Free and open; NSIDC asks for citation as on the dataset page |
| GIBS `IMERG_Precipitation_Rate`, from GPM IMERG Early and Final Precipitation L3 Half Hourly 0.1° v07 (`GPM_3IMERGHHE`, `GPM_3IMERGHH`) | [CMR](https://cmr.earthdata.nasa.gov/search/concepts/C2723758340-GES_DISC.html) | [10.5067/GPM/IMERG/3B-HH-E/07](https://doi.org/10.5067/GPM/IMERG/3B-HH-E/07), [10.5067/GPM/IMERG/3B-HH/07](https://doi.org/10.5067/GPM/IMERG/3B-HH/07) | NASA open data, EOSDIS use guidance |
| GIBS `VIIRS_NOAA20_Thermal_Anomalies_375m_All` (FIRMS active fires), from VIIRS NOAA-20 375 m I-Band Active Fire NRT v2 (`VJ114IMGT_NRT`) | [CMR](https://cmr.earthdata.nasa.gov/search/concepts/C1355615368-LANCEMODIS.html) | [10.5067/FIRMS/VIIRS/VJ114IMGT_NRT.002](https://doi.org/10.5067/FIRMS/VIIRS/VJ114IMGT_NRT.002) | NASA open data, EOSDIS use guidance |

DOIs were read from the NASA CMR collection records on 2026-11-14. The GIBS rows list the source collections named in each layer's metadata (`https://gibs.earthdata.nasa.gov/layer-metadata/v1.0/<layer>.json`). The table is retained for project and toolkit provenance; it does not imply every dataset appears in every recommendation.

### Public-link maintenance

Ravi reports the NASA submission is complete. Keep these checks current for the public app, repository and supporting materials.

- [ ] Every link in the project page (demo, app, video, slides, data, repo) opens without login and works until 2027-01-26
- [ ] Repo is public; README lists how to run, NASA data (above), credits and AI usage
- [ ] Each NASA dataset used appears in the table above with link, DOI and license/policy; non-NASA data (Sentinel-2) only in "Third-party data" with its attribution
- [ ] Citations with DOI for the datasets shown in the demo (POWER: project, version, access date)
- [ ] No credentials, `.netrc` or `.env` in the history

## Third-party data (not NASA)

| Dataset | Provider | Page | DOI | License / terms |
|---|---|---|---|---|
| Zoneamento Agrícola de Risco Climático (ZARC), "Tábua de Risco": planting periods by crop, municipality, soil class and harvest year | MAPA (Ministério da Agricultura e Pecuária), open data portal | [dados.agricultura.gov.br](https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico) | none | Creative Commons Attribution (CC BY, from the catalog metadata); credit "ZARC, MAPA" with the harvest year and portaria. The legal text is the portaria PDF. See [docs/research/brazil-data-sources.md](docs/research/brazil-data-sources.md) |
| Sentinel-2 MSI Level-2A surface reflectance, 10 m (`sentinel-2-l2a`) | ESA / Copernicus, served by the Microsoft Planetary Computer | [Planetary Computer catalog](https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a) | [10.5270/S2_-znk9xsj](https://doi.org/10.5270/S2_-znk9xsj) (Sentinel-2 MSI Level-2A BOA Reflectance Product, ESA) | Free, full and open under the [Copernicus Sentinel data terms](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice); attribution: "Contains modified Copernicus Sentinel data [year]". Service use: [Planetary Computer terms of use](https://planetarycomputer.microsoft.com/terms) |
| Open-Meteo Weather Forecast API (ECMWF IFS / NOAA GFS, up to 15 days + FAO-56 ET0) | Open-Meteo | [open-meteo.com](https://open-meteo.com/) | none | Free for non-commercial use under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); attribution required ("Weather data by Open-Meteo.com") |
| Oceanic Niño Index (ONI), historical season labels in the rain-risk view | NOAA Climate Prediction Center | [NOAA CPC ONI](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/index.php) | none | NOAA data are public domain; cite NOAA CPC. ONI is used for historical labels, not as a crop recommendation or forecast. NOAA CPC now identifies RONI for official ENSO monitoring. |
| Produção Agrícola Municipal (PAM), table 5457: area, production, yield and value by municipality and crop, 1974 to 2025 | IBGE (Instituto Brasileiro de Geografia e Estatística), via the SIDRA API | [SIDRA table 5457](https://sidra.ibge.gov.br/tabela/5457) | none | Licence **not verified yet** (the IBGE terms pages block automated access); credit "Fonte: IBGE, Pesquisa Agrícola Municipal" and the access date. See [docs/research/brazil-data-sources.md](docs/research/brazil-data-sources.md) |

The municipal mesh in `data/sample/ibge_se_municipalities.geojson` (used to find the IBGE code of a plot, which selects the ZARC rows) comes from the IBGE malhas API v3, state 28, lowest quality; credit "Fonte: IBGE, Malha Municipal". Third-party data, not NASA.

The Sergipe rows of the ZARC used by the engine are committed in `data/reference/zarc/` so the deployed API needs no download: `zarc_2026-2027_se.csv` (maize and beans, safra 2026/2027) and `zarc_perene_se.csv` (cassava, perennial file), both filtered by `python -m src.data.zarc` on 2026-11-15 from the MAPA open-data catalog (Tábua de Risco, portarias 45/2026, 136/2026, 237/2026, 262/2026, 372/2026 and 17/2020). Credit: "ZARC, Ministério da Agricultura e Pecuária (MAPA) / Embrapa, dados abertos, CC BY". A fresh download in `data/processed/` takes precedence. Third-party data, not NASA.

Sentinel-2 is **European data** and IBGE PAM is **Brazilian data**: neither is NASA data, so they are not part of "NASA data used". Sentinel-2 is read through the `planetary` source of the toolkit (no account, no key); IBGE PAM is read with `python -m src.data.sidra` (public API, no key). The NASA path to 30 m imagery is **HLS** (`hls` source, table above). If the demo shows Sentinel-2, keep the Copernicus attribution next to it; if it shows PAM numbers, credit IBGE.

## Pre-generated data (internal map)

The internal map reads static JSON and GeoJSON files from `apps/web/public/data/`, built by `python -m src.data.snapshots` from the sources above (POWER, GLDAS monthly, IMERG, SMAP, VIIRS NDVI, NASADEM). No server and no login. How to regenerate it, its size and the file format: [src/data/README.md](src/data/README.md#snapshots-for-the-internal-map) and [docs/data-format.md](docs/data-format.md). Terrain code is based on work by [@dudxyz](https://github.com/dudxyz).

## Contributing
Team workflow: [CONTRIBUTING.md](CONTRIBUTING.md) · instructions for AI agents: [AGENTS.md](AGENTS.md).

## AI usage
Built with the help of AI coding assistants; the idea and decisions are the team's own. The data toolkit in `src/data/`, its tests and `scripts/earthdata-login.sh` were generated with Claude Code and carry an `AI-assisted` header (review pending). The internal map front end in `apps/web/` was also generated with Claude Code and carries the same header (reviewed by Ravi).

On Nov 14, 2026 an AI assistant was also used to critique our scope against the Field Shift challenge text (what the challenge asks for versus what we had planned). The team discussed that critique and decided the priority itself: decision engine first, then its validation against ZARC and past seasons, then the dashboard (see [docs/team/decisions.md](docs/team/decisions.md)).

On Nov 15, 2026 an AI assistant (Claude Code, BMad deep-recon) was used to research, with cited sources, who leads or advises planting decisions in Sergipe ([docs/research/persona-discovery.md](docs/research/persona-discovery.md)). It did not rank the roles or choose a persona; the team chooses the persona and the role of AI.

The Crop Helper web interface in `apps/web/src/plot/immersive/`, `scripts/build_risk_cache.py` and the all-combinations mode of `scripts/build_demo_cache.py` were built with AI coding assistants and carry `AI-assisted` headers. For a selected address the app computes seasonal rain risk in the browser from NASA POWER; historical El Niño season labels use the NOAA CPC Oceanic Niño Index (third party, credited above).

## Credits

Libraries (pinned in [requirements.txt](requirements.txt); pytest in [requirements-dev.txt](requirements-dev.txt)):

| Library | License |
|---|---|
| [earthaccess](https://github.com/nsidc/earthaccess) | MIT |
| [xarray](https://xarray.dev/) | Apache-2.0 |
| [netCDF4](https://github.com/Unidata/netcdf4-python) | MIT |
| [h5netcdf](https://github.com/h5netcdf/h5netcdf) | BSD-3-Clause |
| [h5py](https://www.h5py.org/) | BSD-3-Clause |
| [rioxarray](https://corteva.github.io/rioxarray/) | Apache-2.0 |
| [pandas](https://pandas.pydata.org/) | BSD-3-Clause |
| [numpy](https://numpy.org/) | BSD-3-Clause |
| [rasterio](https://rasterio.readthedocs.io/) | BSD-3-Clause |
| [fsspec](https://filesystem-spec.readthedocs.io/) | BSD-3-Clause |
| [pyarrow](https://arrow.apache.org/docs/python/) | Apache-2.0 |
| [requests](https://requests.readthedocs.io/) | Apache-2.0 |
| [pyhdf](https://github.com/fhs/pyhdf) | MIT |
| [pystac-client](https://github.com/stac-utils/pystac-client) (STAC search for Planetary Computer; added because the `planetary` source queries the STAC API) | Apache-2.0 |
| [planetary-computer](https://github.com/microsoft/planetary-computer-sdk-for-python) (signs asset URLs, no key; added for the same reason) | MIT |
| [PyYAML](https://pyyaml.org/) (reads `src/engine/rules/*.yaml`) | MIT |
| [pytest](https://pytest.org/) | MIT |
| [fastapi](https://fastapi.tiangolo.com/) | MIT |
| [uvicorn](https://www.uvicorn.org/) | BSD-3-Clause |
| [pydantic](https://docs.pydantic.dev/) | MIT |
| [httpx](https://www.python-httpx.org/) | BSD-3-Clause |

Crop Helper web app (`apps/web/`, dependencies pinned in [apps/web/package.json](apps/web/package.json)):

| Library, data or font | License / terms |
|---|---|
| [OpenStreetMap](https://www.openstreetmap.org/copyright) base map tiles | Data © OpenStreetMap contributors, [ODbL](https://opendatacommons.org/licenses/odbl/); [tile usage policy](https://operations.osmfoundation.org/policies/tiles/) |
| [Nominatim](https://nominatim.org/) address search (OpenStreetMap data), limited to Sergipe, one request per search | Data © OpenStreetMap contributors, [ODbL](https://opendatacommons.org/licenses/odbl/); [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/) |
| [MapLibre GL JS](https://maplibre.org/) | BSD-3-Clause |
| [React](https://react.dev/) | MIT |
| [Vite](https://vite.dev/) | MIT |
| [Geist](https://vercel.com/font) font via [@fontsource-variable/geist](https://fontsource.org/fonts/geist) | SIL Open Font License 1.1 |
| NASA GIBS imagery and its official colormaps and layer styles (live, not copied into the repo; see "NASA data used") | NASA open data, EOSDIS use guidance; no NASA logo or Worldview code is used |

Rules cited by the decision engine (not copied):

| Work | Terms |
|---|---|
| Kalaivani et al., IEEE CICT 2025, DOI [10.1109/CICT67193.2025.11399212](https://doi.org/10.1109/CICT67193.2025.11399212) | IEEE copyright. The engine cites the rotation rules only: do not repeat the previous crop's botanical family, and after a nitrogen-depleting crop prefer a legume. The paper's text, figures, and logistic-regression model are not used. |

## License
[Apache License 2.0](LICENSE)
