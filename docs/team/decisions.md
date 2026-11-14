# Decisions

> Team notes — ideas and decisions are the team's; summaries assisted by AI.

Only what the team **formally decided** goes here, with date and who confirmed it. Discussions go in [brainstorm-log.md](brainstorm-log.md).

| Date | Decision | Confirmed by |
|---|---|---|
| Nov 14, 2026 | The **internal data map** is published on Cloudflare Pages under a `*.pages.dev` address, with no custom domain. | Ravi (Tech Lead) |
| Nov 14, 2026 | The farmer-facing bot channel is **Telegram** for now. WhatsApp is future work, mentioned in the pitch. | Ravi (Tech Lead) |
| Nov 14, 2026 | Work is split into **three fronts** (A internal map, B farmer product, C judges' delivery); see [CONTEXT.md](CONTEXT.md#2-three-fronts). Nothing in front B is built before the formal idea decision and the PRD. | Ravi (Tech Lead) |
| Nov 14, 2026 | The internal map uses **pre-generated data and no API**: a toolkit script builds light JSON/GeoJSON snapshots (Sergipe/Nordeste) published with the front end on `*.pages.dev`; NASA GIBS layers stay live. No login inside the front end. Durable hosting for front B is decided after the idea. | Ravi (Tech Lead) |
| Nov 14, 2026 | Internal map access: **no login**. The `*.pages.dev` URL is not advertised and the site sends `noindex` (robots meta + `X-Robots-Tag`). Hosted on **Ravi's Cloudflare account**, with a neutral project name (e.g. `nether-field-map`). | Ravi (Tech Lead) |
| Nov 14, 2026 | **Voice in the Telegram bot is in scope:** the bot understands voice messages (speech-to-text) and replies with voice (text-to-speech) as well as short text. Built with the rest of front B, after the idea decision and the PRD. | Ravi (Tech Lead) |
| Nov 14, 2026 | **Official project idea & persona (Space Apps Rule 1):** Decision-support tool for **Brazilian family farming in Sergipe (Agreste & Semiárido)** across **two interfaces sharing one API** (Telegram Bot for smallholders + Producer Web Dashboard for larger farms/extension), comparing **at least 3 crop/rotation strategies** per plot (including *consórcio* / intercropping and cover crops) weighted by farmer priority, with **projection and prescription**: it tells the farmer **what to do**, not only how things are now. Unblocks `bmad-product-brief` and PRD. | **Ravi (Tech Lead), on behalf of the team**; wording by Duda (Eduarda) |
| Nov 14, 2026 | **Global physical data core:** `SMAP + GLDAS + IMERG + FAO-56` (alongside NASA POWER, SRTM/NASADEM, and HLS/Sentinel-2 NDVI) as the global core. Regional **ANA HidroWeb** integration is scoped as future Brazil expansion. | Ravi (Tech Lead), on behalf of the team; proposed by Duda (Eduarda) |
| Nov 14, 2026 | **Weather forecasts:** **Open-Meteo** (ECMWF/GFS models, up to 15 days, CC BY 4.0, no API key) in the **product API (`apps/api/`)**, not in the internal-map snapshots. Its free API is for non-commercial use: fine for the hackathon demo, a risk if the product becomes commercial. It is not NASA data (credited as third party). **NASA GEOS-FP** is cited in the pitch as the NASA path for forecasts. | Ravi (Tech Lead), on behalf of the team; proposed by Duda (Eduarda) |
| Nov 14, 2026 | **Messaging bot flow & production path:** **Telegram Bot API** with `KeyboardButton(request_location=True)` for the hackathon demo; **WhatsApp Cloud API** positioned as post-hackathon production expansion. | Ravi (Tech Lead), on behalf of the team; proposed by Duda (Eduarda) |
| Nov 14, 2026 | **Web map stack:** **MapLibre GL + OpenStreetMap + NASA GIBS** layers (free, no API key, aligned with Epic #19). | Ravi (Tech Lead), on behalf of the team; proposed by Duda (Eduarda) |
| Nov 14, 2026 | **Issues:** **Ravi (Tech Lead)** opens and coordinates issues and splits tasks among teammates; **Lucas leads requirements gathering**. AI agents only prepare drafts (BMad epics and stories); Ravi assigns. | Ravi (Tech Lead) |
| Nov 14, 2026 | **ZARC** (Brazil's agricultural climate-risk zoning, MAPA/Embrapa) is used as a **validation reference** for planting windows. | Ravi (Tech Lead) |
| Nov 14, 2026 | **Voice TTS:** Piper runs as a **separate service/process** (GPL-3.0), never imported into product code. | Ravi (Tech Lead) |
| Nov 14, 2026 | **Validation with farmers is skipped** during the hackathon; the pitch lists it as the **next step**. | Ravi (Tech Lead) |
| Nov 14, 2026 | **Traffic light:** Ravi (Tech Lead) keeps [STATUS.md](STATUS.md) up to date and calls out red items. | Ravi (Tech Lead) |
| Nov 14, 2026 | **Everything on Google Cloud** (Global Offers credit, US$ 300 for 90 days, activated by Ravi by Nov 15): **Cloud Run** for the API, the bot and the voice service; **Vertex AI Gemini Flash** for the explanations, with a **template text fallback** on error or missing quota; **Google Speech-to-Text and Text-to-Speech** (pt-BR and en) for voice, with **Piper and faster-whisper as fallback** (Piper kept isolated, GPL). **Budget alert at US$ 50.** No GPU. Secrets via environment variables or Secret Manager. | Ravi (Tech Lead) |
| Nov 14, 2026 | **Language:** the bot is in **Portuguese by default with an English option** (`/language` command or button), voice included; the producer dashboard is in **English by default with a PT-BR button**. | Ravi (Tech Lead) |
| Nov 14, 2026 | **Crops for v1:** corn (milho), beans (feijão) and cassava (mandioca). | Ravi (Tech Lead) |
