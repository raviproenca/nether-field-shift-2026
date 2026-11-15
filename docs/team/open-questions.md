# Open questions

> Team notes — ideas and decisions are the team's; summaries assisted by AI.

| # | Question | Raised | Owner |
|---|---|---|---|
| 1 | ~~Is there a **global** alternative to the USGS water-access dataset (US only)?~~ **Decided Nov 14:** Global core uses `SMAP + GLDAS + IMERG + FAO-56` (+ POWER, SRTM/NASADEM); **ANA HidroWeb** left as future Brazil expansion (see [decisions.md](decisions.md)). | 10:24 | — |
| 2 | ~~Where would **forecasts** come from? (current data is historical)~~ **Decided Nov 14:** **Open-Meteo** in the product API for the demo (non-commercial use); **NASA GEOS-FP** cited in the pitch (see [decisions.md](decisions.md)). | 11:15 | — |
| 3 | ~~Which other datasets beyond POWER, IMERG, SMAP, Sentinel-2, Landsat, SRTM, SoilGrids and ANA?~~ **Decided Nov 14:** Global core = `SMAP + GLDAS + IMERG + POWER + FAO-56 + SRTM/NASADEM + HLS/Sentinel-2 + Open-Meteo`; SoilGrids optional static baseline; ANA HidroWeb future work (see [decisions.md](decisions.md)). | 11:15 | — |
| 4 | ~~Can a WhatsApp bot ask for the user's location with a button?~~ **Decided Nov 14:** Hackathon demo uses **Telegram Bot API** (`request_location=True` reply keyboard button); **WhatsApp Cloud API** (interactive location request) is post-hackathon production expansion (see [decisions.md](decisions.md)). | 10:45 | — |
| 5 | ~~Demo channel: Telegram, WhatsApp or SMS?~~ **Decided Nov 14: Telegram for now** (see [decisions.md](decisions.md)). | 10:45 | — |
| 6 | ~~Which map API for the dashboards?~~ **Decided Nov 14: MapLibre GL + OpenStreetMap** (free, no key, Epic #19; see [decisions.md](decisions.md)). | 10:36 | — |
| 7 | ~~Who gathers the requirements and opens the issues?~~ **Decided Nov 14:** Ravi opens and coordinates issues; Lucas leads requirements (see [decisions.md](decisions.md)). | 11:15 | — |
| 8 | ~~Internal map access: no login or Cloudflare Access?~~ **Decided Nov 14: no login** (see [decisions.md](decisions.md)). | 11:40 | — |
| 9 | ~~Which Cloudflare account hosts the `*.pages.dev` project?~~ **Decided Nov 14: Ravi's account**, neutral project name. | 11:40 | — |
| 10 | ~~**Voice TTS license:** `piper-tts` is GPL-3.0-or-later; this repo is Apache-2.0.~~ **Decided Nov 14:** Piper runs as a separate service/process (see [decisions.md](decisions.md)). Still check the `pt_BR-faber-medium` voice license. | 11:50 | — |
| 11 | ~~**Language strategy** (English rule vs. Brazilian farmer persona)~~ **Decided Nov 14:** bot in Portuguese by default with an English option (voice included); producer dashboard in English by default with a PT-BR button (see [decisions.md](decisions.md)). | 11:45 | — |
| 12 | ~~**Hosting for the farmer product (front B)**~~ **Decided Nov 14:** Google Cloud (Global Offers credit): Cloud Run, Vertex AI Gemini Flash, Speech-to-Text/Text-to-Speech, budget alert at US$ 50 (see [decisions.md](decisions.md)). | 12:20 | — |
| 13 | **Product name:** still open; the team chooses (the planning docs use a working title). | 12:30 | team |
| 14 | **ZARC access format** (download, API or tables per municipality): research in progress. | 12:30 | Satélite (research) → Ravi |
