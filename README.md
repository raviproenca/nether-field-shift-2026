# Nether · Field Shift (NASA Space Apps Challenge 2026)

Team **Nether**'s project for the [NASA Space Apps Challenge 2026](https://www.spaceappschallenge.org/), local event in **Aracaju, Brazil**.

**Challenge:** [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/)

> 🚧 **Work in progress.** Development happens during the hackathon (November 14–15, 2026), per the event rules.

## How to run

Requirements: [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv venv -p 3.12 .venv && uv pip install -r requirements.txt
```

Data toolkit (details in [src/data/README.md](src/data/README.md)):

```bash
source .venv/bin/activate
# POWER needs no login
python -m src.data power --point -10.91,-37.07 --radius-km 1 --start 2025-01-01 --end 2025-12-31 \
  --variable T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN --out data/sample/power_aracaju_2025.csv
# Count granules without login
python -m src.data modis --search-only --start 2025-01-01 --end 2025-01-31
# GLDAS, IMERG, SMAP, MODIS, VIIRS and HLS downloads need a free NASA Earthdata account:
scripts/earthdata-login.sh        # once; stores credentials in ~/.netrc, never in the repo
python -m src.data gldas --variable SoilMoi0_10cm_inst --start 2025-01-01 --end 2025-01-31
```

Tests: `.venv/bin/python -m pytest` (offline). Real POWER call: `.venv/bin/python -m pytest -m network`.

## NASA data used

Every dataset the project can read. NASA Earth science data are open: free to use and redistribute with attribution, see the [Earthdata data use guidance](https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance). The *License / policy* column says where each dataset states its terms.

| Dataset | Page | DOI | License / policy |
|---|---|---|---|
| NASA POWER, daily point API (MERRA-2 + CERES SYN1deg) | [power.larc.nasa.gov](https://power.larc.nasa.gov/) | none | Open; own [referencing guide](https://power.larc.nasa.gov/docs/referencing/): cite the POWER project, the version and the access date |
| GLDAS Noah Land Surface Model L4 3-hourly 0.25° v2.1 (`GLDAS_NOAH025_3H`) | [GES DISC](https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_3H_2.1/summary) | [10.5067/E7TYRXPJKWOQ](https://doi.org/10.5067/E7TYRXPJKWOQ) | NASA open data, EOSDIS use guidance |
| GPM IMERG Late Precipitation L3 1 day 0.1° v07 (`GPM_3IMERGDL`) | [GES DISC](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDL_07/summary) | [10.5067/GPM/IMERGDL/DAY/07](https://doi.org/10.5067/GPM/IMERGDL/DAY/07) | NASA open data, EOSDIS use guidance |
| GPM IMERG Final Precipitation L3 1 day 0.1° v07 (`GPM_3IMERGDF`, up to 2025-09-30) | [GES DISC](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary) | [10.5067/GPM/IMERGDF/DAY/07](https://doi.org/10.5067/GPM/IMERGDF/DAY/07) | NASA open data, EOSDIS use guidance |
| SMAP Enhanced L3 Radiometer Soil Moisture Daily 9 km v006 (`SPL3SMP_E`) | [NSIDC](https://nsidc.org/data/spl3smp_e/versions/6) | [10.5067/M20OXIZHY3RJ](https://doi.org/10.5067/M20OXIZHY3RJ) | Free and open; NSIDC asks for citation as on the dataset page |
| MODIS/Terra Vegetation Indices 16-Day L3 250 m v061 (`MOD13Q1`) | [LP DAAC](https://lpdaac.usgs.gov/products/mod13q1v061/) | [10.5067/MODIS/MOD13Q1.061](https://doi.org/10.5067/MODIS/MOD13Q1.061) | NASA open data, EOSDIS use guidance |
| VIIRS/NPP Vegetation Indices 16-Day L3 500 m v002 (`VNP13A1`) | [LP DAAC](https://lpdaac.usgs.gov/products/vnp13a1v002/) | [10.5067/VIIRS/VNP13A1.002](https://doi.org/10.5067/VIIRS/VNP13A1.002) | NASA open data, EOSDIS use guidance |
| HLS Landsat Surface Reflectance 30 m v2.0 (`HLSL30`) | [LP DAAC](https://lpdaac.usgs.gov/products/hlsl30v002/) | [10.5067/HLS/HLSL30.002](https://doi.org/10.5067/HLS/HLSL30.002) | NASA open data, EOSDIS use guidance |
| HLS Sentinel-2 Surface Reflectance 30 m v2.0 (`HLSS30`) | [LP DAAC](https://lpdaac.usgs.gov/products/hlss30v002/) | [10.5067/HLS/HLSS30.002](https://doi.org/10.5067/HLS/HLSS30.002) | NASA open data, EOSDIS use guidance |

DOIs were read from the NASA CMR collection records on 2026-11-14 and every link above answered HTTP 200 that day. Trim this table to the datasets actually used before submitting.

### Page checklist before submitting

- [ ] Every link in the project page (demo, app, video, slides, data, repo) opens without login and works until 2027-01-26
- [ ] Repo is public; README lists how to run, NASA data (above), credits and AI usage
- [ ] Each NASA dataset used appears in the table above with link, DOI and license/policy
- [ ] Citations with DOI for the datasets shown in the demo (POWER: project, version, access date)
- [ ] No credentials, `.netrc` or `.env` in the history

## Contributing
Team workflow: [CONTRIBUTING.md](CONTRIBUTING.md) · instructions for AI agents: [AGENTS.md](AGENTS.md).

## AI usage
Built with the help of AI coding assistants; the idea and decisions are the team's own. The data toolkit in `src/data/`, its tests and `scripts/earthdata-login.sh` were generated with Claude Code and carry an `AI-assisted` header (review pending).

## Credits

Libraries (pinned in [requirements.txt](requirements.txt)):

| Library | License |
|---|---|
| [earthaccess](https://github.com/nsidc/earthaccess) | MIT |
| [xarray](https://xarray.dev/) | Apache-2.0 |
| [netCDF4](https://github.com/Unidata/netcdf4-python) | MIT |
| [h5netcdf](https://github.com/h5netcdf/h5netcdf) | BSD-3-Clause |
| [h5py](https://www.h5py.org/) | BSD-3-Clause |
| [rioxarray](https://corteva.github.io/rioxarray/) | Apache-2.0 |
| [pandas](https://pandas.pydata.org/) | BSD-3-Clause |
| [pyarrow](https://arrow.apache.org/docs/python/) | Apache-2.0 |
| [requests](https://requests.readthedocs.io/) | Apache-2.0 |
| [pyhdf](https://github.com/fhs/pyhdf) | MIT |
| [pytest](https://pytest.org/) | MIT |

## License
[Apache License 2.0](LICENSE)
