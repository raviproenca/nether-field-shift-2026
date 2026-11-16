<!-- AI-assisted: written with Claude Code (BMad correct-course, batch mode); pending review by Ravi (Tech Lead). The decision is the team's. -->

# Sprint Change Proposal: engine first, then validation, then dashboard (Nov 14, 2026)

## 1. Issue summary

- **Trigger:** a mentor's feedback on Nov 14. The judging criteria weigh **validity** and **relevance**, so the engine has to be shown to work before the channel matters.
- **Decision:** recorded in `docs/team/decisions.md` (PR #78), confirmed by Ravi (Tech Lead). Approved before this workflow ran, so it was run in batch mode with no step-by-step review.

## 2. Impact analysis

| Checklist area | Status | Finding |
|---|---|---|
| 1. Trigger and context | Done | Change in priority, not a defect. Evidence: the decision row of PR #78. |
| 2. Epic impact | Done | E1 gains story 1.6 (backtest, #79). E4 moves to the end, "after the engine is validated". The E numbers stay. |
| 3. Artifact conflicts | Done | PRD: the vision, UJ-3, §4.6, §6.1 and SM-1 put the bot at the center. Brief: the success criteria counted the bot as a judge path. Epics: the list order. Architecture spine: no conflict found. No UX document exists. |
| 4. Path forward | Done | Direct adjustment of the existing plan; no rollback; the MVP keeps its features but changes order. |
| 5. Handoff | Done | Moderate: backlog reorder (already done on the board) plus the doc updates below. |

## 3. Recommended approach

Direct adjustment. The decision changes the order and the judge path, not the product idea. Nothing is deleted: the bot and voice stories are kept at the end of the Backlog.

## 4. Change proposals (applied in this PR)

- **PRD (`prd.md`):** revision note; a priority note in §0; the vision now leads with the dashboard and the validation; UJ-1 marked "after engine validation"; UJ-3 makes the bot optional; the engine inputs and outputs from the decision added in §4.4; **FR-22 Historical backtest** added; §4.6 marked "after engine validation"; §6.1 in priority order; crop photos out (§6.2); SM-1 reworded and **SM-4** added; open question 5 added.
- **PRD addendum:** a "Priority change" section with the date, the reason, the order and the engine inputs and outputs.
- **Epics (`epics.md`):** a "Priority order" section; the epic list reordered; story 1.6 (backtest, #79) added; E4 marked "after the engine is validated"; issue numbers in the issue list.
- **Brief (`brief.md`):** success criteria now use the dashboard demo mode as the judge flow, with the bot optional; validation added; crop photos out.
- **New `docs/scope.md`:** the single source for the current scope, linked from `docs/team/CONTEXT.md` and the README.

## 5. Open questions for Ravi (not decided here)

1. **New engine inputs and outputs vs stories #44 to #47.** Soil and previous crops are new inputs; the pest-cycle break, the planting schedule and the water demand per crop are new outputs. The stories do not mention them yet. Which soil source (SoilGrids is listed as out of the MVP), how are previous crops entered, and should the stories change?
2. **#53 depends on #52**, the E3 template text, but E3 now comes after E5. Should #52 move before #53, or should the text leave the acceptance criteria of #53?
3. **"E2, only what the dashboard needs":** the dashboard stories depend on all five E2 stories (#49, #50, #51, #53, #54). Confirm that nothing in E2 is dropped.
4. **#65 deploys the API, the bot and the TTS service.** With the bot after validation, should #65 deploy only the API for now? Where is the dashboard hosted?
5. **#66 credits Piper as GPL.** That applies only if the bot and voice ship.
6. **The brief's "What makes this different"** still leads with "persona first: voice". Should the pitch angle change too?
