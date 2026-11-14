<!-- AI-assisted: generated with Claude Code (Periélio), scope set by Ravi; pending review by Ravi -->

# Epic: Internal data map

> **Internal team tool, not the product decision.** This map exists so the team can look at the data while the project idea is still under discussion (see [docs/team/CONTEXT.md](../../docs/team/CONTEXT.md)). Nothing here decides what the judges will see.

Epic issue: #19.

## Goal

A small web map that the team uses to browse NASA layers over Sergipe and the Northeast of Brazil and to see time series for a clicked point, served by the existing `src/data` toolkit.

## Constraints

- Free services only, no API keys, and no trial that expires before Jan 26, 2027.
- No credentials in Git: the shared password and any secret come from environment variables or deploy secrets.
- The shared login protects only this internal map. Anything the judges open later has no login.
- Credits in the app: OpenStreetMap contributors, NASA GIBS. No NASA logos or branding; NASA Worldview is visual inspiration only (no copied code or marks).
- English in code, UI and docs.

## Stories

### Story 1: Front setup (#12)

The proposed default is Vite, React, TypeScript and MapLibre GL (free, no key) in `apps/web/`. The owner may choose another stack, but records the choice in AGENTS.md section 2 in a separate PR.

- [ ] `apps/web/` runs locally with one documented command.
- [ ] The stack choice is recorded in AGENTS.md section 2 in a separate PR.
- [ ] Lint or type check runs without errors.

### Story 2: Base map and region selector (#13)

- [ ] OpenStreetMap tiles with visible attribution.
- [ ] Starts focused on Sergipe.
- [ ] A region selector with the same presets as `src/data` (`sergipe`, `nordeste`).

### Story 3: NASA GIBS layers (#14)

WMTS, no key.

- [ ] Layers: true color, NDVI (MODIS/VIIRS), precipitation (IMERG), soil moisture (SMAP), land surface temperature and fire hotspots (FIRMS/VIIRS).
- [ ] Each layer has an on/off toggle and a legend.
- [ ] A date selector changes the date of every layer.
- [ ] GIBS credits are shown in the app.

### Story 4: Point time-series panel (#15)

Depends on Story 5 (#16).

- [ ] Clicking the map opens a side panel with time series from our API for that point (POWER, IMERG, SMAP, GLDAS…).
- [ ] Loading, empty and error states show a clear message.

### Story 5: Minimal data API (#16)

For example FastAPI in `apps/api/`, exposing `src/data` by point, radius and period.

- [ ] An endpoint for each source, taking point, radius and period.
- [ ] Responses are cached locally.
- [ ] API errors are clear JSON messages, never a crash.
- [ ] Tests run with pytest.

### Story 6: Shared login for the internal map (#17)

- [ ] A simple shared login for the internal map only.
- [ ] The password comes from an environment variable or secret and is never in the repo.
- [ ] Judge-facing pages are not affected.

### Story 7: Deploy the internal map (#18)

- [ ] The front end is on Cloudflare Pages or GitHub Pages.
- [ ] The API hosting choice is written down, with the options considered.
- [ ] No service depends on a trial or free credit that expires before Jan 26, 2027.
