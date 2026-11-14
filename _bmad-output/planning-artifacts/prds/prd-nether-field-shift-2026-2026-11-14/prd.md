---
title: "PRD: Field Shift decision support for family farming in Sergipe"
status: draft
created: 2026-11-14
updated: 2026-11-14
revision: 'Nov 14 (3): priority change: engine first, then validation, then dashboard; bot after validation'
---

<!-- AI-assisted: drafted with Claude Code (Periélio, BMad PRD, headless fast path) from the team's brief, docs/requirements.md and docs/team/*; pending review by Ravi (Tech Lead). The idea is the team's (docs/team/decisions.md). -->

# PRD: Field Shift decision support for family farming in Sergipe
*Working title. The team names the product.*

## 0. Document Purpose

This PRD is for the team and for the BMad steps that follow it: architecture, then epics and stories. It turns the confirmed idea into features and requirements for **front B, the farmer product**, for the 48-hour hackathon.

It builds on:
- the brief, `briefs/brief-nether-field-shift-2026-2026-11-14/brief.md`;
- the requirements draft by Lucas, `docs/requirements.md`, whose REQ-* IDs are cited where they apply;
- the team notes, `docs/team/*`.

Technology choices live in `addendum.md` and in the architecture document. Inferred points carry an `[ASSUMPTION]` tag; they are listed in §9.

> **Priority change (Nov 14, Ravi, Tech Lead):** the decision engine comes first, then its validation (ZARC and a historical backtest), then the producer dashboard. The Telegram bot with voice is no longer the core of v1: the channel and the audience are decided after the engine is validated. Details in `addendum.md` and in `docs/scope.md`.

## 1. Vision

A family farmer in Sergipe sends a location and a crop and gets back **what to do next**. The answer compares at least three strategies for the plot, ranked by what the farmer cares about most. It is based on NASA observations of the recent past plus a short-term forecast. It is said in plain language and states its uncertainty honestly.

The first interface is the **producer web dashboard**, which shows the strategy comparison with its evidence and has a demo mode for judges. The engine is **validated** first, against ZARC and in a historical backtest on real Sergipe years. A channel for the farmer, such as a Telegram bot with voice, is decided after the engine is validated. The product goes **from projection to prescription**. Its calculations are deterministic, and AI only explains them.

## 2. Target User

### 2.1 Jobs To Be Done
- **Farmer:** "Tell me if and when to plant what I planned. Tell me what to plant next, and how to protect my soil, without making me read charts."
- **Farmer:** "Talk to me in my language, by voice, on my weak connection, without installing an app."
- **Producer or extension worker:** "Show me the evidence behind the advice for a plot, so I can trust it or adjust it."
- **Judge:** "Let me try the full flow in a minute, with no login."

### 2.2 Non-Users (v1)
- Farms outside Sergipe. The data core is global, but v1 is tuned and demoed only in Sergipe.
- Agronomists who want a full agronomic model. This product gives guidance and points to local validation.

### 2.3 Key User Journeys
- **UJ-1. A smallholder in Itabaiana (Agreste) asks by voice whether to plant beans now.** *After engine validation: this journey depends on the channel decision (Nov 14).*
  1. The farmer opens the bot with no account, taps **Share location** and records "I want to plant beans".
  2. The bot asks for a priority with buttons: water, soil, erosion or income.
  3. Within seconds `[ASSUMPTION]`, the farmer gets a short audio reply plus three short text cards: keep the current practice, a soil and water option, and an income or forage option. Each card says what to do this week and why, in one line each.
  4. The bot adds "check with your local technician" where the uncertainty is high.

  **Edge case:** if the voice note cannot be understood, the bot asks again with buttons for the most common crops.
- **UJ-2. A producer in Nossa Senhora da Glória (Semiárido) checks the evidence on the dashboard.**
  - The producer opens the public dashboard link, picks the pilot site and selects a crop and a priority.
  - The dashboard shows the three strategies side by side, with recent rain and soil moisture, the 15-day forecast, the water balance and the terrain, all on a map.
  - Each number names its data source.
- **UJ-3. A judge tries the demo.**
  - The judge opens the dashboard in demo mode and clicks a pre-loaded pilot. They see the strategy comparison with its evidence.
  - Sending `/start` to the bot is optional: it applies only if the bot ships after the engine is validated.
  - No step asks for a login.

## 3. Glossary
- **Plot**: the place a request is about. It is a point, from the location, plus a small radius.
- **Crop**: the crop the farmer plans or practices. The v1 list is **maize, beans and cassava** (decided Nov 14). Intercropping and cover crops are **Strategies**, not Crops.
- **Language**: the user's interface language, either `pt-BR` or `en`. The bot defaults to `pt-BR` and the dashboard to `en`.
- **Priority**: the farmer's chosen weight. It is one of **water**, **soil**, **erosion** or **income**. REQ-PRED-03.
- **Strategy**: one option for the plot over the next season. Each **Recommendation** has at least three: **Current practice**, **Soil and water conservation** and **Resilient income or forage**. REQ-PRED-02.
- **Diagnosis**: the plot's recent and seasonal conditions, taken from NASA data. It includes rain, soil moisture, vegetation, temperature, the water balance, terrain and **Bare-soil windows**.
- **Projection**: the plot's expected conditions over the next days. It comes from the **Forecast**.
- **Forecast**: the short-term weather forecast, Open-Meteo in v1. It is not NASA.
- **Recommendation**: the ranked **Strategies** plus the concrete actions for each, the evidence behind them, an **Uncertainty note** and a **Validation note**.
- **Uncertainty note**: a plain statement of the data's limits. Examples: coarse resolution, a missing day, or a forecast that is not an observation.
- **Validation note**: where a local technician must confirm the advice, and where ZARC disagrees.
- **Pilot site**: a pre-loaded plot used for demos. The two pilot sites are **Itabaiana** in the Agreste and **Nossa Senhora da Glória** in the Semiárido.
- **Bare-soil window**: a recurring period with low vegetation cover. REQ-PRED-04.

## 4. Features

### 4.1 Request intake (bot and dashboard)
**Description:** collect the **Plot**, the **Crop** and the **Priority** with as little effort as possible. This realizes UJ-1, UJ-2 and UJ-3.

#### FR-1: Location in one tap
The farmer can send the **Plot** with Telegram's location button. The dashboard user can click the map or pick a **Pilot site**.
- If the location is outside Sergipe, the user gets a clear message, and the **Pilot sites** are offered.

#### FR-2: Crop by voice, text or button
The farmer can name the **Crop** with a voice note, with text, or with a button for the most common crops.
- A voice note is transcribed in the user's **Language** and mapped to a **Crop** on the v1 list.
- If the mapping fails, the bot shows buttons instead of guessing.

#### FR-3: Priority choice
The user picks one **Priority**. If they skip it, the default is **water** `[ASSUMPTION]`.

### 4.2 Diagnosis from NASA data
**Description:** build the plot's **Diagnosis** from the shared data layer (`src/data` and the snapshot format) and cache it so the demo works offline. REQ-DATA-01 to 04, 07; REQ-INFRA-01.

#### FR-4: Recent and seasonal conditions
The system returns, for the **Plot**:
- rain: IMERG and POWER;
- soil moisture: SMAP and GLDAS;
- temperature: POWER;
- vegetation: MODIS or VIIRS NDVI.

It covers the recent weeks and the same season in past years.
- Each value carries its source, its resolution and its date.
- A missing day is shown as missing, never as a filled value.

#### FR-5: Water balance and terrain
The system computes the daily FAO-56 ET0 and the water balance (rain minus ET0) from POWER. It also adds elevation and slope from NASADEM/SRTM. This is based on Duda's work, folded into #16.

#### FR-6: Bare-soil windows
The system flags the plot's recurring **Bare-soil windows** from the NDVI history. REQ-PRED-04.

### 4.3 Projection
#### FR-7: Short-term forecast
The system adds a 15-day **Forecast** (rain, temperature, ET0) for the **Plot**. It is labeled "forecast, not NASA, non-commercial use", and it lives only in the product API. REQ-PRED-06.
- If the **Forecast** is unavailable, the **Recommendation** is still returned, with an **Uncertainty note**.

### 4.4 Prescription: strategy comparison
**Description:** deterministic rules turn the **Diagnosis** and the **Projection** into a **Recommendation**. REQ-PRED-01, 02, 03, 05.

**Engine inputs and outputs (decided Nov 14):** in go the farmer's crops, the soil, the region, the season and the previous crops; out come the rotation options with their trade-offs, the planting schedule and dates per crop, the water demand and the pest-cycle break. How these map onto FR-8 to FR-12 is open question 5 (§8).

#### FR-8: At least three strategies
The system returns at least three **Strategies** for the **Plot** and **Crop**: **Current practice**, **Soil and water conservation** (for example intercropping or cover crops) and **Resilient income or forage**.

#### FR-9: Ranked by priority
The **Strategies** are ranked by the chosen **Priority**. The ranking is reproducible: the same inputs give the same output.

#### FR-10: Concrete actions
Each **Strategy** comes with what to do in the next days and weeks, for example plant now or wait, protect the soil, or plant on the contour on slopes. Each action shows the evidence behind it in one line.

#### FR-11: ZARC check
The planting window advice is compared with ZARC (MAPA/Embrapa) for the crop and the municipality. Any difference goes into the **Validation note**. The ZARC data access is being researched.

#### FR-12: Uncertainty and validation
Every **Recommendation** includes an **Uncertainty note** and a **Validation note**.

#### FR-22: Historical backtest (added Nov 14)
The engine is run on 2 or 3 real past years in Sergipe, at least one wet and one dry, with historical NASA data. The result shows how each **Strategy** would have done in each year. Issue #79.

### 4.5 Plain-language explanation
#### FR-13: Explain, never decide
An AI layer only rewrites the deterministic **Recommendation** in short, plain language in the user's **Language**. It must not change numbers or **Strategies**. REQ-PRED-07.
- The explanation uses Vertex AI Gemini Flash.
- If the call errors or the quota runs out, the system uses the fixed template text instead.
- The numbers in the text equal the numbers in the structured output.
- If the AI layer fails, the bot sends a fixed template text instead.

### 4.6 Telegram bot with voice (after engine validation)

The bot is a channel decided after the engine is validated (Nov 14). FR-14, FR-15, FR-16 and FR-20 stay as written for when it ships.

#### FR-14: Open bot, no account
Anyone can start the bot with `/start`. There is no login or registration. REQ-DEV-BE-04.

#### FR-15: Voice in and out
The bot accepts voice notes, using speech-to-text. It replies with a short voice note, using text-to-speech, plus short text cards. Audio is OGG/Opus in both directions. REQ-DEV-BE-05, decided Nov 14.
- Speech-to-text and text-to-speech use the user's **Language** (`pt-BR` or `en`).
- The primary engine is Google Cloud Speech-to-Text and Text-to-Speech.
- The fallback is faster-whisper for speech-to-text and Piper for text-to-speech. The fallback runs when the primary engine errors or runs out of quota.

#### FR-20: Bot language choice
The bot speaks Portuguese by default. The user can switch it to English, or back, with `/language` or a button. The choice applies to text, voice in and voice out for the rest of the chat.

#### FR-16: Light messages
Replies fit weak connections: short texts, small audio, and at most one small image. REQ-INFRA-05.

### 4.7 Producer web dashboard
#### FR-17: Plot view
The dashboard shows the **Recommendation** for a **Plot** on a map with NASA GIBS layers and charts of the **Diagnosis** and the **Projection**. REQ-DEV-FE-02.

#### FR-21: Dashboard language toggle
The dashboard is in English by default. A button switches every label, explanation and unit name to PT-BR.

#### FR-18: Demo mode for judges
The dashboard has a public demo mode with the **Pilot sites** pre-loaded. A judge reaches a result in one click, with no login.

### 4.8 Shared API
#### FR-19: One API for both interfaces
The bot and the dashboard use the same API: request a **Recommendation**, plus read endpoints for the **Diagnosis** and the **Forecast**. REQ-DEV-BE-01 to 03.
- Errors return clear JSON and never crash.
- Cached **Pilot site** responses keep working when NASA services are slow.

**Cross-cutting NFRs**
- **NFR-1. Access:** everything a judge opens works without login and stays online until **Jan 26, 2027**. NFR-DEPLOY-01, 02.
- **NFR-2. Resilience:** upstream failures become clear messages, with cached **Pilot site** data as the fallback. NFR-DEPLOY-03.
- **NFR-3. Credits:** NASA and third-party sources are credited in the README and the UI.
  - Open-Meteo is credited as CC BY 4.0, non-commercial, not NASA.
  - Sentinel-2 is credited as ESA.
  - ZARC, MapBiomas and IBGE are credited as third-party data.
  - NFR-DEV-08.
- **NFR-4. Licenses:** GPL components (Piper TTS) run as a separate service and are never imported into product code. The repo stays Apache-2.0.
- **NFR-5. No secrets in Git**, English in code and UI. Telegram, AI and Earthdata credentials come only from env vars or secrets. NFR-DEV-02, NFR-DEPLOY-06.
- **NFR-6. Voice latency:** a full voice round trip takes a few seconds on CPU `[ASSUMPTION]`. In the Nov 14 spike, Whisper small took 1.2 s to transcribe 5.5 s of audio, and Piper took 0.4 s to generate 5.5 s of audio.

## 5. Non-Goals
- Not an agronomic expert system or a yield predictor. ML is future work.
- No WhatsApp in v1.
- No user accounts, farm profiles or history in v1 `[ASSUMPTION]`.
- No field sensors in v1.
- No commercial use of the **Forecast** source.

## 6. MVP Scope
### 6.1 In Scope
For Sergipe, the two **Pilot sites** and the v1 crops (maize, beans and cassava), in this order (Nov 14):
1. The decision engine (FR-5, FR-6, FR-8 to FR-12).
2. Its validation: the ZARC check (FR-11) and the historical backtest (FR-22).
3. The shared API, only what the dashboard needs (FR-4, FR-7, FR-19), with cached pilot data.
4. The dashboard with demo mode (FR-17, FR-18, FR-21).
5. The plain-language explanation (FR-13).
6. Deploy and judge readiness (NFR-1 to NFR-5).
7. **After the engine is validated:** the bot with voice (FR-1 to FR-3 in the bot, FR-14 to FR-16, FR-20). The channel and the audience are decided then.

### 6.2 Out of Scope for MVP
- **Crop photos** (decided Nov 14).
- **Validation with real farmers.** It is skipped in the hackathon and is the next step in the pitch.
- **Other states.**
- **Languages other than PT-BR and English.**
- **Seasonal outlook beyond 15 days.** The pitch names NASA GEOS-FP as the NASA path for forecasts.
- **ANA HidroWeb, SoilGrids and MapBiomas integration.** Planned; research is in progress.

## 7. Success Metrics
- **SM-1:** a judge completes UJ-3 in the dashboard demo mode without login or help. The bot is optional. Validates FR-18.
- **SM-4:** the historical backtest shows, for at least one wet and one dry year in Sergipe, how each **Strategy** would have done, and the ZARC check is reported. Validates FR-11, FR-22.
- **SM-2:** both **Pilot sites** return a full **Recommendation** (at least 3 **Strategies**, evidence, an **Uncertainty note** and a **Validation note**), including when NASA services are offline, from the cache. Validates FR-8 to FR-12, FR-19.
- **SM-3:** every number shown traces to a named source. Validates FR-4, FR-5, FR-7, FR-13.
- **SM-C1 (counter-metric):** do not add strategies, crops or features at the cost of explainability. Every action must keep its one-line evidence. Counterbalances SM-2.

## 8. Open Questions
1. **Product name.** Owner: the team.
2. **ZARC data access.** Is it a file or an API, and at what granularity? Owner: research, in progress.
3. **Piper `pt_BR` voice license.** Piper is only the fallback now. See open question 10 in `docs/team/open-questions.md`.
4. **Cloud credit window.** The Global Offers credits last 90 days from activation. If they are activated on Nov 14, they end around Feb 12, 2027, which covers Jan 26, 2027. Confirm the activation date. Owner: Ravi.

5. **Engine inputs and outputs (Nov 14).** The soil and the previous crops are new inputs, and the pest-cycle break, the planting schedule and the water demand per crop are new outputs. Which soil source, how previous crops are entered, and whether stories #44 to #47 change? Owner: Ravi, with the engine owner.

**Decided Nov 14 (Ravi), no longer open:**
- Hosting on Google Cloud.
- Vertex AI Gemini Flash for the explanations.
- Google Speech-to-Text and Text-to-Speech, with Piper and faster-whisper as the fallback.
- The bot in PT-BR with an English option, and the dashboard in English with a PT-BR toggle.
- The v1 crops: maize, beans and cassava.
- Priority: engine, then validation, then dashboard; the bot after validation; crop photos out.

## 9. Assumptions Index
- §4.1 FR-3: the default **Priority** is water.
- §2.3 UJ-1 and §4.6: a voice reply comes back "within seconds" on CPU.
- §5: there are no accounts or farm history in v1.
