# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Summary of all solved runs for role 4, one row per run and planning year.

    pixi run python workshop/trade/summary_all_runs.py

Reads results/<run>/networks/solved_<year>.nc, writes workshop/trade/results_summary.csv.
Only runs and years whose network exists are included. Germany only for the
price and import figures; the trade runs also contain the neighbours.
"""

from pathlib import Path

import pandas as pd
import pypsa

RUNS = [
    "de10-myopic",
    "de10-trade",
    "de10-trade-v2",
    "de10-trade-cable",
    "de10-trade-cable2050",
]
YEARS = [2025, 2030, 2035, 2040, 2045, 2050]
RENEWABLES = [
    "solar",
    "solar-hsat",
    "onwind",
    "offwind-ac",
    "offwind-dc",
    "offwind-float",
    "ror",
    "hydro",
    "biomass",
    "geothermal",
    "waste",
]


def german_buses(n):
    return n.buses.index[(n.buses.country == "DE") & (n.buses.carrier == "AC")]


def summary(n):
    w = n.snapshot_weightings.generators
    de = german_buses(n)
    load = n.loads_t.p_set[n.loads.index[n.loads.bus.isin(de)]].sum(axis=1).mul(w)
    price = n.buses_t.marginal_price[de]
    gen = n.generators[n.generators.bus.isin(de)]
    energy = n.generators_t.p[gen.index].mul(w, axis=0).sum().groupby(gen.carrier).sum()
    su = n.storage_units[n.storage_units.bus.isin(de)]
    if len(su):
        st = n.storage_units_t.p[su.index].mul(w, axis=0).sum().groupby(su.carrier).sum()
        energy = energy.add(st, fill_value=0)
    energy = energy[energy.index != "load"]
    domestic = energy.sum()
    emissions = (
        n.generators_t.p[gen.index].mul(w, axis=0).sum()
        * gen.carrier.map(n.carriers.co2_emissions)
    ).sum()
    return {
        "demand_TWh": load.sum() / 1e6,
        "load_weighted_price_EUR_MWh": (price.mean(axis=1) * load).sum() / load.sum(),
        "mean_price_EUR_MWh": price.mean().mean(),
        "max_price_EUR_MWh": price.max().max(),
        "emissions_Mt": emissions / 1e6,
        "renewable_share_pct": 100 * energy[energy.index.isin(RENEWABLES)].sum() / domestic,
        "net_imports_TWh": (load.sum() - domestic) / 1e6,
        "system_cost_bn_EUR": n.objective / 1e9,
    }


def main():
    rows = []
    for run in RUNS:
        for year in YEARS:
            path = Path(f"results/{run}/networks/solved_{year}.nc")
            if not path.exists():
                continue
            rows.append({"run": run, "year": year, **summary(pypsa.Network(path))})
    df = pd.DataFrame(rows).round(2)
    out = Path("workshop/trade/results_summary.csv")
    df.to_csv(out, index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
