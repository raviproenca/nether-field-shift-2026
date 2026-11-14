<!-- AI-assisted: written with Claude Code from the team's recorded decisions; pending review by Ravi (Tech Lead). The idea and the decisions are the team's. -->

# Project scope (single source)

_Last updated: Nov 14, 2026. This file is the single source for the current scope. If it disagrees with an issue or the board, tell Ravi (Tech Lead)._

Built only from recorded decisions: [decisions.md](team/decisions.md), [CONTEXT.md](team/CONTEXT.md), the [PRD](../_bmad-output/planning-artifacts/prds/prd-nether-field-shift-2026-2026-11-14/prd.md) and [epics.md](../_bmad-output/planning-artifacts/epics.md).

## 1. The challenge

[Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/) asks for a **decision-support tool**, not only a map, that combines NASA Earth observations, local soil, crop characteristics and farmer priorities to **compare at least three crop rotation strategies** (including the current one), with the evidence, the trade-offs and the uncertainty explained.

## 2. What we deliver

A decision-support tool for **family farming in Sergipe** (Agreste and Semiárido), demoed on two pilot sites: Itabaiana and Nossa Senhora da Glória. v1 crops: maize, beans and cassava.

- **Decision engine** (`src/engine`). Deterministic rules on NASA data, no ML.
  - **In:** the farmer's crops, the soil, the region, the season and the previous crops.
  - **Out:** rotation options with trade-offs, a planting schedule and dates per crop, the water demand and the pest-cycle break.
- **Validation** of the engine against ZARC and in a historical backtest on 2 or 3 real Sergipe years (at least one wet and one dry), showing how each strategy would have done.
- **Producer dashboard** with the strategy comparison and a one-click **demo mode** for the judges, on the product API (`apps/api`).
- **Plain-language explanation.** AI only rewrites the engine's result and never changes a number. A fixed template text is the fallback.

## 3. Priority order (decided Nov 14)

After a mentor's feedback, and because the judging criteria weigh **validity** and **relevance**:

1. **E1 Decision engine** [#38](https://github.com/raviproenca/nether-field-shift-2026/issues/38): [#44](https://github.com/raviproenca/nether-field-shift-2026/issues/44) → [#45](https://github.com/raviproenca/nether-field-shift-2026/issues/45) → [#46](https://github.com/raviproenca/nether-field-shift-2026/issues/46) → [#47](https://github.com/raviproenca/nether-field-shift-2026/issues/47).
2. **Validation:** ZARC check [#48](https://github.com/raviproenca/nether-field-shift-2026/issues/48) and the historical backtest [#79](https://github.com/raviproenca/nether-field-shift-2026/issues/79).
3. **E2 Product API** [#39](https://github.com/raviproenca/nether-field-shift-2026/issues/39), only what the dashboard needs: [#49](https://github.com/raviproenca/nether-field-shift-2026/issues/49), [#50](https://github.com/raviproenca/nether-field-shift-2026/issues/50), [#51](https://github.com/raviproenca/nether-field-shift-2026/issues/51), [#53](https://github.com/raviproenca/nether-field-shift-2026/issues/53), [#54](https://github.com/raviproenca/nether-field-shift-2026/issues/54).
4. **E5 Producer dashboard and demo mode** [#42](https://github.com/raviproenca/nether-field-shift-2026/issues/42): [#62](https://github.com/raviproenca/nether-field-shift-2026/issues/62), [#63](https://github.com/raviproenca/nether-field-shift-2026/issues/63), [#64](https://github.com/raviproenca/nether-field-shift-2026/issues/64).
5. **E3 Plain-language explanation** [#40](https://github.com/raviproenca/nether-field-shift-2026/issues/40): [#52](https://github.com/raviproenca/nether-field-shift-2026/issues/52), [#55](https://github.com/raviproenca/nether-field-shift-2026/issues/55).
6. **E6 Deploy and judge readiness** [#43](https://github.com/raviproenca/nether-field-shift-2026/issues/43): [#65](https://github.com/raviproenca/nether-field-shift-2026/issues/65), [#66](https://github.com/raviproenca/nether-field-shift-2026/issues/66); bot/voice deployment [#82](https://github.com/raviproenca/nether-field-shift-2026/issues/82) remains in the Backlog until validation.
7. **E4 Telegram bot with voice** [#41](https://github.com/raviproenca/nether-field-shift-2026/issues/41), **after the engine is validated**: [#56](https://github.com/raviproenca/nether-field-shift-2026/issues/56)–[#58](https://github.com/raviproenca/nether-field-shift-2026/issues/58), [#60](https://github.com/raviproenca/nether-field-shift-2026/issues/60), [#61](https://github.com/raviproenca/nether-field-shift-2026/issues/61), and the Piper service [#59](https://github.com/raviproenca/nether-field-shift-2026/issues/59) last; deploy follows in [#82](https://github.com/raviproenca/nether-field-shift-2026/issues/82).

The **channel** (Telegram bot, voice) and the **audience** are decided only after the engine is validated. The template explanation [#52](https://github.com/raviproenca/nether-field-shift-2026/issues/52) is a prerequisite of API story #53 and therefore comes before #53; the rest of E3 remains later. The bot and voice issues are kept, at the end of the Backlog.

## 4. Out of scope

- Crop photos.
- HLS and Sentinel-2 in the internal-map snapshot. They stay available in the `src/data` command line, as GeoTIFF.
- Validation with real farmers. It is skipped in the hackathon and named as the next step in the pitch.
- Also out, from the PRD: other states, WhatsApp, ML yield prediction, field sensors, user accounts, commercial use of the Open-Meteo forecast, and forecasts beyond 15 days.

## 5. Fronts

| Front | What | State |
|---|---|---|
| **A. Internal map** | Team tool to explore the data, **not judged**. Static site on Cloudflare Pages with pre-generated snapshots and live NASA GIBS layers; no API, no login. Epic [#19](https://github.com/raviproenca/nether-field-shift-2026/issues/19). | Setup, base map and GIBS layers merged; point panel [#15](https://github.com/raviproenca/nether-field-shift-2026/issues/15) and deploy [#18](https://github.com/raviproenca/nether-field-shift-2026/issues/18) open |
| **B. Farmer product** | Engine, validation, API and dashboard, in the order of section 3. | Building E1 first |
| **C. Judges' delivery** | Project page on the Space Apps site, the demo (video or slides), public links. In English. | At the end |

## 6. Who does what (per the board)

Area labels and assignees as on the [project board](https://github.com/users/raviproenca/projects/1) on Nov 14, late afternoon. The board is the live source for assignees; if this table is out of date, the board wins.

| Area (label) | What | Who |
|---|---|---|
| `predição` | Decision engine (`src/engine`): #38, #44 to #47 | Duda (`@dudxyz`) and Lucas (`@LucasFe3152`) |
| `predição` | Historical backtest #79 | Ravi and Gabriel (`@gabrielchavesas`) |
| `dados` | ZARC check #48 | Ravi and Gabriel |
| `dados` | Open-Meteo forecast #51 | Duda and Ravi |
| `back` | API (`apps/api`): #39, #49, #50, #53, #54 | Ravi |
| `back` | Explanation (`src/explain`): #40, #52, #55 | No assignee yet; #52 must precede #53 |
| `back` | Bot: #41, #56, #57 (and voice #58, #60, #61) | Gabriel; Ravi and Lucas also on #56 |
| `front` | Producer dashboard: #42, #62 to #64 | Ravi |
| `front` | Internal map: #15 (epic #19 has no assignee) | Gabriel |
| `deploy` | Cloudflare Pages #18, API Cloud Run #65, credits and link check #66; bot/voice deploy #82 after validation | Ravi; Lucas on #65; Duda on #66 |
| `infra` | Piper service #59 | Ravi and Gabriel |

Ravi (`@raviproenca`, Tech Lead) opens and assigns issues, approves and merges every PR.

## 7. Event rules that limit scope

- Every link the judges open is **public, with no login**, and stays valid until **Jan 26, 2027**.
- The demo is a **video of at most 30 s** or **at most 7 slides**. Over the limit means out of global judging.
- The **idea is the team's**. AI must not come up with it.
- **AI use is declared** in the README, and AI-generated files carry a header.
- Every NASA and third-party source is credited with its license.

## 8. Read more

- Decisions: [docs/team/decisions.md](team/decisions.md)
- Team context: [docs/team/CONTEXT.md](team/CONTEXT.md)
- PRD: [prd.md](../_bmad-output/planning-artifacts/prds/prd-nether-field-shift-2026-2026-11-14/prd.md) and [addendum.md](../_bmad-output/planning-artifacts/prds/prd-nether-field-shift-2026-2026-11-14/addendum.md)
- Epics and stories: [epics.md](../_bmad-output/planning-artifacts/epics.md)
- Board: <https://github.com/users/raviproenca/projects/1>
