# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Where is Brazil's onshore wind and solar potential, outside indigenous areas?

Eligible land (PyPSA-Eur land cover rules, 0.01 deg screening grid, see plot_eligible_area.py) is
aggregated to the 0.3 deg cells of the ERA5 cutout and multiplied with the mean 2013 capacity factor
of each cell (atlite, same turbine and panel as PyPSA-Eur; PV tilted towards the equator) and with
PyPSA-Eur's installable capacity per km2. Result: annual generation potential per cell and state.

Scenarios (what is excluded on top of land cover):
  outside indigenous: only indigenous areas (WDPA "Indigenous Area" / "Indigenous Reserve")
  no protected area:  every WDPA polygon, indigenous areas included (the PyPSA-Eur default)

    pixi run python workshop/brazil/potential_outside_indigenous.py
"""

import sys
from pathlib import Path

import atlite
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.colors import Normalize
from rasterio.enums import Resampling
from scipy.ndimage import binary_dilation

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "workshop/plotstyle").is_dir())
sys.path.insert(0, str(ROOT / "workshop/plotstyle"))
sys.path.insert(0, str(Path(__file__).parent))
import studystyle as st  # noqa: E402
import plot_eligible_area as pe  # noqa: E402

DATA = ROOT / "data-brazil"
OUT = ROOT / "results/brazil"
MW_PER_KM2 = {"onwind": 3.0, "solar": 5.1}  # config.default.yaml, renewable.<tech>.capacity_per_sqkm
CELL = 0.3


def cutout_cf():
    cutout = atlite.Cutout(DATA / "weather/brazil-2013-era5.nc")
    wind = cutout.wind(turbine="Vestas_V112_3MW", capacity_factor=True, add_cutout_windspeed=True)
    pv = cutout.pv(panel="CSi", orientation="latitude_optimal", capacity_factor=True)
    return cutout, wind.load(), pv.load()


def main():
    states = gpd.read_file(f"zip://{DATA}/raw/gadm/gadm41_BRA_1.json.zip")
    states["geometry"] = states.make_valid().buffer(0)
    states["uf"] = states.HASC_1.str.split(".").str[1]
    brazil = pe.burn(states.geometry)
    state_id = np.zeros((pe.NY, pe.NX), "int16")
    for i, g in enumerate(states.geometry, 1):
        state_id[pe.burn([g])] = i

    lc, _ = pe.read_resampled(DATA / "layers/copernicus_lc100.tif", Resampling.mode)
    wdpa = gpd.read_file(DATA / "layers/wdpa_brazil.gpkg")
    wdpa = wdpa[wdpa.source_kind == "polygons"]  # point records are drawn ~100x too large, see plot_eligible_area
    indigenous = pe.burn(wdpa.geometry[wdpa.DESIG_ENG.str.contains("Indigenous")])
    protected = pe.burn(wdpa.geometry)

    urban_buffer = binary_dilation(lc == pe.URBAN, iterations=pe.URBAN_DISTANCE_PX)
    km2 = (pe.RES * 111.32) ** 2 * np.cos(np.deg2rad(pe.LAT))[:, None] * np.ones((1, pe.NX))
    scenarios = {"outside indigenous": brazil & ~indigenous, "no protected area": brazil & ~protected}

    cutout, wind_cf, pv_cf = cutout_cf()
    cf = {"onwind": wind_cf, "solar": pv_cf}
    x, y = cutout.data.x.values, cutout.data.y.values
    # cutout cell index of every pixel of the 0.01 deg grid
    ix = np.clip(np.floor((pe.LON - (x[0] - CELL / 2)) / CELL).astype(int), -1, len(x))
    iy = np.clip(np.floor(((y[-1] + CELL / 2) - pe.LAT) / CELL).astype(int), -1, len(y))  # y ascending
    iy = len(y) - 1 - iy
    inside = ((ix >= 0) & (ix < len(x)))[None, :] & ((iy >= 0) & (iy < len(y)))[:, None]
    cell = np.where(inside, iy[:, None] * len(x) + ix[None, :], -1)

    rows, cells = [], {}
    for scen, land in scenarios.items():
        for tech, codes in {"onwind": pe.ONWIND_CODES, "solar": pe.SOLAR_CODES}.items():
            ok = land & np.isin(lc, codes)
            if tech == "onwind":
                ok &= ~urban_buffer
            ok &= inside
            area = np.bincount(cell[ok], weights=km2[ok], minlength=len(x) * len(y)).reshape(len(y), len(x))
            gwh = area * MW_PER_KM2[tech] * cf[tech].values * 8.76  # MW * CF * 8760 h / 1000 = GWh
            cells[(scen, tech)] = (area, gwh)
            # state of each cell = state holding most of its eligible area, for the tables use pixels directly
            sid = state_id[ok]
            pix_gwh = km2[ok] * MW_PER_KM2[tech] * cf[tech].values.ravel()[cell[ok]] * 8.76
            by_state = pd.Series(pix_gwh).groupby(sid).sum() / 1e3  # TWh
            by_area = pd.Series(km2[ok]).groupby(sid).sum() / 1e3
            for i, uf in enumerate(states.uf, 1):
                if i in by_state.index:
                    rows.append((scen, tech, uf, by_area[i], by_state[i]))
    tab = pd.DataFrame(rows, columns=["scenario", "tech", "state", "area_1000km2", "TWh_per_year"])
    OUT.mkdir(parents=True, exist_ok=True)
    tab.to_csv(OUT / "potential_by_state.csv", index=False)

    for scen in scenarios:
        print(f"\n== {scen} ==")
        t = tab[tab.scenario == scen].pivot(index="state", columns="tech", values="TWh_per_year").fillna(0)
        t["total"] = t.sum(axis=1)
        print(t.sort_values("total", ascending=False).head(10).round(0).astype(int).to_string())
        print("Brazil total TWh/yr:", t.sum().round(0).to_dict())

    # best cells: potential in good-resource cells only (capacity factor above a threshold)
    scen = "outside indigenous"
    tops = {}
    for tech, thr in [("onwind", 0.40), ("solar", 0.20)]:
        area, gwh = cells[(scen, tech)]
        good = cf[tech].values >= thr
        print(f"\n{tech}: eligible area with CF >= {thr}: {area[good].sum() / 1e3:,.0f} thousand km2, "
              f"{gwh[good].sum() / 1e3:,.0f} TWh/yr, mean CF {np.average(cf[tech].values[good], weights=area[good]):.2f}")
        cand = pd.DataFrame({"lon": np.tile(x, len(y)), "lat": np.repeat(y, len(x)),
                             "cf": cf[tech].values.ravel(), "area_km2": area.ravel(), "GWh": gwh.ravel()})
        cand = cand.sort_values("GWh", ascending=False)
        picked = []
        for _, r in cand.iterrows():  # greedy: keep a cell only if >= 1 deg from those already chosen
            if all(max(abs(r.lon - q.lon), abs(r.lat - q.lat)) >= 1.0 for q in picked):
                picked.append(r)
            if len(picked) == 5:
                break
        top = pd.DataFrame(picked).reset_index(drop=True)
        top.insert(0, "rank", range(1, len(top) + 1))
        top["MW"] = top.area_km2 * MW_PER_KM2[tech]
        top["state"] = [states.uf[states.contains(__import__("shapely").Point(r.lon, r.lat))].iloc[0]
                        if states.contains(__import__("shapely").Point(r.lon, r.lat)).any() else "?"
                        for r in top.itertuples()]
        tops[tech] = top
        print(top.round(2).to_string(index=False))
        top.assign(tech=tech).to_csv(OUT / f"top_cells_{tech}.csv", index=False)

    # map: annual potential per cell, onshore wind and solar, outside indigenous areas
    st.use()
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 4.2))
    for ax, tech, title in zip(axs, ["onwind", "solar"], ["Onshore wind", "Solar PV"]):
        _, gwh = cells[(scen, tech)]
        dens = np.where(gwh > 0, gwh / 1e3, np.nan)
        im = ax.imshow(dens, extent=(x[0] - CELL / 2, x[-1] + CELL / 2, y[0] - CELL / 2, y[-1] + CELL / 2),
                       origin="lower", cmap="viridis", norm=Normalize(0, np.nanpercentile(dens, 99)),
                       interpolation="nearest")
        states.simplify(0.02).boundary.plot(ax=ax, color=st.TEXT, linewidth=0.3)
        ind = wdpa[wdpa.DESIG_ENG.str.contains("Indigenous")]
        ind.simplify(0.02).plot(ax=ax, color="none", edgecolor=st.VERMILLION, linewidth=0.2, alpha=0.6)
        ax.set_xlim(-74.5, -32.5)
        ax.set_ylim(-34.5, 6.0)
        ax.set_aspect(1 / np.cos(np.deg2rad(-14)))
        st.map_axes(ax)
        ax.set_title(title, loc="left")
        for r in tops[tech].itertuples():
            ax.plot(r.lon, r.lat, "o", ms=5, mfc="white", mec=st.TEXT, mew=1.0, zorder=5)
            ax.annotate(f"{r.rank}: {r.GWh / 1e3:.1f} TWh/yr, CF {r.cf:.2f}",
                        (r.lon, r.lat), xytext=(6, 4), textcoords="offset points", fontsize=6, color=st.TEXT,
                        zorder=6, bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
        cax = ax.inset_axes([0.05, 0.05, 0.5, 0.025])
        st.colorbar(fig, im, cax, "TWh/yr per 0.3° cell")
    fig.suptitle("Renewable potential in Brazil outside indigenous areas (outlined), 2013 weather", x=0.01, ha="left",
                 fontsize=10, fontweight="bold")
    fig.savefig(OUT / "potential_outside_indigenous.pdf")
    fig.savefig(OUT / "potential_outside_indigenous.png", dpi=300)
    print("saved", OUT / "potential_outside_indigenous.png")


if __name__ == "__main__":
    main()
