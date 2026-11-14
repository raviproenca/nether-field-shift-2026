# Decisions

> Team notes — ideas and decisions are the team's; summaries assisted by AI.

Only what the team **formally decided** goes here, with date and who confirmed it. Discussions go in [brainstorm-log.md](brainstorm-log.md).

| Date | Decision | Confirmed by |
|---|---|---|
| Nov 14, 2026 | The **internal data map** is published on Cloudflare Pages under a `*.pages.dev` address, with no custom domain. | Ravi (Tech Lead) |
| Nov 14, 2026 | The farmer-facing bot channel is **Telegram** for now. WhatsApp is future work, mentioned in the pitch. | Ravi (Tech Lead) |
| Nov 14, 2026 | Work is split into **three fronts** (A internal map, B farmer product, C judges' delivery); see [CONTEXT.md](CONTEXT.md#2-three-fronts). Nothing in front B is built before the formal idea decision and the PRD. | Ravi (Tech Lead) |
| Nov 14, 2026 | The internal map uses **pre-generated data and no API**: a toolkit script builds light JSON/GeoJSON snapshots (Sergipe/Nordeste) published with the front end on `*.pages.dev`; NASA GIBS layers stay live. No login inside the front end. Durable hosting for front B is decided after the idea. | Ravi (Tech Lead) |
| Nov 14, 2026 | Internal map access: **no login**. The `*.pages.dev` URL is not advertised and the site sends `noindex` (robots meta + `X-Robots-Tag`). Hosted on **Ravi's Cloudflare account**, with a neutral project name (e.g. `nether-field-map`). | Ravi (Tech Lead) |
| Nov 14, 2026 | **Voice in the Telegram bot is in scope:** the bot understands voice messages (speech-to-text) and replies with voice (text-to-speech) as well as short text. Built with the rest of front B, after the idea decision and the PRD. | Ravi (Tech Lead) |
| — | _Pending: the project idea itself is still under discussion._ | — |
