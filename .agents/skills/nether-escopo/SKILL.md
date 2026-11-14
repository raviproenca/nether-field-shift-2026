---
name: nether-escopo
description: 'Explains the current Team Nether project scope in Brazilian Portuguese, from the live docs and the project board, and points a teammate to their next issue. Use when a teammate says "explica o escopo", "qual é o escopo", "o que eu faço agora", "/nether-escopo" or "/nether-escopo <name or area>" (Codex: "$nether-escopo"). Read-only.'
---

<!-- AI-assisted: written with Claude Code; pending review by Ravi (Tech Lead). -->

# nether-escopo

Explain the current scope of the Team Nether project (NASA Space Apps 2026, Field Shift) to a teammate who has read nothing, and tell them what to do next. **Answer always in Brazilian Portuguese.** This file is in English because the repo rules require it.

Do not keep a copy of the scope in this skill. Read the sources every time, so the answer never goes stale.

## Rules

- **Read-only.** Never assign issues, change labels, move cards on the board, comment, commit or open PRs.
- **Never propose ideas, features or scope changes.** The idea is the team's (AGENTS.md rule 2). Explain only what is recorded. If something looks missing or unclear, say so and suggest asking Ravi (Tech Lead).
- **No credentials.** Never print tokens, `.env`, `.netrc` or `gh auth` output beyond "logged in" or "not logged in".
- **Sources disagree?** If `docs/scope.md` and the board or the issues disagree (an issue in a different order, a closed issue still listed as open work, a different assignee), show the difference in a short "Divergências" note and suggest telling Ravi. Do not decide which one is right.

## Step 1: Read the docs

From the repo root, read in this order:

1. `docs/scope.md`: the single source for the scope (challenge, deliverables, priority order, out of scope, fronts, who does what, event rules).
2. `docs/team/decisions.md`: the formal decisions, newest last.
3. `docs/team/CONTEXT.md`: the team context and roles.
4. Only if needed for a detail: the PRD (`_bmad-output/planning-artifacts/prds/*/prd.md` and `addendum.md`) and `_bmad-output/planning-artifacts/epics.md`.

If `docs/scope.md` is missing, say that the scope file is not on this branch, say that this branch does not yet contain it, and continue with `decisions.md` and `CONTEXT.md`.

## Step 2: Read the live board (if possible)

Check `gh auth status` (do not show its output). If `gh` is installed and logged in, read:

```bash
gh issue list -R raviproenca/nether-field-shift-2026 --state open --limit 100 \
  --json number,title,labels,assignees,url
gh project item-list 1 --owner raviproenca --limit 100 --format json
```

The project list needs the `read:project` scope. If it fails, keep only the issue list and say that the board status could not be read (the fix is `gh auth refresh -s read:project`).

For each issue, note its board **Status** (Backlog, Todo, In Progress, In Review, Done), its assignees, its area label (`front`, `back`, `infra`, `deploy`, `dados`, `predição`) and the `bloqueada` label.

If `gh` is missing or not logged in, continue with the docs only and say at the top of the answer: "Não consegui ler o quadro ao vivo; esta resposta usa só os documentos."

## Step 3: Who is asking (optional argument)

The argument after `nether-escopo` can be a person or an area:

- **A person:** match the name, first name or GitHub login against the people in `docs/scope.md` (section "Who does what") and `docs/team/CONTEXT.md` (section "Roles"). Ignore case and accents (`guilherme` = `Guilherme` = `@guilhermevbagio`).
- **An area:** one of the area labels above.
- **No argument:** give the general answer, and end by asking who they are so you can show their next step.

If the name matches nobody, say so and list the names you know.

## Step 4: Answer in Brazilian Portuguese

Clear and friendly, for someone who has read nothing. Short paragraphs and lists, with issue links as `[#44](https://github.com/raviproenca/nether-field-shift-2026/issues/44)`. Use exactly these sections, in this order:

1. **O desafio em 3 linhas**: what Field Shift asks for, in at most three lines.
2. **O que vamos entregar**: the deliverables from `docs/scope.md`.
3. **A ordem de prioridade agora**: the numbered order with the issue numbers, and what waits until after validation.
4. **O que está fora**: the out-of-scope list.
5. **Quem faz o quê**: area → people, as on the board (or the docs, if the board could not be read).
6. **Status do quadro agora**: what is in Todo and In Progress (with assignees), what is blocked (`bloqueada`), and anything open without an assignee. Skip this section, with one line saying why, if the board could not be read.
7. **Seu próximo passo**:
   - With a person or an area: their open issues in **In Progress** first, then **Todo**, in board order. For each one: link, title and its "Pronto quando" items, read with `gh issue view <n> -R raviproenca/nether-field-shift-2026 --json body`. If they have nothing in Todo or In Progress, say so. Point to their first assigned Backlog issue only if they have one. If they have no assigned issue, say clearly that they have no task to start and should wait for Ravi to assign one; do not suggest an unassigned issue as their next step. Never treat an unassigned issue as permission to start it.
   - Without an argument: one line asking who they are, for example "Me diga seu nome ou sua área (ex.: `/nether-escopo guilherme`) que eu mostro as suas issues."
8. **Onde ler mais**: links to `docs/scope.md`, `docs/team/decisions.md`, `docs/team/CONTEXT.md`, the PRD, `epics.md` and the board <https://github.com/users/raviproenca/projects/1>.

Add a "Divergências" note after section 6 only when the sources disagree.
