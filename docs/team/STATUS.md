# Status ("traffic light")

> Team notes — ideas and decisions are the team's; summaries assisted by AI.

What is done and what is missing for the submission. 🟢 done · 🟡 in progress or partial · 🔴 not started or blocked · ⚪ skipped by decision. Kept by Ravi (Tech Lead). No times or estimates: just the current state. Updated on every change.

| Item | State | Notes |
|---|---|---|
| Project idea formally confirmed | 🟢 | Confirmed Nov 14 by Ravi (Tech Lead) on behalf of the team, with projection and prescription. See [decisions.md](decisions.md) |
| PRD (BMad): brief, PRD, architecture, epics | 🟡 | In progress |
| Validation with 1–2 farmers or agribusiness people | ⚪ | Skipped by decision; "next step" in the pitch |
| Data toolkit (`src/data`): NASA sources | 🟢 | POWER, GLDAS, IMERG, SMAP, MODIS, VIIRS, HLS tested against the real services; Sentinel-2 (third party) too |
| Extra sources: SRTM terrain, ET0 and water balance | 🟡 | Being merged into the snapshot generator (#16) |
| Brazil data sources (ZARC, MapBiomas, IBGE PAM, drought monitor) | 🟡 | Research in progress |
| Internal map: snapshot data (#16) | 🟡 | In progress |
| Internal map: front end (#12–#15) | 🔴 | Not started |
| Internal map: deploy (#18) | 🟡 | Workflow merged; Cloudflare project and repo secrets still to be set by Ravi |
| Farmer product: Telegram bot | 🔴 | Waits for the PRD |
| Farmer product: producer web dashboard | 🔴 | Waits for the PRD |
| Farmer product: hosting | 🟡 | Proposed: Google Cloud (Global Offers); pending Ravi's OK |
| Voice (speech-to-text / text-to-speech) | 🟡 | Offline spike works; Piper as a separate service (license) |
| Pitch skeleton | 🟡 | Keywords collected in [pitch-keywords.md](pitch-keywords.md) |
| Demo: video ≤ 30 s or ≤ 7 slides | 🔴 | Not started |
| Project page on the Space Apps site (submission form) | 🔴 | Not started |
| Public repo, license, no credentials | 🟢 | Apache-2.0; credentials only on local machines |
| README: NASA data used, credits, AI usage | 🟡 | Toolkit sources listed; to be trimmed to what the product actually uses |
| All submitted links public, no login, valid until Jan 26, 2027 | 🔴 | Checked at the end |
