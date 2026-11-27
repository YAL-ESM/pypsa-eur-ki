# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Where on Brazil's coast can nearby wind, solar and offshore plants together deliver a steady 2 GW into the cable?

For every candidate landing point on the coast (sampled every STEP_KM along the whole coast), a small linear
programme picks the cheapest set of plants within RADIUS_KM of the landing whose combined output is at least
FIRM_GW in every hour of 2013 (ERA5). Wind, sun and sea alone cannot do that anywhere on the coast (a few calm
nights a year), so a battery at the landing may shift surplus into those hours:

  variables:   capacity (GW) of onshore wind, solar PV, offshore fixed and floating in every 0.3 deg weather cell;
               battery energy (GWh) and power (GW) with hourly charge, discharge and state of charge
  constraint:  plant output - charge + discharge >= FIRM_GW in all 8760 hours; battery cyclic over the year
  limits:      the potential of each cell outside all protected areas (optimal_land_use.py, offshore_potential.py);
               onshore wind and PV share the cell's land (3 MW/km2 wind, 5.1 MW/km2 PV)
  cost:        annualised investment + FOM (plants, battery storage and inverter) from PyPSA-Eur's cost data (European costs, 2035, as a relative
               weight only: Brazilian costs are not derived yet), plus a connection to the landing point
               (HVAC overhead line on land, AC submarine cable + substation offshore), straight-line distance

Output above FIRM_GW does not fit into the cable; it is reported as surplus (usable in Brazil's grid or curtailed).
Same capacity factors as the potential scripts: Vestas V112 with 10% wake loss, CSi latitude-optimal PV,
NREL 5.5 MW (fixed) / 5 MW (floating) offshore x 0.8855.

    pixi run python workshop/brazil/optimal_land_use.py      # writes land_twh_cell.npz
    pixi run python workshop/brazil/offshore_potential.py    # writes offshore_twh_cell.npz
    pixi run python workshop/brazil/firm_supply.py
    pixi run python workshop/brazil/firm_supply.py --no-connection   # plants and battery only, files *_noconn.*

Exact positions stay in results/ (git-ignored); the hourly series of the best landing (GW only) goes to
workshop/brazil/timeseries/.
"""

import sys
from multiprocessing import Pool
from pathlib import Path

import atlite
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.sparse as sp
from pyproj import Transformer
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).parent))
import potential_outside_indigenous as po  # noqa: E402

st, DATA, OUT, CELL, ROOT = po.st, po.DATA, po.OUT, po.CELL, po.pe.ROOT
FIRM_GW = 2.0
RADIUS_KM = 150
STEP_KM = 25
TS_DIR = Path(__file__).parent / "timeseries"  # hourly series of the best landing, tracked in git
CONNECTION = "--no-connection" not in sys.argv  # include the lines from the plants to the landing
SUFFIX = "" if CONNECTION else "_noconn"
WORKERS = 4  # each LP needs about 1 GB; the workspace limit is 10 GB
COSTS = ROOT / "resources/de10-myopic/costs_2035_processed.csv"
TECHS = ["onwind", "solar", "fixed", "floating"]
COST_NAME = {"onwind": "onwind", "solar": "solar-utility", "fixed": "offwind", "floating": "offwind-float"}
LABEL = {"onwind": "Onshore wind", "solar": "Solar PV", "fixed": "Offshore wind, fixed", "floating": "Offshore wind, floating"}
COLOR = {"onwind": st.GROUPS["Onshore wind"], "solar": st.GROUPS["Solar"], "fixed": st.GROUPS["Offshore wind"],
         "floating": st.GROUPS["Offshore wind"]}
MW_PER_KM2 = po.MW_PER_KM2
OFF_CORR = 0.8855


def capacity_factors(cells_y, cells_x):
    """Hourly capacity factor (8760 x cells) per technology, only for the cells given (float32, one at a time)."""
    cutout = atlite.Cutout(DATA / "weather/brazil-2013-era5.nc")
    runs = {"onwind": (lambda: cutout.wind(turbine="Vestas_V112_3MW", capacity_factor_timeseries=True,
                                           add_cutout_windspeed=True), 1 - po.WAKE_LOSS["onwind"]),
            "solar": (lambda: cutout.pv(panel="CSi", orientation="latitude_optimal",
                                        capacity_factor_timeseries=True), 1.0),
            "fixed": (lambda: cutout.wind(turbine="NREL_ReferenceTurbine_2020ATB_5.5MW", capacity_factor_timeseries=True,
                                          add_cutout_windspeed=True), OFF_CORR),
            "floating": (lambda: cutout.wind(turbine="NREL_ReferenceTurbine_5MW_offshore", capacity_factor_timeseries=True,
                                             add_cutout_windspeed=True), OFF_CORR)}
    out = {}
    for k, (f, factor) in runs.items():
        da = f().transpose("time", "y", "x")
        out[k] = (da.values[:, cells_y, cells_x] * factor).astype("float32")
        del da
        print(f"  capacity factors {k}: mean {out[k].mean():.2f}", flush=True)
    return out, cutout.data.time.values


def coast_points(states, step_m):
    eez = gpd.read_file(DATA / "layers/eez_brazil.gpkg").to_crs("ESRI:102033").geometry.union_all().simplify(500)
    pts = []
    for uf, g in zip(states.uf, states.to_crs("ESRI:102033").geometry.simplify(500)):
        coast = g.boundary.intersection(eez.buffer(3000))
        for ln in getattr(coast, "geoms", [coast]):
            if ln.length > 0 and ln.geom_type == "LineString":
                pts += [(uf, p.x, p.y) for p in (ln.interpolate(d) for d in np.arange(step_m / 2, ln.length, step_m))]
    return pd.DataFrame(pts, columns=["state", "px", "py"])


def solve(opt, cf, cost, idx, land_km2, bat):
    """Cheapest plants (options `idx`) and battery that give FIRM_GW in every hour; (None, nan) if not feasible.

    Variables: plant capacities (GW), battery energy E (GWh) and power P (GW), hourly charge, discharge, state of charge.
      gen_t - charge_t + discharge_t >= FIRM_GW          (surplus is spilled)
      soc_t = soc_{t-1} + eta * charge_t - discharge_t / eta,  cyclic over the year
      soc_t <= E,  charge_t <= P,  discharge_t <= P
    Onshore wind and PV in the same cell share its land: wind/3 + PV/5.1 (km2 per MW) <= land of the cell.
    """
    T, n = cf.shape[0], len(idx)
    sub = opt.iloc[idx]
    nv = n + 2 + 3 * T  # plants, E, P, charge, discharge, soc
    iE, iP, ic, idis, isoc = n, n + 1, n + 2, n + 2 + T, n + 2 + 2 * T
    t = np.arange(T)
    eye = sp.identity(T, format="csr")
    # balance: -gen + charge - discharge <= -FIRM
    bal = sp.hstack([sp.csr_matrix(-cf[:, idx]), sp.csr_matrix((T, 2)), eye, -eye, sp.csr_matrix((T, T))])
    # soc limits and power limits: soc - E <= 0, charge - P <= 0, discharge - P <= 0
    col_e = sp.csr_matrix((np.ones(T), (t, np.zeros(T))), shape=(T, 1))
    z = sp.csr_matrix((T, T))
    zn = sp.csr_matrix((T, n))
    lim = sp.vstack([sp.hstack([zn, -col_e, sp.csr_matrix((T, 1)), z, z, eye]),
                     sp.hstack([zn, sp.csr_matrix((T, 1)), -col_e, eye, z, z]),
                     sp.hstack([zn, sp.csr_matrix((T, 1)), -col_e, z, eye, z])])
    rows = [bal, lim]
    b = [np.full(T, -FIRM_GW), np.zeros(3 * T)]
    land_rows, b_land = [], []
    for (a, b_), g in sub[sub.tech.isin(["onwind", "solar"])].groupby(["iy", "ix"]):
        if len(g) == 2:
            r_ = np.zeros(nv)
            for k, r in g.iterrows():
                r_[np.searchsorted(idx, k)] = 1e3 / MW_PER_KM2[r.tech]
            land_rows.append(r_)
            b_land.append(land_km2[a, b_])
    if land_rows:
        rows.append(sp.csr_matrix(np.array(land_rows)))
        b.append(np.array(b_land))
    # soc dynamics (equality): soc_t - soc_{t-1} - eta charge_t + discharge_t / eta = 0, soc_{-1} = soc_{T-1}
    shift = sp.csr_matrix((np.ones(T), (t, (t - 1) % T)), shape=(T, T))
    dyn = sp.hstack([zn, sp.csr_matrix((T, 2)), -bat["eta"] * eye, eye / bat["eta"], eye - shift])
    cost_v = np.concatenate([cost[idx], [bat["E"], bat["P"]], np.zeros(3 * T)])
    bounds = np.zeros((nv, 2))
    bounds[:, 1] = np.inf
    bounds[:n, 1] = sub.cap_max.values
    res = linprog(cost_v, A_ub=sp.vstack(rows, format="csr"), b_ub=np.concatenate(b), A_eq=dyn.tocsr(),
                  b_eq=np.zeros(T), bounds=bounds, method="highs")
    if res.status != 0:
        return None, np.nan
    cap = np.zeros(len(opt))
    cap[idx] = res.x[:n]
    storage = {"E": res.x[iE], "P": res.x[iP], "charge": res.x[ic:ic + T], "discharge": res.x[idis:idis + T],
               "soc": res.x[isoc:isoc + T]}
    return (cap, storage), res.fun


def _solve_point(i):
    """Worker: solve landing point i (globals set by the parent before forking)."""
    G = _G
    sel = G["dist"][i] <= RADIUS_KM
    if not sel.any():
        return i, None, np.nan
    c = G["base"] + np.where(G["is_off"], G["line"]["sea"] * G["dist"][i] + G["station"], G["line"]["land"] * G["dist"][i])
    out, fun = solve(G["opt"], G["cf"], c, np.nonzero(sel)[0], G["land_km2"], G["bat"])
    return i, out, fun


_G = {}


def main():
    land, off = np.load(OUT / "land_twh_cell.npz"), np.load(OUT / "offshore_twh_cell.npz")
    x, y = land["x"], land["y"]
    gmax = {"onwind": land["onwind_alone_GW"], "solar": land["solar_alone_GW"],
            "fixed": off["fixed_GW"], "floating": off["floating_GW"]}
    land_km2 = land["land_km2"]

    states = gpd.read_file(f"zip://{DATA}/raw/gadm/gadm41_BRA_1.json.zip")
    states["geometry"] = states.make_valid().buffer(0)
    states["uf"] = states.HASC_1.str.split(".").str[1]
    coast = coast_points(states, STEP_KM * 1e3)
    to_xy = Transformer.from_crs("EPSG:4326", "ESRI:102033", always_xy=True)
    to_ll = Transformer.from_crs("ESRI:102033", "EPSG:4326", always_xy=True)
    coast["lon"], coast["lat"] = to_ll.transform(coast.px.values, coast.py.values)
    print(f"{len(coast)} candidate landing points along {len(coast) * STEP_KM:,} km of coast")

    # plant options: (cell, technology) with potential, within RADIUS_KM of any landing point
    rows = []
    for t in TECHS:
        iy, ix = np.nonzero(gmax[t] > 0.01)
        rows += [(t, a, b_) for a, b_ in zip(iy, ix)]
    opt = pd.DataFrame(rows, columns=["tech", "iy", "ix"])
    opt["lon"], opt["lat"] = x[opt.ix], y[opt.iy]
    opt["px"], opt["py"] = to_xy.transform(opt.lon.values, opt.lat.values)
    dist = np.hypot(coast.px.values[:, None] - opt.px.values[None, :], coast.py.values[:, None] - opt.py.values[None, :]) / 1e3
    keep = (dist <= RADIUS_KM).any(axis=0)
    opt, dist = opt[keep].reset_index(drop=True), dist[:, keep]
    opt["cap_max"] = [gmax[t][a, b_] for t, a, b_ in zip(opt.tech, opt.iy, opt.ix)]
    print(f"{len(opt)} plant options (cell x technology) within {RADIUS_KM} km of the coast")

    # hourly capacity factors of every option
    cache = OUT / f"firm_supply_cf_{RADIUS_KM}km.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        cf, time = z["cf"], z["time"]
    else:
        cells = opt[["iy", "ix"]].drop_duplicates().reset_index(drop=True)
        cf_cells, time = capacity_factors(cells.iy.values, cells.ix.values)
        col = {(a, b_): j for j, (a, b_) in enumerate(zip(cells.iy, cells.ix))}
        cf = np.empty((len(time), len(opt)), "float32")
        for j, r in opt.iterrows():
            cf[:, j] = cf_cells[r.tech][:, col[(r.iy, r.ix)]]
        del cf_cells
        np.savez(cache, cf=cf, time=time)
    opt["cf"] = cf.mean(axis=0)
    if "--diagnose" in sys.argv:  # weakest hour if every option within the radius were fully built
        rows = []
        for i in range(len(coast)):
            sel = dist[i] <= RADIUS_KM
            full = cf[:, sel] @ opt.cap_max.values[sel]
            wind = cf[:, sel & (opt.tech != "solar").values] @ opt.cap_max.values[sel & (opt.tech != "solar").values]
            rows.append((coast.state[i], coast.lat[i], coast.lon[i], full.min(), (full < FIRM_GW).sum(), wind.mean()))
        d = pd.DataFrame(rows, columns=["state", "lat", "lon", "min_GW", "hours_below", "wind_mean_GW"])
        print(d.sort_values("hours_below").head(15).round(2).to_string(index=False))
        print(d.groupby("state")[["min_GW", "hours_below"]].agg(["max", "min"]).round(2))
        return

    # cost, M EUR per GW and year
    costs = pd.read_csv(COSTS, index_col=0)
    cc = {t: costs.at[COST_NAME[t], "capital_cost"] / 1e3 for t in TECHS}  # EUR/MW/yr -> M EUR/GW/yr
    line = {"land": costs.at["HVAC overhead", "capital_cost"] / 1e3,  # M EUR/GW/km/yr
            "sea": costs.at["offwind-ac-connection-submarine", "capital_cost"] / 1e3}
    station = costs.at["offwind-ac-station", "capital_cost"] / 1e3
    if not CONNECTION:
        line, station = {"land": 0.0, "sea": 0.0}, 0.0
        print("Without connection costs: plants and battery only")
    is_off = opt.tech.isin(["fixed", "floating"]).values
    base = np.array([cc[t] for t in opt.tech])
    bat = {"E": costs.at["battery storage", "capital_cost"] / 1e3,  # M EUR/GWh/yr
           "P": costs.at["battery inverter", "capital_cost"] / 1e3,  # M EUR/GW/yr
           "eta": costs.at["battery inverter", "efficiency"]}
    _G.update(opt=opt, cf=cf, dist=dist, base=base, is_off=is_off, line=line, station=station, land_km2=land_km2, bat=bat)

    results, keep_out = [], {}
    with Pool(WORKERS) as pool:
        for n_done, (i, out, fun) in enumerate(pool.imap_unordered(_solve_point, range(len(coast))), 1):
            if n_done % 25 == 0:
                print(f"  {n_done}/{len(coast)} landing points solved", flush=True)
            if out is None:
                results.append({"i": i, "feasible": False})
                continue
            cap, sto = out
            gen = cf @ cap
            results.append({"i": i, "feasible": True, "cost_M": fun, "GW": cap.sum(),
                            **{f"GW_{t}": cap[opt.tech.values == t].sum() for t in TECHS},
                            "battery_GW": sto["P"], "battery_GWh": sto["E"],
                            "mean_GW": gen.mean(), "surplus_share": 1 - FIRM_GW / gen.mean(),
                            "n_cells": int((cap > 0.005).sum()),
                            "lcoe_firm": fun * 1e6 / (FIRM_GW * 1e3 * len(time))})  # EUR per MWh into the cable
            keep_out[i] = out
    res_df = coast.join(pd.DataFrame(results).set_index("i"), how="inner")
    res_df.drop(columns=["px", "py"]).round(4).to_csv(OUT / f"firm_supply_by_landing{SUFFIX}.csv", index=False)
    ok = res_df[res_df.feasible == True].sort_values("cost_M")  # noqa: E712
    print(f"\nFeasible landing points: {len(ok)} of {len(res_df)}")
    show = ["state", "lat", "lon", "cost_M", "lcoe_firm", "GW", "GW_onwind", "GW_solar", "GW_fixed", "GW_floating",
            "battery_GW", "battery_GWh", "mean_GW", "surplus_share", "n_cells"]
    print("Cheapest landing points (cost in M EUR/yr; lcoe_firm in EUR/MWh of the firm 2 GW):")
    print(ok[show].head(12).round(2).to_string(index=False))
    print("\nBest landing point per state:")
    print(ok.groupby("state").head(1)[show].round(2).to_string(index=False))

    # the best landing: plants, hourly output
    best = ok.iloc[0]
    i = best.name
    cap, sto = keep_out[i]
    print(f"Battery: {sto['P']:.2f} GW, {sto['E']:.1f} GWh ({sto['E'] / max(sto['P'], 1e-9):.1f} h); "
          f"discharged {sto['discharge'].sum() / 1e3:.2f} TWh/yr")
    plants = opt.assign(GW=cap, dist_km=dist[i])[cap > 0.005].sort_values("GW", ascending=False)
    print(f"\nBest landing: {best.state}, {best.lat:.2f}, {best.lon:.2f}")
    print(plants[["tech", "lat", "lon", "GW", "cf", "dist_km", "cap_max"]].round(2).to_string(index=False))
    plants.drop(columns=["px", "py"]).round(4).to_csv(OUT / f"firm_supply_plants{SUFFIX}.csv", index=False)
    by_t = pd.DataFrame({t: cf[:, opt.tech.values == t] @ cap[opt.tech.values == t] for t in TECHS}, index=time)
    by_t["battery"] = sto["discharge"] - sto["charge"]
    # hourly time series of the best landing, GW (state of charge in GWh)
    plant = by_t[TECHS].sum(axis=1)
    ts = pd.DataFrame({"solar_GW": by_t.solar, "onwind_GW": by_t.onwind,
                       "offwind_fixed_GW": by_t.fixed, "offwind_floating_GW": by_t.floating,
                       "offwind_GW": by_t.fixed + by_t.floating, "plants_GW": plant,
                       "battery_charge_GW": sto["charge"], "battery_discharge_GW": sto["discharge"],
                       "battery_soc_GWh": sto["soc"],
                       "into_cable_GW": np.minimum(plant - sto["charge"] + sto["discharge"], FIRM_GW),
                       "surplus_GW": np.maximum(plant - sto["charge"] + sto["discharge"] - FIRM_GW, 0)}, index=time)
    ts.index.name = "time"
    # tracked in git (GW per hour only, no positions): workshop/brazil/timeseries/
    ts_file = TS_DIR / f"firm_supply_timeseries{SUFFIX}.csv"
    TS_DIR.mkdir(parents=True, exist_ok=True)
    ts.round(4).to_csv(ts_file)
    print(f"saved {ts_file}:\n", ts.describe().loc[["mean", "min", "max"]].round(2).to_string())
    by_t.to_csv(OUT / f"firm_supply_hourly{SUFFIX}.csv")
    tot = by_t[TECHS].sum(axis=1)
    into = np.minimum(tot + by_t.battery, FIRM_GW * 10)
    print(f"Into the cable: min {into.min():.2f} GW (target {FIRM_GW}); battery covers {(by_t.battery > 1e-3).sum()} hours")
    print(f"Plant output: min {tot.min():.2f}, mean {tot.mean():.2f}, max {tot.max():.2f} GW; "
          f"{(tot > FIRM_GW * 1.5).mean():.0%} of hours above 3 GW")

    # figure: map of the plants; output by technology over a week; sorted hourly output
    st.use()
    fig = plt.figure(figsize=(11, 4.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.5])
    ax = fig.add_subplot(gs[:, 0])
    states.simplify(0.01).boundary.plot(ax=ax, color=st.TEXT, linewidth=0.4)
    circ = gpd.GeoSeries(gpd.points_from_xy([best.px], [best.py]), crs="ESRI:102033").buffer(RADIUS_KM * 1e3).to_crs(4326)
    circ.boundary.plot(ax=ax, color="#aaaaaa", linewidth=0.8, linestyle="--")
    for t in TECHS:
        p = plants[plants.tech == t]
        ax.scatter(p.lon + {"onwind": -0.06, "solar": 0.06}.get(t, 0), p.lat, s=p.GW * 120, color=COLOR[t],
                   hatch="////" if t == "floating" else None, edgecolor="white", linewidth=0.5, zorder=4)
    ax.plot(best.lon, best.lat, "o", ms=7, mfc=st.VERMILLION, mec="white", mew=1.0, zorder=6)
    ax.annotate("Cable landing", (best.lon, best.lat), xytext=(8, -10), textcoords="offset points", fontsize=7.5,
                color=st.TEXT)
    pad = RADIUS_KM / 111 + 0.4
    ax.set_xlim(best.lon - pad, best.lon + pad)
    ax.set_ylim(best.lat - pad, best.lat + pad)
    ax.set_aspect(1 / np.cos(np.deg2rad(best.lat)))
    st.map_axes(ax)
    st.legend_squares(ax, [(COLOR[t], f"{LABEL[t]}: {best[f'GW_{t}']:.1f} GW") for t in TECHS if best[f"GW_{t}"] > 0.005]
                      + ([(st.GROUPS["Storage"], f"Battery: {best.battery_GW:.1f} GW, {best.battery_GWh:.0f} GWh")]
                         if best.battery_GW > 0.005 else []))
    ax.set_title(f"Plants within {RADIUS_KM} km, {best.GW:.1f} GW", loc="left")

    ax1 = fig.add_subplot(gs[0, 1])
    end = tot.rolling(168).mean().idxmin()
    wk = by_t.loc[end - pd.Timedelta(hours=167):end]
    parts = [wk[t] for t in TECHS] + [wk.battery.clip(lower=0)]
    ax1.stackplot(wk.index, *parts, colors=[COLOR[t] for t in TECHS] + [st.GROUPS["Storage"]], linewidth=0)
    ax1.axhline(FIRM_GW, color=st.VERMILLION, linewidth=1.2)
    ax1.text(wk.index[-1], FIRM_GW, " 2 GW cable", va="center", fontsize=7.5, color=st.TEXT)
    ax1.set_title("Output in the weakest week of 2013, GW", loc="left")
    ax1.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%d %b"))

    ax2 = fig.add_subplot(gs[1, 1])
    dur = np.sort(tot.values)[::-1]
    ax2.fill_between(np.arange(len(dur)), np.minimum(dur, FIRM_GW), color=st.VERMILLION, linewidth=0)
    ax2.fill_between(np.arange(len(dur)), FIRM_GW, np.maximum(dur, FIRM_GW), color=st.NEUTRAL, linewidth=0)
    ax2.text(len(dur) * 0.55, FIRM_GW * 0.5, "into the cable", fontsize=7.5, color="white")
    ax2.text(len(dur) * 0.05, FIRM_GW * 1.15, f"surplus {best.surplus_share:.0%}", fontsize=7.5, color=st.TEXT)
    ax2.set_xlim(0, len(dur))
    ax2.set_title("Hourly output of the year, sorted, GW", loc="left")
    ax2.set_xlabel("Hours")
    fig.suptitle(f"Steady 2 GW: cheapest plant mix within {RADIUS_KM} km of the cable landing ({best.state})",
                 x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.savefig(OUT / f"firm_supply{SUFFIX}.pdf")
    fig.savefig(OUT / f"firm_supply{SUFFIX}.png", dpi=300)

    # overview map: cost of a firm 2 GW at every landing point along the coast
    fig, ax = plt.subplots(figsize=(5.6, 5.6))
    states.simplify(0.02).boundary.plot(ax=ax, color=st.TEXT, linewidth=0.3)
    sc = ax.scatter(ok.lon, ok.lat, c=ok.lcoe_firm, cmap="viridis_r", s=10, zorder=4,
                    vmin=ok.lcoe_firm.min(), vmax=ok.lcoe_firm.quantile(0.9))
    ax.plot(best.lon, best.lat, "o", ms=8, mfc="none", mec=st.VERMILLION, mew=1.5, zorder=5)
    ax.set_xlim(-74.5, -32.5)
    ax.set_ylim(-34.5, 6.0)
    ax.set_aspect(1 / np.cos(np.deg2rad(-14)))
    st.map_axes(ax)
    ax.set_title("Cost of a steady 2 GW at each coast point, EUR/MWh", loc="left")
    st.colorbar(fig, sc, ax.inset_axes([0.05, 0.05, 0.5, 0.025]), "EUR per MWh into the cable (European costs)")
    fig.savefig(OUT / f"firm_supply_coast{SUFFIX}.pdf")
    fig.savefig(OUT / f"firm_supply_coast{SUFFIX}.png", dpi=300)
    print("saved", OUT / f"firm_supply{SUFFIX}.png", OUT / f"firm_supply_coast{SUFFIX}.png")


if __name__ == "__main__":
    main()
