# Team context (current state)

> Team notes — ideas and decisions are the team's; summaries assisted by AI.

_Last updated: Nov 14, 2026, 11:45 BRT. Read this and [decisions.md](decisions.md) before any task._

## 1. Where we are

- **Challenge:** Field Shift: Adapting Farms with NASA Data. Team Nether, Aracaju local event.
- **Deadline:** Sun Nov 15, 2026, 23:59 BRT.
- **Project idea:** **Confirmed (Nov 14):** Brazilian family farming in Sergipe (Agreste & Semiárido), two interfaces (Telegram Bot + Web Dashboard) sharing one API, comparing >= 3 crop/rotation strategies including *consórcio*. See [decisions.md](decisions.md). Unblocks `bmad-product-brief` and PRD.

## 2. Three fronts

To avoid building the wrong thing, the work is split into three fronts (decided Nov 14; see [decisions.md](decisions.md)):

| Front | What | Status |
|---|---|---|
| **A. Internal map** | Team tool to explore and validate data. No visual polish, **not judged**. Static site on Cloudflare Pages (`*.pages.dev`) with **pre-generated data and no API**; NASA GIBS layers live. | In progress (epic [#19](https://github.com/raviproenca/nether-field-shift-2026/issues/19)) |
| **B. Farmer product** | A **Telegram bot** (family farmers, `request_location`) and a **producer web dashboard** (larger farms, MapLibre GL + OSM), both on the same API (`apps/api/` + Open-Meteo). Anything judges open works **without login**. | **Idea confirmed (Nov 14):** ready for `bmad-product-brief` and PRD before implementation |
| **C. Judges' delivery** | Project page on the Space Apps site (submission form), video ≤ 30 s or ≤ 7 slides, public links (demo, repo), all in English. | At the end; the checklist already exists |

**Shared by all three, worth investing in now:** the data layer (`src/data/`) and its snapshot format. An API (`apps/api/`) is **not** built for the internal map; it comes with front B, after the PRD, and serves the same snapshot format + Open-Meteo forecasts. The internal map's layers and MapLibre GL component can be reused in the producer dashboard.

**Notes for the PRD and architecture (front B, not built yet):**
- Voice in the bot (decided): speech-to-text with `faster-whisper` (already used by the team; `small` or `medium` on CPU int8 is enough for short Brazilian Portuguese audio); text-to-speech with **Piper** (open source, runs locally, Brazilian Portuguese voice). No service with a trial or key that expires before Jan 26, 2027.
- Telegram sends voice as OGG/Opus; replies go back as short OGG/Opus.
- Voice adds CPU and RAM needs: include it in the hosting decision for front B.

## 2b. Confirmed product direction

- **Who:** Brazilian family farming (*agricultura familiar*) in Sergipe (Agreste & Semiárido) for the primary persona, plus larger farms/extension on the web dashboard.
- **Minimum input:** farmer's location (Telegram `request_location` or map pin) + current/intended crop + priority (water, soil, erosion, or income/forage); everything else is pulled from data.
- **Strategies:** compare **at least 3 crop/rotation strategies** (baseline + calculated alternatives including *consórcio*/intercropping and cover crops).
- **Delivery:** asynchronous messages through **Telegram Bot API** (hackathon demo; WhatsApp Cloud API as future work) and a **MapLibre GL + OpenStreetMap** web dashboard on the same API.
- **Data:** Global physical core `SMAP + GLDAS + IMERG + FAO-56` (+ NASA POWER, SRTM/NASADEM elevation/slope, HLS/Sentinel-2 NDVI) + **Open-Meteo** 15-day forecasts; local measurements for validation; **ANA HidroWeb** and complex ML scoped as future work.
- **Logic:** deterministic agronomic/water-balance calculations; AI only to explain the results in plain language with uncertainties/evidence.
- **Open for sign-off:** Language strategy (`EN` default + `PT-BR` toggle vs. English-first UI with subtitled PT-BR walkthrough) — see question #11 in [open-questions.md](open-questions.md).

Session-by-session notes: [brainstorm-log.md](brainstorm-log.md).

## 3. What already exists

**Data toolkit** in `src/data/` (see [src/data/README.md](../../src/data/README.md)):

```bash
uv venv -p 3.12 .venv && uv pip install -r requirements-dev.txt   # once
scripts/earthdata-login.sh                                         # once per machine; writes ~/.netrc (600)
.venv/bin/python -m src.data <source> [--bbox sergipe|nordeste|W,S,E,N | --point LAT,LON --radius-km N] \
  --start YYYY-MM-DD --end YYYY-MM-DD --variable NAME [--out PATH] [--search-only]
```

Tested against the real services (Nov 14, Sergipe):

| Source | Resolution | Status |
|---|---|---|
| `power` NASA POWER (no login) | 0.5° × 0.625° | ✅ OK |
| `gldas` GLDAS Noah 2.1, 3-hourly | 0.25° | ✅ OK |
| `imerg` GPM IMERG Late, daily | 0.1° | ✅ OK |
| `hls` HLS L30 / S30 v2.0 | 30 m | ✅ OK |
| `planetary` Sentinel-2 L2A (ESA/Copernicus, not NASA; no account) | 10 m | ✅ OK |
| `smap` SMAP L3 enhanced | 9 km | ✅ OK (fixed in #22) |
| `modis` MOD13Q1 NDVI | 250 m | ✅ OK (fixed in #22) |
| `viirs` VNP13A1 NDVI | 500 m | ✅ OK (fixed in #22) |

Earthdata Login: each person runs `scripts/earthdata-login.sh` in their own terminal. Never share or commit credentials.

## 4. Work split: internal data map (team tool, not the product decision)

Epic [#19](https://github.com/raviproenca/nether-field-shift-2026/issues/19). The internal map is a tool for the team to look at the data; it is **not** the product decision.

| Issues | Area | Who |
|---|---|---|
| [#12](https://github.com/raviproenca/nether-field-shift-2026/issues/12)–[#15](https://github.com/raviproenca/nether-field-shift-2026/issues/15) | Front end (`apps/web/`): setup, base map, NASA GIBS layers, point side panel (front A) | **Gabriel (Chaves)** |
| [#16](https://github.com/raviproenca/nether-field-shift-2026/issues/16)–[#18](https://github.com/raviproenca/nether-field-shift-2026/issues/18) | Snapshot generator (pre-built data in `apps/web/public/data/`), access choice, deploy to `*.pages.dev` | **Ravi**, with AI agents |

- **No API for the internal map** (decided Nov 14): the front end reads pre-generated JSON/GeoJSON files. The format (from the earlier API contract draft) is documented first, so the front end can build against it right away.
- The front-end setup (#12) is Gabriel's. The data side writes only to `apps/web/public/data/` (generated files).
- Access (#17, closed): **no login**; unlisted `*.pages.dev` URL with `noindex`. Deploy (#18) via GitHub Actions to Ravi's Cloudflare account, project name neutral (e.g. `nether-field-map`).

## 5. Roles

- **Ravi:** Tech Lead; approves and merges every PR.
- **Duda (Eduarda):** data (sources, organization, analysis).
- **Chaves (Gabriel):** screens (internal dashboard first).
- **Lucas (`@LucasFe3152`):** requirements and issues (`docs/requirements.md`).

## 6. Space Apps rules that matter

- The idea and decisions are the team's. AI must not come up with the idea.
- Everything public in English (video may be spoken in Portuguese with English subtitles).
- Demo: video ≤ 30 s or ≤ 7 slides. Over the limit = out of global judging.
- Every submitted link opens **without login or password** and stays valid **until Jan 26, 2027** (winners announcement). An internal team dashboard may have a login; anything judges open may not.
- Hosting for the demo and page: something that does not expire (GitHub Pages, Cloudflare Pages). Do not host it on trials such as Azure (30 days) or depend on offers that end with the hackathon (Meteomatics).
- Credit all NASA and third-party data, code and images; mark AI-generated content.

## 7. Global Offers (partner resources, read on Nov 14)

- **Useful:** Microsoft Planetary Computer (free, no account, STAC: Sentinel-2, Landsat, MODIS); free domain with 1 year of hosting and SSL; Google Cloud US$ 300 for 90 days (asks for a card, no auto-charge).
- **Risky for the Jan 26, 2027 rule:** Azure (US$ 200 for 30 days), Meteomatics (hackathon only).

## 8. Open questions

See [open-questions.md](open-questions.md).
