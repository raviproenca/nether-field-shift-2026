<!-- AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa -->

# Draft requirements — Field Shift: Adapting Farms with NASA Data

> **Draft proposal, idea not decided; front B is not built before the formal decision and the PRD.** Only [docs/team/decisions.md](team/decisions.md) counts as decided. Requirements for the farmer product (front B) are proposals for the PRD.

> **Status:** Draft requirements gathered from team discovery sessions ([docs/team/CONTEXT.md](team/CONTEXT.md), [docs/team/brainstorm-log.md](team/brainstorm-log.md), and [docs/team/decisions.md](team/decisions.md)) to support formal product definition and BMad planning.

---

## 1. Domain Context & Target Persona

### 1.1 Primary Persona: Brazilian Family Farmer (*Agricultor Familiar*)
- **Profile:** Smallholder farmer (1 to 20 hectares), primarily in regions vulnerable to shifting rainfall, drought, and soil degradation (such as Sergipe and the Brazilian Northeast).
- **Literacy & Digital Access:** Frequently faces functional illiteracy or difficulty reading dense technical reports, charts, and scientific terminology (e.g., *NDVI*, *evapotranspiration*, *soil moisture anomaly*). Comfortable using mobile messaging apps through **voice notes, photos, buttons, and location sharing**.
- **Connectivity:** Intermittent 3G/4G or low-bandwidth rural Wi-Fi. Heavy web apps or complex 3D maps fail in field conditions.
- **Secondary Persona:** Medium/larger agricultural producers or technical extension workers (ATER/cooperatives) who benefit from a detailed **Producer Web Dashboard** consuming the same backend API.

### 1.2 Core Farmer Activities in Crop Rotation
1. **Soil Diagnosis & Season Planning:** Assessing whether land is depleted ("tired soil"), compacted, or pest-ridden; balancing family subsistence crops (beans, cassava, maize), animal forage, and cash crops; dividing plots across flat lowlands and sloped terrain.
2. **Soil Preparation & Cover Cropping:** Managing crop residue (*palhada*/mulch) to retain moisture and reduce surface heat; planting nitrogen-fixing cover crops (*adubação verde*: *Crotalaria*, *Mucuna*, *feijão-de-porco*, *guandu*) instead of leaving fields bare between harvests.
3. **Planting & Climate Window Selection:** Distinguishing false early rains (*veranicos* / dry spells shortly after germination) from sustained soil moisture; arranging row spacing and contour planting (*plantio em nível*) on slopes to prevent erosion.
4. **Crop Maintenance & Stress Monitoring:** Observing heat stress, leaf wilting, pest recurrence from previous cycles, and managing scarce supplemental water (cisterns, ponds, wells).
5. **Harvest, Fallow & Transition:** Evaluating yield changes and immediately protecting the soil after harvest against solar baking or torrential runoff.

### 1.3 Key Pain Points Addressed
- **Loss of Traditional Rain Calendars:** Shifting temperatures and erratic rainfall invalidate generational planting dates, causing seed loss during unexpected dry spells (*veranicos*) or topsoil loss during extreme rain events.
- **Bare Soil Degradation:** Leaving fields exposed between seasons accelerates moisture loss, surface heating, erosion, and nitrogen depletion.
- **Improper Rotation Choices:** Repeating botanical families or selecting successor crops whose water demand exceeds residual soil moisture.
- **Scarce Technical Assistance:** Limited access to on-site agronomists when urgent planting or maintenance decisions must be made.
- **Technical & Connectivity Barriers:** Existing agricultural platforms require high bandwidth, desktop screens, and mastery of agronomic/geospatial jargon.
- **Zero Margin for Error:** Smallholders cannot risk family livelihood on opaque recommendations without clear explanations, trade-offs, and local validation guidance.

---

## 2. Functional Requirements by Category

Each requirement is classified into one of four architectural pillars:
- **`[DATA]`** — Data Acquisition, Harmonization & Storage
- **`[DEV-BE]` / `[DEV-FE]`** — Software Development (Backend API, Telegram Bot & Web Frontends)
- **`[PRED]`** — Crop & Rotation Prediction / Decision-Support Engine
- **`[INFRA]`** — Infrastructure, Caching & Connectivity

---

### 2.1 Data Requirements (`[DATA]`)

| ID | Category | Requirement | Description & NASA / Local Sources |
|---|---|---|---|
| **REQ-DATA-01** | `[DATA]` | Agroclimatic Time-Series Ingestion | Fetch and process historical and near-real-time temperature, solar radiation, precipitation, and agroclimatic parameters via **NASA POWER** (`src/data/power.py`, 0.5° × 0.625°, no login required). |
| **REQ-DATA-02** | `[DATA]` | Precipitation & Extreme Event Tracking | Retrieve daily precipitation and detect dry spells (*veranicos*) or extreme rainfall events using **NASA GPM IMERG Late** (`GPM_3IMERGDL`, source `imerg` in `src/data/earthdata.py`, 0.1°). |
| **REQ-DATA-03** | `[DATA]` | Root-Zone & Surface Soil Moisture | Retrieve soil moisture profiles and anomalies using **NASA SMAP L3 Enhanced** (`SPL3SMP_E`, source `smap` in `src/data/earthdata.py`, 9 km) and **NASA GLDAS Noah 2.1** (`GLDAS_NOAH025_3H`, source `gldas` in `src/data/earthdata.py`, 0.25°, 3-hourly, including evapotranspiration and soil temperature). |
| **REQ-DATA-04** | `[DATA]` | Vegetation Health & Bare-Soil Detection | Compute and track vegetation indices (NDVI/EVI) to identify seasonal crop stress and periods when fields are left bare using **MODIS MOD13Q1** (250 m), **VIIRS VNP13A1** (500 m), **HLS L30/S30** (30 m), and **Sentinel-2 L2A** (10 m via Planetary Computer; ESA/Copernicus, third-party data, not NASA). MODIS and VIIRS provide NDVI/EVI directly; the toolkit returns **bands** for HLS and Sentinel-2, so NDVI must be computed from them. |
| **REQ-DATA-05** | `[DATA]` | Terrain Elevation & Slope Analysis | **Planned** (not in `src/data` yet). Extract elevation and slope gradients from **NASA SRTM** to assess runoff/erosion risk and guide spatial crop arrangement across flat vs. sloped plots. |
| **REQ-DATA-06** | `[DATA]` | Soil Properties & Regional Hydrology | **Planned** (not in `src/data` yet; license and credit go in the README when added). Integrate complementary soil texture/organic carbon baseline data (**SoilGrids**) and regional water availability references (**ANA** - Brazilian National Water Agency) alongside NASA datasets. |
| **REQ-DATA-07** | `[DATA]` | Multi-Resolution Spatial & Temporal Harmonization | Harmonize datasets with differing spatial (10 m to 0.5°) and temporal (3-hourly to 16-day) resolutions to a unified point/bounding-box query interface (`--point LAT,LON --radius-km N` or `--bbox`), including nearest-cell fallback for small farm plots. |
| **REQ-DATA-08** | `[DATA]` | Ground-Truth / Local Sensor Integration Hook | Support optional ingestion of local field measurements (e.g., farmer-reported soil type, rain gauge, or low-cost soil moisture/temperature sensor readings) to calibrate and validate coarse satellite observations. |

---

### 2.2 Crop & Rotation Prediction Requirements (`[PRED]`)

| ID | Category | Requirement | Description & Acceptance Criteria |
|---|---|---|---|
| **REQ-PRED-01** | `[PRED]` | Deterministic Agronomic Scoring Engine | Evaluate environmental suitability using deterministic, explainable water-balance, thermal-stress, and soil-health rules rather than opaque black-box models (complex ML yield prediction is scoped as future work). |
| **REQ-PRED-02** | `[PRED]` | Comparison of At Least 3 Rotation Strategies | For any queried farm location and current crop, generate and compare **at least three rotation strategies**: (1) **Baseline** (the farmer's current crop/rotation), (2) **Soil & Water Conservation Strategy** (e.g., nitrogen-fixing cover crops / consortia), and (3) **Resilient Income / Forage Strategy** (drought-tolerant cash or forage rotation). |
| **REQ-PRED-03** | `[PRED]` | Alignment with Farmer Priorities | Weight and rank rotation scenarios according to the farmer's stated priority: **water conservation**, **soil health / organic matter recovery**, **erosion reduction**, **pest-cycle disruption**, or **supplemental income / animal forage**. |
| **REQ-PRED-04** | `[PRED]` | Vulnerability & Bare-Field Window Detection | Automatically flag historical and seasonal windows when the field is typically left bare (low NDVI + high surface temperature) or when the current crop faces peak water/heat vulnerability. |
| **REQ-PRED-05** | `[PRED]` | Spatial Plot Arrangement & Maintenance Guidance | Recommend how to arrange crops on the terrain (e.g., contour planting on slopes, intercropping/strip-cropping, mulching) and provide actionable maintenance tips based on slope, soil moisture, and evaporative demand. |
| **REQ-PRED-06** | `[PRED]` | Seasonal Outlook & Forecast Integration | **Open question** (see [CONTEXT.md](team/CONTEXT.md)): NASA data is historical, and the source of forecasts is not decided. Proposal: combine historical NASA climate baselines and recent anomalies with short/medium-term weather forecast indicators so recommendations look forward rather than only reporting past rain. |
| **REQ-PRED-07** | `[PRED]` | Plain-Language AI Explanation & Uncertainty Disclaimers | Use an LLM/NLP layer strictly to translate deterministic outputs and scientific indicators (NDVI, evapotranspiration, SMAP anomalies) into accessible rural Portuguese (and English for judges), explicitly stating evidence, information gaps, satellite vs. ground differences, and where local agronomic validation is required. |

---

### 2.3 Development Requirements — Frontend & Backend (`[DEV-BE]` / `[DEV-FE]`)

| ID | Category | Requirement | Description & Acceptance Criteria |
|---|---|---|---|
| **REQ-DEV-BE-01** | `[DEV-BE]` | Shared REST API (`apps/api/`) | Implement a FastAPI backend exposing an OpenAPI contract FIRST, serving the farmer product from the shared `src/data/` toolkit and decision engine. Consumers: Telegram bot and producer web dashboard (front B). The internal team map (front A) does not use this API. |
| **REQ-DEV-BE-02** | `[DEV-BE]` | Point, Radius & Period Data Endpoints | Expose endpoints for each data source (`power`, `imerg`, `smap`, `gldas`, `modis`, `viirs`, `hls`, `planetary`) accepting latitude, longitude, radius (km), and date range, returning structured JSON with clear error messages on upstream failure. Consumers: Telegram bot and producer web dashboard (front B). |
| **REQ-DEV-BE-03** | `[DEV-BE]` | Rotation Recommendation Endpoint | Expose an endpoint that receives minimal farmer inputs (`latitude`, `longitude`, `current_crop`, optional `priority`, optional `soil_notes`) and returns the 3+ structured rotation strategies, evidence summary, and maintenance schedule. Consumers: Telegram bot and producer web dashboard (front B). |
| **REQ-DEV-BE-04** | `[DEV-BE]` | Telegram Bot Server-Side Webhook/Polling | Implement a Telegram bot controller capable of asynchronous conversational flows with minimal user input (location pin + crop selection via interactive buttons, text, or voice). |
| **REQ-DEV-BE-05** | `[DEV-BE]` | Voice-First Interaction (STT & TTS) | Process incoming Telegram voice messages (Speech-to-Text) from farmers with reading difficulties and reply with short, natural-sounding audio guidance (Text-to-Speech) alongside concise icon-based text and lightweight static images. **In scope** (Tech Lead decision, Nov 14, [decisions.md](team/decisions.md)). Notes for the PRD: STT with faster-whisper (small or medium, CPU int8), TTS with Piper PT-BR, OGG/Opus in both directions. Spike, Nov 14: Whisper small CPU int8 transcribed 5.5 s of audio in 1.2 s (1.1 s model load); Piper generated 5.5 s of audio in 0.4 s. |
| **REQ-DEV-FE-01** | `[DEV-FE]` | Internal Team Data Map (`apps/web/`) | Build a web map (Vite + React + TypeScript + MapLibre GL) with OpenStreetMap base tiles, region presets (`sergipe`, `nordeste`), NASA GIBS WMTS overlays (True Color, NDVI, IMERG, SMAP, LST, FIRMS), date selector, and a click-to-inspect time-series side panel. Front A: it **does not use the API and has no login**; point time series come from **pre-generated snapshots** in `apps/web/public/data/` (built by the `src/data` snapshot generator, #16), and the site sends `noindex`. |
| **REQ-DEV-FE-02** | `[DEV-FE]` | Producer Web Dashboard & Judge Demo Mode | Provide a public, login-free interactive web view (reusing map and chart components from `apps/web/`) where judges and larger producers can explore the 3+ rotation strategies, inspect NASA layer timelines, and test pre-loaded Sergipe farm scenarios with one click. |

---

### 2.4 Infrastructure Requirements (`[INFRA]`)

| ID | Category | Requirement | Description & Acceptance Criteria |
|---|---|---|---|
| **REQ-INFRA-01** | `[INFRA]` | Local Disk Caching for NASA Queries | Applies to both the product API (front B) and the snapshot generator for the internal map (front A). Cache all processed NASA API and Earthdata responses in `data/cache/` and `data/processed/` so repeated queries, bot demos, and dashboard interactions respond instantaneously even over slow event Wi-Fi or when NASA upstream services throttle requests. |
| **REQ-INFRA-02** | `[INFRA]` | Static Hosting on Cloudflare Pages | Deploy web frontends (`apps/web/`) to Cloudflare Pages (`*.pages.dev`) with automatic builds, HTTPS, and no expiring trial dependency. |
| **REQ-INFRA-03** | `[INFRA]` | Persistent Backend & Bot Hosting | Host the FastAPI service (`apps/api/`) and Telegram bot process on an always-available cloud runtime that remains live and publicly accessible without expiration through at least **January 26, 2027**. **Pending:** hosting for front B is decided after the idea ([decisions.md](team/decisions.md)); the choice must account for the CPU and RAM load of the voice pipeline (REQ-DEV-BE-05). |
| **REQ-INFRA-04** | `[INFRA]` | Environment-Based Secret & Auth Management | Manage NASA Earthdata credentials (`~/.netrc` with `0600` permissions or environment variables), Telegram Bot tokens, and AI API keys strictly via environment variables / platform secrets—never in Git. |
| **REQ-INFRA-05** | `[INFRA]` | Low-Bandwidth Payload Optimization | Restrict Telegram bot media attachments to compressed static visuals (< 100 KB) and compact voice notes (OGG/Opus) so farmers on weak 3G connections can receive full recommendations. |

---

## 3. Non-Functional Requirements (Development & Product Deployment)

### 3.1 Development Standards & Repository Governance (`NFR-DEV`)

| ID | Requirement | Specification |
|---|---|---|
| **NFR-DEV-01** | **Branch Protection & PR Workflow** | Never commit or push directly to `dev` or `main`. All work must be developed on `<type>/<name>-<task>` branches (lowercase, hyphens, no accents) and merged into `dev` via Pull Request after approval by the Tech Lead (`@raviproenca`). |
| **NFR-DEV-02** | **Language Policy** | All code, identifiers, comments, docstrings, commit messages, PR titles, UI labels (for judge-facing views), README, and documentation must be written in **English**. Conversational bot outputs for Brazilian farmers support Portuguese with an English demo toggle/transcript for judges. |
| **NFR-DEV-03** | **Conventional Commits** | All commits must follow the Conventional Commits specification in imperative English (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `style`, `perf`, `data`). |
| **NFR-DEV-04** | **Modular Architecture & Separation of Concerns** | Keep data acquisition (`src/data/`), agronomic/rotation logic, API transport (`apps/api/`), and UI presentation (`apps/web/`, bot handlers) strictly decoupled with small, single-responsibility functions and no dead code. |
| **NFR-DEV-05** | **Dependency Pinning & Justification** | All Python (`requirements.txt`, `requirements-dev.txt`) and frontend dependencies must have pinned versions. New dependencies must be justified in the PR description. |
| **NFR-DEV-06** | **Automated Testing & Quality Gates** | Backend modules and data pipelines must include `pytest` unit/integration tests; frontend code must pass type-checking and linting before opening a PR. |
| **NFR-DEV-07** | **AI Attribution & Brand Compliance** | Files or large blocks mostly generated by AI must include an attribution header (`# AI-assisted: generated with <tool>, reviewed by <name>`). AI-generated images must carry a visible watermark. Never use or modify NASA logos or branding. |
| **NFR-DEV-08** | **Open Source & Dataset Attribution** | Every NASA dataset, third-party API (e.g., Planetary Computer, OpenStreetMap, GIBS), and open-source library must be explicitly credited with links and licenses in `README.md` and UI footers. |

### 3.2 Deployment, Reliability & Space Apps Compliance (`NFR-DEPLOY`)

| ID | Requirement | Specification |
|---|---|---|
| **NFR-DEPLOY-01** | **Public Access with Zero Login Wall for Judges** | Every URL submitted to NASA Space Apps judges (producer web dashboard, demo links, Telegram bot, slides/video, repository) must open immediately **without any login, password, or registration wall**. |
| **NFR-DEPLOY-02** | **Link Longevity Until Jan 26, 2027** | All deployed services, domains, and demo links must remain online and functional until at least **January 26, 2027** (global winners announcement). Avoid 30-day cloud trials (e.g., Azure 30-day trial) or hackathon-only API keys (e.g., Meteomatics) for critical demo paths. |
| **NFR-DEPLOY-03** | **Graceful Degradation & Fault Tolerance** | Upstream NASA Earthdata or API timeouts, missing granules, or empty bounding boxes must be caught and returned as clear, user-friendly fallback messages or cached pre-computed Sergipe datasets—never causing an unhandled exception or crash during a live demo. |
| **NFR-DEPLOY-04** | **Download Size & Resource Guardrails** | Remote data requests must enforce bounding-box, date-range, and file-size guards (`src/data/`) so a single query cannot exhaust server memory or disk in production. Raw satellite files (`*.nc`, `*.hdf`, `*.tif`, `*.h5`) are never committed to Git. |
| **NFR-DEPLOY-05** | **Reproducible Local & Cloud Setup** | Both `apps/web/` and `apps/api/` must be runnable locally with a single documented command per service and configured solely via `.env` (modeled by `.env.example`). |
| **NFR-DEPLOY-06** | **Zero Secrets in Version Control** | Credentials, tokens, `.env`, and `~/.netrc` files are strictly git-ignored; `scripts/earthdata-login.sh` enforces `0600` file permissions. |
