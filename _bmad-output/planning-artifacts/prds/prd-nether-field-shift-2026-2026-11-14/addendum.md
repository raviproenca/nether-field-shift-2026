<!-- AI-assisted: drafted with Claude Code (Periélio) from the team's decisions; pending review by Ravi. -->

# PRD addendum: technical choices already decided (Nov 14)

These are the technical choices the team has already decided. They come from `docs/team/decisions.md` and the Tech Lead's message of Nov 14. The architecture document develops them.

## Priority change (decided Nov 14)
- **Date and source:** Nov 14, 2026, Ravi (Tech Lead); `docs/team/decisions.md`, PR #78.
- **Why:** a mentor's feedback, and the judging criteria weigh **validity** and **relevance**. The engine has to be shown to work before the channel matters.
- **Order:** E1 decision engine (#44 to #47) → validation: ZARC check (#48) and historical backtest on 2 or 3 real Sergipe years, at least one wet and one dry (#79) → E2 API, only what the dashboard needs → E5 producer dashboard → E3 explanation → E6 deploy → E4 Telegram bot and voice last, with the Piper service (#59) at the end.
- **Engine:** in go the farmer's crops, the soil, the region, the season and the previous crops; out come the rotation options with trade-offs, the planting schedule and dates per crop, the water demand and the pest-cycle break.
- **Channel and audience:** decided only after the engine is validated. The bot and voice issues are kept, at the end of the Backlog. The judge flow goes through the dashboard demo mode.
- **Out of scope:** crop photos.
- The current scope is summarized in `docs/scope.md`.

## Channels and interface
- **Interfaces:** first a web dashboard built with MapLibre GL, OpenStreetMap and NASA GIBS (WMTS). After the engine is validated, a Telegram Bot API bot, which uses `KeyboardButton(request_location=True)` for the location.
- **Shared API:** the bot and the dashboard use the same API, `apps/api`.

## Voice (updated Nov 14)
- **Primary engines:** Google Cloud Speech-to-Text and Text-to-Speech, in `pt-BR` and `en`, following the user's language.
- **Fallback speech-to-text:** faster-whisper, model `small` or `medium` on CPU int8.
- **Fallback text-to-speech:** Piper. Piper is GPL-3.0, so it stays in a **separate service**, `apps/tts`, and is never imported into the Apache-2.0 product code.
- **Audio format:** OGG/Opus in both directions.
- **Spike, Nov 14:**
  - Whisper small: 5.5 s of audio transcribed in 1.2 s, plus 1.1 s to load the model.
  - Piper: 5.5 s of audio generated in 0.4 s.

## Data
- **Toolkit:** `src/data` (POWER, GLDAS, IMERG, SMAP, MODIS, VIIRS, HLS, and Sentinel-2 via the Planetary Computer).
- **Snapshot generator (#16):**
  - Builds a grid of points for Sergipe and the Nordeste.
  - Adds the two pilot sites.
  - Adds SRTM/NASADEM terrain and the FAO-56 ET0 and water balance.
  - Outputs the format documented in `docs/data-format.md`.
- **Forecast:** Open-Meteo, in the **product API only**, never in the internal snapshot. It is CC BY 4.0, free for non-commercial use, and not NASA. The pitch names NASA GEOS-FP as the NASA path for forecasts.
- **Validation reference:** ZARC (MAPA/Embrapa).

## Hosting (decided Nov 14)
- **Front A (internal map):** Cloudflare Pages.
- **Front B (product):** everything runs on **Google Cloud**, paid with the Global Offers credits (US$ 300 for 90 days).
  - **Cloud Run:** `apps/api`, `apps/bot` and the voice fallback service `apps/tts`. No GPU.
  - **Explanations:** Vertex AI Gemini Flash, with template text as the fallback.
  - **Budget alert:** US$ 50.
  - **Secrets:** environment variables or Secret Manager.
  - **GitHub Actions to GCP:** Workload Identity Federation, with no long-lived JSON key.

## Languages (decided Nov 14)
- **Bot:** PT-BR by default, with English through `/language` or a button. The choice also applies to voice.
- **Dashboard:** English by default, with a PT-BR button.

## Crops (decided Nov 14)
- The v1 crops are maize, beans and cassava.

## Process
- Validation with farmers is skipped in the hackathon and becomes the next step in the pitch.
- Ravi opens, coordinates and assigns the issues. Agents only draft epics and stories.
