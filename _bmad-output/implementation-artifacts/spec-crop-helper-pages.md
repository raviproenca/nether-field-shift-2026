---
title: 'Carry Crop History into Honest Rotation Guidance'
type: 'feature'
created: '2026-11-15'
status: 'in-progress'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '307ef0d5fc341cc39c1a9c7f8862a822c2d4326a'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/team/CONTEXT.md'
  - '{project-root}/docs/team/decisions.md'
  - '{project-root}/docs/scope.md'
  - '{project-root}/docs/data-format/recommendation.schema.json'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The dashboard asks which crop to plant but not what was grown last, although the engine scores rotation choices using the previous crop's botanical family. A saved demo run can also look like a live response to the current map point and selections, and the mobile controls compete with the result panel for screen space.

**Approach:** Add distinct previous-crop and intended-crop controls, pass the previous crop through `previous_crops` into the existing API, engine and cache dimensions, and show the actual assumptions and evidence behind each ranked strategy. Keep demo results clearly identified as saved examples, state the decision-support and historical-ranking limits, and improve mobile responsiveness while retaining the established visual identity.

## Boundaries & Constraints

**Always:** The audience is the technical professional who leads planting decisions in Sergipe. The dashboard compares three deterministic strategies (current practice, soil/water conservation, resilient income/forage), shows planting windows, water demand, trade-offs, pest-cycle notes, sources, uncertainty and ZARC validation when available. Scores use the existing engine's priority weights and evidence. Describe the product as decision support; do not claim yield or harvest prediction. Preserve the known limit that the same top-ranked strategy appeared in 45 of 45 tested seasons. Keep English as the default and existing PT-BR toggle, no-login behavior, NASA/third-party source credits, existing routes, and the visual identity. A missing previous crop is explicit and distinct from an intended crop. An omitted `previous_crops` API field may retain legacy behavior; an explicitly empty list means no known previous crop.

**Never:** Invent agronomic data, rotation benefits, scores or causal claims; imply historical demo output was recomputed for arbitrary points or current inputs; substitute a saved pilot after a configured live API error; redesign the product, add dependencies, deploy, publish, change CORS, merge, push, or alter protected branches.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Known prior crop | Prior = beans; intended = maize | UI sends `previous_crops: ["beans"]`; response reflects it in plot context and the engine's family-break scoring | Show API validation errors clearly |
| No known prior crop | Prior = unknown; intended crop selected | UI sends `previous_crops: []`; API does not replace explicit empty history with inferred history | Explain that history is unknown |
| Saved demo | API URL absent or explicit pilot selected | Show saved location, generated date and actual saved crop/history; label values as an example and disclose selections not applied by that file | Do not describe it as a live or per-point calculation |
| Live API failure | API URL configured; recommendation request fails | Keep the selected assumptions visible and show the service error | Never substitute a nearby pilot |
| Mobile | Narrow viewport, on-screen keyboard, controls and result open | Inputs and result remain readable, scrollable and operable without horizontal overflow | Preserve map access and touch targets |

</frozen-after-approval>

## Code Map

- `apps/web/src/plot/immersive/ImmersiveApp.tsx` -- crop/priority state, map point selection, request lifecycle and current fallback to the nearest saved pilot.
- `apps/web/src/plot/types.ts` and `apps/web/src/plot/api.ts` -- client request/response types, network call, and saved demo fetches.
- `apps/api/recommendation.py` -- Pydantic request; already accepts `previous_crops` but currently lets empty history inherit plot history. Preserve inherited history only when the field is omitted; respect explicit `[]`.
- `src/engine/model.py`, `src/engine/recommend.py`, `apps/api/cache.py` -- `Plot.previous_crops`, last recognized crop family in scoring, and server cache key dimensions already exist. The cache's default fallback currently ignores requested history; retain history when falling back by season and never return another history's scores.
- `apps/web/src/plot/immersive/ResultPanel.tsx`, `apps/web/src/plot/PlotView.tsx`, and `apps/web/src/plot/immersive/engineText.ts` -- ranked strategies, actions, score, pest-cycle note, diagnosis, projection, sources and explanation text.
- `apps/web/src/plot/immersive/copy.ts` and `apps/web/src/plot/immersive/immersive.css` -- bilingual UI copy and current floating desktop/mobile panel layout.
- `apps/web/public/demo/` and `scripts/build_demo_cache.py` -- precomputed pilot results; their recorded plot assumptions/date are authoritative for demo labels.
- `tests/test_api_recommendation.py`, `tests/test_engine_recommend.py`, and `tests/test_api_cache.py` -- API-to-engine, prior-family scoring and cache regression tests.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/plot/immersive/ImmersiveApp.tsx`, `apps/web/src/plot/immersive/copy.ts`, and `apps/web/src/plot/types.ts` -- add distinct previous and intended crop inputs in English/PT-BR; include history in request payload and result key; retain selections through loading/errors.
- [x] `apps/api/recommendation.py` -- distinguish omitted history from explicit empty history and pass the selected history into the engine plot and response.
- [x] `apps/web/src/plot/api.ts`, `apps/api/recommendation.py`, and `apps/api/cache.py` -- prevent stale/mismatched live results by including history in relevant lookup keys; preserve existing server key dimensions and restrict season fallback to the same history.
- [x] `apps/web/src/plot/immersive/ResultPanel.tsx`, `apps/web/src/plot/PlotView.tsx`, `apps/web/src/plot/immersive/engineText.ts`, and `apps/web/src/plot/immersive/copy.ts` -- explain the selected transition, ranked rotation, score inputs, pest-cycle result, evidence and limitations without unsupported claims; label saved examples with their actual inputs/date and limits.
- [x] `apps/web/src/plot/immersive/immersive.css` -- repair responsive control/result layout at phone widths while preserving the established visual language.
- [x] `tests/test_api_recommendation.py`, `tests/test_engine_recommend.py`, `tests/test_api_cache.py`, and focused web tests -- cover history propagation, explicit empty versus omitted, cache separation, demo labeling and live failure behavior.
- [x] Run focused Python tests and web tests, `npm run lint`, `npm run typecheck`, and `npm run build`; do not deploy or publish.
- [ ] Inspect 320px and tablet layouts in a browser. The browser inventory was empty in this session, so visual viewport inspection remains unverified.

**Acceptance Criteria:**
- Given a selected intended crop and known last-grown crop, when a live recommendation is requested, then the request, API plot, engine scoring and cache entry all use that previous crop and results are keyed separately from other histories.
- Given no known previous crop, when the request includes an empty history, then the API preserves it as empty and the UI identifies the uncertainty rather than silently substituting another crop.
- Given a saved demo response, when any point or input is selected, then the UI states the saved run's actual location, date and assumptions and does not claim it reflects uncomputed selections.
- Given a configured live API failure, when the user requests an analysis, then the UI displays the error and never falls back to a pilot result.
- Given the ranked strategies, when the user reads the answer and details, then they can see the rotation sequence, score basis, actions, pest-cycle result, source/uncertainty context and the limitation that this is not a yield forecast and historical ranking was unchanged in 45/45 seasons.
- Given narrow phone and tablet widths, when the user enters history, chooses an intended crop, selects a point and reads the result, then all controls and content remain reachable without horizontal overflow.
- Given existing routes and language controls, when loaded, then `#internal`, `#classic`, English and PT-BR remain functional.

## Implementation Notes

- Scope was revised per Ravi's explicit implementation dispatch. The prior Pages deployment/CORS tasks are excluded from this change; publishing remains blocked pending separate validation.
- Demo behavior intentionally uses saved pilot outputs only when the API URL is absent or the user explicitly chooses a pilot. Saved inputs/date are disclosed, and configured API failures remain visible.

## Spec Change Log


## Review Triage Log

## Verification

**Commands:**
- `./.venv/bin/python -m pytest -q tests/test_engine_recommend.py tests/test_explain_template.py` -- 22 passed.
- `./.venv/bin/python -m pytest -q tests/test_api_cache.py::test_recommendation_cache_fallback_keeps_previous_crop_dimension tests/test_api_recommendation.py::test_explicit_empty_previous_crops_overrides_inferred_plot_history` -- 2 passed.
- `npm test` -- 5 focused request/demo tests passed (Node built-in test runner; no new dependency).
- `npm run lint`, `npm run typecheck`, `npm run build` -- passed; Vite emitted the existing large-chunk warning.
- The broader `tests/test_api_recommendation.py` TestClient run stalled in this environment before producing a result, so it is not counted as passed. The direct API propagation regression above passed.

**Manual checks:**
- Not completed: no browser was available for 320px/tablet viewport inspection. Static responsive CSS and production build were checked; visual overflow is not claimed as verified.
