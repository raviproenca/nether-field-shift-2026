<!-- AI-assisted: drafted with Claude Code (Periélio) from the team's decisions; pending review by Ravi. -->

# PRD addendum: technical choices already decided (Nov 14)

These are the technical choices the team has already decided. They come from `docs/team/decisions.md` and the Tech Lead's message of Nov 14. The architecture document develops them.

## Channels and interface
- **Interfaces:** a Telegram Bot API bot, which uses `KeyboardButton(request_location=True)` for the location, and a web dashboard built with MapLibre GL, OpenStreetMap and NASA GIBS (WMTS).
- **Shared API:** the bot and the dashboard use the same API, `apps/api`.

## Voice
- **Speech-to-text:** faster-whisper, model `small` or `medium` on CPU int8.
- **Text-to-speech:** Piper pt-BR. Piper is GPL-3.0, so it runs as a **separate service or process** and is never imported into the Apache-2.0 product code.
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

## Hosting
- **Front A (internal map):** Cloudflare Pages.
- **Front B (product):** Google Cloud is proposed (Global Offers, US$ 300 for 90 days). It is pending Ravi's OK and must account for the CPU and RAM load of voice.

## Process
- Validation with farmers is skipped in the hackathon and becomes the next step in the pitch.
- Ravi opens, coordinates and assigns the issues. Agents only draft epics and stories.
