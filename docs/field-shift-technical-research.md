<!-- AI-assisted: generated with Antigravity, reviewed by Eduarda / Team Nether -->

> **Background research, not a team decision.**

# Technical Research Report — NASA Space Apps 2026: *Field Shift: Adapting Farms with NASA Data*

> **Epistemological Note:** Throughout this document, we explicitly distinguish between **Officially documented facts** (specifications from space agencies and data maintainers), **Scientific findings** (established physical and agronomic relationships), **Technical interpretations** (analytical assessments of dataset suitability), and **Assumptions requiring local validation**. Where a specification could not be verified directly from official sources, this is stated explicitly.

---

## 1. Executive Summary

The **[Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/)** challenge of the 2026 NASA Space Apps Challenge calls for a **decision-support tool** (rather than a purely descriptive map or dashboard) that integrates NASA Earth observations, local soil information, crop characteristics, and farmer priorities to **compare at least three crop rotation strategies** (including the existing rotation) with evidence-backed explanations and transparent uncertainty reporting.

### Key Research Findings

1. **Spatial scale mismatch is the core technical constraint:** Global NASA hydrological products (**SMAP** at 9–36 km, **GPM IMERG** at ~10 km, **NASA POWER** at ~50–100 km, and **GLDAS** at ~25 km) capture *regional climate and water-balance context*, not individual agricultural fields. Only medium-to-high-resolution optical and thermal sensors (**Sentinel-2** at 10–20 m, **Landsat** at 30 m, **ECOSTRESS** at ~70 m, **SRTM** at ~30 m) resolve intra-farm and field-level variability.
2. **Severe geographic asymmetry across the listed challenge resources:** Out of the 25 listed datasets, **12 are restricted to the United States (or North America)**—including all detailed soil surveys (Web Soil Survey, SSURGO/STATSGO2), historical crop classification maps (CDL/CropScape), fine-grained climate grids (PRISM), aerial imagery (NAIP), and market/agricultural statistics (AMS/NASS). Any system targeting regions outside the U.S. (such as Brazil or global deployments) must rely on **global NASA/ESA/ECMWF datasets** and, where appropriate, **regional open equivalents** (e.g., **SoilGrids**, **MapBiomas**, **CHIRPS**, **INMET**, **Embrapa/PronaSolos**).
3. **Satellites do not directly measure soil fertility or nitrogen fixation:** Earth observation instruments measure surface reflectance, thermal radiance, microwave brightness temperature, and radar elevation. Agronomic properties such as biological nitrogen fixation, organic matter accumulation, rooting depth, and market suitability must come from **agronomic knowledge bases and farmer inputs**, coupled with **satellite-derived indicators** (water deficit, thermal/evaporative stress, bare-soil windows, and topographic erosion risk).
4. **Clarification of *"SI techniques"*:** Within the official **2026 NASA Space Apps Challenge** context ([spaceappschallenge.org](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/)), **SI** refers to **Super Intelligence**—the organization's umbrella term in 2026 guidelines and challenges for AI, large language models, and intelligent synthesis systems used to translate complex data into practical insights (as also used in other 2026 challenges such as *Flame in Freefall*). *(Outside Space Apps 2026 terminology, "SI" in remote sensing and agronomy commonly denotes Spectral Indices or Sustainable Intensification).*
5. **Technical feasibility:** A global analytical core could combine field-scale optical/terrain data (10–30 m), regional water/climate data (9–50 km) and soil profiles. Cloud-native access options make it possible to do this without downloading full global archives, for example the **NASA POWER REST API**, **STAC** catalogs with COGs, **earthaccess** (already used in `src/data`), **Google Earth Engine**, or **USDA SDA** where applicable. Which tools to use is open.

---

## 2. Problem Summary (Portuguese Context Reference)

*(Per repository language policy in `AGENTS.md`, repository documentation is maintained in English; see Section 3 for the complete problem summary.)*

In summary for Brazilian/Portuguese-speaking contributors: o desafio pede uma ferramenta de apoio à decisão (não apenas um mapa ambiental) que traduza séries históricas da NASA, propriedades locais do solo, características de culturas e prioridades do produtor em comparações transparentes de **pelo menos 3 estratégias de rotação de culturas** (incluindo a atual), explicando evidências, trade-offs e limitações que exigem validação agronômica em campo.

---

## 3. Problem Summary in English

### What problem are we expected to solve?
Farmers worldwide are facing increasingly erratic rainfall, rising heat extremes, water scarcity, soil erosion, and declining soil health. Because environmental conditions are shifting, traditional heuristics for choosing **which crops to grow and in what multi-season sequence (crop rotation)** are breaking down. A crop that builds soil organic matter or fixes nitrogen in one context may fail due to water deficits, heat stress during flowering, pest/disease carryover, or mismatched growing windows in another.

### Who experiences this problem and why does it matter?
Farmers, agronomists, agricultural cooperatives, and rural extension advisors—particularly those operating without dense local weather stations or precision-agronomy consulting. Poor rotation choices accelerate topsoil loss, deplete nutrients and groundwater, and expose farms to climate shocks.

### What is the expected technological solution and what role should NASA data play?
The challenge asks for a **decision-support application, analytical model, or interactive tool** that fuses **NASA Earth observation datasets** with **local soil properties, crop agronomic profiles, and farmer priorities**. NASA missions provide consistent, multi-year, objective environmental baselines—capturing precipitation dynamics, surface and root-zone soil moisture, evapotranspiration/thermal stress, vegetation cover/bare-soil periods, climate normals, and terrain slope—allowing the system to diagnose field/regional environmental constraints even where local sensors are absent.

### Key technical requirements and deliverables
1. Analyze historical and current environmental conditions (rainfall, temperature, soil moisture, evaporation, vegetation stress).
2. Detect recurring **bare-soil windows** and periods when existing crops are environmentally vulnerable.
3. Evaluate candidate alternative crops considering water demand, nitrogen fixation, erosion protection, organic matter contribution, forage potential, and market fit.
4. **Compare at least three crop rotation strategies**, explicitly including the farmer's **current (baseline) rotation**.
5. Deliver **explainable recommendations** backed by quantitative evidence, while transparently communicating **uncertainties, resolution mismatches, missing local data, and risks** requiring validation by farmers or local agronomists.
6. Support—never replace—human agricultural judgment.

### Visualization dashboard vs. true decision-support tool
A visualization dashboard stops at displaying raw environmental layers (*"NDVI dropped in July; rainfall was below average"*). A genuine decision-support tool translates multi-source signals into **actionable agronomic trade-offs**: quantifying how alternative crop sequences align with seasonal water/thermal windows, soil-erosion exposure, and the farmer's stated goals, while exposing confidence bounds and assumptions.

---

## 4. Challenge Decomposition

| Technical Subproblem | What Needs to Be Understood | Contribution of Available Datasets | Boundary / What Satellites Alone Cannot Provide |
|---|---|---|---|
| **1. Water availability & balance** | Is there enough water in the growing window? When do surface or root-zone deficits recur? | Precipitation (GPM IMERG, NASA POWER, PRISM, CHIRPS), surface/root-zone soil moisture (SMAP L3/L4, GLDAS/NLDAS), ET & evaporative stress (ECOSTRESS, OpenET) | Actual irrigation efficiency, water rights/permits, local water-table depth |
| **2. Climate & thermal vulnerability** | Which weeks/months expose crops to heat stress, frost, or dry spells? | Min/max air temperature, solar radiation, humidity, VPD, extreme heat days (NASA POWER, ERA5, PRISM), canopy/land-surface temperature (ECOSTRESS, Landsat TIRS, VIIRS) | Microclimate in local valleys/slopes and exact planted cultivar |
| **3. Soil degradation & erosion risk** | Where and when is bare soil exposed to intense rainfall on sloped terrain? | Slope and terrain flow (SRTM), intense rainfall rates (GPM IMERG 30-min), bare-soil windows via spectral indices (Landsat/Sentinel-2), soil texture/K-factor/drainage (SSURGO/WSS or SoilGrids) | Subsurface compaction, existing conservation practices (no-till residue, terraces) |
| **4. Land-use history & phenology** | What has been planted? What are actual planting, peak-greenness, and fallow/bare periods? | NDVI/EVI/NDWI/BSI time series (Sentinel-2, Landsat, HLS, MODIS/VIIRS), annual crop maps (CDL/CropScape in U.S.; MapBiomas in Brazil) | Exact cultivar, fertilizer application, actual pest/disease outbreaks |
| **5. Crop suitability & rotation synergies** | Which alternative crops fit climate/soil constraints and offset current rotation weaknesses? | Environmental indicators above + external agronomic parameters (FAO-56 $K_c$, N-fixation, root depth, botanical family, market stats AMS/QuickStats/CONAB) | Farm-gate net prices, machinery availability, local storage/buyers |
| **6. Explainability, prioritization & uncertainty** | Why does Strategy B outperform Baseline under farmer priorities, and how confident is that estimate? | Transparent multi-criteria scoring, explicit spatial-scale flags (9–50 km vs. 10–30 m), cloud/quality masks, and grounded SI explanation layer | Final farmer judgment and local agronomist field validation |

---

## 5. Complete Dataset Inventory

Consolidated inventory of all **25 resources** listed in the challenge briefing (preserving original names), plus **GRACE / GRACE-FO** (referenced in the challenge's technical approaches).

| # | Official Name | Category | Provider / Distributor | Geographic Coverage | Primary Spatial Resolution | Temporal Resolution | Evaluation |
|---|---|---|---|---|---|---|---|
| 1 | **SMAP — Soil Moisture Active Passive** | NASA EO | NASA / JPL / NSIDC DAAC (and GEE) | Global | 36 km (L3) / 9 km (L3_E & L4) | Daily (L3) / 3-hourly (L4) | **HIGH PRIORITY** |
| 2 | **GPM / IMERG — Global Precipitation Measurement** | NASA EO | NASA / JAXA / GES DISC | Global (optimal calibration 60°N–60°S; V07 quasi-global) | 0.1° (~10 km) | 30-min (aggregable daily/monthly) | **HIGH PRIORITY** |
| 3 | **Landsat** | NASA/USGS EO | USGS / NASA / EROS | Global | 30 m (optical); 100 m TIRS resampled to 30 m | 8 days (L8+L9) / 16 days each | **HIGH PRIORITY** |
| 4 | **MODIS** | NASA EO | NASA / LP DAAC | Global | 250 m / 500 m / 1 km | Daily / 8- & 16-day composites | **MEDIUM PRIORITY** |
| 5 | **VIIRS** | NASA/NOAA EO | NASA / NOAA / LP DAAC | Global | 375 m / 500 m / 1 km | Daily / 8- & 16-day composites | **MEDIUM PRIORITY** |
| 6 | **NASA POWER** | NASA Agroclimatology | NASA LaRC | Global | 0.5°×0.625° (meteo) / 1°×1° (solar) | Hourly / Daily / Monthly (1981+) | **HIGH PRIORITY** |
| 7 | **SRTM — Shuttle Radar Topography Mission** | NASA Topography | NASA / NGA / LP DAAC / USGS | Near-global (60°N–56°S) | 1 arc-sec (~30 m) | Static (Feb 2000) | **HIGH PRIORITY** |
| 8 | **ECOSTRESS** | NASA EO (ISS) | NASA JPL / LP DAAC | 52°N–52°S | ~70 m | Irregular (~3–5 days avg, varying time of day) | **MEDIUM PRIORITY** |
| 9 | **GEDI — Global Ecosystem Dynamics Investigation** | NASA LiDAR (ISS) | NASA / UMD / LP & ORNL DAAC | 51.6°N–51.6°S | ~25 m footprints (sampled; 600 m cross-track gaps) | Sampled (2019–present, hiatus Mar 2023–Apr 2024) | **LOW PRIORITY** |
| 10 | **NLDAS / GLDAS — Land Data Assimilation Systems** | NASA Modeling/Assimilation | NASA GSFC / GES DISC | NLDAS: North America; GLDAS: Global | NLDAS: 0.125° (~12 km); GLDAS: 0.25° (~25 km) & 1° | Hourly (NLDAS) / 3-hourly (GLDAS) | **MEDIUM PRIORITY** |
| 11 | **USDA Ag Data Commons** | Agricultural Repository | USDA NAL | Mostly U.S. studies | Varies by study (plot/point) | Static / per experiment | **LOW PRIORITY** |
| 12 | **Web Soil Survey (WSS)** | Soils (Web Portal) | USDA NRCS | U.S. & territories | 1:12,000–1:63,360 (via SSURGO) | Static (periodic updates) | **MEDIUM PRIORITY** *(HIGH if U.S. scope)* |
| 13 | **Cropland Data Layer (CDL) — CropScape** | Agricultural Land Cover | USDA NASS / GMU CSISS | CONUS (+ Hawaii pilot) | 30 m (2006–07: 56 m) | Annual (CONUS wall-to-wall 2008+) | **HIGH PRIORITY** *(U.S. only)* |
| 14 | **PRISM Climate Data** | Climate | PRISM Climate Group (OSU) | CONUS | 4 km (free) / 800 m | Daily (1981+), Monthly (1895+) | **MEDIUM PRIORITY** *(U.S. only)* |
| 15 | **SSURGO / STATSGO2 — USDA NRCS Soil Data** | Soils (SDA API) | USDA NRCS | U.S. & territories | SSURGO: ~1:24,000; STATSGO2: 1:250,000 | Static (periodic updates) | **HIGH PRIORITY** *(U.S. only)* |
| 16 | **NAIP — National Agriculture Imagery Program** | Aerial Imagery | USDA FSA | CONUS (+ recent territories) | 0.6 m (historical 1 m) | ~2–3 year cycle (leaf-on) | **LOW PRIORITY** |
| 17 | **NLCD — National Land Cover Database** | Land Cover | USGS / MRLC | U.S. (CONUS & extensions) | 30 m | Annual (Annual NLCD 1985–2025) | **LOW PRIORITY** |
| 18 | **CoCoRaHS** | Citizen Science Rainfall | CoCoRaHS / CSU / NOAA | U.S., Canada, Bahamas, PR/USVI | Point stations | Daily | **LOW PRIORITY** |
| 19 | **USGS NWIS — National Water Information Systems** | Hydrology | USGS | U.S. & territories | Point gauges/wells | Continuous (15-min) / Daily | **OPTIONAL / FUTURE** |
| 20 | **USDA AMS Market News** | Agricultural Markets | USDA AMS | U.S. | State / Regional / Terminal | Daily / Weekly | **OPTIONAL / FUTURE** |
| 21 | **USDA NASS QuickStats** | Agricultural Statistics | USDA NASS | U.S. | County / State / National | Annual / Monthly / Census | **MEDIUM PRIORITY** *(U.S. only)* |
| 22 | **OpenET** | Evapotranspiration | OpenET / USGS / NASA / DRI / EDF | CONUS (23 Western states core + CONUS; OpenET-Brazil collaborative initiative) | 30 m | Daily / Monthly / Annual (2000+) | **MEDIUM PRIORITY** *(HIGH if Western U.S./CONUS)* |
| 23 | **USFS LANDFIRE** | Vegetation / Fire Fuels | USDA Forest Service / DOI | U.S. (CONUS, AK, HI, territories) | 30 m | Periodic releases | **LOW PRIORITY** |
| 24 | **Copernicus Sentinel-2 — ESA** | ESA EO | ESA / Copernicus (CDSE) | Global | 10 m (RGB+NIR) / 20 m (Red-Edge+SWIR) / 60 m | ~5 days (equator; 2–3 days mid-latitudes) | **HIGH PRIORITY** |
| 25 | **ERA5 — ECMWF Reanalysis** | Climate Reanalysis | ECMWF / Copernicus C3S (CDS) | Global | 0.25° (~31 km) | Hourly (1940–present) | **MEDIUM PRIORITY** |
| *Extra* | **GRACE / GRACE-FO** | Gravimetry / TWS | NASA / GFZ / JPL / CSR / GSFC | Global | Native ~300–400 km; Mascon 1°; GRACE-DA-DM 0.25° (0.125° CONUS) | Monthly (mascons) / Weekly (DA) | **LOW PRIORITY / OPTIONAL** |

---

## 6. Individual Technical Analysis of Every Dataset

### A. NASA Earth Observation Data

#### 1. SMAP — Soil Moisture Active Passive
- **Identification:** NASA **SMAP** mission (JPL); archived/distributed by **NSIDC DAAC** ([nsidc.org/data/smap](https://nsidc.org/data/smap), overview at [earthdata.nasa.gov/.../smap](https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/smap)). Key products: **SPL3SMP** (V9, L3 daily 36 km), **SPL3SMP_E** (9 km enhanced), **SPL4SMGP** (V8, L4 assimilated 9 km, mirrored in Google Earth Engine as `NASA/SMAP/SPL4SMGP/008`).
- **What it measures:** L-band (1.41 GHz) radiometer measures passive microwave **brightness temperature** from the top **~0–5 cm** of soil (*direct radiometric observation* converted to volumetric soil moisture, $\mathrm{m^3/m^3}$, in L2/L3). **SPL4SMGP (L4)** is a **model-data assimilation product** (Catchment LSM assimilating SMAP brightness temperatures + IMERG/meteorological forcing) estimating surface (0–5 cm) and **root-zone (0–100 cm)** soil moisture (`sm_rootzone`), dimensionless wetness (`sm_rootzone_wetness`), and soil temperature. *(SMAP's active radar failed in 2015).*
- **Technical characteristics:** Nominal grid: **36 km** (SPL3SMP), **9 km** via Backus-Gilbert interpolation (SPL3SMP_E; effective radiometric footprint remains ~36–40 km), **9 km** EASE-Grid 2.0 (SPL4SMGP). Temporal: daily composite (2–3 day revisit, L3) and **3-hourly** (L4, ~2–3 day latency). History: **March 2015–present**. Global coverage (degraded over frozen ground, open water, dense forest). HDF5 via Earthdata/NSIDC/AppEEARS or direct GEE collection.
- **Practical usefulness:** Quantifies **root-zone water deficits (0–100 cm)** and **seasonal soil moisture anomalies** (historical percentiles 2015–present). *Concrete example:* Computing weekly `sm_rootzone` percentiles (2016–2025) identifies a recurring July–September root-zone deficit below the 20th percentile, prompting the system to favor drought-tolerant second-season crops or moisture-conserving cover crops over shallow-rooted high-water crops. Complements GPM IMERG and ECOSTRESS/Landsat.
- **Limitations:** **9–36 km pixel size** cannot distinguish individual fields or management differences (no-till vs. conventional tillage) within the same grid cell; L4 relies on model physics and forcing quality. Cannot alone determine whether a specific field is irrigated or dry.
- **Evaluation:** **HIGH PRIORITY.** Only global root-zone soil moisture dataset with ~10-year record and straightforward GEE/AppEEARS access.

#### 2. GPM / IMERG — Global Precipitation Measurement
- **Identification:** **NASA / JAXA GPM** mission. Product: **IMERG Version 07 (V07B)** distributed by **NASA GES DISC** ([gpm.nasa.gov/data](https://gpm.nasa.gov/data)). Runs: *Early* (~4 h latency), *Late* (~12–14 h), and *Final* (~3.5 months latency, gauge-calibrated via GPCC). Available in GES DISC, Giovanni, and GEE.
- **What it measures:** **Multi-satellite derived precipitation rate and accumulation** (`precipitation`, $\mathrm{mm/h}$ and $\mathrm{mm}$) fusing passive microwave sensors with geostationary IR and monthly rain-gauge calibration in the *Final Run*. Not a direct field rain-gauge reading.
- **Technical characteristics:** **0.1° × 0.1° (~10 km)** spatial resolution; **30-minute** temporal resolution (aggregable to daily/monthly). V07 integrates TRMM + GPM eras (**1998–present**; verify exact subproduct start date before ingestion). Global grid (highest calibration reliability **60°N–60°S**). Formats: HDF5, NetCDF, GeoTIFF, GEE.
- **Practical usefulness:** Quantifies **seasonal rainfall totals, onset/cessation reliability, consecutive dry days (dry spells), and intense storm events** (e.g., > 30–50 mm/day or 30-min peak intensity driving erosion). *Concrete example:* Using IMERG Final V07 daily data (2001–2025), detecting that 40% of > 40 mm/day storms occur in November–December—when Landsat/Sentinel-2 shows bare soil—quantifies high seasonal erosion exposure and prioritizes pre-planting cover crops. Complements SMAP, SRTM, and NASA POWER.
- **Limitations:** ~10 km resolution smooths localized convective storms and can exhibit bias in complex mountainous terrain; 3.5-month latency for *Final Run*. Cannot alone tell whether rainfall infiltrated or ran off.
- **Evaluation:** **HIGH PRIORITY.** Highest-frequency global precipitation dataset for rainfall reliability and erosivity analysis.

#### 3. Landsat
- **Identification:** **USGS / NASA** Landsat 8 (OLI/TIRS) and Landsat 9 (OLI-2/TIRS-2), plus historical Landsat 4/5/7. Recommended products: **Collection 2 Level-2 Science Products (L2SP)** — Surface Reflectance (SR) and Surface Temperature (ST), with `QA_PIXEL` and `QA_RADSAT`. Accessed via [EarthExplorer](https://earthexplorer.usgs.gov/), STAC APIs (USGS/Planetary Computer/AWS), AppEEARS (`HLSL30`), and GEE (`LANDSAT/LC08/C02/T1_L2`, `LC09/C02/T1_L2`).
- **What it measures:** Atmospherically corrected **surface reflectance** (Coastal, Blue, Green, Red, NIR, SWIR-1, SWIR-2) and **Surface Temperature (ST)** derived from Thermal Band 10. Direct optical/thermal observations corrected for atmosphere, enabling NDVI, EVI, NDWI, and bare-soil/residue indices (BSI, NDTI).
- **Technical characteristics:** **30 m** optical resolution; thermal band captured natively at **100 m** and resampled to **30 m** in L2SP (effective thermal resolution remains 100 m). **8-day combined revisit** (L8+L9; 16 days individually). Archive from **1984** (L8 from 2013; L9 from 2021). Global land coverage; COG GeoTIFF.
- **Practical usefulness:** Core **field-scale (30 m)** historical record to detect **bare-soil windows**, multi-year cropping intensity (single vs. double cropping), intra-field heterogeneity, and thermal stress during past droughts. *Concrete example:* Analyzing 2014–2025 Landsat 8/9 imagery masked with `QA_PIXEL` reveals ~130 days/year with NDVI < 0.25 and elevated BSI between April and September, quantifying an unprotected fallow window suitable for a cover crop. Complements Sentinel-2 (forming ~2–3 day revisit via HLS), SRTM, and SMAP.
- **Limitations:** **Cloud cover** severely limits clear observations during wet tropical seasons; 30 m pixels mix edges on very small plots (< 0.5 ha). Cannot identify exact crop species alone without ground/auxiliary classification (e.g., CDL/MapBiomas).
- **Evaluation:** **HIGH PRIORITY.** Unmatched multi-decade global 30 m optical + SWIR + thermal record.

#### 4. MODIS
- **Identification:** **NASA** MODIS instruments on **Terra** (2000+) and **Aqua** (2002+), distributed by **LP DAAC** ([lpdaac.usgs.gov/products/](https://lpdaac.usgs.gov/products/)). Key products: **MOD13Q1/MYD13Q1** (250 m 16-day NDVI/EVI), **MOD13A1** (500 m 16-day), **MOD09GA** (500 m daily SR), **MOD11A2** (1 km 8-day LST), **MOD16A2GF** (500 m 8-day ET).
- **What it measures:** Surface reflectance, vegetation indices (**NDVI, EVI**), land surface temperature (**LST**), and modeled Penman-Monteith evapotranspiration (**MOD16**).
- **Technical characteristics:** **250 m, 500 m, and 1 km** grids; daily and 8/16-day composites; global coverage since **2000**. **Critical mission status (2025–2026):** Both Terra and Aqua have experienced orbital drift (shifting equator-crossing times) and are scheduled for **end of operations in late 2026 / early 2027**, with NASA officially advising transition to **VIIRS** for operational continuity.
- **Practical usefulness:** Useful for **25-year regional phenological baselines (2000–2025)** to measure how regional vegetation responded to historical severe droughts. *Concrete example:* Computing municipal-scale 2001–2025 EVI Z-scores from MOD13Q1 to contextualize whether recent stress is unprecedented compared to the 25-year norm.
- **Limitations:** **250 m–1 km pixels** (6.25–100 ha) mix fields, roads, and woodlots; orbital drift affects recent LST/reflectance comparability; approaching end-of-mission. Unsuitable for single-field management.
- **Evaluation:** **MEDIUM PRIORITY.** Strong 25-year regional baseline, but superseded by Sentinel-2/Landsat for fields and VIIRS for forward continuity.

#### 5. VIIRS
- **Identification:** **NASA / NOAA** VIIRS aboard **Suomi NPP** (2012+), **NOAA-20**, and **NOAA-21**, distributed by **LP DAAC** ([search.earthdata.nasa.gov/search?q=VIIRS](https://search.earthdata.nasa.gov/search?q=VIIRS)). Key products: **VNP13A1** (500 m 16-day NDVI/EVI/EVI2), **VNP09GA** (500 m/1 km daily SR), **VNP21A1D** (1 km daily daytime LST).
- **What it measures:** Surface reflectance, vegetation indices (NDVI, EVI, EVI2), and daytime/nighttime LST/emissivity.
- **Technical characteristics:** Native 375 m/750 m bands gridded to **500 m** (VNP13A1/VNP09GA) and **1 km** (VNP21A1D); daily and 16-day composites; **January 2012–present**; global; official successor to MODIS.
- **Practical usefulness:** Provides near-daily **regional anomaly monitoring** (EVI2 and daytime LST) when optical high-resolution sensors are cloud-obstructed. *Concrete example:* Tracking weekly VNP21A1D daytime LST anomalies across the surrounding agricultural district during heatwaves to flag regional thermal stress onset.
- **Limitations:** **500 m–1 km resolution** remains too coarse for individual farm fields or smallholders.
- **Evaluation:** **MEDIUM PRIORITY.** Important for post-MODIS continuity at regional scale, secondary to Sentinel-2/Landsat for field diagnostics.

#### 6. NASA POWER
- **Identification:** **NASA Langley Research Center (LaRC)** Prediction of Worldwide Energy Resources ([power.larc.nasa.gov](https://power.larc.nasa.gov/)), Agroclimatology community (`community=AG`). Direct keyless REST API (JSON, CSV, NetCDF, ICASA) plus `nasapower` (R) / `pynasapower` (Python).
- **What it measures:** **Assimilated meteorological reanalysis (MERRA-2)** (`T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`, `QV2M`, `WS2M`, `PS`, `PRECTOTCORR`, `GWETTOP`) and **satellite-derived solar irradiance (CERES)** (`ALLSKY_SFC_SW_DWN`, `ALLSKY_SFC_PAR_TOT`). Gridded model/satellite estimates, not local weather stations.
- **Technical characteristics:** **0.5° × 0.625° (~50 × 69 km)** for meteorology and **1.0° × 1.0° (~111 km)** for solar radiation. **Daily & monthly since 1981**; **hourly since 2001**; global, cloud-free, zero-auth REST API returning single-point time series in < 2 seconds.
- **Practical usefulness:** Supplies every input required for **FAO-56 Penman-Monteith Reference Evapotranspiration ($ET_0$)**, **Growing Degree Days (GDD)**, **frost risk ($T_{min}$)**, **heat-stress day counts ($T_{max} > \text{crop threshold}$)**, and 40+ year climate trends. *Concrete example:* One API call for 1995–2025 computes daily $ET_0$ and historical probability of > 34 °C heat stress during maize silking vs. sorghum flowering. Complements GPM IMERG (10 km rain) and SMAP.
- **Limitations:** **Very coarse grid (~50–100 km)** misses local convective rainfall, topographic cold pockets, and irrigation cooling effects. IMERG (10 km) or PRISM (4 km U.S.) better captures local rainfall than `PRECTOTCORR`.
- **Evaluation:** **HIGH PRIORITY.** Fast, free, global, 45-year daily record tailored for agroclimatic equations ($ET_0$, GDD, heat thresholds).

#### 7. SRTM — Shuttle Radar Topography Mission
- **Identification:** **NASA / NGA** SRTM Global 1 Arc-Second V3 (**SRTMGL1**, void-filled) via **LP DAAC / EarthExplorer** ([earthdata.nasa.gov/data/instruments/srtm](https://www.earthdata.nasa.gov/data/instruments/srtm)) and GEE (`USGS/SRTMGL1_003`).
- **What it measures:** Interferometric C-band radar **Digital Elevation Model (DEM)** (surface elevation from Feb 2000), from which **slope**, **aspect**, **flow accumulation**, and topographic wetness indices are derived.
- **Technical characteristics:** **1 arc-second (~30 m)** spatial resolution; absolute vertical accuracy better than **9 m (90% confidence)** (typically 5.6–9.0 m); coverage **60°N–56°S**; static; `.HGT` / GeoTIFF / GEE.
- **Practical usefulness:** Computes field-level **mean/max slope (%)** and runoff concentration zones for qualitative/relative **erosion risk (RUSLE $LS$-factor)** when combined with rainfall intensity (IMERG) and bare-soil cover (Sentinel-2/Landsat). *Concrete example:* Detecting an average 9% slope combined with 4 months of bare soil triggers higher priority for dense cover crops, contour planting, and permanent residue retention.
- **Limitations:** Static (year 2000, misses newer terraces/grading); vertical noise on very flat terrain (< 1–2% slope); omits latitudes > 60°N. Measures *topographic potential*, not actual soil loss.
- **Evaluation:** **HIGH PRIORITY.** Essential, lightweight 30 m global terrain layer for erosion-risk differentiation.

#### 8. ECOSTRESS
- **Identification:** **NASA / JPL** ECOSTRESS aboard the ISS ([ecostress.jpl.nasa.gov/data](https://ecostress.jpl.nasa.gov/data)), archived at **LP DAAC** and accessible via **AppEEARS**. Key products: V1 (`ECO2LSTE`, `ECO3ETPTJPL`, `ECO4ESIPTJPL`, `ECO4WUE`) and V2 MGRS COG tiles (`ECO_L2T_LSTE`, `ECO_L3T_JET` ET, **ESI** — Evaporative Stress Index, **WUE** — Water Use Efficiency).
- **What it measures:** Direct thermal infrared radiance converted to **Land Surface Temperature (LST)** and emissivity (`L2T_LSTE`), plus **modeled estimates** (PT-JPL algorithm + ancillary meteorology) of **ET**, **ESI** (actual/potential ET stress indicator), and **WUE**.
- **Technical characteristics:** **~70 m** spatial resolution (up to ~90 m at swath edges); **irregular revisit (~3–5 days average)** at **varying times of day** (precessing ISS orbit); **July 2018–present**; **52°N–52°S**; accessed via AppEEARS API or Earthdata Cloud COGs.
- **Practical usefulness:** Detects **early plant water stress / stomatal closure** at sub-field scale (~70 m) before visible yellowing. *Concrete example:* Identifying a field patch exhibiting 4 °C higher LST and ESI < 0.6 during summer heat peaks signals acute crop water stress, supporting transition to higher-WUE crops or residue mulching. Complements NASA POWER ($T_{air}$) and SMAP.
- **Limitations:** Variable time-of-day sampling complicates raw time-series comparisons; cloud-blocked; **asynchronous AppEEARS extraction queue** (minutes to hours) makes live on-the-fly user queries risky in a hackathon demo compared to pre-cached pilot studies.
- **Evaluation:** **MEDIUM PRIORITY.** High scientific value at 70 m, best used for pre-cached pilot demonstrations rather than live synchronous API queries.

#### 9. GEDI — Global Ecosystem Dynamics Investigation
- **Identification:** **NASA / University of Maryland** GEDI full-waveform LiDAR on the ISS ([gedi.umd.edu/data](https://gedi.umd.edu/data)). L1/L2 at **LP DAAC**; L3/L4 (`GEDI04_A` V3, `GEDI04_B` 1 km) at **ORNL DAAC**; GEE mirrors V2/2.1 (`LARSE/GEDI/...`).
- **What it measures:** Active laser waveforms estimating **canopy height (RH metrics)**, vertical foliage profiles/LAI (L2B), and **modeled woody aboveground biomass density** (AGBD, $\mathrm{Mg/ha}$, L4A).
- **Technical characteristics:** **~25 m circular footprints** spaced 60 m along-track and **~600 m cross-track** (non-wall-to-wall sampling); **51.6°N–51.6°S**; **April 2019–March 2023** + **resumed April 2024–present** (hibernation gap in between).
- **Practical usefulness:** Minimal direct value for annual crop rotations—designed for 3D forest structure and carbon stocks. Potentially useful only to map tall windbreaks, riparian buffers, or agroforestry tree layers bordering fields. *Concrete example:* Checking whether perennial tree belts (> 5 m canopy) exist around silvopastoral or agroforestry plots.
- **Limitations:** **600 m gaps between tracks** leave many fields completely unsampled; herbaceous crops (< 1–2 m) blend into ground return pulses; 2023–2024 operational hiatus.
- **Evaluation:** **LOW PRIORITY.** Forest-oriented sampling mission; unsuitable for crop rotation planning.

#### 10. NLDAS / GLDAS — Land Data Assimilation Systems
- **Identification:** **NASA GSFC** LDAS systems at **GES DISC** ([disc.gsfc.nasa.gov](https://disc.gsfc.nasa.gov/), via [earthdata.nasa.gov](https://www.earthdata.nasa.gov/)). Products: **GLDAS_NOAH025** (2.0: 1948–2014; 2.1: 2000–present; 2.2: GRACE-assimilated 2003+) and **NLDAS-2** (`NLDAS_FORA0125`, Noah/VIC/Mosaic/SAC). Also on GEE (`NASA/GLDAS/V021/NOAH/G025/T3H`).
- **What it measures:** **Land-surface model (LSM) outputs** driven by observational forcing without cloud gaps: **multi-layer soil moisture** (Noah: 0–10, 10–40, 40–100, 100–200 cm), soil temperature, surface/subsurface **runoff**, evaporation, and surface energy fluxes.
- **Technical characteristics:** **GLDAS:** Global (60°S–90°N), **0.25° (~25 km)** or 1°, **3-hourly** and monthly, **1948–present** (2.0+2.1). **NLDAS-2:** North America (~25°N–53°N, 125°W–67°W), **0.125° (~12 km)**, **hourly**, **1979–present** (2–4 day latency).
- **Practical usefulness:** Fills pre-SMAP historical gaps (pre-2015) and provides continuous **runoff** and **deep-layer (1–2 m) soil moisture** series. *Concrete example:* Using GLDAS-2.1 (2000–2025) to extend drought-frequency statistics to 25 years and track seasonal runoff spikes alongside IMERG.
- **Limitations:** Coarse resolution (25 km global / 12 km North America); model-dependent soil assumptions; cannot resolve field-level irrigation or tillage.
- **Evaluation:** **MEDIUM PRIORITY.** Strong gap-filler and pre-2015 hydrological archive, though largely overlapped by **NASA POWER + SMAP L4** in a minimal MVP.

---

### B. USDA, USGS and Other Agricultural Data

#### 11. USDA Ag Data Commons
- **Identification:** **USDA National Agricultural Library (NAL)** open research data repository ([data.nal.usda.gov](https://data.nal.usda.gov) / [nal.usda.gov/services/agdatacommons](https://www.nal.usda.gov/services/agdatacommons)).
- **What it measures:** Heterogeneous collection of **experimental field-trial datasets** from USDA-funded research (soil water storage, bulk density, aggregate stability, multi-year rotation trial yields, cover crop experiments, phenology).
- **Technical characteristics:** Non-uniform schemas/formats (CSV, Excel, ZIP, shapefiles); mostly U.S. experimental stations; downloadable via persistent DOIs rather than a unified spatial query API.
- **Practical usefulness:** **Offline scientific reference** to calibrate or justify agronomic rules (e.g., documenting empirical water-retention or organic-matter effects of cover crops from ARS trials). *Concrete example:* Grounding rotation soil-health coefficients in published LTAR/ARS trial datasets.
- **Limitations:** Not spatially continuous; non-standardized schemas; unsuitable for real-time farm-by-farm querying.
- **Evaluation:** **LOW PRIORITY.** Offline reference library only.

#### 12. Web Soil Survey (WSS)
- **Identification:** **USDA NRCS** interactive web application ([websoilsurvey.nrcs.usda.gov/app/](https://websoilsurvey.nrcs.usda.gov/app/)) serving **SSURGO** and **STATSGO2** soil surveys.
- **What it measures:** Field-mapped and lab-analyzed soil properties: texture, organic matter, available water capacity, hydrologic soil group (A–D), drainage class, erodibility (K-factor), pH, and suitability ratings.
- **Technical characteristics:** Inherits SSURGO scale (**1:12,000–1:63,360**, typically 1:24,000); **U.S. and territories only**; **interactive browser workflow** (draw AOI, export ZIP/PDF) — programmatic automation uses **Soil Data Access (SDA)** (see #15).
- **Practical usefulness:** Quick human exploration and verification of U.S. pilot farms' soil profiles and limitations.
- **Limitations:** U.S.-only; manual UI (not an API).
- **Evaluation:** **MEDIUM PRIORITY** (as exploration portal; **SDA API #15** is the programmatic path for U.S. sites).

#### 13. Cropland Data Layer (CDL) — CropScape
- **Identification:** **USDA NASS** Cropland Data Layer via **CropScape** (GMU CSISS, [nassgeodata.gmu.edu/CropScape/](https://nassgeodata.gmu.edu/CropScape/), dev guide [here](https://nassgeodata.gmu.edu/CropScape/devhelp/help.html)), GEE (`USDA/NASS/CDL`), and Planetary Computer.
- **What it measures:** **Annual satellite-derived crop-specific land cover classification** (corn, soybeans, winter wheat, cotton, alfalfa, fallow/idle cropland, pasture, etc.) trained with FSA farmer reports.
- **Technical characteristics:** **30 m** raster (2006–2007: 56 m); **annual**; wall-to-wall **CONUS from 2008–present** (pilots from 1997; Hawaii preview); **U.S.-only**; REST API (`GetCDLData`, `GetCDLStatData`, WMS) and instant GEE querying.
- **Practical usefulness:** **Automated baseline rotation reconstruction** in the U.S.! *Concrete example:* Querying 2018–2024 CDL for an Iowa/Kansas polygon automatically extracts the sequence (`Corn → Corn → Soy → Corn`) and flags multi-year monoculture without manual user entry.
- **Limitations:** **Unavailable outside the U.S.**; annual resolution can miss short winter cover crops or double crops; classification errors occur on minor crops or small fields.
- **Evaluation:** **HIGH PRIORITY (for U.S. locations)** / **Not applicable outside the U.S.**

#### 14. PRISM Climate Data
- **Identification:** **PRISM Climate Group** (Oregon State University, [prism.oregonstate.edu](https://prism.oregonstate.edu/)).
- **What it measures:** Topographically aware **interpolated climate grids**: precipitation (`ppt`), `tmin`, `tmean`, `tmax`, dewpoint (`tdmean`), `vpdmin`/`vpdmax`, and solar radiation normals.
- **Technical characteristics:** **4 km** (publicly free) and **800 m** grids; **daily (1981–present)**, **monthly (1895–present)**, **1991–2020 normals**; **CONUS-restricted** (partial AK/HI/territories); HTTPS web services (COG/ZIP), point explorer (up to 500 points), R `prism` / Python scripts.
- **Practical usefulness:** Higher spatial fidelity than NASA POWER (~50 km) in complex U.S. terrain for **frost dates, VPD atmospheric dryness, and local precipitation gradients**. *Concrete example:* Computing exact 30-year last-spring/first-fall frost dates at 4 km for a U.S. orchard or grain farm.
- **Limitations:** **U.S.-only**; lacks daily wind speed/radiation variables needed standalone for full Penman-Monteith $ET_0$.
- **Evaluation:** **MEDIUM PRIORITY (U.S. only)**; replaced globally by NASA POWER + ERA5.

#### 15. SSURGO / STATSGO2 — USDA NRCS Soil Data
- **Identification:** Official **USDA NRCS** soil databases ([nrcs.usda.gov/resources/data-and-reports/soils](https://www.nrcs.usda.gov/resources/data-and-reports/soils)), queried programmatically via **Soil Data Access (SDA)** ([sdmdataaccess.nrcs.usda.gov](https://sdmdataaccess.nrcs.usda.gov/)).
- **What it measures:** Field-surveyed soil map units and horizon tables: sand/silt/clay %, **organic matter (%)**, **available water capacity (`awc`)**, **hydrologic soil group (`hydgrpdcd`: A–D)**, drainage class (`drclassdcd`), **erodibility `kwfact`**, pH, and depth to restrictive layers.
- **Technical characteristics:** **SSURGO:** **1:12,000–1:63,360 (mostly 1:24,000)** — farm/field suitable. **STATSGO2:** **1:250,000** (1:1,000,000 AK) — generalized regional/basin planning only, **too coarse for field rotation decisions** when SSURGO exists. **U.S. & territories only.** SDA accepts T-SQL spatial/tabular REST/SOAP queries and OGC WFS/WMS.
- **Practical usefulness:** Supplies root-zone water-holding capacity and infiltration properties satellites cannot see. *Concrete example:* A single SDA SQL query for a field polygon retrieves Hydrologic Group C (slow infiltration), `kwfact = 0.37`, and `awc = 0.14 cm/cm`, calibrating root-zone storage capacity in the water-balance model.
- **Limitations:** **Strictly U.S.-only**; reflects historical pedological survey baselines rather than recent management-induced changes in surface organic matter or compaction.
- **Evaluation:** **HIGH PRIORITY (for U.S. locations)**; replaced by **SoilGrids / Embrapa** outside the U.S.

#### 16. NAIP — National Agriculture Imagery Program
- **Identification:** **USDA FSA** aerial imagery ([naip-usdaonline.hub.arcgis.com](https://naip-usdaonline.hub.arcgis.com/)), also on GEE and Planetary Computer.
- **What it measures:** High-resolution leaf-on **RGB + NIR aerial orthophotos**.
- **Technical characteristics:** **0.6 m** GSD (2018+; 1 m earlier); **~2–3 year revisit cycle**; **CONUS** (+ recent HI/PR/USVI additions).
- **Practical usefulness:** Visual verification of field boundaries, terraces, or gullies in U.S. case studies; **useless for seasonal or annual rotation tracking** due to 2–3 year frequency.
- **Limitations:** U.S.-only; multi-year latency; heavy file sizes for minimal analytical gain over Sentinel-2 (10 m every 5 days).
- **Evaluation:** **LOW PRIORITY.**

#### 17. NLCD — National Land Cover Database
- **Identification:** **USGS / MRLC** ([usgs.gov/.../national-land-cover-database](https://www.usgs.gov/centers/eros/science/national-land-cover-database)).
- **What it measures:** 16-class **Anderson Level II land cover** from Landsat (separating `Cultivated Crops`, `Pasture/Hay`, forest, wetlands, urban, barren).
- **Technical characteristics:** **30 m**; **U.S.-only**; **Annual NLCD covers 1985–2025**.
- **Practical usefulness:** Landscape context (confirming cropland vs. pasture/urban conversion over decades), but **does not distinguish crop species**.
- **Limitations:** U.S.-only; completely superseded by **CDL** for crop rotation analysis.
- **Evaluation:** **LOW PRIORITY.**

#### 18. CoCoRaHS — Community Collaborative Rain, Hail and Snow Network
- **Identification:** Volunteer rain-gauge network ([cocorahs.org/Maps](https://www.cocorahs.org/Maps)), export endpoint (`data.cocorahs.org/cocorahs/export/exportreports.aspx`), and Data Explorer ([dex.cocorahs.org](https://dex.cocorahs.org)).
- **What it measures:** Direct **manual rain-gauge precipitation** (rain, hail, snow) reported daily by volunteers.
- **Technical characteristics:** Sparse point stations; **U.S., Canada, Puerto Rico, Bahamas, USVI**; CSV/XML HTTP export (`&Units=Metric`) and NOAA GHCN-Daily ingestion.
- **Practical usefulness:** Optional local ground-truth check against GPM IMERG where a nearby volunteer gauge exists in North America. *Concrete example:* Displaying nearest-station gauge totals alongside IMERG to quantify local satellite bias.
- **Limitations:** Geographic restriction; uneven rural station density; missing weekend/holiday observations.
- **Evaluation:** **LOW PRIORITY.**

#### 19. USGS NWIS — National Water Information Systems
- **Identification:** **USGS** hydrological monitoring ([waterdata.usgs.gov/nwis](https://waterdata.usgs.gov/nwis)), modernized via **USGS Water Data APIs** ([api.waterdata.usgs.gov](https://api.waterdata.usgs.gov/)) and `dataretrieval` (Python) / `dataRetrieval` (R).
- **What it measures:** Direct **in-situ streamflow, river stage, groundwater well levels, and water quality**.
- **Technical characteristics:** Point gauges/wells; 15-min continuous and daily series; **U.S. & territories only**; open REST/OGC API (optional free key for higher rate limits).
- **Practical usefulness:** Contextualizing **aquifer depletion or basin streamflow restrictions** for irrigated farms in the U.S.
- **Limitations:** U.S.-only; point stations do not measure field soil moisture; sparse groundwater wells in many agricultural counties.
- **Evaluation:** **OPTIONAL / FUTURE.**

#### 20. USDA AMS Market News
- **Identification:** **USDA Agricultural Marketing Service** ([ams.usda.gov/market-news](https://www.ams.usda.gov/market-news)), **MyMarketNews / MARS API** ([mymarketnews.ams.usda.gov](https://mymarketnews.ams.usda.gov/)).
- **What it measures:** Daily/weekly **commodity prices, cash bids, and market volume** (grains, specialty crops, cotton, organic, livestock/forage).
- **Technical characteristics:** U.S. market hubs; REST JSON API (`marsapi.ams.usda.gov/services/v1.2/reports`); requires free registration + personal API key.
- **Practical usefulness:** Benchmarking regional gross crop price levels or price volatility for economic suitability in U.S. markets.
- **Limitations:** U.S.-only; heterogeneous report schemas (`slug_id` parsing); regional spot prices omit farm-specific input costs, transport, and local contracts.
- **Evaluation:** **OPTIONAL / FUTURE.**

#### 21. USDA NASS QuickStats
- **Identification:** **USDA NASS** ([quickstats.nass.usda.gov](https://quickstats.nass.usda.gov/), API at [quickstats.nass.usda.gov/api](https://quickstats.nass.usda.gov/api)).
- **What it measures:** Official county/state/national **planted/harvested area, yield, production, and prices**.
- **Technical characteristics:** Administrative aggregation (County/State/National); annual/monthly/5-year census; **U.S.-only**; free API key with **50,000-row cap per request** (`get_counts/` helper).
- **Practical usefulness:** Checking **regional market adoption and county yield baselines** in the U.S. *Concrete example:* Querying top county crops over 10 years to confirm local supply-chain viability and compare drought-year vs. normal-year county yields.
- **Limitations:** U.S.-only; county averages hide field-level variance; privacy suppression `(D)` in counties with few growers.
- **Evaluation:** **MEDIUM PRIORITY (U.S. only)**.

#### 22. OpenET
- **Identification:** **OpenET** consortium ([openetdata.org](https://openetdata.org/) / [etdata.org](https://etdata.org/)). Also includes an international collaborative initiative **OpenET-Brazil** (UFRGS + NASA + USGS + ANA).
- **What it measures:** **Field-scale actual evapotranspiration ($ET_a$)** computed as an outlier-filtered **ensemble of 6 Landsat-driven models** (ALEXI/DisALEXI, eeMETRIC, geeSEBAL, PT-JPL, SIMS, SSEBop).
- **Technical characteristics:** **30 m** spatial resolution; **daily, monthly, annual (2000–present)**; operational API/Explorer covers **CONUS** (launched across 23 Western U.S. states, expanded across CONUS); free API with registration and acreage quotas. *(Verify public API endpoint coverage before relying on OpenET outside CONUS).*
- **Practical usefulness:** Directly answers **"how much water does the current crop actually consume?"** in mm/month. *Concrete example:* Extracting 2018–2024 monthly $ET_a$ for an irrigated or rainfed field to compute net consumptive deficit ($ET_a - P$) during peak summer.
- **Limitations:** Primarily U.S. operational API; acreage quotas; cloud gaps in Landsat reduce temporal fidelity during cloudy summers.
- **Evaluation:** **MEDIUM PRIORITY (HIGH PRIORITY if Western U.S./CONUS)**.

#### 23. USFS LANDFIRE
- **Identification:** **USDA Forest Service / DOI** ([landfire.gov](https://www.landfire.gov/)).
- **What it measures:** Wildfire fuel models, Existing Vegetation Type/Cover/Height (`EVT`/`EVC`/`EVH`), disturbance, and historical biophysical settings (`BpS`).
- **Technical characteristics:** **30 m**; **U.S.-only**; periodic versions.
- **Practical usefulness:** Negligible for crop rotations (agricultural lands are lumped into generic cropland/non-burnable fuel classes).
- **Limitations:** Built for wildfire and forest management, not agronomy; U.S.-only.
- **Evaluation:** **LOW PRIORITY.**

---

### C. Space Agency Partner Resources

#### 24. Copernicus Sentinel-2 — ESA
- **Identification:** **ESA Copernicus Sentinel-2 (A/B/C)** via **Copernicus Data Space Ecosystem (CDSE)** ([dataspace.copernicus.eu](https://dataspace.copernicus.eu/)), STAC/Process API, Planetary Computer, GEE (`COPERNICUS/S2_SR_HARMONIZED`), and NASA **HLS (`HLSS30`)**.
- **What it measures:** **Bottom-of-Atmosphere (L2A) surface reflectance** across **13 spectral bands**: RGB + NIR (**10 m**), **3 Red-Edge bands + narrow NIR + 2 SWIR bands (20 m)**, coastal/water vapor (**60 m**), plus Scene Classification Layer (`SCL`).
- **Technical characteristics:** **10 m / 20 m / 60 m**; **~5-day revisit at equator** (2–3 days mid-latitudes); global coverage (systematic L2A ~2017/2018–present).
- **Practical usefulness:** Best global free sensor at **field and smallholder scale (10–20 m)** for: (1) detecting **exact bare-soil vs. crop-cover periods** (NDVI 10 m + SWIR residue indices NDTI/BSI 20 m); (2) detecting **early chlorophyll/nitrogen stress** via Red-Edge (**NDRE**). *Concrete example:* Reconstructing a 5-year 10 m phenology timeline to measure exact planting, harvest, and bare-soil duration to within ~5–10 days.
- **Limitations:** Cloud obstruction in wet seasons (mitigated by combining with Landsat/HLS or Sentinel-1 SAR); no thermal band. Cannot identify crop species without training labels or user input.
- **Evaluation:** **HIGH PRIORITY.** Essential global 10 m field-scale engine.

#### 25. ERA5 — ECMWF Reanalysis
- **Identification:** **ECMWF / Copernicus C3S** `reanalysis-era5-single-levels` via **Climate Data Store (CDS)** ([cds.climate.copernicus.eu](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview)) and GEE (`ECMWF/ERA5/DAILY`, plus `ERA5_LAND` at ~9 km).
- **What it measures:** Global **numerical atmospheric reanalysis** assimilating decades of observations: 2 m temperature and dewpoint, 10 m wind, precipitation, solar/thermal radiation, potential evaporation, and volumetric soil water layers.
- **Technical characteristics:** **0.25° × 0.25° (~31 km)** (ERA5-Land: 0.1° / ~9 km); **hourly from January 1940–present** (~5-day latency); global; Python `cdsapi` (account + `~/.cdsapirc`, often queued/slow) or instant GEE mirrors.
- **Practical usefulness:** Best global dataset for **multi-decadal climate shift detection (1940–present)** and **hourly dewpoint/VPD** analysis. *Concrete example:* Comparing 2016–2025 against the 1981–2010 baseline to quantify shifting heat-stress days and delayed rainy-season onset.
- **Limitations:** ~31 km resolution; CDS API download queue is too slow for live on-demand web requests unless pre-cached or queried via GEE; NASA POWER offers much faster direct point REST access.
- **Evaluation:** **MEDIUM PRIORITY.** Valuable for long-term climate baselines and VPD, secondary to NASA POWER for rapid hackathon API integration.

#### Note on Extra Resource from Section 2: GRACE / GRACE-FO
- **Identification & measurement:** **NASA / GFZ** gravimetry missions measuring **Total Water Storage (TWS)** anomalies (groundwater + soil moisture + snow + surface water). Native footprint **~300–400 km** (Tellus Mascons 1°; assimilated **GRACE-DA-DM** at 0.25° global / 0.125° CONUS). Useful only for **macro-aquifer depletion context**, unsuitable for field-level rotation planning (**LOW PRIORITY / OPTIONAL**).

---

## 7. Geographic Coverage and Restrictions

### 7.1 Coverage Classification Matrix

| Geographic Scope | Challenge Datasets | System Design Implication |
|---|---|---|
| **1. Global (all land)** | Landsat, MODIS, VIIRS, NASA POWER, ERA5, Sentinel-2, GLDAS (60°S–90°N) | Work out-of-the-box for any agricultural coordinate worldwide |
| **2. Near-global (latitude bands)** | SMAP (global except frozen/dense forest), GPM IMERG (global; optimal calibration 60°N–60°S), SRTM (60°N–56°S), ECOSTRESS (52°N–52°S), GEDI (51.6°N–51.6°S) | Cover virtually all major agricultural zones globally |
| **3. North America** | NLDAS (~25°N–53°N), CoCoRaHS (U.S., Canada, Bahamas, PR/USVI) | Unavailable in South America, Europe, Africa, Asia |
| **4. United States only** | Web Soil Survey, SSURGO/STATSGO2, CDL/CropScape, PRISM, NAIP, NLCD, USGS NWIS, USDA AMS Market News, USDA NASS QuickStats, LANDFIRE, USDA Ag Data Commons (predominantly U.S.) | **Cannot be hard dependencies** for a global or Brazilian tool |
| **5. Specific U.S. states / regional** | OpenET (operational across Western U.S./23+ states & CONUS expansion; separate OpenET-Brazil pilot collaboration) | Requires coverage checks outside Western U.S./CONUS |

### 7.2 Equivalent Open Alternatives for Global and Brazilian Contexts *(listed separately; do not replace official resources)*

| Missing U.S. Capability | Global Open Equivalent | Brazil Open Equivalent |
|---|---|---|
| **SSURGO / Web Soil Survey** (Soils) | **SoilGrids 2.0 (ISRIC)** — 250 m global ML soil maps (clay, sand, silt, SOC, pH, bulk density) | **Embrapa PronaSolos / GeoInfo**, **Plataforma Saúde do Solo BR**, **MapBiomas Soil** (30 m SOC/texture) |
| **CDL / CropScape** (Crop history) | **ESA WorldCover** (10 m general land cover) / **GLAD Cropland** (30 m) — *do not separate annual crop species* | **MapBiomas Brasil** (30 m annual / 10 m recent collections separating soy, sugarcane, maize/temp crops, coffee, pasture) |
| **PRISM** (Fine climate/rain) | **CHIRPS v3** (UCSB, 0.05° / ~5 km, 1981–present, 60°N–60°S) + **ERA5-Land** (~9 km) | **INMET BDMEP** (ground weather stations) + **CHIRPS** (~5 km) |
| **OpenET** (30 m ET) | **FAO WaPOR** (Africa/Near East 250–30 m) or FAO-56 $ET_0 \times K_c$ scaled by NDVI | **OpenET-Brazil** (UFRGS/ANA/NASA/USGS) + POWER $ET_0$ × Sentinel-2 NDVI |
| **NASS QuickStats** (Ag stats) | **FAOSTAT / FAO GAEZ** | **CONAB** (via Python `agrobr`) + **IBGE PAM** |

### 7.3 Geographic Scope Considerations
- One possibility is a **global analytical core** built only from global datasets (for example **NASA POWER, GPM IMERG, SMAP L4, Sentinel-2/Landsat, SRTM, SoilGrids 250 m**), which would not depend on regional availability.
- **Regional adapters** could be added where regional data exist, for example **CDL + SSURGO** inside CONUS or **MapBiomas** inside Brazil.
- **Explicit assumption:** Outside regions with annual species-level crop maps (CONUS CDL or specific MapBiomas classes), the farmer must specify their **current crop rotation**, which also improves accuracy over automated classification on small fields.

---

## 8. Dataset Complementarity and Data Fusion

### 8.1 Redundancies vs. Synergistic Combinations

- **Overlapping variables (select best-fit to avoid bloat):**
  - *Precipitation:* GPM IMERG (~10 km, 30-min/daily) outperforms NASA POWER (~50 km), ERA5 (~31 km), and GLDAS (~25 km) in spatial detail and storm intensity globally; PRISM (4 km) outperforms IMERG for U.S. CONUS climatology.
  - *Optical Vegetation:* **Sentinel-2 (10–20 m) + Landsat (30 m) / HLS** outperforms MODIS (250–500 m) and VIIRS (500 m) for field boundaries and bare-soil detection.
  - *Agroclimatology:* **NASA POWER** offers instant global REST access for FAO-56 $ET_0$ and GDD, overlapping ERA5 unless pre-1981 records are needed.

- **High-value fusion combinations:**
  1. **SMAP L4 (0–100 cm) + GPM IMERG + Soil (SSURGO / SoilGrids):** High rainfall events paired with weak root-zone moisture gain on high-clay or sloped soils indicate runoff loss rather than effective infiltration.
  2. **Sentinel-2/Landsat (NDVI/BSI, 10–30 m) + SRTM Slope (30 m) + GPM IMERG (> 30 mm/day):** Pinpoints **erosion-critical windows** where bare soil coincides with intense rainfall on sloped fields.
  3. **ECOSTRESS (LST/ESI, 70 m) + NASA POWER ($T_{air}$, $ET_0$) + SMAP:** Separates atmospheric heat from actual crop water stress (elevated $LST - T_{air}$, depressed ESI) confirmed by regional root-zone deficits.
  4. **Landsat + Sentinel-2 (HLS / GEE harmonization):** Compresses effective optical revisit from 5–8 days to **~2–3 days**, critical for catching cloud-free windows during tropical rainy seasons.
  5. **NASA Earth Observations + CDL/MapBiomas + Farmer Input:** Satellites quantify *when* bare soil and stress occurred; historical crop maps or farmer input identify *which crop* experienced that stress.

---

## 9. Data Processing and Harmonization Strategy

### 9.1 Spatial, Temporal, and Format Harmonization

| Dimension | Heterogeneity | Harmonization Strategy |
|---|---|---|
| **Spatial resolution** | 10 m (Sentinel-2) up to 50–69 km (NASA POWER) | Maintain **two explicit analytical tiers**: (a) **Field Tier (10–30 m)** using zonal stats inside the farm polygon (NDVI, BSI, SRTM slope, soil); (b) **Regional Climate/Moisture Tier (9–50 km)** sampled at the polygon centroid with **explicit scale labeling** in the UI. |
| **Temporal cadence** | 30-min (IMERG), 3-hourly (SMAP L4), daily (POWER), 5–8 day (S2/Landsat), static (SRTM/Soil) | Aggregate dynamic time series onto a **unified 10-day (dekadal) and monthly calendar** across 5–10 years, while retaining **extreme-event counts** (e.g., days $> 34\,^\circ\text{C}$, days $> 30\text{ mm}$ rain). |
| **CRS** | Sinusoidal, EASE-Grid 2.0, UTM MGRS, WGS84 | Compute area/slope/zonal stats in local **UTM / Equal-Area** projections; serialize outputs in **WGS84 (`EPSG:4326`)** GeoJSON/JSON. |
| **Missing data / clouds** | Cloud/shadow gaps in optical/thermal imagery | Apply `SCL` (Sentinel-2) and `QA_PIXEL` (Landsat) masking, build monthly/dekadal composites, and compute **valid-observation percentage** as a data-confidence metric. |
| **Units & formats** | COG GeoTIFF, HDF5, NetCDF4, JSON; K vs °C; mm/h vs mm/day | Convert strictly to standard agronomic units: °C, mm/day or mm/month, volumetric moisture ($\mathrm{m^3/m^3}$) or percentile (0–100%), slope (%). |

> **Critical Resampling Caveat:** Resampling a 9 km SMAP pixel or ~50 km NASA POWER cell down to 10 m or 30 m **does not create new spatial information**. It merely duplicates or smoothly interpolates regional values onto smaller pixels. Therefore, coarse datasets must **never** be used to differentiate adjacent fields within the same farm; intra-farm differentiation must come strictly from 10–70 m sensors (Sentinel-2, Landsat, SRTM, ECOSTRESS, SSURGO).

### 9.2 Example Processing Pipeline and Possible Tools

Illustrative only: the stages, thresholds and tools below are examples of what could be done, not choices made by the team.

1. **Acquisition:** Options include `earthaccess` for NASA Earthdata (already used in `src/data`), `pystac-client` with STAC catalogs such as the Planetary Computer, the Google Earth Engine Python API (`earthengine-api`), and plain REST (`requests`/`httpx`) for NASA POWER and USDA SDA.
2. **Preprocessing:** Scale/offset calibration, cloud/cirrus/shadow masking (`SCL`, `QA_PIXEL`).
3. **Quality Control (QC):** For example, reject scenes with a high cloud fraction over the field polygon and track the valid-pixel fraction per month.
4. **Spatial Harmonization:** Zonal statistics (`mean`, `median`, `p10`, `p90`) inside the field GeoJSON for 10–30 m layers; centroid extraction for 9–50 km layers.
5. **Temporal Harmonization:** Dekadal (10-day) and monthly alignment over several years, for example with `pandas` / `xarray`.
6. **Feature Extraction:** NDVI, EVI, bare-soil/residue indices (BSI/NDTI), FAO-56 Penman-Monteith $ET_0$, GDD, standardized anomalies (Z-scores) for rain and root-zone soil moisture.
7. **Indicator Generation:** Bare-soil duration (days/year below an NDVI threshold), heat-stress windows, water-deficit windows ($P - ET_0$ and SMAP percentiles), relative topographic-pluvial erosion risk.
8. **Analytical Modeling:** A transparent water-balance and agronomic rule scoring could match field indicators against curated crop profiles.
9. **Explanation layer:** One option is to pass structured JSON metrics to a grounded explanation generator (an "SI" component, in the Space Apps sense) that translates trade-offs, evidence and uncertainty into plain language without fabricating numbers.
10. **Visualization:** Could be an interactive web map (for example Leaflet, MapLibre or Mapbox GL) plus seasonal and scenario comparison charts (for example ECharts, Plotly or Recharts).

### 9.3 Practical Access Summary

| Dataset | Auth Required? | Python / GEE Access | Full Download Needed? | Typical Query Latency |
|---|---|---|---|---|
| **NASA POWER** | None (open API) | Yes (`requests`) | No (lat/lon + dates) | < 2 s |
| **IMERG / SMAP L4 / Landsat / Sentinel-2 / SRTM** | Free GEE account (or Earthdata Login) | Yes (`earthengine-api` / STAC) | **No** (server-side polygon clip) | 5–20 s (instant if cached) |
| **SSURGO (U.S.)** | None (open SDA REST) | Yes (`requests` T-SQL) | No | 1–3 s |
| **SoilGrids (Global)** | None | Yes (GEE Community / WCS) | No | 1–5 s |
| **ECOSTRESS** | Yes (Earthdata Login) | Yes (AppEEARS async API) | No (subsetting) | **Minutes–hours** (async queue; pre-cache for demos) |

---

## 10. Agronomic Interpretation and Rotation Indicators

### 10.1 Separating Direct Measurements, Derived Indicators, and Agronomic Knowledge

| Crop / Rotation Characteristic | Inferable from Satellites? | Primary Source Required | Evidence Classification |
|---|---|---|---|
| **Water demand ($K_c$, $ET_c$)** | **Partially** (actual $ET_a$ for *current* crops via ECOSTRESS/OpenET; atmospheric demand $ET_0$ via POWER) | **FAO-56 ($K_c$ coefficients, stage lengths)** + NASA POWER | *Derived indicator + literature coefficient* |
| **Drought & heat tolerance** | **No for candidate crops** (only observed stress on *past/current* crops via NDVI/LST) | Agronomic crop tables (critical flowering temp thresholds) | *Agronomic parameterization* |
| **Ground cover & erosion protection** | **Yes for historical/current management** (NDVI, BSI/NDTI); **estimated** for alternatives | Sentinel-2/Landsat (observed) + canopy closure speed (literature) | *Indirect spectral measurement (past) + estimate (candidates)* |
| **Biological Nitrogen Fixation (BNF)** | **No!** Satellites cannot detect *Rhizobium* nodulation or soil N fixation | Botanical family / species traits (legumes vs. grasses) | *Agronomic hypothesis (requires inoculation & proper soil pH)* |
| **Organic matter (SOM) contribution** | **No directly** (satellites see aboveground greenness/residue, not stabilized soil carbon) | Residue biomass & C/N ratio literature + SoilGrids/SSURGO baseline | *Agronomic estimate / hypothesis* |
| **Rooting depth & soil structure** | **No** | Crop root architecture traits + soil texture/drainage | *Agronomic knowledge (requires field infiltration/pit check)* |
| **Nutrient cycling** | **No** | Deep-scavenging cover-crop literature | *Agronomic hypothesis* |
| **Pest & disease cycle interruption** | **No** (cannot diagnose causal pest from NDVI drops alone) | **Botanical family rotation rules** (avoiding back-to-back host families) | *Phytosanitary rule (requires grower's real pest history)* |
| **Forage potential** | **Partially** (off-season biomass vigor if already grazed/cut) | Dual-purpose crop profiles + farmer livestock goals | *Agronomic trait + user input* |
| **Growing-season compatibility** | **Yes (strong quantitative basis)** | Crop cycle length / GDD vs. frost-free & wet-season window | *Quantitative agroclimatic estimate* |
| **Market suitability** | **No** | Farmer local market input + QuickStats/AMS (U.S.) or CONAB (Brazil) | *External socioeconomic data* |

### 10.2 Indicator-to-Decision Relationship Matrix

| Environmental Observation | Data Type | Technical Interpretation | Potential Rotation Implication *(requires local validation)* |
|---|---|---|---|
| **SMAP L4 root-zone moisture < 25th percentile for > 4 weeks in second season** | Assimilated estimate (9 km) | Recurring root-zone water constraint during off-season / second-crop window | Favor short-cycle, drought-tolerant, low-$K_c$ crops (e.g., sorghum, millet, cowpea) or cover crops over water-demanding second maize |
| **Sharp NDVI drop + high LST / low ESI or $T_{max} > 34\,^\circ\text{C}$ during flowering** | Spectral/thermal observation + reanalysis | Acute thermal/water stress window for existing crop | Shift planting dates, select earlier-maturing cultivars, or introduce heat-tolerant species |
| **SRTM slope > 5–8% + bare soil (NDVI < 0.25) during IMERG storms (> 30 mm/day)** | Direct radar/optical + satellite rain estimate | High susceptibility to sheet/rill erosion and nutrient runoff | Insert fast-establishing cover crops, maintain residue cover (no-till), avoid long bare fallow |
| **Extended bare-soil periods (> 90 continuous days/year)** | Derived spectral index (10–30 m) | Reduced annual biomass input, higher soil surface heating, elevated evaporation loss | Test intensified rotations with off-season cover mixes or forage crops |
| **Multi-year repetition of same crop/family (CDL/MapBiomas or farmer input)** | Historical classification / user input | Narrow rotation increases nematode, soil-borne pathogen, and selective nutrient depletion risk | Alternate botanical families (e.g., Grass ↔ Legume ↔ Brassica/Cover) to break pest cycles |

---

## 11. Possible Solution Approaches

Neutral descriptions of three kinds of approach, in no particular order and without ranking. They are background material; the team has not chosen among them.

| | Approach A: Geospatial Monitoring + Rule-Based Engine | Approach B: Historical Time-Series + Predictive ML Modeling | Approach C: Multi-Criteria Decision Support with an Explanation Layer |
|---|---|---|---|
| **Mechanism** | Computes NASA indicators and applies deterministic `if-then` agronomic rules to flag risks and suggest crops | Trains ML models (for example Random Forest, XGBoost or LSTM) on historical crop maps, climate and county yields to predict suitability or yield | Extracts a NASA field/regional profile (water, heat, erosion, bare soil), simulates a water/phenology balance for $\ge 3$ rotations (baseline vs. alternatives), scores them against farmer priorities, and uses a grounded explanation layer for plain-language output |
| **Data needed** | Climate, soil, optical/terrain data and a crop trait table | A large set of labeled fields with yield and rotation outcomes | The inputs of A, plus farmer priority weights and a structured crop table |
| **Limitations** | Fixed thresholds do not capture trade-offs between farmer priorities | Labeled yield and rotation data are scarce outside a few regions; risk of leakage and overfitting; predictions are hard to validate where labels do not exist | Literature-based crop coefficients need local agronomic calibration before field use |
