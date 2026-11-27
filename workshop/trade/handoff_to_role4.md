# Handoff to Role 4: trade and 2050 cable results

Pull `workshop-baseline` from `YAL-ESM/pypsa-eur-ki` for the tables.

## Ready to analyse

- [`results_summary.csv`](results_summary.csv): all six horizons (2025–2050)
  for `de10-myopic`, `de10-trade`, `de10-trade-v2` and `de10-trade-cable2050`.
  The separate `de10-trade-cable` run only has 2025 and 2030, before the cable.
- [`cable2050_comparison.csv`](cable2050_comparison.csv): annual system cost,
  cable deliveries, and CO₂ cap shadow prices for the matched 2050 comparison.
- [`comparison_baseline_vs_trade.csv`](comparison_baseline_vs_trade.csv):
  island vs the original trade run, with curtailment and load shedding.

The summary CSV's `system_cost_bn_EUR` is the myopic objective; use the
2050 comparison for annual total system costs, including inherited assets and
the fixed cable. The summary CSV's net-import and emissions columns are
generation-based proxies; use model accounting for physical cross-border
flows or reported CO₂ totals.

## 2050 result

`de10-trade-v2` (no cable) and `de10-trade-cable2050` (fixed 2 GW cable from
2050) use identical solved 2045 networks and 6-hour resolution in 2050. Both
2050 solves terminated as optimal.

The cable delivers **7.57 TWh/year** to Germany. Annual system cost rises
from **€222.08bn** to **€227.06bn**: savings before paying for the cable are
**€0.37bn/year**, against an annual cable cost of **€5.35bn**. Net benefit
(without minus with) is **−€4.98bn/year** under this scenario's assumptions.

The zero-CO₂ cap remains binding, with a shadow price of about €33,000/t in
both cases. Treat this as a 2050 sensitivity under the current cap; see
[`caveat-2050.md`](caveat-2050.md). No completed multi-horizon cable comparison
is available yet.

For the study design, decide whether to keep this 2050 case or test a revised
cap, and whether to add a cable capacity-expansion case. Use a common discount
rate and cost year when comparing scenarios.

```bash
pixi run python workshop/trade/summary_all_runs.py
pixi run python workshop/cable/evaluate_cable.py de10-trade-v2 de10-trade-cable2050 2050
```

These commands regenerate the summary and the underlying comparison in the
workspace that has the solved networks and cable evaluation script.
