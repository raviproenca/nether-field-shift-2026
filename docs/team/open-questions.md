# Open questions

> Team notes — ideas and decisions are the team's; summaries assisted by AI.

| # | Question | Raised | Owner |
|---|---|---|---|
| 1 | ~~Is there a **global** alternative to the USGS water-access dataset (US only)?~~ **Decided Nov 14:** Global core uses `SMAP + GLDAS + IMERG + FAO-56` (+ POWER, SRTM/NASADEM); **ANA HidroWeb** left as future Brazil expansion (see [decisions.md](decisions.md)). | 10:24 | — |
| 2 | ~~Where would **forecasts** come from? (current data is historical)~~ **Decided Nov 14:** Integrate **Open-Meteo** (ECMWF/GFS up to 15 days, free CC BY 4.0) in the data toolkit and `apps/api/` (see [decisions.md](decisions.md)). | 11:15 | — |
| 3 | ~~Which other datasets beyond POWER, IMERG, SMAP, Sentinel-2, Landsat, SRTM, SoilGrids and ANA?~~ **Decided Nov 14:** Global core = `SMAP + GLDAS + IMERG + POWER + FAO-56 + SRTM/NASADEM + HLS/Sentinel-2 + Open-Meteo`; SoilGrids optional static baseline; ANA HidroWeb future work (see [decisions.md](decisions.md)). | 11:15 | — |
| 4 | ~~Can a WhatsApp bot ask for the user's location with a button?~~ **Decided Nov 14:** Hackathon demo uses **Telegram Bot API** (`request_location=True` reply keyboard button); **WhatsApp Cloud API** (interactive location request) is post-hackathon production expansion (see [decisions.md](decisions.md)). | 10:45 | — |
| 5 | ~~Demo channel: Telegram, WhatsApp or SMS?~~ **Decided Nov 14: Telegram for now** (see [decisions.md](decisions.md)). | 10:45 | — |
| 6 | ~~Which map API for the dashboards?~~ **Decided Nov 14: MapLibre GL + OpenStreetMap** (free, no key, Epic #19; see [decisions.md](decisions.md)). | 10:36 | — |
| 7 | ~~Who gathers the requirements and opens the issues?~~ **Decided Nov 14: Lucas (`@LucasFe3152`)** (see [decisions.md](decisions.md)). | 11:15 | — |
| 8 | ~~Internal map access: no login or Cloudflare Access?~~ **Decided Nov 14: no login** (see [decisions.md](decisions.md)). | 11:40 | — |
| 9 | ~~Which Cloudflare account hosts the `*.pages.dev` project?~~ **Decided Nov 14: Ravi's account**, neutral project name. | 11:40 | — |
| 10 | **Language strategy (`AGENTS.md` English rule vs. Brazilian farmer persona):** Choose between **(A — Recommended)** bilingual Web UI (`EN` default on load for judges + 1-click `PT-BR` toggle) with `PT-BR` Telegram farmer demo + `/lang en` + English subtitles on the <=30 s video, or **(B)** English-only Web & Bot UI everywhere with PT-BR only in a subtitled demo walkthrough. | 11:45 | Ravi / team |
