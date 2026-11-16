---
title: 'Template explanation without AI'
type: 'feature'
created: '2026-11-15'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<!-- AI-assisted: generated with Cursor, reviewed by Guilherme -->

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A finished Recommendation has no short text. The product must explain the three strategies without calling an AI provider.

**Approach:** Add `src/explain` with a fixed template in `en` and `pt-BR`. The text names every strategy, copies that strategy's first action summary, and states the Recommendation `uncertainty_note` once. It adds no number of its own. A strategy with no actions is named and says it has no action. `lang` is `en` or `pt-BR`; the dashboard default is `en`.

</frozen-after-approval>

## Implementation Notes

- Added `src/explain/template.py` with `explain(recommendation, lang="en")`. `src/explain/__init__.py` re-exports it.
- Strategy lines follow rank. The first action summary is copied. A strategy with no actions gets a fixed sentence with no digits.
- The Recommendation `uncertainty_note` is printed once, after the strategies.
- Tests: `tests/test_explain_template.py` (7 passed). Numbers in the text must come from the copied title, first action summary, or uncertainty note.

## Review Triage Log

- First action only: false. Issue #52 and the frozen intent ask for the first action summary, not later actions or evidence.
- Missing crops, schedule, water demand, and validation note: false. The frozen intent copies the title, the first action, and `uncertainty_note`, and adds no number of its own.
- Portuguese leaves engine sentences in English: false. Those sentences are copied from the Recommendation. The template translates only its own wrappers.
- Number check was a substring of the whole JSON: medium. The test now allows only numbers from the copied fields, and asserts water demand and a later action stay out.
- Missing tests for rank order, no strategies, and the Portuguese empty-action line: low. Added those tests.
- Kind codes, Vertex settings, and the epic-context tension: false. This story does not emit kind codes or call a model. The context file records the later AI design as on hold.
