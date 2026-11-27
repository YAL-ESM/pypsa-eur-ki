# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Compare the island baseline (de10-myopic) with the trade run (de10-trade), Germany only.

    pixi run python workshop/trade/compare_trade.py

Prints one table per run with the German figures per horizon, and the yearly
net imports of Germany by neighbour for the trade run.
"""

from pathlib import Path

import pandas as pd
import pypsa

RUNS = {"island": "de10-myopic", "trade": "de10-trade"}
YEARS = [2025, 2030, 2035, 2040, 2045, 2050]
GROUPS = {
    "wind": ["onwind", "offwind-ac", "offwind-dc", "offwind-float"],
    "solar": ["solar", "solar-hsat", "solar rooftop"],
    "gas": ["CCGT", "OCGT"],
    "coal+lignite": ["coal", "lignite"],
}


def german_figures(n: pypsa.Network) -> dict:
    w = n.snapshot_weightings.generators
    country = n.buses.country
    de_bus = n.buses.index[(country == "DE") & (n.buses.carrier == "AC")]
    gen = n.generators[n.generators.bus.isin(de_bus)]
    energy = n.generators_t.p[gen.index].mul(w, axis=0).sum().groupby(gen.carrier).sum()
    load = n.loads_t.p_set[n.loads.index[n.loads.bus.isin(de_bus)]].mul(w, axis=0)
    price = n.buses_t.marginal_price[de_bus]
    # load-weighted German price per snapshot, then averaged over the year
    lw = load.T.groupby(n.loads.bus).sum().T.reindex(columns=de_bus).fillna(0)
    avg_price = (price * lw).sum().sum() / lw.sum().sum()

    out = {
        "demand TWh": load.sum().sum() / 1e6,
        **{
            f"{k} TWh": energy.reindex(v).fillna(0).sum() / 1e6
            for k, v in GROUPS.items()
        },
        "avg price EUR/MWh": avg_price,
        "max price EUR/MWh": price.max().max(),
    }
    em = (
        n.generators_t.p[gen.index].mul(w, axis=0).sum()
        / gen.efficiency
        * gen.carrier.map(n.carriers.co2_emissions)
    ).sum()
    out["CO2 Mt"] = em / 1e6
    shed = gen.index[gen.carrier == "load"]
    out["load shed GWh"] = n.generators_t.p[shed].mul(w, axis=0).sum().sum() / 1e3
    st = n.stores[n.stores.bus.map(country).eq("DE")]
    out["battery GWh"] = st.loc[st.carrier == "battery", "e_nom_opt"].sum() / 1e3
    out["H2 store TWh"] = st.loc[st.carrier == "H2", "e_nom_opt"].sum() / 1e6
    out["net import TWh"] = net_imports(n, de_bus).sum() / 1e6
    return out


def net_imports(n: pypsa.Network, de_bus) -> pd.Series:
    """Net yearly flow into Germany (MWh) per neighbouring country, from lines and DC links."""
    w = n.snapshot_weightings.generators
    country = n.buses.country
    flows = {}
    for c, p0, p1 in [("Line", "p0", "p1"), ("Link", "p0", "p1")]:
        st = n.static(c)
        if c == "Link":
            st = st[st.carrier == "DC"]
        if st.empty:
            continue
        a = st.bus0.isin(de_bus)
        b = st.bus1.isin(de_bus)
        cross = st.index[a ^ b]
        dyn = n.dynamic(c)
        for i in cross:
            if a[i]:  # Germany at bus0: power into Germany is -p0
                other, inflow = country[st.bus1[i]], -dyn[p0][i]
            else:  # Germany at bus1: power into Germany is -p1
                other, inflow = country[st.bus0[i]], -dyn[p1][i]
            flows[other] = flows.get(other, 0) + (inflow * w).sum()
    return pd.Series(flows, dtype=float)


def main():
    tables, imports = {}, {}
    for label, run in RUNS.items():
        rows = {}
        for y in YEARS:
            f = Path(f"results/{run}/networks/solved_{y}.nc")
            if not f.exists():
                continue
            n = pypsa.Network(f)
            rows[y] = german_figures(n)
            if label == "trade":
                de_bus = n.buses.index[(n.buses.country == "DE") & (n.buses.carrier == "AC")]
                imports[y] = net_imports(n, de_bus) / 1e6
        tables[label] = pd.DataFrame(rows)

    pd.set_option("display.width", 160)
    for label, t in tables.items():
        print(f"\n=== {label} ({RUNS[label]}), Germany ===")
        print(t.round(1).to_string())
    if imports:
        print("\n=== trade: net imports into Germany by neighbour (TWh, + = import) ===")
        print(pd.DataFrame(imports).round(1).to_string())


if __name__ == "__main__":
    main()
