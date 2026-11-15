# Epic 3 Context: Plain-language explanation (`src/explain`)

<!-- AI-assisted: generated with Cursor, reviewed by Guilherme -->

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Turn a finished Recommendation into short text for a technical professional who leads planting decisions in Sergipe. The product must answer with no AI provider: a fixed template is always available and is the only explanation that ships until the team records how AI should help this user. Discovery collects that decision; until it is recorded, leave the AI role unspecified. The engine stays deterministic. This layer does not change a number, a Strategy, or a ranking, and no machine-learning model produces the recommendation.

## Stories

- Story 3.1: Template explanation (no AI)
- Story 3.2: AI rewrite with number check (on hold until E7.2)

## Requirements & Constraints

The reader is the technical decision-maker on the dashboard. The Telegram bot and voice are out of v1. The dashboard is the only product client.

For every Recommendation, the template names each Strategy, that Strategy's first action, and its uncertainty. Every number in the text already appears in the Recommendation.

Any later AI explanation may use only the Recommendation and that Recommendation's Diagnosis and Projection. It leaves numbers and Strategies unchanged. A stated number must already exist in the structured result. When it does not, when the model call errors, or when the quota runs out, return the fixed template. Vertex AI Gemini Flash is the available model. Story 3.2 stays on hold and will be rewritten after the team records the role of AI. The number check, the template fallback, and the requested language stay fixed. Do not add a separate AI endpoint before that decision. The template is in the MVP; the AI rewrite is not.

Code and comments stay in English. AI credentials come only from environment variables or the Cloud Run service account, never from Git. A number the user sees still traces to a named source; this layer does not invent sources.

## Technical Decisions

`src/explain` takes a finished Recommendation and returns text only. `apps/web` receives that text from the API and does not import this package. The recommendation response carries the structured Recommendation and the explanation together. The engine owns the Recommendation schema. Explain consumes it and does not change it. The schema is language-neutral: identifiers, numbers, and codes.

Numbers enter the template only through placeholders filled from the structured Recommendation. A check rejects model output that contains a number absent from the input, and the template is used. The template exists in both `pt-BR` and `en`.

`lang` on the request is `pt-BR` or `en`. The dashboard defaults to `en`. Only this layer, the template strings, and the UI strings depend on language. The response cache stores the structured result once and keys explanation text by `lang`.

Vertex AI uses the Cloud Run service account, with no API key. Config names are `EXPLAIN_MODEL`, `GCP_PROJECT`, and `GCP_REGION`, listed empty in `.env.example`. Pin `EXPLAIN_MODEL` at deploy time to the current generally available Gemini Flash model. The client library is `google-genai` 3.3.0. Logs are JSON lines to stdout and omit tokens.

Strategy kinds the text must name: `current_practice`, `soil_water_conservation`, and `resilient_income_forage`. The Recommendation already includes an Uncertainty note and a Validation note.

## UX & Interaction Patterns

No UX specification exists yet. One follows discovery and the team's AI decision. Until then, the dashboard is English by default, and a control switches every label, the explanation, and unit names to Brazilian Portuguese by calling the API with `lang=pt-BR`. The explanation is short text beside the strategy comparison.

## Cross-Story Dependencies

Story 3.1 depends on the domain model and Recommendation schema (story 1.1). The recommendation endpoint (story 2.4) depends on 3.1 and includes this text. Story 3.2 depends on 3.1 and waits on story 7.2, which records the persona and the role of AI. The template issue is #52. The rewrite issue #55 stays on hold.

The dashboard language control (story 5.3) shows the explanation and sends `lang`. Epic 3 is later than the dashboard in priority, and the recommendation response still needs the template before that endpoint is done.

Call path: dashboard to API, API runs the engine, then explain. Explain does not fetch data and does not rank strategies.
