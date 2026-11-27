# Handoff to role 4: what is ready to analyse

Pull `mine/workshop-baseline`. Everything here is Germany-only unless noted.

## Ready now

- `workshop/trade/results_summary.csv` — one row per run and year that has a
  solved network: demand, load-weighted and max price, emissions, renewable
  share, net imports, system cost. Regenerate with
  `pixi run python workshop/trade/summary_all_runs.py`.
- `workshop/trade/comparison_baseline_vs_trade.csv` — island vs trade, all
  horizons, with curtailment and load shedding.
- `workshop/trade/caveat-2050.md` — why 2050 is not a safe basis for the cable
  decision.

Runs available: `de10-myopic` (2025-2050), `de10-trade` (2025-2050),
`de10-trade-v2` (2025-2040; 2045/2050 were killed for memory and need a rerun).

## Not ready yet

- `de10-trade-v2` 2045/2050 and the cable run `de10-trade-cable` 2035-2050.
- No cable flows or with/without-cable system cost yet.

## What the numbers already say

- German load-weighted prices are 76-117 EUR/MWh in 2025-2045. The 2050 zero-CO2
  cap pushes the max to 2,959 EUR/MWh (island) / 4,371 EUR/MWh (trade).
- Role 1's 2,000 MW routes cost 68-72 bn EUR and lose 34-36% at full load.
  Annualised at 3-4% WACC over 40 years, that is ~290-360 EUR/MWh delivered
  before Brazilian generation. The cable only looks worthwhile against the 2050
  cap artefact.

## Decisions role 4 needs to make early

- Whether 2050 stays in the study, and whether the zero-CO2 cap is dropped or
  fixed first.
- Capacity expansion vs cost-benefit of a given cable (the cable config assumes
  a given 2,000 MW link).
- One harmonised discount rate and cost year for Germany, Brazil and the cable.
