<!-- AI-assisted: written with Claude Code from the backtest output, reviewed by <pending Gabriel>. Appended to backtest-report.md by scripts/backtest.py. -->

## Findings

Numbers come from the tables above and from `data/processed/backtest_years.csv` (rerun the script to reproduce). 45 seasons per pilot, 1981 to 2025.

1. **The pain is real in the Semiárido.**
   - In Nossa Senhora da Glória, municipal maize yield moves with rain in the ZARC window (Spearman ρ = 0.53).
   - The median maize yield anomaly is −27% in dry seasons and +32% in wet ones.
   - Beans react less (ρ = 0.32; −10% in dry seasons), and cassava barely reacts (ρ ≈ 0; 0%).
   - Rain timing in April to June decides the maize season there.
2. **Itabaiana does not show this link.**
   - Rain-yield correlations are near zero or negative (maize ρ = −0.03, beans −0.39).
   - This fits its irrigated, vegetable and tuber profile (see `docs/research/persona-discovery.md`).
   - Municipal PAM there says little about rain-fed decisions.
3. **The engine does not change its advice with the season.**
   - For maize with the water priority, rank 1 is "soil and water conservation" (maize + beans) in all 45 years at both pilots.
   - It stays the same with no forecast and with a perfect 15-day forecast.
   - The scores move, but the fixed crop traits dominate the ranking.
4. **Rank 1 matched the best PAM outcome only slightly more often than chance.**
   - With the water, soil or erosion priority: 38% against 34%.
   - With the income priority, it did worse than chance (28%). The income score is a constant in the code, not data.
5. **The January to March diagnosis says nothing about the season.**
   - Its water balance has no correlation with April to June rain (ρ = 0.01 and −0.08).
   - Information available on March 31 cannot anticipate the season. This matches the El Niño analysis: ENSO raises risk but does not predict it.
6. **The rule profiles disagree with the data on cassava.**
   - The engine gives cassava the highest water need (1000 mm), which penalises the "resilient income" strategy (maize + cassava) under the water priority.
   - In PAM, cassava is the crop whose yield is *least* affected by dry seasons.

## What this means for the product

- **What the data supports:**
  - "In the Semiárido, maize yield follows April to June rain, beans less, cassava hardly at all";
  - "strong El Niño years had longer dry spells and less rain in that window".
- **What the data does not support:**
  - a claim that the current engine ranking anticipates good or bad seasons;
  - any income ranking.
- **Engine changes the data points to** (decisions for the engine owners):
  - make the ranking respond to seasonal risk (dry-spell and window-rain risk, e.g. from the ENSO analogs);
  - revisit cassava's water penalty;
  - replace the constant income score or label it as a heuristic.

## Limits

- **PAM** is municipal and annual. It mixes all farms (irrigated and rain-fed, single crops and intercrops) and has gaps.
- **Cassava values in PAM** are often unchanged from year to year: 24% of years in Itabaiana and 51% in Glória show a zero anomaly. This looks like carried-forward estimates.
- **POWER** is a ~0.5° × 0.625° grid. The two pilots move together, so they are not independent samples.
- **ET0 for 1983 is missing**, because POWER solar radiation starts in 1984.
- **Fixed inputs:** previous crop maize and decision date March 31. The ZARC window is the Itabaiana anchor in `crops.yaml` for both pilots; the per-municipality ZARC check is issue #48.
- **Correlation is not causation.** Few strong El Niño years (5).

## Sources

- NASA POWER daily API: https://power.larc.nasa.gov/
- NOAA CPC Oceanic Niño Index (third party, not NASA): https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
- IBGE PAM, SIDRA table 5457 (third party): https://sidra.ibge.gov.br/tabela/5457
- SRTM elevation and slope from the project snapshots (`apps/web/public/data/sergipe/srtm.json`)
