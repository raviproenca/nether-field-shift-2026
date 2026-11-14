---
title: "Product Brief: Field Shift decision support for family farming in Sergipe"
status: draft
created: 2026-11-14
updated: 2026-11-14
---

<!-- AI-assisted: drafted with Claude Code (Periélio, BMad product brief, headless fast path) from the team's own idea and notes; pending review by Ravi (Tech Lead). The idea is the team's: see docs/team/decisions.md. -->

# Product Brief: Field Shift decision support for family farming in Sergipe

> Working title. The team has not chosen a product name. `[ASSUMPTION]` tags mark points inferred from the team notes that still need confirmation.

## Executive Summary

The team confirmed the idea on Nov 14, 2026 (Ravi, Tech Lead, for the team; source: `docs/team/decisions.md`, PR #29). It is a decision-support tool for **Brazilian family farmers in Sergipe** (Agreste and Semiárido). The farmer says where they farm and what they plan to grow. The tool answers with **what to do next**: it compares **at least three crop or rotation strategies** for that plot, including the farmer's current practice, intercropping (*consórcio*) and cover crops, weighted by the priority the farmer picks (water, soil, erosion or income).

The answer looks forward: it **projects** conditions for the coming days and **prescribes** concrete actions (when to plant, what to plant next, how to protect the soil). This follows the mentor's advice to go "from projection to prescription". The calculations are deterministic and built on NASA data. AI only turns the results into plain language. No ML model makes the recommendation.

There are two interfaces on **one API**: a **Telegram bot**, with voice in and out, for smallholders, and a **producer web dashboard** for larger farms and extension workers. Everything the judges open works without login.

## The Problem

- Traditional planting calendars no longer hold. One example from the team: "after São João you plant corn". With climate change that date has moved, and corn is sensitive to heat.
- "It rained yesterday" does not help. Farmers need to know what comes next, and history alone is no longer reliable.
- The data exists (rain, soil moisture, vegetation, temperature), but it is scattered across sources and written in technical language.
- Generic apps for small farmers list the barriers (weak internet, trouble reading) and then ignore them: "the persona was missing". The mentor sees the farmer's language as the biggest challenge.

## The Solution

1. **Minimal input.** The farmer shares a location with the Telegram button and says the crop, by voice or by text. Everything else comes from data.
2. **Diagnosis from NASA data.**
   - Past and recent conditions: POWER, IMERG, SMAP, GLDAS, NDVI from MODIS/VIIRS/HLS, and NASADEM/SRTM terrain.
   - Water balance: FAO-56 ET0 minus rainfall.
3. **Projection.** A 15-day weather forecast from Open-Meteo. It is used only in the product API, for non-commercial use during the hackathon, and credited as not NASA. NASA GEOS-FP is named in the pitch as the NASA path for forecasts.
4. **Prescription.** At least three strategies are compared and ranked by the farmer's priority: the current practice, a soil and water conservation option, and a resilient income or forage option. Each comes with the evidence behind it, its trade-offs, its uncertainty, and when to check with a local agronomist. The official ZARC zoning (MAPA/Embrapa) is the reference to check planting windows against.
5. **Delivery.**
   - **Bot:** short messages and audio. Speech-to-text uses faster-whisper. Text-to-speech uses Piper, which runs as a separate service because it is GPL.
   - **Dashboard:** the same results on a MapLibre map with OpenStreetMap and NASA GIBS layers, plus a demo mode for judges.

## What Makes This Different

- **Persona first.** Voice, short messages, no app to install, and it works on weak connections.
- **Prescriptive, not descriptive.** It says "what to do", not only "how it is".
- **Explainable.** Every number traces back to a NASA dataset and a rule. AI only rewrites results in plain language.
- This is honest about its edge: the team is not claiming any technical moat. The bet is persona and execution, with free and open data.

## Who This Serves

- **Primary user: the family farmer in Sergipe** (small to medium plot). They use the phone and messaging a lot, have weak internet, and may have trouble reading or writing. Success for them means a clear next step they trust, in their own language.
- **Secondary users: larger producers and extension workers (ATER, cooperatives).** They use the dashboard to see the evidence in detail.
- **Pilot sites:**
  - Itabaiana, in the Agreste;
  - Nossa Senhora da Glória, in the Semiárido.

## Success Criteria (hackathon)

_Updated Nov 14 for the new priority: engine first, then validation, then dashboard (`docs/team/decisions.md`)._

- A judge completes the full flow in the **dashboard demo mode**, with no login: a pilot site in, the strategy comparison out, with evidence and uncertainty. Both pilot sites work. The bot is optional.
- The engine is **validated**: its planting windows are checked against ZARC, and a historical backtest on 2 or 3 real Sergipe years (at least one wet and one dry) shows how each strategy would have done.
- Every number shown can be traced to a named NASA dataset, or to a credited third-party source.
- Every submitted link is public and stays valid until Jan 26, 2027.
- If the bot ships after validation: a voice reply comes back in a few seconds on CPU `[ASSUMPTION]`. In the Nov 14 spike, Whisper small took 1.2 s to transcribe 5.5 s of audio, and Piper took 0.4 s to generate 5.5 s of audio.

## Scope

**In (hackathon v1):**
- Decision engine and its validation (ZARC check and historical backtest), built first.
- Producer dashboard with a judge demo mode.
- Telegram bot with location, crop, priority and voice: after the engine is validated; channel and audience decided then.
- Shared API on `src/data` and the snapshot format, covering Sergipe and the two pilots.
- Deterministic strategy comparison.
- Open-Meteo forecast.
- Plain-language explanation.

**Out:**
- Validation with real farmers. It is skipped in the hackathon and becomes the next step in the pitch.
- Crop photos.
- WhatsApp, which is future work.
- ML yield prediction.
- Field sensors.
- Other states.
- Commercial use of Open-Meteo.

**Pending decisions:**
- Product hosting. The proposal is Google Cloud from Global Offers (US$ 300 for 90 days), pending Ravi's OK.
- The product name.

## Vision

After the hackathon:
- Validate with farmers and extension workers in Sergipe.
- Add WhatsApp as the channel.
- Move forecasts to a NASA source (GEOS-FP) or a commercially licensed one.
- Expand from Sergipe to the rest of the Northeast with the same data core.
