# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Best use of the land: wind or solar PV, outside all protected areas.

All WDPA protected-area polygons are excluded (indigenous areas, parks, reserves, environmental protection
areas, Ramsar sites ...), as in PyPSA-Eur's default. The 251 WDPA point records are left out, because their
circles are drawn about 100 times too large (see plot_eligible_area.py).

Wind and PV compete for the same land, so their potentials must not be added. Here every eligible
0.01 deg pixel (~1.1 km2) is given to the technology that yields more energy per km2 in that pixel:

    wind:  MW_PER_KM2 x capacity factor x (1 - wake loss) x 8760 h
    PV:    MW_PER_KM2 x capacity factor x 8760 h

where a technology is allowed only on its own land cover classes and below its slope limit (all
assumptions as in potential_outside_indigenous.py, which this script imports). A pixel that only one
technology may use goes to that technology. No co-location (agrivoltaics, PV between turbines) and no
mixing within a pixel. Result: the yearly output of the best plant mix per 0.3 deg cell and state.

    pixi run python workshop/brazil/optimal_land_use.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize
from rasterio.enums import Resampling
from scipy.ndimage import binary_dilation

sys.path.insert(0, str(Path(__file__).parent))
import plot_eligible_area as pe  # noqa: E402
import potential_outside_indigenous as po  # noqa: E402

st, DATA, OUT, CELL = po.st, po.DATA, po.OUT, po.CELL
MW, WAKE, SLOPE = po.MW_PER_KM2, po.WAKE_LOSS, po.MAX_SLOPE_DEG


def coast_point(uf, ufs, states, state_id, km2, use_w, use_s, e_w, e_s):
    """Coast point nearest to the output-weighted centre of the best mix in state `uf`.

    The coast is the part of the state border that lies on the EEZ (Marine Regions), i.e. on the sea.
    Distances in ESRI:102033 (South America Albers). Also prints how much of the yearly output lies within
    100 / 250 / 500 km of that point, for the state and for Brazil as a whole.
    """
    from pyproj import Transformer
    from shapely.geometry import Point
    from shapely.ops import nearest_points

    i = ufs.index(uf) + 1
    energy = km2 * np.where(use_w, e_w, np.where(use_s, e_s, 0.0))  # GWh per pixel and year
    yy, xx = np.nonzero((state_id == i) & (energy > 0))
    w = energy[yy, xx].astype("float64")
    lon_c, lat_c = np.average(pe.LON[xx], weights=w), np.average(pe.LAT[yy], weights=w)

    to_xy = Transformer.from_crs("EPSG:4326", "ESRI:102033", always_xy=True)
    to_ll = Transformer.from_crs("ESRI:102033", "EPSG:4326", always_xy=True)
    shape = states[states.uf == uf].to_crs("ESRI:102033").geometry.union_all()
    eez = gpd.read_file(DATA / "layers/eez_brazil.gpkg").to_crs("ESRI:102033").geometry.union_all().simplify(500)
    coast = shape.boundary.intersection(eez.buffer(3000))
    c = Point(*to_xy.transform(lon_c, lat_c))
    near = nearest_points(coast, c)[0]
    lon_k, lat_k = to_ll.transform(near.x, near.y)
    print(f"\nState {uf}: output-weighted centre {lat_c:.3f}, {lon_c:.3f}")
    print(f"Nearest coast point:      {lat_k:.3f}, {lon_k:.3f}   ({near.distance(c) / 1e3:,.0f} km from the centre)")

    ay, ax_ = np.nonzero(energy > 0)
    px, py = to_xy.transform(pe.LON[ax_], pe.LAT[ay])
    dist = np.hypot(px - near.x, py - near.y) / 1e3
    e = energy[ay, ax_] / 1e3  # TWh
    in_state = state_id[ay, ax_] == i
    for r in (100, 250, 500, 1000):
        m = dist <= r
        print(f"  within {r:>4} km of the coast point: {e[m].sum():8,.0f} TWh/yr in Brazil, {e[m & in_state].sum():8,.0f} in {uf}")
    pd.DataFrame([{"state": uf, "centre_lat": lat_c, "centre_lon": lon_c, "coast_lat": lat_k, "coast_lon": lon_k,
                   "distance_km": near.distance(c) / 1e3}]).to_csv(OUT / "coast_point.csv", index=False)


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
    wdpa = wdpa[wdpa.source_kind == "polygons"]
    protected_gdf = wdpa
    land = brazil & ~pe.burn(protected_gdf.geometry)
    slope = po.slope_deg()
    urban_buffer = binary_dilation(lc == pe.URBAN, iterations=pe.URBAN_DISTANCE_PX)
    km2 = ((pe.RES * 111.32) ** 2 * np.cos(np.deg2rad(pe.LAT))[:, None] * np.ones((1, pe.NX))).astype("float32")

    cutout, wind_cf, pv_cf = po.cutout_cf()
    x, y = cutout.data.x.values, cutout.data.y.values
    ny, nx = len(y), len(x)
    ix = np.clip(np.floor((pe.LON - (x[0] - CELL / 2)) / CELL).astype(int), -1, nx)
    iy = len(y) - 1 - np.clip(np.floor(((y[-1] + CELL / 2) - pe.LAT) / CELL).astype(int), -1, ny)
    inside = ((ix >= 0) & (ix < nx))[None, :] & ((iy >= 0) & (iy < ny))[:, None]
    cell = np.where(inside, iy[:, None] * nx + ix[None, :], 0)

    ok_w = land & np.isin(lc, pe.ONWIND_CODES) & ~urban_buffer & (slope <= SLOPE["onwind"]) & inside
    ok_s = land & np.isin(lc, pe.SOLAR_CODES) & (slope <= SLOPE["solar"]) & inside
    # energy per km2 and year, GWh/km2 (MW x CF x 8760 h / 1000)
    e_w = (MW["onwind"] * (1 - WAKE["onwind"]) * 8.76 * wind_cf.values.ravel()[cell]).astype("float32")
    e_s = (MW["solar"] * (1 - WAKE["solar"]) * 8.76 * pv_cf.values.ravel()[cell]).astype("float32")
    use_w = ok_w & (~ok_s | (e_w >= e_s))
    use_s = ok_s & ~use_w

    def per_cell(mask, weight):
        return np.bincount(cell[mask], weights=weight[mask], minlength=nx * ny).reshape(ny, nx)

    area = {"onwind": per_cell(use_w, km2), "solar": per_cell(use_s, km2)}
    twh = {"onwind": per_cell(use_w, km2 * e_w) / 1e3, "solar": per_cell(use_s, km2 * e_s) / 1e3}  # TWh/yr
    gw = {t: area[t] * MW[t] / 1e3 for t in area}

    # comparison: what each technology alone would give on its own land (as in potential_outside_indigenous.py)
    alone = {"onwind": (km2 * e_w)[ok_w].sum() / 1e3, "solar": (km2 * e_s)[ok_s].sum() / 1e3}
    both = ok_w & ok_s
    print("Technology alone, TWh/yr:", {k: round(v) for k, v in alone.items()}, "sum (double counts):", round(sum(alone.values())))
    print(f"Land open to both: {km2[both].sum() / 1e3:,.0f} thousand km2; only wind {km2[ok_w & ~ok_s].sum() / 1e3:,.0f}, "
          f"only PV {km2[ok_s & ~ok_w].sum() / 1e3:,.0f}")
    print(f"On the land open to both, wind wins on {km2[both & use_w].sum() / 1e3:,.0f} thousand km2, "
          f"PV on {km2[both & use_s].sum() / 1e3:,.0f}")
    tot = {t: twh[t].sum() for t in twh}
    print("\nBest mix, whole Brazil outside all protected areas:")
    for t in twh:
        print(f"  {t:>6}: {area[t].sum() / 1e3:7,.0f} thousand km2  {gw[t].sum():8,.0f} GW  {tot[t]:8,.0f} TWh/yr")
    print(f"   total: {sum(tot.values()):,.0f} TWh/yr  (average power {sum(tot.values()) * 1e3 / 8760:,.0f} GW)")

    # by state
    rows = []
    for i, uf in enumerate(states.uf, 1):
        r = {"state": uf}
        for t, m in (("onwind", use_w), ("solar", use_s)):
            sel = m & (state_id == i)
            r[f"{t}_area_1000km2"] = km2[sel].sum() / 1e3
            r[f"{t}_GW"] = km2[sel].sum() * MW[t] / 1e3
            r[f"{t}_TWh"] = (km2 * (e_w if t == "onwind" else e_s))[sel].sum() / 1e3
        rows.append(r)
    bys = pd.DataFrame(rows).set_index("state")
    bys["total_TWh"] = bys.onwind_TWh + bys.solar_TWh
    bys = bys.sort_values("total_TWh", ascending=False)
    OUT.mkdir(parents=True, exist_ok=True)
    bys.round(2).to_csv(OUT / "optimal_use_by_state.csv")
    print("\nTop states:\n", bys.head(10)[["onwind_TWh", "solar_TWh", "total_TWh", "onwind_GW", "solar_GW"]].round(0).astype(int))

    coast_point(bys.index[0], list(states.uf), states, state_id, km2, use_w, use_s, e_w, e_s)

    # cells: total yearly output and share of wind
    tot_cell = twh["onwind"] + twh["solar"]
    a_cell = area["onwind"] + area["solar"]
    wind_share = np.divide(area["onwind"], a_cell, out=np.full_like(a_cell, np.nan), where=a_cell > 0)
    cand = pd.DataFrame({"lon": np.tile(x, ny), "lat": np.repeat(y, nx), "TWh": tot_cell.ravel(),
                         "wind_share": wind_share.ravel(), "wind_TWh": twh["onwind"].ravel(),
                         "solar_TWh": twh["solar"].ravel(), "wind_GW": gw["onwind"].ravel(),
                         "solar_GW": gw["solar"].ravel()}).sort_values("TWh", ascending=False)
    picked = []
    for _, r in cand.iterrows():  # keep a cell only if >= 1 deg from those already chosen
        if all(max(abs(r.lon - q.lon), abs(r.lat - q.lat)) >= 1.0 for q in picked):
            picked.append(r)
        if len(picked) == 5:
            break
    top = pd.DataFrame(picked).reset_index(drop=True)
    top.insert(0, "rank", range(1, 6))
    top["state"] = [next((u for u, g in zip(states.uf, states.geometry) if g.contains(__import__("shapely").Point(r.lon, r.lat))), "?")
                    for r in top.itertuples()]
    print("\nBest cells (best mix):\n", top.round(2).to_string(index=False))
    top.to_csv(OUT / "optimal_top_cells.csv", index=False)  # exact cell positions: stays local (results/ is ignored)

    # map: share of wind in the best mix, and the yearly output of the best mix per cell
    st.use()
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 4.4))
    ext = (x[0] - CELL / 2, x[-1] + CELL / 2, y[0] - CELL / 2, y[-1] + CELL / 2)
    cmap = LinearSegmentedColormap.from_list("ws", [st.YELLOW, st.SKY])
    panels = [("Best technology", np.where(a_cell > 0, wind_share, np.nan), cmap, Normalize(0, 1), "Share of land best used for wind"),
              ("Yearly output of the best mix", np.where(tot_cell > 0, tot_cell, np.nan), "viridis",
               Normalize(0, np.nanpercentile(tot_cell[tot_cell > 0], 99)), "TWh/yr per 0.3° cell")]
    for ax, (title, data, cm, norm, label) in zip(axs, panels):
        im = ax.imshow(data, extent=ext, origin="lower", cmap=cm, norm=norm, interpolation="nearest")
        states.simplify(0.02).boundary.plot(ax=ax, color=st.TEXT, linewidth=0.3)
        protected_gdf.simplify(0.02).plot(ax=ax, color="none", edgecolor=st.VERMILLION, linewidth=0.15, alpha=0.5)
        ax.set_xlim(-74.5, -32.5)
        ax.set_ylim(-34.5, 6.0)
        ax.set_aspect(1 / np.cos(np.deg2rad(-14)))
        st.map_axes(ax)
        ax.set_title(title, loc="left")
        if ax is axs[1]:
            for r in top.itertuples():
                ax.plot(r.lon, r.lat, "o", ms=5, mfc="white", mec=st.TEXT, mew=1.0, zorder=5)
                ax.annotate(f"{r.rank}: {r.TWh:.1f} TWh/yr", (r.lon, r.lat), xytext=(6, 4), textcoords="offset points",
                            fontsize=6, color=st.TEXT, zorder=6,
                            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
        st.colorbar(fig, im, ax.inset_axes([0.05, 0.05, 0.5, 0.025]), label)
    fig.suptitle(f"Best use of land outside all protected areas: {sum(tot.values()):,.0f} TWh/yr "
                 f"({tot['onwind']:,.0f} wind, {tot['solar']:,.0f} solar)", x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.savefig(OUT / "optimal_land_use.pdf")
    fig.savefig(OUT / "optimal_land_use.png", dpi=300)
    print("saved", OUT / "optimal_land_use.png")


if __name__ == "__main__":
    main()
