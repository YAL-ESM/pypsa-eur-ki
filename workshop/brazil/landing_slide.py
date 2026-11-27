# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Map and cost table of the cable landing for a steady 2 GW (run A of firm_supply.py, with connection costs).

The map shows the landing point, the 150 km catchment and the public output potential per weather cell around it.
It does not mark the single plant cells the optimisation picked: some lie close to confidential shortlist sites.

    pixi run python workshop/brazil/firm_supply.py      # results/brazil/firm_supply_*.csv
    pixi run python workshop/brazil/landing_slide.py    # results/brazil/landing_A_map.png, landing_A_costs.csv
"""

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize

sys.path.insert(0, str(Path(__file__).parent))
import firm_supply as fs  # noqa: E402

st, DATA, OUT, CELL = fs.st, fs.DATA, fs.OUT, fs.CELL
COSTS = fs.COSTS
NAME = fs.COST_NAME
TS = fs.TS_DIR / "firm_supply_timeseries.csv"


def cost_table():
    c = pd.read_csv(COSTS, index_col=0)
    cap = lambda t: c.at[t, "capital_cost"] / 1e3  # noqa: E731  M EUR per GW (GWh) and year
    plants = pd.read_csv(OUT / "firm_supply_plants.csv")
    ts = pd.read_csv(TS, index_col=0)
    best = pd.read_csv(OUT / "firm_supply_by_landing.csv").query("feasible == True").sort_values("cost_M").iloc[0]
    col = {"onwind": "onwind_GW", "solar": "solar_GW", "fixed": "offwind_fixed_GW", "floating": "offwind_floating_GW"}
    rows, plant_M = [], 0.0
    for t in ["solar", "onwind", "fixed", "floating"]:
        gw = plants.loc[plants.tech == t, "GW"].sum()
        if gw < 0.005:
            continue
        M, twh = gw * cap(NAME[t]), ts[col[t]].sum() / 1e3
        plant_M += M
        rows.append({"Item": fs.LABEL[t], "Capacity": f"{gw:.1f} GW", "TWh/yr": f"{twh:.1f}",
                     "M EUR/yr": f"{M:,.0f}", "EUR/MWh": f"{M / twh:.0f}"})
    bat_M = best.battery_GWh * cap("battery storage") + best.battery_GW * cap("battery inverter")
    rows.append({"Item": "Battery", "Capacity": f"{best.battery_GW:.1f} GW / {best.battery_GWh:.0f} GWh",
                 "TWh/yr": "", "M EUR/yr": f"{bat_M:,.0f}", "EUR/MWh": ""})
    rows.append({"Item": "Connections to the landing", "Capacity": "", "TWh/yr": "",
                 "M EUR/yr": f"{best.cost_M - plant_M - bat_M:,.0f}", "EUR/MWh": ""})
    gen = ts.plants_GW.sum() / 1e3
    rows.append({"Item": "Plants on average", "Capacity": "", "TWh/yr": f"{gen:.1f}",
                 "M EUR/yr": f"{plant_M:,.0f}", "EUR/MWh": f"{plant_M / gen:.0f}"})
    rows.append({"Item": "Steady 2 GW into the cable", "Capacity": "2.0 GW", "TWh/yr": f"{2 * 8.76:.1f}",
                 "M EUR/yr": f"{best.cost_M:,.0f}", "EUR/MWh": f"{best.lcoe_firm:.0f}"})
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "landing_A_costs.csv", index=False)
    print(tab.to_string(index=False))
    return best


def landing_map(best):
    land, off = np.load(OUT / "land_twh_cell.npz"), np.load(OUT / "offshore_twh_cell.npz")
    x, y = land["x"], land["y"]
    twh = land["onwind"] + land["solar"] + off["offshore"]
    states = gpd.read_file(f"zip://{DATA}/raw/gadm/gadm41_BRA_1.json.zip")
    states["geometry"] = states.make_valid().buffer(0)
    states["uf"] = states.HASC_1.str.split(".").str[1]

    st.use()
    fig, ax = plt.subplots(figsize=(5.6, 5.0))
    ext = (x[0] - CELL / 2, x[-1] + CELL / 2, y[0] - CELL / 2, y[-1] + CELL / 2)
    data = np.where(twh > 0, twh, np.nan)
    im = ax.imshow(data, extent=ext, origin="lower", cmap="viridis", interpolation="nearest",
                   norm=Normalize(0, np.nanpercentile(data, 99)), alpha=0.85)
    states.boundary.plot(ax=ax, color=st.TEXT, linewidth=0.5)
    circle = gpd.GeoSeries(gpd.points_from_xy([best.lon], [best.lat]), crs=4326).to_crs("ESRI:102033")
    circle.buffer(fs.RADIUS_KM * 1e3).to_crs(4326).boundary.plot(ax=ax, color=st.VERMILLION, linewidth=1.2,
                                                                  linestyle="--")
    ax.plot(best.lon, best.lat, "o", ms=9, mfc=st.VERMILLION, mec="white", mew=1.2, zorder=6)
    ax.annotate("Cable landing\nMacau / Guamaré", (best.lon, best.lat), xytext=(10, 10), textcoords="offset points",
                fontsize=8, color=st.TEXT, fontweight="bold", zorder=7,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85))
    ax.annotate(f"{fs.RADIUS_KM} km", (best.lon + 0.2, best.lat - fs.RADIUS_KM / 111 + 0.12), fontsize=7.5,
                color=st.VERMILLION, zorder=7)
    for uf, lon, lat in [("Rio Grande\ndo Norte", -36.6, -5.9), ("Ceará", -39.4, -5.2), ("Paraíba", -36.6, -7.1)]:
        ax.text(lon, lat, uf, fontsize=7, color=st.TEXT, ha="center", alpha=0.8)
    pad_x, pad_y = 3.2, 2.6
    ax.set_xlim(best.lon - pad_x, best.lon + pad_x)
    ax.set_ylim(best.lat - pad_y, best.lat + pad_y)
    ax.set_aspect(1 / np.cos(np.deg2rad(best.lat)))
    st.map_axes(ax)
    ax.set_title("Cable landing on the north coast of Rio Grande do Norte", loc="left")
    st.colorbar(fig, im, ax.inset_axes([0.05, 0.06, 0.45, 0.025]), "Land and offshore output, TWh/yr per 0.3° cell")

    # inset: where in Brazil
    ins = ax.inset_axes([0.70, 0.02, 0.30, 0.34])
    states.simplify(0.05).plot(ax=ins, color=st.LAND, edgecolor="white", linewidth=0.2)
    ins.plot(best.lon, best.lat, "o", ms=4, mfc=st.VERMILLION, mec="white", mew=0.6)
    ins.set_xlim(-74.5, -32.5)
    ins.set_ylim(-34.5, 6.0)
    ins.set_aspect(1 / np.cos(np.deg2rad(-14)))
    st.map_axes(ins)
    fig.savefig(OUT / "landing_A_map.pdf")
    fig.savefig(OUT / "landing_A_map.png", dpi=300)
    print("saved", OUT / "landing_A_map.png")


def main():
    best = cost_table()
    landing_map(best)


if __name__ == "__main__":
    main()
