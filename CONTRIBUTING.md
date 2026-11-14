# Como contribuir (Equipe Nether)

Regra de ouro: **nunca commitar direto em `dev` ou `main`.** Tudo entra por PR para `dev`, com a aprovação do Tech Lead (Ravi), que faz o merge. A `dev` é a branch padrão e toda branch parte dela. A `main` fica parada até a entrega, quando só o Ravi leva a `dev` para a `main`.

## Passo a passo

1. **Clonar** (uma vez só):
   ```bash
   git clone https://github.com/raviproenca/nether-field-shift-2026.git
   cd nether-field-shift-2026
   ```
2. **Atualizar a `dev` e criar a sua branch** (a cada tarefa):
   ```bash
   git switch dev && git pull
   git switch -c feat/<seu-nome>-<tarefa>     # ex.: feat/ravi-mapa-ndvi
   ```
   Prefixos: `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/`. Tudo minúsculo, com hífen e sem acento.
3. **Commitar** em inglês, no padrão Conventional Commits:
   ```bash
   git add <arquivos>
   git commit -m "feat(map): add NDVI layer from MODIS"
   ```
4. **Enviar e abrir o PR para `dev`:**
   ```bash
   git push -u origin feat/<seu-nome>-<tarefa>
   gh pr create --base dev --fill    # ou pelo site, escolhendo base: dev
   ```
   Preencha o template (o que muda, a história do BMad, como testar e o checklist).
5. **Revisão e merge:** o PR só entra com a aprovação do Ravi (CODEOWNER), e quem faz o merge é o Ravi. Não mescle o seu próprio PR. Depois do merge, apague a branch e volte ao passo 2.

## Lembretes do Space Apps

- Código, commits, PRs, README, docs e interface **em inglês** (aqui no CONTRIBUTING pode ser em português).
- Issues e quadro do Project **em português (PT-BR)**: título, descrição e etiquetas.
- **Credencial nunca vai para o Git:** `.env` e `~/.netrc` ficam só na sua máquina. Use o `.env.example` como modelo.
- Arquivos de dados grandes não entram no repo: use um script que baixa.
- Todo dado da NASA ou de terceiros usado precisa ser citado no README, com link.
- **A ideia é da equipe:** IA ajuda no código, mas não gera a ideia.
- Links da entrega abrem sem login. A demo tem no máximo 30 s de vídeo ou 7 slides.

## IA e BMad

Cada um pode usar o agente que quiser (Claude Code, Codex, Cursor…). Todos leem o [AGENTS.md](AGENTS.md). O fluxo BMad (PRD → arquitetura → épicos → histórias) gera arquivos em `_bmad-output/`. Se não souber o próximo passo, rode a skill `bmad-help`.
