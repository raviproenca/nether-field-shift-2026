<!-- AI-assisted: generated with Cursor, reviewed by Lucas Feitosa -->

# Epic 1 Context: Decision engine (`src/engine`)

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Build a pure decision engine that turns a plot's Diagnosis and Projection, plus crop and priority, into one ranked Recommendation of at least three strategies. This epic is first because judging weighs validity and relevance: the advice is checked against ZARC and against real past Sergipe years before a channel (the producer dashboard, then an optional bot) is treated as the product.

## Stories

- Story 1.1: Domain model and Recommendation schema
- Story 1.2: Rules and crop profiles as data
- Story 1.3: Strategy generation and ranking
- Story 1.4: Actions, uncertainty and validation notes
- Story 1.5: ZARC check
- Story 1.6: Historical backtest in Sergipe (wet year and dry year)

## Requirements & Constraints

`recommend()` accepts a Diagnosis, a Projection, a Crop, a Priority, and reference data the caller already loaded. It returns one Recommendation. It does not fetch data and it does not write farmer-facing prose.

Shared types are Plot, Crop, Priority, Strategy, Diagnosis, Projection, and Recommendation. Field names are snake_case and follow the glossary. A Plot is a point plus a small radius. v1 crops are maize, beans, and cassava. Intercropping and cover crops are strategies. Priority is one of water, soil, erosion, or income.

Diagnosis fields the engine consumes, already computed upstream, are rain, soil moisture, vegetation, temperature, daily water balance (rain minus FAO-56 ET0), elevation and slope, and recurring bare-soil windows from NDVI history. A missing day stays missing. Projection is a 15-day forecast of rain, temperature, and ET0. Forecast series stay labeled non-NASA. If the forecast is absent, still return a Recommendation and record that limit in the uncertainty note.

Every Recommendation includes at least these strategies, ranked by the given Priority: current practice (`current_practice`), soil and water conservation (`soil_water_conservation`, for example intercropping or cover crops), and resilient income or forage (`resilient_income_forage`). Each strategy has concrete actions for the coming days and weeks (plant now or wait, protect the soil, plant on the contour where slope calls for it). Each action carries one line of evidence. Adding strategies or crops does not drop that evidence.

Every Recommendation has an uncertainty note (coarse resolution, a missing day, or a forecast that is not an observation) and a validation note (where a local technician must confirm the advice, and any disagreement between the planting window and ZARC for that crop and municipality). ZARC is the MAPA/Embrapa reference.

Crop profiles for maize, beans, and cassava record water need, cycle length, and heat limit, each with a source citation. Those numbers and the priority weights live in `src/engine/rules/crops.yaml` and `thresholds.yaml`. The caller loads them and passes an `EngineRules` object into `recommend()`.

The Recommendation is language-neutral: identifiers, numbers, and codes. There is no account and no stored farm history. Farmer trials, crop photos, and states other than Sergipe are out of this hackathon. SoilGrids is not an MVP source.

Done means: identical inputs produce a byte-identical Recommendation; a ZARC disagreement appears in the validation note; and a backtest of two or three real past Sergipe years, at least one wet and one dry, reports how each strategy would have done.

Story 1.3 ranks with the loaded rules. Inputs that change the score are the Diagnosis (rain, water balance, soil moisture, NDVI, temperature, slope), the Projection, `plot.region`, `plot.season`, and the previous crop. A strategy does not earn a family break while it still plants the previous botanical family. Priority weights change the order, not only the ties. Water demand comes from the crop profiles. Story 1.4 fills planting dates from the profile window and the diagnosis period, actions with one evidence line each, and the pest-cycle note. The validation note still says a technician must confirm and that the ZARC check is not done. ZARC access stays with story 1.5.

## Technical Decisions

`src/engine` is pure. No I/O, no network, no clock, and no randomness. Tests assert byte-identical output for the same inputs. The caller loads crop profiles, thresholds, and ZARC windows and passes them in.

Profiles and thresholds live in versioned YAML under `src/engine/rules/`.

The engine owns `docs/data-format/recommendation.schema.json`. A serialized sample Recommendation validates against it. Schema changes ship in the same change as the code that requires them. Diagnosis and forecast series keep the existing series shape (`time`, `values`, `unit`, `source`, `nasa`), owned outside this epic.

The backtest is one documented command outside the pure function. It loads only real observations for the chosen years (POWER, GLDAS, IMERG), calls the engine, and reports each strategy against the IBGE PAM (SIDRA) reference. Wet and dry years are justified by observed rain. Every source used is listed in the README with a link.

## Cross-Story Dependencies

- 1.2 follows the types and schema from 1.1. The issue list also ties crop profiles to open question 2, which is ZARC access format and granularity. Threshold numbers stay in YAML once the team sets them.
- 1.3 needs the model (1.1) and the loaded profiles (1.2).
- 1.4 adds actions and both notes on the ranked strategies from 1.3.
- 1.5 compares planting windows with ZARC. It needs 1.3 plus the ZARC research and connector (merged). The caller supplies the windows while access format stays open.
- 1.6 runs after 1.1 through 1.5 and needs the historical data connectors.
- The product API is the client-facing caller of `recommend()`. Clients do not import the engine. A later explanation layer may only rewrite a finished Recommendation; it must leave numbers, strategies, and ranking unchanged.
