# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Offshore wind potential of Brazil, outside all protected areas.

PyPSA-Eur's offshore rules (config.default.yaml, `renewable: offwind-*`) on the Brazil layers, same screening
grid (0.01 deg) as plot_eligible_area.py:

  area:     inside the 200 NM EEZ, outside every WDPA polygon, ship density below 400 x 8760 x 6, depth > 0
            fixed foundation 0-60 m (turbine NREL 5.5 MW), floating 60-1000 m (NREL 5 MW offshore)
  output:   2 MW/km2 x ERA5 2013 capacity factor x correction_factor 0.8855 (PyPSA-Eur's offshore factor,
            for wake and other losses) x 8760 h
  not done: shore-distance split (offwind-ac within 30 km, offwind-dc beyond), cable and foundation cost.
            Offshore area does not compete with land, so it is added to the land result of optimal_land_use.py.

The 251 WDPA point records are left out (circles about 100 times too large).
Each sea pixel is assigned to the nearest state, to show which coast it belongs to.

    pixi run python workshop/brazil/offshore_potential.py
"""

import sys
from pathlib import Path

import atlite
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from matplotlib.colors import Normalize
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).parent))
import plot_eligible_area as pe  # noqa: E402
import potential_outside_indigenous as po  # noqa: E402

st, DATA, OUT, CELL = po.st, po.DATA, po.OUT, po.CELL
MARK_TOP_CELLS = False  # the best cells lie next to confidential sites (e.g. the offshore shortlist site): keep markers off for anything pushed
MW_PER_KM2 = 2.0
CORRECTION = 0.8855
TURBINE = {"fixed": "NREL_ReferenceTurbine_2020ATB_5.5MW", "floating": "NREL_ReferenceTurbine_5MW_offshore"}


def main():
    states = gpd.read_file(f"zip://{DATA}/raw/gadm/gadm41_BRA_1.json.zip")
    states["geometry"] = states.make_valid().buffer(0)
    states["uf"] = states.HASC_1.str.split(".").str[1]
    brazil = pe.burn(states.geometry)
    state_id = np.zeros((pe.NY, pe.NX), "int16")
    for i, g in enumerate(states.geometry, 1):
        state_id[pe.burn([g])] = i
    # nearest state of every pixel (for sea pixels: which coast)
    _, (ry, rx) = distance_transform_edt(state_id == 0, return_indices=True)
    nearest = state_id[ry, rx]
    dist_px = distance_transform_edt(~brazil)  # distance to the coast in pixels (about 1.1 km)

    wdpa = gpd.read_file(DATA / "layers/wdpa_brazil.gpkg")
    wdpa = wdpa[wdpa.source_kind == "polygons"]
    protected = pe.burn(wdpa.geometry)
    eez = pe.burn(gpd.read_file(DATA / "layers/eez_brazil.gpkg").geometry)
    with rasterio.open(DATA / "layers/shipdensity_brazil.tif") as src:
        ships = src.read(1)
        busy = (ships != src.nodata) & (ships > pe.SHIP_LIMIT)
    busy = busy.reshape(pe.NY, 2, pe.NX, 2).any(axis=(1, 3))
    del ships
    elev = xr.open_dataset(DATA / "layers/gebco_brazil.nc")["elevation"]
    elev = elev.sel(lat=xr.DataArray(pe.LAT, dims="y"), lon=xr.DataArray(pe.LON, dims="x"), method="nearest").values
    depth = -elev.astype("float32")

    cutout = atlite.Cutout(DATA / "weather/brazil-2013-era5.nc")
    cf = {k: cutout.wind(turbine=t, capacity_factor=True, add_cutout_windspeed=True).load().values
          for k, t in TURBINE.items()}
    x, y = cutout.data.x.values, cutout.data.y.values
    ny, nx = len(y), len(x)
    ix = np.clip(np.floor((pe.LON - (x[0] - CELL / 2)) / CELL).astype(int), -1, nx)
    iy = ny - 1 - np.clip(np.floor(((y[-1] + CELL / 2) - pe.LAT) / CELL).astype(int), -1, ny)
    inside = ((ix >= 0) & (ix < nx))[None, :] & ((iy >= 0) & (iy < ny))[:, None]
    cell = np.where(inside, iy[:, None] * nx + ix[None, :], 0)
    km2 = ((pe.RES * 111.32) ** 2 * np.cos(np.deg2rad(pe.LAT))[:, None] * np.ones((1, pe.NX))).astype("float32")

    sea = eez & ~brazil & ~protected & ~busy & (depth > 0) & inside
    masks = {"fixed": sea & (depth <= pe.FIXED_MAX_DEPTH),
             "floating": sea & (depth > pe.FIXED_MAX_DEPTH) & (depth <= pe.FLOAT_MAX_DEPTH)}
    e = {k: (MW_PER_KM2 * CORRECTION * 8.76 * cf[k].ravel()[cell]).astype("float32") for k in masks}  # GWh/km2/yr

    print("Offshore wind, outside all protected areas:")
    twh_cell = np.zeros(nx * ny)
    rows = []
    for k, m in masks.items():
        area, twh = km2[m].sum() / 1e3, (km2 * e[k])[m].sum() / 1e3
        cfm = np.average(cf[k].ravel()[cell[m]], weights=km2[m])
        print(f"  {k:>8}: {area:7,.0f} thousand km2  {area * MW_PER_KM2:7,.0f} GW  {twh:7,.0f} TWh/yr  mean CF {cfm:.2f}")
        twh_cell += np.bincount(cell[m], weights=(km2 * e[k])[m], minlength=nx * ny) / 1e3
        for i, uf in enumerate(states.uf, 1):
            sel = m & (nearest == i)
            rows.append((uf, k, km2[sel].sum() / 1e3, km2[sel].sum() * MW_PER_KM2 / 1e3, (km2 * e[k])[sel].sum() / 1e3))
    total = twh_cell.sum()
    gw_cell = {k: (np.bincount(cell[m], weights=km2[m], minlength=nx * ny) * MW_PER_KM2 / 1e3).reshape(ny, nx)
               for k, m in masks.items()}
    np.savez(OUT / "offshore_twh_cell.npz", x=x, y=y, offshore=twh_cell.reshape(ny, nx),
             fixed_GW=gw_cell["fixed"], floating_GW=gw_cell["floating"])  # for landing_point.py and firm_supply.py
    print(f"     total: {total:,.0f} TWh/yr")
    tab = pd.DataFrame(rows, columns=["state", "type", "area_1000km2", "GW", "TWh"]).pivot(
        index="state", columns="type", values=["area_1000km2", "GW", "TWh"])
    tab.columns = [f"{t}_{k}" for t, k in tab.columns]
    tab["total_TWh"] = tab.TWh_fixed + tab.TWh_floating
    tab = tab.sort_values("total_TWh", ascending=False)
    OUT.mkdir(parents=True, exist_ok=True)
    tab.round(2).to_csv(OUT / "offshore_by_state.csv")
    print("\nBy nearest coast state (TWh/yr):\n", tab.head(8)[["TWh_fixed", "TWh_floating", "total_TWh", "GW_fixed", "GW_floating"]].round(0).astype(int))

    near = (masks["fixed"] | masks["floating"]) & (dist_px * pe.RES * 111.32 <= 30)
    print(f"\nWithin 30 km of the coast (offwind-ac in PyPSA-Eur): {(km2 * np.where(masks['fixed'], e['fixed'], e['floating']))[near].sum() / 1e3:,.0f} TWh/yr")

    # combine with the land result (outside all protected areas), from optimal_land_use.py
    land_csv = OUT / "optimal_use_by_state.csv"
    if land_csv.exists():
        land = pd.read_csv(land_csv, index_col=0)
        lw, ls = land.onwind_TWh.sum(), land.solar_TWh.sum()
        print(f"\nLand best mix: wind {lw:,.0f} + solar {ls:,.0f} = {lw + ls:,.0f} TWh/yr;  with offshore: {lw + ls + total:,.0f} TWh/yr")
        comb = pd.DataFrame({"land_wind": land.onwind_TWh, "land_solar": land.solar_TWh,
                             "offshore": tab.total_TWh}).fillna(0)
        comb["total"] = comb.sum(axis=1)
        comb.sort_values("total", ascending=False).round(1).to_csv(OUT / "total_by_state.csv")
        print((comb.sort_values("total", ascending=False).head(8)).round(0).astype(int))

    # best cells (>= 1 deg apart); exact positions stay in results/ (git-ignored)
    area_cell = np.bincount(cell[sea], weights=km2[sea], minlength=nx * ny)
    cand = pd.DataFrame({"lon": np.tile(x, ny), "lat": np.repeat(y, nx), "TWh": twh_cell,
                         "area_km2": area_cell}).query("TWh > 0").sort_values("TWh", ascending=False)
    picked = []
    for _, r in cand.iterrows():
        if all(max(abs(r.lon - q.lon), abs(r.lat - q.lat)) >= 1.0 for q in picked):
            picked.append(r)
        if len(picked) == 5:
            break
    top = pd.DataFrame(picked).reset_index(drop=True)
    top.insert(0, "rank", range(1, 6))
    top["cf"] = [cf["fixed"].ravel()[int(np.argmin(np.abs(np.arange(nx * ny) - (np.argmin(abs(y - r.lat)) * nx + np.argmin(abs(x - r.lon))))))]
                 for r in top.itertuples()]
    print("\nBest offshore cells:\n", top.round(2).to_string(index=False))
    top.to_csv(OUT / "offshore_top_cells.csv", index=False)

    st.use()
    fig, ax = plt.subplots(figsize=(5.6, 5.6))
    data = np.where(twh_cell > 0, twh_cell, np.nan).reshape(ny, nx)
    ext = (x[0] - CELL / 2, x[-1] + CELL / 2, y[0] - CELL / 2, y[-1] + CELL / 2)
    im = ax.imshow(data, extent=ext, origin="lower", cmap="viridis", norm=Normalize(0, np.nanpercentile(data, 99)),
                   interpolation="nearest")
    states.simplify(0.02).boundary.plot(ax=ax, color=st.TEXT, linewidth=0.3)
    ax.set_xlim(-74.5, -32.5)
    ax.set_ylim(-34.5, 6.0)
    ax.set_aspect(1 / np.cos(np.deg2rad(-14)))
    st.map_axes(ax)
    for r in top.itertuples() if MARK_TOP_CELLS else []:
        ax.plot(r.lon, r.lat, "o", ms=5, mfc="white", mec=st.TEXT, mew=1.0, zorder=5)
        ax.annotate(f"{r.rank}: {r.TWh:.1f} TWh/yr", (r.lon, r.lat), xytext=(6, 4), textcoords="offset points",
                    fontsize=6.5, color=st.TEXT, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
    ax.set_title(f"Offshore wind outside protected areas: {total:,.0f} TWh/yr", loc="left")
    st.colorbar(fig, im, ax.inset_axes([0.05, 0.05, 0.5, 0.025]), "TWh/yr per 0.3° cell")
    fig.savefig(OUT / "offshore_potential.pdf")
    fig.savefig(OUT / "offshore_potential.png", dpi=300)
    print("saved", OUT / "offshore_potential.png")


if __name__ == "__main__":
    main()
