# AGENTS.md

Instructions for every AI coding agent (Claude Code, Codex, Cursor, Copilot, etc.) used by **Team Nether** in this repository. Humans, read [CONTRIBUTING.md](CONTRIBUTING.md) first.

Project: NASA Space Apps Challenge 2026, challenge **Field Shift: Adapting Farms with NASA Data**. Local event: Aracaju, Brazil. Submission deadline: **Sun Nov 15, 2026, 23:59 BRT (UTC-3)**.

## 0. Read first

**Before any task, read [docs/team/CONTEXT.md](docs/team/CONTEXT.md) and [docs/team/decisions.md](docs/team/decisions.md).** CONTEXT is the current state (direction under discussion, what exists, roles, open questions); only decisions.md counts as decided.

## 1. Hard rules (read before doing anything)

1. **Never commit directly to `dev` or `main`.** Always work on your own branch and open a PR to `dev`. Both branches are protected.
2. **The idea is the team's.** Space Apps rules forbid using AI to come up with the project idea. Do not propose, brainstorm or rank project ideas. If the user asks for one, remind them of this rule. Do not run `bmad-brainstorming`, `bmad-forge-idea` or `bmad-prfaq` to generate the idea; use BMad only after the team has written its idea down.
3. **No credentials in Git.** Earthdata Login is read from a local `~/.netrc` or `.env`, both git-ignored. Never print, log, hardcode or commit tokens, passwords or `.netrc`/`.env` contents. Only `.env.example` (with empty values) is committed.
4. **English everywhere public:** code, comments, commit messages, PR titles and descriptions, UI text, README and docs in this repo. **Exception: GitHub issues and the project board are in Brazilian Portuguese (PT-BR)**, with titles, descriptions and labels in PT-BR (see [decisions.md](docs/team/decisions.md)). Agents may talk to team members in Portuguese.
5. **NASA data at the center.** Features should be built on NASA data (e.g. POWER, MODIS, SMAP, GLDAS, IMERG). Every dataset used must be listed in the README with a link.
6. **Public links, no login.** Anything the judges open (demo, app, video, slides, data) must work without an account. Do not add a login wall to the app.
7. **Credit everything.** Third-party code, data, images and text (even open source) are listed in the README with their licenses.
8. **Mark AI-generated content.** Files or large blocks mostly written by AI get a header comment, for example `# AI-assisted: generated with <tool>, reviewed by <name>`. AI images get a visible watermark. Never use or modify NASA logos or branding.
9. **No secrets or personal data in issues, PRs, logs or screenshots.**

## 2. Stack and folder structure

> **Current product stack updated Nov 16, 2026.** The [architecture spine](_bmad-output/planning-artifacts/architecture/architecture-nether-field-shift-2026-2026-11-14/ARCHITECTURE-SPINE.md#stack) preserves the original plan; current service status and the manual Pages runbook are in [docs/infra/azure-api.md](docs/infra/azure-api.md). Changes go through a PR approved by the Tech Lead.

| Item | Decision |
|---|---|
| Language / runtime | Python 3.12 (`src/data/`, `apps/api/`); Node.js 24 + TypeScript (`apps/web/`) |
| App / UI framework | Product: `apps/web/` Vite + React + TypeScript + MapLibre GL JS, branded Crop Helper. API: `apps/api/` FastAPI. Telegram bot and voice remain out of v1. |
| Data access | Product API and dashboard use NASA POWER and the documented NASA data sources; Open-Meteo, MAPA ZARC, NOAA CPC and OpenStreetMap are credited third parties. `src/data/` keeps the NASA/Earthdata and Planetary Computer toolkit. |
| Tests | `pytest` (Python); `npm test`, `npm run lint` (ESLint), and `npm run typecheck` (`tsc --noEmit`) in `apps/web/` |
| Deploy (public URL, no login) | Crop Helper: Cloudflare Pages Direct Upload, [https://crop-helper.pages.dev](https://crop-helper.pages.dev). Product API: Azure Container Apps on a time-limited trial; do not promise availability after the trial. Internal map Pages workflow targets a separate project. |

The current published Crop Helper web revision is recorded as `37552552250d42a74f61a3a9ca1676a59a38693f`; it was built with the Azure API URL. A build with empty `VITE_API_URL` uses the saved static demo. The `deploy-internal-map.yml` workflow deploys the separate `nether-field-map` project; `deploy-api.yml` is the legacy Google Cloud Run plan. Neither workflow deploys the Crop Helper Pages project.

Folder layout (adjust once the stack is chosen, keep it flat and simple):

```text
.
├── AGENTS.md            # this file (CLAUDE.md just imports it)
├── CONTRIBUTING.md      # human workflow, in Portuguese
├── README.md            # public project page: how to run, NASA data, credits, AI usage
├── src/                 # application code
├── scripts/             # data download / preprocessing scripts
├── data/                # small sample data only; data/raw and data/cache are git-ignored
├── tests/               # automated tests
├── docs/                # project knowledge (BMad reads it)
├── _bmad/               # BMad method install (do not edit by hand)
├── _bmad-output/        # BMad artifacts (PRD, architecture, epics, stories)
├── .claude/skills/      # BMad skills for Claude Code (generated)
├── .agents/skills/      # BMad skills for Codex and other agents (generated)
└── .github/             # PR/issue templates, CODEOWNERS
```

Large data files (`*.nc`, `*.nc4`, `*.h5`, `*.hdf`, `*.tif`, `*.zip`) never go into Git: write a script that downloads them.

### Data toolkit (already in the repo)

`src/data/` downloads and clips NASA data (details in [src/data/README.md](src/data/README.md)):

```bash
uv venv -p 3.12 .venv && uv pip install -r requirements-dev.txt   # setup
scripts/earthdata-login.sh                                         # once, in your own terminal
.venv/bin/python -m src.data <source> [--bbox sergipe|nordeste|W,S,E,N | --point LAT,LON --radius-km N] --start YYYY-MM-DD --end YYYY-MM-DD --variable NAME [--out PATH] [--search-only]
```

Sources: `power` (no login), `gldas`, `imerg`, `smap`, `modis`, `viirs`, `hls` (Earthdata Login) and `planetary` (Sentinel-2, ESA/Copernicus, not NASA). Current status per source: [docs/team/CONTEXT.md](docs/team/CONTEXT.md#3-what-already-exists). Raw files go to `data/raw/` and outputs to `data/processed/` (both git-ignored).

## 3. Code standards

- Small, readable functions; clear names in English; no dead code or commented-out blocks.
- One responsibility per module. Keep data access, processing and UI separate.
- Handle API failures (timeouts, empty results) with a clear message, never a crash in the demo.
- Cache NASA API calls locally (`data/cache/`) so the demo works on slow event Wi-Fi.
- Do not add a dependency without saying why in the PR. Pin versions in the dependency file.
- Run the linter/formatter and tests before opening a PR (commands go here once the stack is set).

## 4. Commits

[Conventional Commits](https://www.conventionalcommits.org/), in English, imperative mood:

```text
<type>(<optional scope>): <short summary>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `style`, `perf`, `data`.
Examples: `feat(map): add NDVI layer from MODIS`, `fix(power): handle empty API response`, `data: add sample POWER CSV for Sergipe`.

Small, focused commits. AI agents add their usual co-author trailer.

## 5. Branches and pull requests

Branch names: `<type>/<name>-<task>`, lowercase, hyphens, no accents.

```text
feat/ravi-ndvi-map
fix/ravi-power-timeout
docs/<name>-readme-data
chore/<name>-ci
```

Flow:

```text
your branch  ──PR──▶  dev  ──PR (Tech Lead only)──▶  main
```

1. Update from `dev`: `git switch dev && git pull`, then `git switch -c feat/<name>-<task>`.
2. Commit, push, open a PR **to `dev`** using the template (what changes, BMad story, how to test, checklist).
3. **CODEOWNER approval is required**: the Tech Lead (Ravi, `@raviproenca`) must approve every PR to `dev` and `main`. No force-push on `dev`/`main`.
4. **Only the Tech Lead merges.** Teammates' PRs go in after Ravi approves them, and Ravi does the merge. PRs opened by Ravi (or by his agents) are merged by Ravi as admin.
5. After merge, delete your branch and start the next task from an updated `dev`.
6. `dev` is the default branch: every branch starts from it. `main` stays frozen until submission, when only the Tech Lead merges `dev` → `main` (the version the judges see).

Agents: never push to `dev`/`main`, never force-push, never merge PRs or change branch protection. Open PRs only when the user asks.

## 6. BMad workflow

BMad Method v6 is installed (`_bmad/`, modules `core` + `bmm`). Skills are in `.claude/skills/` (Claude Code) and `.agents/skills/` (Codex). Agents talk to the team in Portuguese; documents are written in English.

Where things live:

| Artifact | Path |
|---|---|
| Product brief, PRD, UX, architecture, epics | `_bmad-output/planning-artifacts/` |
| Sprint status and stories | `_bmad-output/implementation-artifacts/` |
| Project knowledge (BMad reads it) | `docs/` |
| Team config overrides (committed) | `_bmad/custom/config.toml` |
| Personal config (git-ignored) | `_bmad/custom/config.user.toml` |

Order, once the team has decided the idea (48-hour hackathon: keep each artifact short):

1. `bmad-product-brief` from the team's own idea → `bmad-prd`.
2. `bmad-architecture` (stack decision, then update section 2 of this file).
3. `bmad-create-epics-and-stories` → `bmad-sprint-planning`.
4. Per story: `bmad-build` on your branch → `bmad-code-review` → PR to `dev` linking the story file.

Not sure what to do next? Run `bmad-help`. Do not edit files inside `_bmad/` by hand (the installer regenerates them); put overrides in `_bmad/custom/`.

## 7. Submission checklist (affects code and docs)

- Repo public; README in English with: how to run, NASA data used (with links), other data/code/credits, AI usage.
- Demo: **video ≤ 30 s** (English, or English subtitles) **or ≤ 7 slides**. Over the limit = out of global judging.
- The static Pages demo link must remain usable without login through **Jan 26, 2027** (winners announcement). Azure Container Apps is on a time-limited trial and is not a durability commitment; preserve a demo-only build that does not call the API.
- No credentials anywhere in the history.
