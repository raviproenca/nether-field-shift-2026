<!-- AI-assisted: drafted with Codex from the team's idea, recorded decisions and repository evidence; pending team review. -->

# Project submission copy

Prepared November 15, 2026. Copy the text under each field into the submission form. Editorial notes and the completion checklist are not submission text.

Editorial status: the team reports that Lucas Feitosa completed and checked the working version. This draft follows Gabriel's requested immersive-map presentation. The final deployed version, product name, form character limits and demo URL still need to be matched to this copy. Local evidence is from branch `feat/gabriel-plot-ux-ptbr`; this document does not certify the deployment.

## Project title

Nether — Field Shift

Editorial note: this uses the existing repository/team designation, not a newly chosen product name. Replace it if the team has selected a final name.

## High-level project summary

Nether helps agricultural professionals compare planting strategies for maize, beans and cassava in Sergipe, Brazil. An immersive map connects NASA observations of rainfall, soil moisture, vegetation, climate and terrain with a transparent decision engine. Users compare current practice with two alternatives, inspect planting calendars and water-demand estimates, and check proposed windows against Brazil's ZARC agricultural risk zoning. The prototype brings scattered evidence into one place to support informed planting decisions, with visible sources and limitations.

### Short summary alternative

An immersive map helps agricultural professionals in Sergipe compare three planting strategies using NASA data, inspect water demand and planting calendars, and check windows against Brazil's ZARC risk zoning.

## Detailed project description

### The problem and who we serve

Choosing what and when to plant requires combining information that is usually scattered across satellite products, climate records, crop profiles and agricultural risk zoning. Our initial focus is Sergipe, Brazil, including its Agreste and semi-arid regions. We support the technical professionals who guide planting decisions for farms, bringing environmental evidence and strategy comparisons into a shared view.

### What we built

Our prototype presents planting decision support through an immersive map. The underlying system combines pre-generated NASA data snapshots with a deterministic agronomic engine and a web API. It supports maize, beans and cassava and compares three strategy types: current practice, soil and water conservation, and income or forage resilience. Alternatives introduce companion crops alongside the selected crop.

The engine considers crop choice, previous crops, region, season, available soil information and the user's priority: water, soil, erosion or income. It returns ranked options, crop calendars, rule-based water-demand estimates, crop-family indicators and suggested actions with their evidence. These indicators describe the rules used; they are not measured pest outcomes or financial forecasts.

Users can inspect the environmental context behind the comparison, including rainfall, soil moisture, vegetation and terrain. Planting windows are checked against ZARC, Brazil's official agricultural climate-risk zoning. Our demonstration includes pilot locations in Itabaiana and Nossa Senhora da Glória, representing two different agricultural contexts within Sergipe.

### How NASA data supports the solution

NASA observations and modeled products provide the environmental foundation. GPM IMERG supplies rainfall estimates; SMAP supplies surface soil moisture; NASA POWER supplies meteorological and solar information; VIIRS vegetation indices describe vegetation conditions; GLDAS supplies land-surface context; and NASADEM supplies elevation used to derive slope. The interface links evidence to its source. These products have different dates and resolutions, so a selected map location should not be mistaken for a field sensor measurement.

Open-Meteo provides short-term forecast context separately from NASA observations. ZARC supplies a Brazilian reference for planting-window checks. We distinguish observations, forecasts and derived rule outputs rather than presenting them as interchangeable evidence.

### Validation and limitations

The team implemented ZARC checks and a historical backtest covering wet and dry conditions in Sergipe. The documented backtest returned the same first-ranked strategy in all 45 evaluated seasons. This exposes an important limitation: the ranking has not demonstrated useful sensitivity to year-to-year conditions. We present the prototype as a structured comparison of planting options, not as a harvest or yield prediction system.

Water-demand values come from crop profiles, and strategy scores reflect explicit rules and weights. They are not calibrated yield or profit predictions. Missing data and unavailable forecasts are reported. Field validation with farmers and agricultural professionals remains a next step; operational testing of the software does not establish agronomic effectiveness.

### Value and next steps

The prototype makes NASA evidence easier to inspect alongside planting options and local risk zoning. Its contribution is a reproducible, explainable comparison that a professional can question and discuss. Next steps are field validation, calibration of rules and water-demand estimates, and improvement of ranking sensitivity before broader use.

## NASA data resources

The following products are present in the committed Sergipe snapshots. Retain only those used by the final submitted version.

- **NASA POWER daily point API**, MERRA-2 and CERES SYN1deg, agricultural community: meteorological and solar context. https://power.larc.nasa.gov/ . Snapshot period: October 9–November 7, 2026. Record the retrieval date and service version from generation logs if available; do not substitute the snapshot period for the access date.
- **GPM IMERG Late daily precipitation V07**, `GPM_3IMERGDL`: rainfall estimates. https://doi.org/10.5067/GPM/IMERGDL/DAY/07
- **SMAP Enhanced L3 daily soil moisture V006**, `SPL3SMP_E`: surface soil moisture, 9 km. https://doi.org/10.5067/M20OXIZHY3RJ
- **GLDAS Noah monthly V2.1**, `GLDAS_NOAH025_M`: land-surface context, 0.25°. https://doi.org/10.5067/SXAVCZFAQLNO
- **VIIRS/NPP vegetation indices V002**, `VNP13A1`: 16-day vegetation indices, 500 m. https://doi.org/10.5067/VIIRS/VNP13A1.002
- **NASADEM V001**, `NASADEM_HGT`: elevation and derived slope, 1 arc-second. https://doi.org/10.5067/MEASURES/NASADEM/NASADEM_HGT.001

NASA data use guidance: https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance . Dataset citations and terms are recorded in the repository README.

If the submitted map shows live NASA GIBS layers, also credit **NASA GIBS / EOSDIS** and the exact displayed layer products, using the dataset-specific citations in the README. GIBS is an imagery service; its rendered imagery should not be described as an additional numerical input to the engine.

## Space agency partner and other resources / references

- **ZARC, MAPA / Embrapa**: Brazilian agricultural climate-risk zoning, used to check planting windows. The committed Sergipe reference includes maize and beans for 2026/2027 and perennial cassava records. Credit the relevant harvest year and portaria. Catalog: https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico . Catalog license: CC BY.
- **IBGE municipal boundaries**: municipality lookup for ZARC. Attribution: “Fonte: IBGE, Malha Municipal.” https://servicodados.ibge.gov.br/api/docs/malhas
- **IBGE PAM / SIDRA table 5457**: agricultural statistics used as historical comparison context. https://sidra.ibge.gov.br/tabela/5457 . Attribution: “Fonte: IBGE, Pesquisa Agrícola Municipal.” The repository has not yet verified the license terms; resolve that before including redistributed PAM data in the final materials.
- **Open-Meteo**: short-term weather forecasts and reference evapotranspiration context. https://open-meteo.com/ . Attribution: “Weather data by Open-Meteo.com”; CC BY 4.0, with service restrictions documented in the README.
- **FAO Irrigation and Drainage Paper 56**: reference methodology for evapotranspiration. https://www.fao.org/4/x0490e/x0490e00.htm
- **Microsoft Planetary Computer**: access service for NASADEM. https://planetarycomputer.microsoft.com/dataset/nasadem
- **OpenStreetMap contributors**: base-map data, ODbL. https://www.openstreetmap.org/copyright
- **Software**: Python/FastAPI API and TypeScript/React/Vite/MapLibre GL JS web application. Full library licenses and the agronomic literature cited by the engine are listed in https://github.com/raviproenca/nether-field-shift-2026#credits . Repository license: Apache-2.0.

Editorial note: HLS and Sentinel-2 toolkit support does not prove their use in the submitted demo. If Sentinel-2 is shown, add its exact Copernicus product citation and attribution from the README under non-NASA resources.

## Use of AI / SI tools

The project idea, intended users and product decisions came from the human team. AI tools assisted software development, tests, documentation, source-based research and critique of the implementation scope. Repository file headers identify assistance from Claude Code, Cursor and Antigravity. Codex assisted preparation of this submission text from the team's recorded work. AI-assisted files are marked in the repository, and review status is documented where applicable.

The recommendation engine uses deterministic rules and explicit weights. Generative AI does not determine its numerical scores or alter observations. A template-based explanation is available; we do not claim an active generative-AI explanation service in the submitted version without confirming it. The team remains responsible for checking the software, data attribution and submitted claims.

## Link to final project

https://github.com/raviproenca/nether-field-shift-2026

## Working application link

[TEAM TO INSERT: public URL of the exact version Lucas validated.]

## Link to project demo

[TEAM TO INSERT: public video or slide-deck URL. Follow the recorded team requirement of a video no longer than 30 seconds or a deck no longer than 7 slides; use English or English subtitles.]

### Optional demo narration

In Sergipe, planting decisions depend on scattered environmental information. Nether brings NASA rainfall, soil moisture, vegetation and terrain into an immersive map. Compare three crop strategies, inspect water demand and planting calendars, and check windows against Brazil's ZARC zoning. Every comparison includes evidence and limitations. We support planting decisions; we do not predict yields.

## Completion checklist — not submission text

- [ ] Confirm the final product title and actual form fields and character limits.
- [ ] Match the immersive-map description and features to the exact deployed build Lucas tested.
- [ ] Insert the application and demo URLs; test all submitted links without authentication.
- [ ] Retain only data products used by the final version; add exact GIBS layers if shown.
- [ ] Complete the POWER citation metadata and verify terms for any redistributed third-party data.
- [ ] Confirm AI-tool disclosures with every contributor and add any tools not yet documented.
- [ ] Have the team check the text, particularly the validation claims and known ranking limitation.
- [ ] Confirm link availability through January 26, 2027, and the demo duration or slide count.
- [ ] The human submitting the project must read and accept the actual terms and conditions.

## Evidence and submission requirements — not submission text

The NASA Space Apps organizing team's [November 9 answer](https://github.com/nasa/spaceapps/discussions/1858) lists title, high-level summary, demo link, final project link, detailed description, NASA and other data resources, AI/SI use and agreement to terms. The [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/) returned an access error during preparation; exact field limits remain unverified.

Project claims were checked against `README.md`, `docs/scope.md`, `docs/team/decisions.md`, `src/engine/recommend.py`, `apps/api/diagnosis.py`, and the attribution metadata in `apps/web/public/data/sergipe/`. Latest direction and operational completion were reported by the team in conversation.
