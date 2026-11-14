# Team context (current state)

> Team notes — ideas and decisions are the team's; summaries assisted by AI.

_Last updated: Nov 14, 2026, 11:40 BRT. Read this and [decisions.md](decisions.md) before any task._

## 1. Where we are

- **Challenge:** Field Shift: Adapting Farms with NASA Data. Team Nether, Aracaju local event.
- **Deadline:** Sun Nov 15, 2026, 23:59 BRT.
- **Project idea:** **under discussion, not decided.** Only what is in [decisions.md](decisions.md) counts as decided.

## 2. Three fronts

To avoid building the wrong thing, the work is split into three fronts (decided Nov 14; see [decisions.md](decisions.md)):

| Front | What | Status |
|---|---|---|
| **A. Internal map** | Team tool to explore and validate data. No visual polish, **not judged**. Static site on Cloudflare Pages (`*.pages.dev`) with **pre-generated data and no API**; NASA GIBS layers live. | In progress (epic [#19](https://github.com/raviproenca/nether-field-shift-2026/issues/19)) |
| **B. Farmer product** | A **Telegram bot** (family farmers) and a **producer web dashboard** (larger farms), both on the same API. Anything judges open works **without login** (demo mode in the dashboard; the bot open to anyone). | **Not started on purpose:** built only after the formal idea decision and the PRD (BMad) |
| **C. Judges' delivery** | Project page on the Space Apps site (submission form), video ≤ 30 s or ≤ 7 slides, public links (demo, repo), all in English. | At the end; the checklist already exists |

**Shared by all three, worth investing in now:** the data layer (`src/data/`) and its snapshot format. An API (`apps/api/`) is **not** built for the internal map; it comes with front B, after the idea decision, and can serve the same format. The internal map's layers and map component can be reused in the producer dashboard.

**Notes for the PRD and architecture (front B, not built yet):**
- Voice in the bot (decided): speech-to-text with `faster-whisper` (already used by the team; `small` or `medium` on CPU int8 is enough for short Brazilian Portuguese audio); text-to-speech with **Piper** (open source, runs locally, Brazilian Portuguese voice). No service with a trial or key that expires before Jan 26, 2027.
- Telegram sends voice as OGG/Opus; replies go back as short OGG/Opus.
- Voice adds CPU and RAM needs: include it in the hosting decision for front B.

## 2b. Direction under discussion (repeated and supported out loud; not decided)

- **Who:** family farming (agricultura familiar) in Brazil, with a well-defined persona.
- **Minimum input:** the farmer's location plus the crop; everything else is pulled from data.
- **Delivery:** asynchronous messages through a **Telegram bot (decided: Telegram for now; WhatsApp as future work)** and a more detailed web dashboard for larger farms, both on the same API.
- **Data:** NASA data, plus local measurements for validation (a field device or sensor was discussed).
- **Logic:** deterministic calculations; AI only to explain the results in plain language; complex ML as future work.
- **Open:** forecasts (the data is historical), and where they would come from.

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
| `smap` SMAP L3 enhanced | 9 km | 🔧 being fixed (wrong cell selected) |
| `modis` MOD13Q1 NDVI | 250 m | 🔧 being fixed (scale factor) |
| `viirs` VNP13A1 NDVI | 500 m | 🔧 being fixed (attribute read) |

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

## 5. Roles (as discussed; confirm in decisions.md)

- **Ravi:** Tech Lead; approves and merges every PR.
- **Duda (Eduarda):** data (sources, organization, analysis).
- **Chaves (Gabriel):** screens (internal dashboard first).
- **Requirements and issues:** one person gathers requirements and opens the issues (name to confirm).

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
