---
status: draft
stepsCompleted: [validate-prerequisites, design-epics, create-stories, final-validation]
inputDocuments:
  - prds/prd-nether-field-shift-2026-2026-11-14/prd.md
  - prds/prd-nether-field-shift-2026-2026-11-14/addendum.md
  - architecture/architecture-nether-field-shift-2026-2026-11-14/ARCHITECTURE-SPINE.md
---

<!-- AI-assisted: drafted with Claude Code (Periélio, BMad epics and stories, headless fast path); pending review by Ravi (Tech Lead). DRAFT ONLY: Ravi opens, coordinates and assigns the issues. Nothing here is assigned to anyone. -->

# nether-field-shift-2026 - Epic Breakdown (front B, farmer product)

## Overview

This is a draft breakdown of the PRD (FR-1 to FR-21, NFR-1 to NFR-6) and the architecture spine (AD-1 to AD-10). It was revised on Nov 14 for Google Cloud, languages and the v1 crops, and again on Nov 14 for the new priority order. It is split into stories for the 48-hour hackathon. The stories are small and ordered so that each epic delivers something usable.

**Owners:** none. The Tech Lead creates the issues and splits the tasks.

**Already covered elsewhere:**
- the data adapters in `src/data`;
- the snapshot generator #16 (SRTM, ET0, pilots).

## Priority order (decided Nov 14)

After a mentor's feedback, and because the judging criteria weigh validity and relevance (`docs/team/decisions.md`, `docs/scope.md`):

1. **E1 Decision engine:** stories 1.1 to 1.4 (#44 to #47).
2. **Validation:** story 1.5 ZARC check (#48) and story 1.6 historical backtest (#79).
3. **E2 Product API**, only what the dashboard needs (#49, #50, #51, #53, #54).
4. **E5 Producer dashboard and demo mode** (#62, #63, #64).
5. **E3 Plain-language explanation** (#52, #55).
6. **E6 Deploy and judge readiness** (#65, #66).
7. **E4 Telegram bot with voice: after the engine is validated** (#56 to #58, #60, #61, then the Piper service #59 last). The channel and the audience are decided then.

## FR Coverage Map

| Epic | FRs / NFRs | ADs |
|---|---|---|
| E1 Decision engine | FR-5, FR-6, FR-8 to FR-12, FR-22 | AD-2, AD-4 |
| E2 Product API | FR-4, FR-7, FR-19, NFR-1, NFR-2, NFR-3, NFR-5 | AD-1, AD-4, AD-5, AD-7, AD-8 |
| E3 Plain-language explanation | FR-13 | AD-3, AD-9 |
| E4 Telegram bot with voice | FR-1 to FR-3, FR-14 to FR-16, FR-20, NFR-4, NFR-6 | AD-1, AD-6, AD-9 |
| E5 Producer dashboard and demo mode | FR-1, FR-17, FR-18, FR-21, NFR-1 | AD-1, AD-9 |
| E6 Deploy and judge readiness | NFR-1, NFR-2, NFR-3, NFR-5 | AD-7, AD-8, AD-10 |

## Epic List

Listed in priority order (Nov 14). The E numbers are kept so they match the issues.

1. **E1 Decision engine.** Takes a Diagnosis and a Projection and produces at least three ranked Strategies, deterministically. Includes the validation stories (ZARC check and historical backtest).
2. **E2 Product API.** One FastAPI service serves the Recommendation, Diagnosis and Forecast to every client. Only what the dashboard needs comes before E5.
3. **E5 Producer dashboard and demo mode.** Shows the same Recommendation with its evidence on a map. Judges get one-click pilots.
4. **E3 Plain-language explanation.** Rewrites a Recommendation as short text without changing a number.
5. **E6 Deploy and judge readiness.** Public, no login, online until Jan 26, 2027, credits complete.
6. **E4 Telegram bot with voice (after the engine is validated).** Location, crop and priority go in by voice, text or button. A voice reply and cards come out.

## Epic 1: Decision engine (`src/engine`)

### Story 1.1: Domain model and Recommendation schema
As a builder, I want typed Plot, Crop, Priority, Strategy, Diagnosis, Projection and Recommendation types, plus `docs/data-format/recommendation.schema.json`, so that the API, the bot and the dashboard share one shape.

**Acceptance criteria:**
- **Given** a sample Recommendation, **when** it is serialized, **then** it validates against the schema.
- **And** the field names match the PRD Glossary in snake_case.

### Story 1.2: Rules and crop profiles as data
As a builder, I want crop profiles and thresholds in `src/engine/rules/*.yaml`, so that the team can tune the rules without changing code.

**Acceptance criteria:**
- **Given** the v1 crops (maize, beans and cassava), **when** the rules load, **then** each crop has its water need, its cycle length and its heat limit, each with a source citation.

### Story 1.3: Strategy generation and ranking
As a farmer, I want at least three Strategies ranked by my Priority, so that I can choose what to do.

**Acceptance criteria:**
- **Given** a Diagnosis, a Projection, a Crop and a Priority, **when** `recommend()` runs, **then** it returns `current_practice`, `soil_water_conservation` and `resilient_income_forage`, ranked by the Priority.
- **And** the same inputs give a byte-identical output.
- **And** the engine performs no I/O (AD-2).

### Story 1.4: Actions, uncertainty and validation notes
As a farmer, I want each Strategy to say what to do next and why, so that I can trust it.

**Acceptance criteria:**
- **Given** a Recommendation, **then** each Strategy has concrete actions, each with one line of evidence.
- **And** the Recommendation has an Uncertainty note and a Validation note.

### Story 1.5: ZARC check
As an extension worker, I want the planting window compared with ZARC, so that any disagreement is visible.

**Acceptance criteria:**
- **Given** ZARC reference data for the crop and the municipality, **when** the window differs, **then** the Validation note says so.
- This story depends on the ZARC research and connector (PRs #73 and #74, merged).

### Story 1.6: Historical backtest in Sergipe (wet year and dry year)
As the team, I want the engine run on 2 or 3 real past Sergipe years, at least one wet and one dry, so that we can show how each Strategy would have done. Issue #79.

**Acceptance criteria:**
- **Given** the chosen years, **when** the backtest runs with one documented command, **then** it uses only real data from those years (POWER, GLDAS, IMERG).
- **And** at least one year is wet and one is dry, justified by the observed rain.
- **And** for each year the report shows how each Strategy would have done, compared with the IBGE PAM (SIDRA) reference.
- **And** every source used is listed in the README with a link.

## Epic 2: Product API (`apps/api`)

### Story 2.1: API skeleton
As a client, I want `/health` and `/sources` with the standard error shape, so that the bot and the dashboard can integrate early.

**Acceptance criteria:**
- **Given** a bad parameter, **then** the API returns 400 with `{error:{code,message}}`.
- **And** CORS allows the dashboard origin from an environment variable.

### Story 2.2: Diagnosis endpoint
As a client, I want `/diagnosis?lat&lon&radius_km`, which returns the series shape built from `src/data`, so that both clients show the same evidence.

**Acceptance criteria:**
- **Given** a Plot in Sergipe, **then** the response has rain, soil moisture, temperature, NDVI, ET0, the water balance and terrain, each with its source and `nasa: true`.
- **And** missing days are `null`.

### Story 2.3: Forecast endpoint (Open-Meteo)
As a client, I want `/forecast` for 15 days, so that the advice looks ahead.

**Acceptance criteria:**
- **Given** a Plot, **then** every series has `nasa: false` and the Open-Meteo attribution.
- **And** the snapshot generator does not import it (AD-5).

### Story 2.4: Recommendation endpoint
As a farmer, I want `POST /recommendation {lat, lon, crop, priority}`, which returns the structured Recommendation plus text, so that every client gets the same answer.

**Acceptance criteria:**
- **Given** a valid request, **then** the response validates against `recommendation.schema.json` and includes the text from E3.

### Story 2.5: Cache and pilot pre-warm
As a judge, I want the two pilot sites to answer even when NASA services are slow, so that the demo never fails.

**Acceptance criteria:**
- **Given** the upstream services are offline, **when** a pilot site is requested, **then** the API serves the cached response (AD-7).
- **And** the cache key is the coordinates rounded to 0.01°.

## Epic 3: Plain-language explanation (`src/explain`)

### Story 3.1: Template explanation (no AI)
As a farmer, I want a short fixed-template text for every Recommendation, so that the product works without any AI provider.

**Acceptance criteria:**
- **Given** a Recommendation, **then** the text names each Strategy, its first action and its uncertainty.
- **And** every number in the text appears in the Recommendation.

### Story 3.2: AI rewrite with number check
As a farmer, I want the text in natural, simple language, so that I understand it.

**Acceptance criteria:**
- **Given** the Vertex AI Gemini Flash output, **when** it contains a number that is not in the Recommendation, **then** it is rejected and the template text from 3.1 is used (AD-3).
- **And** if the call errors or the quota runs out, the template text is used.
- **And** the text is in the requested `lang`, either `pt-BR` or `en` (AD-9).

## Epic 4: Telegram bot with voice (`apps/bot`, `apps/tts`)

> **After the engine is validated (decided Nov 14).** The channel and the audience are decided then; these stories are kept, at the end of the Backlog.

### Story 4.1: Bot skeleton, `/start` and location
As a farmer, I want to start the bot with no account and share my location with one tap, so that onboarding takes seconds.

**Acceptance criteria:**
- **Given** `/start`, **then** the bot shows the location button.
- **And** a location outside Sergipe gets a clear message and the pilot sites as options.

### Story 4.2: Crop and priority by text or button
As a farmer, I want to choose the crop and the priority with buttons or text, so that I can answer even with a weak connection.

**Acceptance criteria:**
- **Given** a crop on the v1 list and a priority, **then** the bot calls `POST /recommendation` and shows the three Strategy cards.

### Story 4.3: Voice in (Google Speech-to-Text, faster-whisper fallback)
As a farmer who has trouble reading, I want to say my crop in a voice note, so that I do not have to type.

**Acceptance criteria:**
- **Given** an OGG/Opus voice note in the chat's language, **then** Google Speech-to-Text transcribes it and maps it to a v1 crop.
- **And** if Google errors or runs out of quota, faster-whisper is used instead (AD-6).
- **And** if the mapping fails, the bot shows buttons.

### Story 4.4: TTS fallback service (Piper, GPL boundary)
As a builder, I want `apps/tts` with `POST /tts` (text in, OGG/Opus out) as its own Cloud Run service, so that Piper serves as the voice fallback and is never imported into product code (AD-6).

**Acceptance criteria:**
- **Given** a short text, **then** the service returns OGG/Opus that Telegram plays.
- **And** the license and the voice's model card are recorded in the README.

### Story 4.5: Voice out (Google Text-to-Speech, Piper fallback)
As a farmer, I want a short voice reply with the text cards, so that I can listen to the advice.

**Acceptance criteria:**
- **Given** a Recommendation, **then** the bot sends one voice note from Google Text-to-Speech in the chat's language, plus the cards.
- **And** if Google fails, the bot falls back to `apps/tts`.
- **And** if both fail, the bot still sends the text.

### Story 4.6: Bot language (PT-BR default, English option)
As a farmer or a judge, I want to switch the bot between Portuguese and English with `/language` or a button, so that I can use it in my language.

**Acceptance criteria:**
- **Given** a new chat, **then** the bot speaks PT-BR.
- **When** the user picks English, **then** the texts, the voice in and the voice out all switch to `en` for that chat (AD-9).
- **And** the chosen language is kept only in memory, never on disk.

## Epic 5: Producer dashboard and demo mode

### Story 5.1: Plot view
As a producer, I want to pick a plot on the map and see the three Strategies with charts of the Diagnosis and the Projection, so that I can check the evidence.

**Acceptance criteria:**
- **Given** a plot, **then** the dashboard calls the API only (AD-1) and shows the source of every number.
- It reuses the front A map components (MapLibre, OSM, GIBS).
- Its stack and location depend on #12.

### Story 5.2: Demo mode for judges
As a judge, I want a public demo with the two pilot sites, one click each, so that I can see the product in under a minute.

**Acceptance criteria:**
- **Given** the public URL, **then** no login is asked.
- **And** each pilot shows a full Recommendation from cache.

### Story 5.3: Dashboard language (English default, PT-BR button)
As a producer, I want to switch the dashboard to PT-BR, so that I can read it in my language. Judges see English by default.

**Acceptance criteria:**
- **Given** the dashboard opens, **then** it is in English.
- **When** the user presses the PT-BR button, **then** every label, explanation and unit name switches, and the API is called with `lang=pt-BR`.

## Epic 6: Deploy and judge readiness

### Story 6.1: Google Cloud deployment (Cloud Run)
As the team, I want the API, the bot and the TTS fallback on Cloud Run until Jan 26, 2027, so that the judges' links keep working.

**Acceptance criteria:**
- **Given** a merge, **then** GitHub Actions deploys to Cloud Run through Workload Identity Federation, with no JSON key.
- **And** the secrets live in Secret Manager.
- **And** the bot uses a Telegram webhook.
- **And** no service uses a GPU.
- **And** a US$ 50 budget alert is set (AD-10).
- **And** the credit window is confirmed to cover Jan 26, 2027.

### Story 6.2: Credits and link check
As a judge, I want every source and license credited and every link public, so that the submission follows the rules.

**Acceptance criteria:**
- **Given** the README and the UI footers, **then** every NASA and third-party source used is listed with its license, including Open-Meteo as non-commercial and not NASA, and Piper as GPL as a separate service.
- **And** every submitted link opens without login.

## Issue list (created by the Tech Lead)

Issue numbers were added on Nov 14. The board order follows "Priority order" above.

| Draft title | Epic | Depends on |
|---|---|---|
| Engine: domain model and Recommendation schema | E1 | — |
| Engine: rules and crop profiles as data | E1 | 1.1, open question 2 |
| Engine: strategy generation and ranking | E1 | 1.1, 1.2 |
| Engine: actions, uncertainty and validation notes | E1 | 1.3 |
| Engine: ZARC check (#48) | E1 | 1.3, ZARC research |
| Validation: historical backtest (#79) | E1 | 1.1 to 1.5, data connectors |
| API: skeleton, health, sources, errors | E2 | — |
| API: diagnosis endpoint | E2 | 2.1, #16 |
| API: forecast endpoint (Open-Meteo) | E2 | 2.1 |
| API: recommendation endpoint | E2 | 1.3, 2.2, 2.3, 3.1 |
| API: cache and pilot pre-warm | E2 | 2.4 |
| Explain: template text | E3 | 1.1 |
| Explain: Gemini Flash rewrite with number check | E3 | 3.1 |
| Bot: skeleton, /start, location | E4 | — |
| Bot: crop and priority | E4 | 4.1, 2.4 |
| Bot: voice in (Google STT, faster-whisper fallback) | E4 | 4.2 |
| TTS fallback service (Piper, separate) | E4 | — |
| Bot: voice out (Google TTS, Piper fallback) | E4 | 4.4, 2.4 |
| Bot: language (PT-BR default, English option) | E4 | 4.2 |
| Dashboard: plot view | E5 | 2.4, #12 |
| Dashboard: demo mode | E5 | 5.1, 2.5 |
| Dashboard: language (English default, PT-BR button) | E5 | 5.1 |
| Deploy: Google Cloud (Cloud Run, WIF, Secret Manager, budget alert) | E6 | 2.1, 4.1 |
| Credits and link check | E6 | all |
