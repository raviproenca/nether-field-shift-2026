<!-- AI-assisted: written with Claude Code (BMad correct-course, batch mode) from Gabriel's description of the team's change; pending review by Ravi (Tech Lead). The idea, the audience and the role of AI are the team's; AI only researches facts and does not choose them. -->

# Sprint Change Proposal: a technical planting decision-maker; the role of AI defined after discovery (Nov 15, 2026)

## 1. Issue summary

- **Trigger:** a change of product audience and channel, brought by Gabriel on Nov 15 and reported as approved by Ravi (Tech Lead). It builds on the Nov 14 priority change (PR #78: engine, then validation, then dashboard; channel and audience decided after validation).
- **Type:** strategic pivot of the **audience**, of **how the data is presented**, and of the **channel**. It is not a defect.
- **Old audience:** the family farmer with low literacy, reached by a Telegram bot with voice (PRD §1, §2, UJ-1, §4.6).
- **New audience:** a **more technical user**, the professional who already has agronomic knowledge and leads the planting decisions: what to plant, when and in which rotation. For this user the results become an **interactive analysis** in the dashboard.
- **Channel change:** the **Telegram bot and voice are not needed**. E4 leaves v1.
- **Role of AI: open.** The team wants AI that is genuinely useful for this professional, not a generic layer. Its role is defined by the team **after** discovery (E7), from the professional's real difficulties. Until then, the only fixed rules are AD-3: AI never decides, never changes a number, and works only from the engine's result, with the template text as the fallback.
- **Everything else in the technology stays:**
  - the data layer;
  - the deterministic engine and its validation;
  - the FastAPI API on Cloud Run;
  - the React + MapLibre dashboard;
  - Gemini with the template fallback.
- **Open by design:** the team does **not yet know who this professional is**. The order the team set:
  1. find out **who** they are;
  2. find out **how their work runs**;
  3. find out **their biggest difficulties**;
  4. only then define the analysis and the role of AI for them.
- **Discovery method (Gabriel, Nov 15):** desk research only, with cited sources. The team chooses the persona and the role of AI; AI does not.
- **Constraint:** submission is due **today, Nov 15, 23:59 BRT**.

## 2. Impact analysis (checklist)

| # | Item | Status | Finding |
|---|---|---|---|
| 1.1 | Triggering story | [x] | No story failed. The trigger is the audience and channel change on top of PR #78. |
| 1.2 | Core problem | [x] | Strategic pivot: audience, presentation and channel; the persona and the role of AI are still unknown. |
| 1.3 | Evidence | [!] | Gabriel's report that Ravi approved. **Action:** Ravi signs the new row in `docs/team/decisions.md` in the PR that applies this proposal. |
| 2.1 | Current epic (E1 engine) | [x] | Unchanged. The engine is deterministic and audience-neutral. Validation (ZARC #48, backtest #79) matters even more for a technical user. |
| 2.2 | Epic changes | [x] | **E3** keeps story 3.1 (template) and puts its AI story on hold until the team defines the role of AI. **E5** becomes the interactive analysis for a technical user. **E4** leaves v1. New **E7 Persona discovery**. |
| 2.3 | Future epics | [x] | E2: story 2.4 serves the dashboard only; any AI endpoint waits for the team's definition. E6: story 6.3 (bot and voice deploy, #82) leaves v1; story 6.1 deploys only the API. |
| 2.4 | Obsolete / new epics | [x] | E4 obsolete for v1 (kept in history as possible future work). New E7 (research only). |
| 2.5 | Order | [x] | E1 → validation → **E7 in parallel** → E2 → E5 → E3 → E6. |
| 3.1 | PRD | [!] | Vision, target user, JTBD, journeys, glossary (Language), FR-1 to FR-3 (bot parts), FR-13, §4.6, FR-19, non-users, NFR-4, NFR-6, MVP and metrics. Details in §4. |
| 3.2 | Architecture | [!] | Small. `apps/bot`, `apps/tts`, AD-6 and the voice dependencies leave v1. AD-1 and AD-9 drop the bot. AD-3 stays as the rule for any AI use. |
| 3.3 | UX | [!] | No UX document exists. One is needed **after** discovery and the team's AI decision (`bmad-ux`). |
| 3.4 | Other artifacts | [!] | `docs/scope.md`, `docs/team/CONTEXT.md`, the brief, AGENTS.md §2 (the bot rows), the README (AI usage, Piper credit only if shipped). CI unaffected. |

## 3. Recommended approach

**Direct adjustment.** The build plan keeps its core and drops one channel; the AI part waits for a team decision.

- **Unchanged:**
  - the data layer, the engine (E1) and the validation;
  - the API (E2);
  - the dashboard technology (E5);
  - Gemini with the template fallback as the available AI stack;
  - Sergipe, the two pilot sites, the v1 crops and the deterministic rules;
  - AD-3.
- **Changed:**
  - the persona becomes "technical decision-maker, defined by discovery";
  - E5 shows an interactive analysis;
  - the role of AI becomes "defined by the team after E7".
- **Removed from v1:** E4 (Telegram bot with voice), the TTS service and the bot/voice deploy. Gabriel's local branches for #56 and #59 are not merged.
- **Added:** E7 Persona discovery, which also collects the facts the team needs to decide the role of AI.
- **No rollback:** no merged code depends on the bot.
- **Effort:** low to medium for the documents; code effort depends on the team's AI decision.
- **Risk:** medium to high on timeline, because the persona, the presentation and the role of AI are fixed on the submission day. Mitigation:
  - discovery is desk-only and timeboxed;
  - the template explanation (3.1) works with no AI;
  - the engine and validation continue in parallel.

**Not changed by this proposal:** ML stays a non-goal ("not a yield predictor; ML is future work"). Validation with real users stays out of the hackathon.

## 4. Detailed change proposals

### 4.1 New epic E7: Persona discovery (research only)

**Story 7.1: Who decides the planting in Sergipe, and where their work is hard**
As the team, we want a cited summary of the professionals who lead or advise planting and rotation decisions in Sergipe's Agreste and Semiárido, so that we choose the target persona and the role of AI ourselves.

Acceptance criteria:
- **Given** desk research with cited sources, **then** the summary lists the candidate roles. For each role it gives:
  - who they serve;
  - how their work runs: the decisions they make, when in the season, and with what information;
  - the time and effort each decision takes;
  - where they get it wrong, slow down or depend on someone else;
  - the tools and data they use today and the complaints about them.
- **And** every claim has a source; anything not found is marked "not found", never filled in.
- **And** the summary does not rank roles, choose a persona or propose product features: the team decides, and Ravi records the choice in `docs/team/decisions.md`.

Method: `bmad-deep-recon` (domain and user-voice research), output in `docs/research/`.

**Story 7.2: Persona and role of AI recorded**
**Given** the team's choices, **then**:
- PRD §2 gets the persona, their JTBD and two or three journeys;
- PRD FR-13 gets the role of AI.

AI only writes down what the team decided.

### 4.2 PRD (`prd.md`)

| Section | Old | New |
|---|---|---|
| Title / frontmatter | "decision support for family farming in Sergipe" | "decision support for planting decisions in Sergipe" (working title). Revision note: "Nov 15: technical decision-maker; Telegram bot and voice out of v1; role of AI defined after discovery". |
| §0 | Nov 14 priority note | Add: "**Audience and channel change (Nov 15, Ravi):** the user is a technical professional who leads planting decisions (persona from discovery, E7). The product is the dashboard with an interactive analysis. The Telegram bot and voice are out of v1. The role of AI is defined by the team after discovery." |
| §1 Vision | "A family farmer in Sergipe sends a location and a crop… in plain language… Telegram bot with voice" | "A technical professional who leads planting decisions in Sergipe explores a plot's NASA-based diagnosis and projection and compares at least three strategies with their evidence, trade-offs and uncertainty, in an interactive analysis. The calculations are deterministic; how AI helps this user is defined by the team after discovery, and AI never changes a number." |
| §2.1 JTBD | Farmer: "without making me read charts", "by voice" | "**Technical decision-maker:** to be written after discovery (E7)." Keep the judge JTBD. |
| §2.2 Non-users | "Agronomists who want a full agronomic model" | "Users who expect a full agronomic or yield model: the tool is deterministic decision support and points to local validation." |
| §2.3 Journeys | UJ-1 smallholder by voice; UJ-2 producer; UJ-3 judge | Remove UJ-1. UJ-2 becomes "the technical decision-maker analyses a plot" (detail after E7). UJ-3: remove the bot sentence. |
| §3 Glossary | Language: "the bot defaults to pt-BR" | "The dashboard defaults to `en`, with a PT-BR button." |
| §4.1 FR-1 to FR-3 | Telegram location button, crop by voice, priority | Dashboard only: click the map or pick a Pilot site; crop and priority by selection. Voice removed. |
| §4.5 FR-13 | "rewrites… in short, plain language" | "**FR-13: AI never decides.** The role of AI for the technical user is defined by the team after discovery (E7, open question 7). Whatever it is, it works only from the Recommendation, its Diagnosis and its Projection; it must not change numbers or Strategies; any number it states must exist in the structured result, otherwise the template text is used (AD-3). The template explanation (story 3.1) is always available." |
| §4.6 | Telegram bot with voice (FR-14, FR-15, FR-16, FR-20) | "**Removed from v1 (Nov 15).** No bot and no voice." |
| §4.7 | FR-17, FR-18, FR-21 | FR-17 adds: "the user can change the inputs (crop, priority, previous crops, season) and compare the effect on the strategies; the exact interactions come from the UX document after E7." |
| §4.8 FR-19 | "the bot and the dashboard use the same API" | "the dashboard uses the API". |
| NFR-4, NFR-6 | Piper GPL boundary; voice latency | Removed with the voice. NFR-5 drops "Telegram" credentials. |
| §6.1 MVP | Bot as item 7 | Remove item 7. Item 5 becomes "the template explanation (story 3.1); the AI part after the team's definition (FR-13)". |
| §7 Metrics | SM-1 "the bot is optional" | SM-1 without the bot sentence. Add **SM-5**: "the persona and the role of AI are chosen by the team from the cited discovery and recorded in decisions.md". |
| §8 Open questions | Q3 Piper voice license | Remove Q3. Add "6. Who is the technical decision-maker? Owner: the team, via E7." and "7. What is the role of AI for this user? Owner: the team, after E7." |

### 4.3 Brief (`brief.md`)

- **Executive summary and "Who this serves":** the primary user becomes the technical decision-maker, defined by discovery (E7). The two interfaces become one dashboard.
- **"What makes this different":** "Persona first: voice, short messages" becomes "evidence first: an interactive analysis of NASA-based strategies; the role of AI is decided after discovery".
- **Scope:** bot and voice move to "Out".

### 4.4 Epics (`epics.md`)

- **Priority order:** E1 → validation → **E7** (in parallel) → E2 → E5 → E3 → E6. E4 marked "removed from v1 (Nov 15)".
- **E2:** story 2.4 serves the dashboard only. Any AI endpoint is added after the team's definition.
- **E3:** story 3.1 (template) unchanged. Story 3.2 "**on hold: rewritten after the team defines the role of AI (E7.2)**", keeping the AD-3 number check as a fixed criterion.
- **E5:**
  - wording "As a producer…" becomes "As the technical decision-maker…";
  - story 5.1 adds "change the inputs and compare the effect on the strategies".
- **E6:** story 6.1 deploys only the API. Story 6.3 (#82) removed from v1. Story 6.2 drops the Piper credit unless Piper ships.
- **E4:** removed from v1.
- **New E7** as in §4.1.

### 4.5 Architecture spine

- **Removed from v1:**
  - `apps/bot` and `apps/tts`;
  - AD-6 (voice port and GPL boundary);
  - the stack rows python-telegram-bot, google-cloud-speech, google-cloud-texttospeech, faster-whisper and piper-tts;
  - the bot and TTS Cloud Run services in AD-10.
- **AD-1:** the only product client is `apps/web`.
- **AD-3:** unchanged; it is the rule for any AI use the team defines.
- **AD-9:** the bot default is dropped; the dashboard defaults to `en`.
- **Sequence diagram:** dashboard → API → engine → explain, instead of farmer → bot.
- **No change to:** AD-2, AD-4, AD-5, AD-7, AD-8, the data layer or the rest of the stack.

### 4.6 Other documents

- **`docs/scope.md`:** §2, §3 and §6 (E4 removed; role of AI open).
- **`docs/team/CONTEXT.md`:** the front B row.
- **`docs/team/decisions.md`:** one new row, **signed by Ravi**.
- **AGENTS.md §2:** remove `apps/bot` / python-telegram-bot and "bot and voice" from the deploy row.
- **README "AI usage":** AI was used to research the persona candidates; the team chose the persona and the role of AI.
- **Issues and board (Ravi):**
  - close or move #41, #56 to #61 and #82 out of v1;
  - open E7 (7.1, 7.2);
  - put #55 on hold;
  - reword E5 (in PT-BR).

## 5. Implementation handoff

- **Scope: Moderate.** Audience, presentation and channel change; the core build (data, engine, validation, API, dashboard) does not.
- **Ravi (Tech Lead):**
  - approve;
  - sign the decisions.md row;
  - update the board;
  - merge the docs PR.
- **Team:** choose the persona and the role of AI from the E7 research (7.2).
- **Gabriel (with the AI agents):**
  - run E7.1 now (`bmad-deep-recon`, desk research, cited);
  - apply the PRD, brief, epics, architecture, scope and AGENTS.md edits above in one docs PR to `dev`;
  - after the team's choices, run `bmad-ux` for the analysis.
- **Engine and validation owners:** continue unchanged.

**Success criteria:**
- the decision is recorded and signed;
- the E7 summary is cited and has no invented claims or feature proposals;
- the team-chosen persona and role of AI are in the PRD;
- the UX document exists before the E5 presentation is fixed;
- AI never states a number that is not in the Recommendation;
- no engine or validation work is delayed.
