# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Daily mean output of solar PV, onshore wind, offshore wind and the battery over 2013 at the RN cable landing
(run A of firm_supply.py, with connection costs).

Reads the hourly time series in workshop/brazil/timeseries/. The battery is drawn twice in its colour:
discharging into the cable (positive) and charging (negative, lighter). Its net daily mean would be close to
zero, because it mostly shifts power within the day.

    pixi run python workshop/brazil/plot_timeseries.py
"""

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import potential_outside_indigenous as po  # noqa: E402

st, OUT = po.st, po.OUT
TS = Path(__file__).parent / "timeseries" / "firm_supply_timeseries.csv"


def main():
    hourly = pd.read_csv(TS, index_col=0, parse_dates=True)
    d = hourly.resample("D").mean()
    d["battery_charge_GW"] *= -1

    st.use()
    fig, ax = plt.subplots(figsize=(11, 3.8))
    series = [
        ("solar_GW", "Solar PV", st.GROUPS["Solar"], 1.0),
        ("onwind_GW", "Onshore wind", st.GROUPS["Onshore wind"], 1.0),
        ("offwind_GW", "Offshore wind", st.GROUPS["Offshore wind"], 1.0),
        ("battery_discharge_GW", "Battery discharging", st.GROUPS["Storage"], 1.0),
        ("battery_charge_GW", "Battery charging", st.GROUPS["Storage"], st.TINT),
    ]
    for col, _, color, alpha in series:
        ax.plot(d.index, d[col], color=color, lw=1.3, alpha=alpha)
    ax.axhline(0, color=st.TEXT, lw=0.6, zorder=1)
    ax.set_xlim(d.index[0], d.index[-1])
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_title("Daily mean output at the cable landing in Rio Grande do Norte, 2013, GW", loc="left")
    items = []
    for col, label, color, alpha in series:
        m = d[col].mean()
        txt = "not built" if abs(d[col]).max() < 1e-3 else f"mean {abs(m):.1f} GW"
        items.append((color, f"{label}: {txt}", alpha))
    st.legend_squares(ax, items, ncol=5, loc="upper left", bbox_to_anchor=(0, -0.08))
    fig.savefig(OUT / "timeseries_daily.pdf")
    fig.savefig(OUT / "timeseries_daily.png", dpi=300)
    fig.savefig(Path(__file__).parent / "timeseries_daily.png", dpi=300)  # copy next to the scripts, tracked in git
    print("saved", OUT / "timeseries_daily.png", "and", Path(__file__).parent / "timeseries_daily.png")
    print(d[[c for c, *_ in series]].describe().loc[["mean", "min", "max"]].round(2).to_string())


if __name__ == "__main__":
    main()
