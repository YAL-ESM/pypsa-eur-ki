# Handoff to Role 4: trade and 2050 cable results

Pull `workshop-baseline` from `YAL-ESM/pypsa-eur-ki` for the tables.

## Ready to analyse

- [`results_summary.csv`](results_summary.csv): all six horizons (2025–2050)
  for `de10-myopic`, `de10-trade`, `de10-trade-v2`, `de10-trade-cable2050`
  and `de10-trade-cable-fast`.
  The separate `de10-trade-cable` run only has 2025 and 2030, before the cable.
- [`cable2050_comparison.csv`](cable2050_comparison.csv): annual system cost,
  cable deliveries, and CO₂ cap shadow prices for both cable variants against
  `de10-trade-v2` in 2050.
- [`comparison_baseline_vs_trade.csv`](comparison_baseline_vs_trade.csv):
  island vs the original trade run, with curtailment and load shedding.

The summary CSV's `system_cost_bn_EUR` is the myopic objective; use the
2050 comparison for annual total system costs, including inherited assets and
the fixed cable. The summary CSV's net-import and emissions columns are
generation-based proxies; use model accounting for physical cross-border
flows or reported CO₂ totals.

## 2050 results

All three runs use identical solved networks through 2045 and the same 6-hour
snapshots in 2050. Both cable runs add a fixed 2 GW cable in 2050.
`de10-trade-cable-fast`, the latest run, uses Role 2's Brazilian wind and solar
profiles and models a battery at the export hub. Because the profiles and the
battery both changed, the difference between the cable cases cannot be attributed
to the battery alone.

| Run | Delivery to Germany (TWh/year) | Annual system cost (€bn/year) | Net benefit vs. no cable (€bn/year) |
| --- | ---: | ---: | ---: |
| `de10-trade-v2` | — | 222.08 | — |
| `de10-trade-cable2050` | 7.57 | 227.06 | −4.98 |
| `de10-trade-cable-fast` | 8.23 | 226.93 | −4.85 |

The latest run saves **€0.50bn/year** before paying for the cable, against an
annual cable cost of **€5.35bn**. COPT marked the latest solve `imprecise` with
a relative duality gap of `5.74e-08`; the other two terminated as optimal.

The zero-CO₂ cap remains binding, with a shadow price of about €33,000/t in
all three cases. Treat these as 2050 sensitivities under the current cap; see
[`caveat-2050.md`](caveat-2050.md). No completed multi-horizon cable comparison
is available yet.

For the study design, decide whether to keep this 2050 case or test a revised
cap, and whether to add a cable capacity-expansion case. Use a common discount
rate and cost year when comparing scenarios.

```bash
pixi run python workshop/trade/summary_all_runs.py
pixi run python workshop/cable/evaluate_cable.py de10-trade-v2 de10-trade-cable2050 2050
pixi run python workshop/cable/evaluate_cable.py de10-trade-v2 de10-trade-cable-fast 2050
```

These commands regenerate the summary and the underlying comparisons in the
workspace that has the solved networks and cable evaluation script.
