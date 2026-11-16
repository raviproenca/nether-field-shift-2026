# Brainstorm log (Nov 14, 2026)

> Team notes — ideas and decisions are the team's; summaries assisted by AI.

Curated summary per session, in order. Nothing here is a decision: see [decisions.md](decisions.md).

## 10:07 · Mentor: Global Offers and public links
- Partner resources were released today (free domain, cloud credits, a weather-data API).
- Every submitted URL must be public, with no password, and must not expire. A judge who hits a login or an expired link will not insist: the project is out.
- Check each offer's validity period. Everyone on the team is responsible.

## 10:19 · Ravi and Lucas
- Vegetation and other NASA data need no field collection.
- Soil health could use a **field device (sensor)** in addition to an app.
- The app would merge the NASA data for the farmer's location (broader) with the device data (finer) and recommend what to plant and when, where, and what soil maintenance is needed.

## 10:24 · Duda
- Make clear how satellite observations differ from ground measurements, and validate with local collection and redundancy.
- **Water as a central metric:** access to water varies by region; in the Northeast, drought worsens wildfires (dependence on rain for water and energy).
- Question: the largest water-access dataset found (USGS) covers only the US. Looking for global alternatives.
- Clarified in the session: the NASA products in use are global; some (e.g. NLDAS) cover only North America and will not be used.

## 10:36 · Team
- Gather the requirements for the data to collect.
- In the app, the farmer enters soil type, location and crop; the system estimates the best planting arrangement, how the crop evolves over the years and soil health.
- Core value: **centralize** data that is scattered across different sources and make it useful. Maybe a map.

## 10:43 · Team (a mentor joined briefly)
- Turn the data into intelligence that is useful to farmers.
- Scope: **Brazil, family farming.** Critique of generic "small farmer" projects that list the barriers (cannot read, no phone, no internet) and then ignore the persona.
- Ask for the minimum: get data from the location; the farmer only says what they will plant.
- NASA layers ready for a map: vegetation, rain, fires, temperature.
- Family farmers in Brazil use phones and WhatsApp a lot (including for selling), but internet is weak. Idea well received by the team: **server-side processing, asynchronous delivery by WhatsApp, no app to install, daily maintenance tips.**

## 10:45 · Team
- Define the persona: who they are, what they provide, what they want, what can be collected.
- Location over WhatsApp: the user would send it. Is there a bot button for that?
- WhatsApp's bot API is paid, Telegram's is free: a Telegram demo, with WhatsApp as the ideal with resources. SMS mentioned as an alternative.

## 11:15 (a) · Team
- The data is historical only; the team wants **forecasts** ("it rained yesterday" does not help), and climate change weighs against relying on history alone.
- Compare **at least 3 planting strategies** per area (the rotation the farmer already uses plus 2 calculated ones), with the farmer choosing the priority: water, soil, erosion or income.
- AI only explains results in plain language and justifies them; calculations stay deterministic. Complex ML goes in the pitch as future work (no reliable yield data to train on during the hackathon).
- Download tests: 4–5 non-consecutive days, clipped to Sergipe.

## 11:15 (b) · Team
- **Two channels, one API:** a simple WhatsApp bot with buttons (family farmers) and a detailed web dashboard (larger farms, or the same farmer as they grow).
- An **internal team dashboard** to see everything on a map (NASA plus soil and moisture), with a shared login.
- Data sources proposed by Duda: NASA POWER, GPM IMERG, SMAP, Sentinel-2, Landsat, SRTM, SoilGrids, plus ANA (Brazil). Others welcome.
- State of the art: papers (IEEE) and patents or software registrations (INPI).
- Split discussed: Duda on data; one person on requirements and issues; Chaves (Gabriel) on screens.

## 12:05 · Team with a mentor
**What the team presented:** family farmers (small and medium) in Brazil; a conversational bot instead of complex charts; voice for people who have trouble reading or writing; daily tips and answers on planting, rotation and timing; NASA data plus other free sources for the region; MVP probably on a **Telegram bot** (WhatsApp's API is paid), with bot and dashboard on the same API; AI only to explain. Example from the team: farmers know "after São João (late June) you plant corn", but with climate change the date has shifted, and corn is sensitive to heat.

**Mentor feedback:**
- Good direction. **Close the scope this morning.**
- **Validate with 1–2 people from the field** (a farmer, or a businessperson who knows farmers) by the end of the day: someone saying "I would use this".
- Risk: most challenge datasets focus on the US. The team answered that many NASA datasets are global (rain, soil moisture, vegetation, climate).
- Build the data layer that consolidates everything early.
- Both channels are valid; the main focus is conversational.
- The biggest challenge is translating indicators into the farmer's everyday language.
- Not just the current state: **projection**, and if possible **prescription**.
- Start the **pitch skeleton** now with the keywords that come up.
- Have someone act as a **"traffic light"**: say what is green or red and change course early.
- Offered help with database organization and tooling.
