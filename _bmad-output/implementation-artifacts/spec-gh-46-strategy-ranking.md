<!-- AI-assisted: generated with Cursor; pending review by the team. -->

---
title: 'Strategy generation and ranking'
type: 'feature'
created: '2026-11-15'
status: 'in-review'
route: 'dispatch'
baseline_commit: 'e9e15bd51cf7dfc47ebf32a5f80a0900c48f248f'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 1.3 (issue #46) has no `recommend()`. The domain types from story 1.1 exist, but nothing builds the three strategies or orders them.

**Approach:** Add a pure `recommend()` that always returns `current_practice`, `soil_water_conservation` and `resilient_income_forage`. Order them with the rule engine described by Kalaivani et al. (IEEE CICT 2025, DOI 10.1109/CICT67193.2025.11399212): do not repeat the previous crop's botanical family, and after a nitrogen-depleting crop prefer a legume. The farmer's `Priority` breaks ties only. The logistic-regression half of that paper stays out of this story. The team already decided the engine is deterministic rules on NASA-derived inputs, with no ML (`docs/scope.md`).

## Boundaries & Constraints

**Always:**
- Inputs are the existing `Plot`, `Diagnosis`, `Projection`, `Crop` and `Priority`. The previous crop is the last entry of `plot.previous_crops` when it is `maize`, `beans` or `cassava`. Any other string is ignored.
- Output is one `Recommendation` that validates against `docs/data-format/recommendation.schema.json`. The same inputs produce the same `serialize_recommendation()` bytes. `src/engine` does no I/O (AD-2).
- Crop roles, fixed for the three v1 crops: maize is Poaceae and nitrogen-depleting; beans are Fabaceae and nitrogen-fixing; cassava is Euphorbiaceae and neither. This is the qualitative metadata the paper keeps beside the model (`crop_info.json`: family and nutrient impact). Maize stands in for the paper's nitrogen-depleting cereal example (rice). Beans stand in for the paper's legume example (gram).
- Strategy crops: `current_practice` is the selected crop alone. `soil_water_conservation` adds beans when the selected crop is not beans, and adds cassava when it is. `resilient_income_forage` adds cassava when the selected crop is maize, and adds maize when the selected crop is beans or cassava.
- Sort key, highest first: (1) family break, 1 when the strategy introduces a family other than the previous crop's family; (2) nutrient recovery, 1 when the previous crop is nitrogen-depleting and the strategy introduces beans; (3) priority fit, 1 for `soil_water_conservation` when priority is `soil`, `water` or `erosion`, and 1 for `resilient_income_forage` when priority is `income`; (4) a fixed tie-break `soil_water_conservation`, then `resilient_income_forage`, then `current_practice`. When there is no recognized previous crop, every strategy scores 1 on family break and 0 on nutrient recovery, so priority fit decides.
- Ranks are 1, 2, 3 with no ties. Scores are 3, 2, 1 in that rank order.
- `actions` is empty. `planting_schedule` is empty. `water_demand_mm` is 0. `breaks_pest_cycle` is false and `pest_cycle_note` is empty. Story 1.4 owns actions, dates, water demand and the pest-cycle text.
- `uncertainty_note` says the forecast is not an observation when `projection.available` is true, and that the forecast is absent when it is false. `validation_note` says the ZARC check is not done yet (story 1.5).
- Titles are the kind value with spaces. Each strategy has one trade-off code: `keeps_current_calendar`, `favors_cover_and_soil`, or `favors_forage_or_income`. Recommendation sources are the diagnosis sources followed by the projection sources.
- Cite Kalaivani et al. in the `recommend` module docstring and add one row under README "Credits" for the paper. IEEE holds the copyright; cite the rules, do not copy the paper's text or figures.

**Never:**
- Do not train or call a model. Do not add scikit-learn, the Kaggle crop-recommendation dataset, or N, P, K, pH or humidity inputs. This codebase has no soil-test nutrients; SoilGrids is outside the MVP.
- Do not invent millimetres of water, cycle lengths, heat limits or numeric weights. Story 1.2 (#45, PR #85) owns those YAML files.
- Do not read files, the clock, or the network inside `src/engine`.
- Do not change `src/engine/model.py` or `docs/data-format/recommendation.schema.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| After maize, priority income | `previous_crops` ends with `maize` | Rank 1 is `soil_water_conservation` (it adds beans). Family break and nutrient recovery outrank the income preference | N/A |
| After beans, priority income | `previous_crops` ends with `beans` | Rank 1 is `resilient_income_forage` (adds maize, a different family). `current_practice` is last because it repeats Fabaceae | N/A |
| After maize, priority water | `previous_crops` ends with `maize`, priority `water` | Same rank 1 as the income row: `soil_water_conservation` | N/A |
| No previous crop, priority income | `previous_crops` empty | Rank 1 is `resilient_income_forage`, then `soil_water_conservation`, then `current_practice` | N/A |
| No previous crop, priority soil | `previous_crops` empty, priority `soil`, `water` or `erosion` | Rank 1 is `soil_water_conservation` | N/A |
| Unknown previous label | `previous_crops` ends with `rice` | Treated as no recognized previous crop | N/A |
| Forecast off | `projection.available` is false | A recommendation is still returned; the uncertainty note says the forecast is absent | N/A |
| Repeat call | Same objects as any row above | `serialize_recommendation()` matches the first call byte for byte | N/A |

</frozen-after-approval>

## Code Map

- `src/engine/model.py` -- reuse the story 1.1 types and `serialize_recommendation`. Do not change it.
- `src/engine/recommend.py` -- new pure function and the three-crop family table.
- `src/engine/__init__.py` -- export `recommend`.
- `tests/test_engine_recommend.py` -- new tests for the matrix, plus schema validation copied in style from `tests/test_engine_model.py`.
- `tests/test_engine_model.py` -- do not change.
- `README.md` -- one Credits row for Kalaivani et al., IEEE CICT 2025, with the DOI.
- `docs/data-format/recommendation.schema.json` -- contract. Empty `actions` and `planting_schedule` are valid. Do not edit it.
- `_bmad-output/implementation-artifacts/epic-1-context.md` -- story 1.3 depends on loaded profiles from 1.2. Those files are not on this branch. This story ranks without them.

## Tasks & Acceptance

**Execution:**
- [x] `src/engine/recommend.py` -- add `recommend(plot, diagnosis, projection, crop, priority)` and the family table -- story 1.3
- [x] `src/engine/__init__.py` -- export `recommend`
- [x] `tests/test_engine_recommend.py` -- cover the I/O matrix and schema validation
- [x] `README.md` -- credit Kalaivani et al. with the DOI

**Acceptance Criteria:**
- Given a Diagnosis, a Projection, a Crop and a Priority, when `recommend()` runs, then it returns `current_practice`, `soil_water_conservation` and `resilient_income_forage`, ordered by the frozen sort key.
- Given a previous maize crop, when `recommend()` runs for any priority, then rank 1 is `soil_water_conservation`.
- Given the same inputs, when `recommend()` runs twice, then `serialize_recommendation()` is byte-identical.
- Given any call, when it returns, then it has not read a file, the clock, the network, or a trained model.

## Implementation Notes

- `recommend()` lives in `src/engine/recommend.py` and is exported from `src/engine`.
- `tests/test_engine_recommend_snapshot.py` builds a Diagnosis from the cached Sergipe POWER snapshot (`apps/web/public/data/sergipe/power.json`) for the nearest grid cell to each pilot and checks the maize-previous ranking. The engine itself still does no I/O.

## Spec Change Log

## Review Triage Log

- false — previous maize plus selected beans plus income ranking resilient first. The frozen sort key gives every strategy nutrient recovery when the selected crop is already beans, so income breaks the tie. The matrix row that expects soil-water first says that strategy adds beans, which is the maize or cassava selection.
- patch — tests now cover the last previous-crop label, beans and cassava as non-depleting previous crops, and the full order when there is no previous crop and the priority is soil, water, or erosion. Priority equality uses `==`.
- false — diagnosis values, actions, water demand, and YAML profiles stay out of this story because the frozen block says so.

## Design Notes

The paper's rule engine is a ranked next-crop list keyed by family and nutrient impact. This story keeps the team's three strategy kinds and applies those two rules as a lexicographic key, so no coefficient is invented. Priority fit is only the third key, because FR-9 still requires the farmer's priority to be visible when the rotation rules do not already separate the three strategies.

## Verification

**Commands:**
- `uv run pytest tests/test_engine_recommend.py tests/test_engine_model.py` -- expected: all passed
