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

This is a draft breakdown of the PRD (FR-1 to FR-19, NFR-1 to NFR-6) and the architecture spine (AD-1 to AD-8) into stories for the 48-hour hackathon. The stories are small and ordered so that each epic delivers something usable.

**Owners:** none. The Tech Lead creates the issues and splits the tasks.

**Already covered elsewhere:**
- the data adapters in `src/data`;
- the snapshot generator #16 (SRTM, ET0, pilots).

## FR Coverage Map

| Epic | FRs / NFRs | ADs |
|---|---|---|
| E1 Decision engine | FR-5, FR-6, FR-8 to FR-12 | AD-2, AD-4 |
| E2 Product API | FR-4, FR-7, FR-19, NFR-1, NFR-2, NFR-3, NFR-5 | AD-1, AD-4, AD-5, AD-7, AD-8 |
| E3 Plain-language explanation | FR-13 | AD-3 |
| E4 Telegram bot with voice | FR-1 to FR-3, FR-14 to FR-16, NFR-4, NFR-6 | AD-1, AD-6 |
| E5 Producer dashboard and demo mode | FR-1, FR-17, FR-18, NFR-1 | AD-1 |
| E6 Deploy and judge readiness | NFR-1, NFR-2, NFR-3, NFR-5 | AD-7, AD-8 |

## Epic List

1. **E1 Decision engine.** Takes a Diagnosis and a Projection and produces at least three ranked Strategies, deterministically.
2. **E2 Product API.** One FastAPI service serves the Recommendation, Diagnosis and Forecast to every client.
3. **E3 Plain-language explanation.** Rewrites a Recommendation as short text without changing a number.
4. **E4 Telegram bot with voice.** Location, crop and priority go in by voice, text or button. A voice reply and cards come out.
5. **E5 Producer dashboard and demo mode.** Shows the same Recommendation with its evidence on a map. Judges get one-click pilots.
6. **E6 Deploy and judge readiness.** Public, no login, online until Jan 26, 2027, credits complete.

## Epic 1: Decision engine (`src/engine`)

### Story 1.1: Domain model and Recommendation schema
As a builder, I want typed Plot, Crop, Priority, Strategy, Diagnosis, Projection and Recommendation types, plus `docs/data-format/recommendation.schema.json`, so that the API, the bot and the dashboard share one shape.

**Acceptance criteria:**
- **Given** a sample Recommendation, **when** it is serialized, **then** it validates against the schema.
- **And** the field names match the PRD Glossary in snake_case.

### Story 1.2: Rules and crop profiles as data
As a builder, I want crop profiles and thresholds in `src/engine/rules/*.yaml`, so that the team can tune the rules without changing code.

**Acceptance criteria:**
- **Given** the v1 crop list (open question 2), **when** the rules load, **then** each crop has its water need, its cycle length and its heat limit, each with a source citation.

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
- This story depends on the ZARC research (Satélite).

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
- **Given** the AI provider's output, **when** it contains a number that is not in the Recommendation, **then** it is rejected and the template text from 3.1 is used (AD-3).
- **And** the provider is configured by environment variable (open question 4).

## Epic 4: Telegram bot with voice (`apps/bot`, `apps/tts`)

### Story 4.1: Bot skeleton, `/start` and location
As a farmer, I want to start the bot with no account and share my location with one tap, so that onboarding takes seconds.

**Acceptance criteria:**
- **Given** `/start`, **then** the bot shows the location button.
- **And** a location outside Sergipe gets a clear message and the pilot sites as options.

### Story 4.2: Crop and priority by text or button
As a farmer, I want to choose the crop and the priority with buttons or text, so that I can answer even with a weak connection.

**Acceptance criteria:**
- **Given** a crop on the v1 list and a priority, **then** the bot calls `POST /recommendation` and shows the three Strategy cards.

### Story 4.3: Voice in (faster-whisper)
As a farmer who has trouble reading, I want to say my crop in a voice note, so that I do not have to type.

**Acceptance criteria:**
- **Given** an OGG/Opus voice note in Brazilian Portuguese, **then** it is transcribed and mapped to a crop on the v1 list.
- **And** if the mapping fails, the bot shows buttons.

### Story 4.4: TTS service (Piper, GPL boundary)
As a builder, I want `apps/tts` with `POST /tts` (text in, OGG/Opus out) in its own process or container, so that Piper is never imported into product code (AD-6).

**Acceptance criteria:**
- **Given** a short text, **then** the service returns OGG/Opus that Telegram plays.
- **And** the license and the voice's model card are recorded in the README.

### Story 4.5: Voice out
As a farmer, I want a short voice reply with the text cards, so that I can listen to the advice.

**Acceptance criteria:**
- **Given** a Recommendation, **then** the bot sends one voice note and the cards.
- **And** if TTS fails, the bot still sends the text.

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

## Epic 6: Deploy and judge readiness

### Story 6.1: Product hosting
As the team, I want the API, the bot and the TTS service online until Jan 26, 2027, so that the judges' links keep working.

**Acceptance criteria:**
- **Given** the hosting decision (pending Ravi), **then** the services run with secrets from environment variables (AD-8), and the hosting does not depend on a trial that expires before Jan 26, 2027.

### Story 6.2: Credits and link check
As a judge, I want every source and license credited and every link public, so that the submission follows the rules.

**Acceptance criteria:**
- **Given** the README and the UI footers, **then** every NASA and third-party source used is listed with its license, including Open-Meteo as non-commercial and not NASA, and Piper as GPL as a separate service.
- **And** every submitted link opens without login.

## Issue-ready list (for the Tech Lead; not created)

| Draft title | Epic | Depends on |
|---|---|---|
| Engine: domain model and Recommendation schema | E1 | — |
| Engine: rules and crop profiles as data | E1 | 1.1, open question 2 |
| Engine: strategy generation and ranking | E1 | 1.1, 1.2 |
| Engine: actions, uncertainty and validation notes | E1 | 1.3 |
| Engine: ZARC check | E1 | 1.3, ZARC research |
| API: skeleton, health, sources, errors | E2 | — |
| API: diagnosis endpoint | E2 | 2.1, #16 |
| API: forecast endpoint (Open-Meteo) | E2 | 2.1 |
| API: recommendation endpoint | E2 | 1.3, 2.2, 2.3, 3.1 |
| API: cache and pilot pre-warm | E2 | 2.4 |
| Explain: template text | E3 | 1.1 |
| Explain: AI rewrite with number check | E3 | 3.1, open question 4 |
| Bot: skeleton, /start, location | E4 | — |
| Bot: crop and priority | E4 | 4.1, 2.4 |
| Bot: voice in (faster-whisper) | E4 | 4.2 |
| TTS service (Piper, separate) | E4 | — |
| Bot: voice out | E4 | 4.4, 2.4 |
| Dashboard: plot view | E5 | 2.4, #12 |
| Dashboard: demo mode | E5 | 5.1, 2.5 |
| Deploy: product hosting | E6 | hosting decision |
| Credits and link check | E6 | all |
