# Team context (current state)

> Team notes — ideas and decisions are the team's; summaries assisted by AI.

_Updated Nov 16, 2026 at submission close. The dated Nov 14–15 planning notes below are preserved as history; current delivery status is recorded first. Read [docs/scope.md](../scope.md) for the original scope and [decisions.md](decisions.md) for dated decisions._

## Current delivery — 2026-11-16

- **Product:** Crop Helper, the web decision-support app for the official NASA Space Apps Challenge **Field Shift: Adapting Farms with NASA Data**. Public app: [https://crop-helper.pages.dev](https://crop-helper.pages.dev/).
- **Published web code:** Ravi reported that the live Pages build was generated from commit `37552552250d42a74f61a3a9ca1676a59a38693f`. This is the app revision published on 2026-11-16, not the current documentation branch HEAD.
- **NASA submission:** On 2026-11-16, Ravi confirmed the team submitted its NASA Space Apps entry. This is a team-reported completion status; this note does not assert independent access to the submission record.
- **Web and API:** Cloudflare Pages Direct Upload serves the static app. The current live build calls the product API at `https://field-shift-api.kindpebble-07cb9fe8.brazilsouth.azurecontainerapps.io`; Ravi/Satélite reported Azure Container Apps revision `field-shift-api--0000002` and image `cf835d52a54d`. This is an Azure trial service with a limited lifetime, not a commitment through the Jan 26, 2027 winners announcement.
- **Demo vs. live:** With empty `VITE_API_URL`, the app reads saved demo JSON from `apps/web/public/demo/`. The demo warns when a selected last crop was not applied to a saved result. With `VITE_API_URL` set, the app sends live requests and displays an error if the API is unavailable; it does not silently fall back to saved data. The static demo build remains the durable path after the trial API ends.
- **Inputs:** The UI has separate intended-crop and last-crop-grown fields. A known previous crop is sent in `previous_crops` and participates in the rules/cache key. Unknown history receives no score advantage and no pest-cycle claim; unsupported history is rejected rather than scored as if it were applied.
- **Limits:** The engine is deterministic decision support, not a yield or harvest predictor. The first-ranked strategy was unchanged in 45 of 45 historical backtest seasons. ZARC checks compare planting windows with the published zoning; they are not a guarantee of yield or suitability. The supported crop set is maize, beans and cassava. Any demo or live response must retain these limits.

The sections below retain the discovery and planning state recorded on Nov 14–15; their statuses are historical where they differ from the delivery status above.

## 1. Where we are

- **Challenge:** Field Shift: Adapting Farms with NASA Data. Team Nether, Aracaju local event.
- **Deadline:** Sun Nov 15, 2026, 23:59 BRT.
- **Project idea:** **Confirmed (Nov 14) by Ravi (Tech Lead) on behalf of the team; wording by Duda:** Brazilian family farming in Sergipe (Agreste & Semiárido), an initial two-interface concept (Telegram Bot + Web Dashboard) sharing one API, comparing >= 3 crop/rotation strategies including *consórcio*, with **projection and prescription** (what to do, not only how things are). See [decisions.md](decisions.md). The later priority decision defers the channel and audience until the engine is validated; the dashboard leads the demo. The PRD and epics are recorded in `_bmad-output/planning-artifacts/`.

## 2. Three fronts

To avoid building the wrong thing, the work is split into three fronts (decided Nov 14; see [decisions.md](decisions.md)):

| Front | What | Status |
|---|---|---|
| **A. Internal map** | Team tool to explore and validate data. No visual polish, **not judged**. Static site on Cloudflare Pages (`*.pages.dev`) with **pre-generated data and no API**; NASA GIBS layers live. | In progress (epic [#19](https://github.com/raviproenca/nether-field-shift-2026/issues/19)) |
| **B. Product** | **Nov 15 (Ravi):** the user is the **technical professional who leads planting decisions** (persona from discovery E7, [persona-discovery.md](../research/persona-discovery.md)); the only interface is the dashboard with an interactive analysis; the **Telegram bot and voice are out of v1**; the role of AI is decided after discovery. **Order (Nov 14, after mentor feedback):** (1) the **decision engine** (E1, #44–#47): in: the farmer's crops, soil, region, season and previous crops; out come rotation options with trade-offs, a planting schedule and dates per crop, water demand and pest-cycle break. (2) **Validation** that the engine is right: against ZARC (#48) and a historical backtest on 2–3 real Sergipe years (at least one wet and one dry), showing how each strategy would have done. (3) The **producer dashboard** with the comparison (E5), on the same API (`apps/api/`). (The Nov 14 note that the channel and audience would be decided after validation is superseded by the Nov 15 decision.) Crop photos are out of scope. Anything judges open works **without login**. | PRD, architecture and epics done; building E1 first |
| **C. Judges' delivery** | Project page on the Space Apps site (submission form), video ≤ 30 s or ≤ 7 slides, public links (demo, repo), all in English. | At the end; the checklist already exists |

**Shared by all three, worth investing in now:** the data layer (`src/data/`) and its snapshot format. An API (`apps/api/`) is **not** built for the internal map; it comes with front B, after the PRD, and serves the same snapshot format + Open-Meteo forecasts (Open-Meteo only in the product API, not in the internal snapshots). The internal map's layers and MapLibre GL component can be reused in the producer dashboard.

**Earlier architecture decisions (apply to bot/voice only if the channel is confirmed after validation):**
- Voice in the bot (decided): speech-to-text with `faster-whisper` (already used by the team; `small` or `medium` on CPU int8 is enough for short Brazilian Portuguese audio); text-to-speech with **Piper** (open source, runs locally, Brazilian Portuguese voice) **as a separate service** because of its GPL-3.0 license. No service with a trial or key that expires before Jan 26, 2027.
- Telegram sends voice as OGG/Opus; replies go back as short OGG/Opus.
- **Hosting (decided):** everything on Google Cloud (Global Offers credit): Cloud Run (API, bot, voice service), Vertex AI Gemini Flash for explanations with a template fallback, Google Speech-to-Text/Text-to-Speech (pt-BR, en) with Piper + faster-whisper as fallback. Budget alert at US$ 50, no GPU, secrets in env/Secret Manager.
- **Language (decided):** bot in Portuguese by default with an English option (voice too); producer dashboard in English by default with a PT-BR button.
- **Crops for v1 (decided):** corn, beans, cassava. Product name: still open.
- Forecasts: Open-Meteo in the demo; NASA GEOS-FP cited in the pitch. ZARC as a validation reference for planting windows.
- Validation with farmers: skipped during the hackathon; "next step" in the pitch.

## 2b. Earlier product direction (channel deferred)

The following records the concept before the latest priority change. It is historical context for the engine and data; the channel, voice and audience await confirmation after validation. Follow [docs/scope.md](../scope.md) for current work.

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

## 5. Roles and work split (Nov 14, latest decision)

The live [project board](https://github.com/users/raviproenca/projects/1) is authoritative for status and assignees. The priority and division below follow the decision recorded after the mentor feedback; see [docs/scope.md](../scope.md).

| Who | Current responsibility | Issues |
|---|---|---|
| **Lucas** (`@LucasFe3152`) and **Duda** (`@dudxyz`) | Decision engine, first on the critical path | E1 [#38](https://github.com/raviproenca/nether-field-shift-2026/issues/38), [#44–#47](https://github.com/raviproenca/nether-field-shift-2026/issues/44) |
| **Ravi** (`@raviproenca`) and **Gabriel** (`@gabrielchavesas`) | Validation after the engine: ZARC and historical backtest | [#48](https://github.com/raviproenca/nether-field-shift-2026/issues/48), [#79](https://github.com/raviproenca/nether-field-shift-2026/issues/79) |
| **Ravi** | Tech Lead; coordinates issues, approves and merges PRs. Product API, producer dashboard, deploy and judges' delivery | E2 [#39](https://github.com/raviproenca/nether-field-shift-2026/issues/39), E5 [#42](https://github.com/raviproenca/nether-field-shift-2026/issues/42), E6 [#43](https://github.com/raviproenca/nether-field-shift-2026/issues/43) |
| **Gabriel** | Internal-map front end; Telegram bot and voice remain in the Backlog until the engine is validated | [#15](https://github.com/raviproenca/nether-field-shift-2026/issues/15), E4 [#41](https://github.com/raviproenca/nether-field-shift-2026/issues/41) |
| **Guilherme** (`@guilhermevbagio`) | No assigned issue until Ravi gives a new direction | None |

The explanation epic [#40](https://github.com/raviproenca/nether-field-shift-2026/issues/40) has no assignee. Its template story [#52](https://github.com/raviproenca/nether-field-shift-2026/issues/52) is a prerequisite of the API recommendation [#53](https://github.com/raviproenca/nether-field-shift-2026/issues/53); it must be completed before #53, even though the rest of the explanation epic is later in the priority order. Ravi owns issue assignment; agents do not assign work on their own. The **Submission** milestone marks the demo's critical path.

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
