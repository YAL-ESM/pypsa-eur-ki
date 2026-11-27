# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Where should the HVDC cable from Germany land in Brazil?

1. State: the one with the largest yearly renewable output outside all protected areas
   (best land mix of optimal_land_use.py + offshore wind of offshore_potential.py, total_by_state.csv).
2. Coast point: the state's coast (state border on the EEZ) is sampled every 5 km; each point is scored by
   the yearly output (land + offshore, all of Brazil) within RADIUS_KM of it. The best point is the landing.

Screening only: output within a radius, no grid, port, seabed or cost. Distances in ESRI:102033.
Exact coordinates go to results/ (git-ignored) only.

    pixi run python workshop/brazil/optimal_land_use.py      # writes land_twh_cell.npz
    pixi run python workshop/brazil/offshore_potential.py    # writes offshore_twh_cell.npz
    pixi run python workshop/brazil/landing_point.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).parent))
import potential_outside_indigenous as po  # noqa: E402

st, DATA, OUT, CELL = po.st, po.DATA, po.OUT, po.CELL
RADIUS_KM = 250  # catchment radius for scoring a landing point
RADII = (100, 250, 500)
STEP_M = 5000


def main():
    total = pd.read_csv(OUT / "total_by_state.csv", index_col=0).sort_values("total", ascending=False)
    uf = total.index[0]
    print("Yearly renewable output by state, TWh/yr (land best mix + offshore):")
    print(total.head(6).round(0).astype(int).to_string())
    print(f"\nState with the largest output: {uf}")

    land, off = np.load(OUT / "land_twh_cell.npz"), np.load(OUT / "offshore_twh_cell.npz")
    assert np.allclose(land["x"], off["x"]) and np.allclose(land["y"], off["y"])
    x, y = land["x"], land["y"]
    layers = {"land wind": land["onwind"], "land solar": land["solar"], "offshore": off["offshore"]}
    twh = sum(layers.values())
    yy, xx = np.nonzero(twh > 0)
    to_xy = Transformer.from_crs("EPSG:4326", "ESRI:102033", always_xy=True)
    to_ll = Transformer.from_crs("ESRI:102033", "EPSG:4326", always_xy=True)
    cx, cy = to_xy.transform(x[xx], y[yy])
    e = {k: v[yy, xx] for k, v in layers.items()}
    e_all = twh[yy, xx]

    states = gpd.read_file(f"zip://{DATA}/raw/gadm/gadm41_BRA_1.json.zip")
    states["geometry"] = states.make_valid().buffer(0)
    states["uf"] = states.HASC_1.str.split(".").str[1]
    shape = states[states.uf == uf].to_crs("ESRI:102033").geometry.union_all()
    eez = gpd.read_file(DATA / "layers/eez_brazil.gpkg").to_crs("ESRI:102033").geometry.union_all().simplify(500)
    coast = shape.boundary.intersection(eez.buffer(3000))
    lines = list(getattr(coast, "geoms", [coast]))
    pts = [ln.interpolate(d) for ln in lines if ln.length > 0 for d in np.arange(0, ln.length, STEP_M)]
    px, py = np.array([p.x for p in pts]), np.array([p.y for p in pts])
    print(f"Coast of {uf}: {coast.length / 1e3:,.0f} km, {len(pts)} candidate points")

    d = np.hypot(px[:, None] - cx[None, :], py[:, None] - cy[None, :]) / 1e3  # km, points x cells
    score = {r: (d <= r) @ e_all for r in RADII}
    best = int(np.argmax(score[RADIUS_KM]))
    lon_b, lat_b = to_ll.transform(px[best], py[best])
    # where along the coast: share of the coast length from the north end
    order = np.argsort(-py)
    rank_ns = np.where(order == best)[0][0] / len(pts)
    print(f"\nBest landing point in {uf} (max output within {RADIUS_KM} km): {lat_b:.3f}, {lon_b:.3f}"
          f"  ({rank_ns:.0%} of the coast from the north end)")
    rows = []
    for r in RADII:
        m = d[best] <= r
        row = {"radius_km": r, **{k: v[m].sum() for k, v in e.items()}}
        row["total"] = sum(v[m].sum() for v in e.values())
        row["coast_min"], row["coast_median"] = score[r].min(), np.median(score[r])
        rows.append(row)
    tab = pd.DataFrame(rows).set_index("radius_km")
    print("Output within the radius, TWh/yr (coast_min/median: same radius, other points on the coast):")
    print(tab.round(0).astype(int).to_string())

    # compare with the earlier rule (coast point nearest to the output-weighted centre of the state)
    cp = OUT / "coast_point.csv"
    if cp.exists():
        old = pd.read_csv(cp).iloc[0]
        ox, oy = to_xy.transform(old.coast_lon, old.coast_lat)
        dist_old = np.hypot(ox - px[best], oy - py[best]) / 1e3
        s_old = (np.hypot(ox - cx, oy - cy) / 1e3 <= RADIUS_KM) @ e_all
        print(f"\nEarlier point (nearest coast to the centre of {old.state}): {s_old:,.0f} TWh/yr within {RADIUS_KM} km,"
              f" {dist_old:,.0f} km from the new point")

    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"state": uf, "lat": lat_b, "lon": lon_b, "radius_km": RADIUS_KM,
                   "TWh_within_radius": score[RADIUS_KM][best]}]).to_csv(OUT / "landing_point.csv", index=False)
    tab.round(1).to_csv(OUT / "landing_point_catchment.csv")
    pd.DataFrame({"lat": to_ll.transform(px, py)[1], "lon": to_ll.transform(px, py)[0],
                  **{f"TWh_{r}km": score[r] for r in RADII}}).to_csv(OUT / "landing_coast_scores.csv", index=False)

    # map: output per cell, the state's coast coloured by score, the landing point and its catchment
    st.use()
    fig, ax = plt.subplots(figsize=(5.6, 5.6))
    ext = (x[0] - CELL / 2, x[-1] + CELL / 2, y[0] - CELL / 2, y[-1] + CELL / 2)
    data = np.where(twh > 0, twh, np.nan)
    im = ax.imshow(data, extent=ext, origin="lower", cmap="viridis", norm=Normalize(0, np.nanpercentile(data, 99)),
                   interpolation="nearest")
    states.simplify(0.02).boundary.plot(ax=ax, color=st.TEXT, linewidth=0.3)
    states[states.uf == uf].simplify(0.02).boundary.plot(ax=ax, color=st.TEXT, linewidth=1.0)
    circle = gpd.GeoSeries(gpd.points_from_xy([px[best]], [py[best]]), crs="ESRI:102033").buffer(RADIUS_KM * 1e3)
    circle.to_crs(4326).boundary.plot(ax=ax, color=st.VERMILLION, linewidth=1.0, linestyle="--")
    ax.plot(lon_b, lat_b, "o", ms=6, mfc=st.VERMILLION, mec="white", mew=1.0, zorder=5)
    ax.annotate(f"Landing in {uf}: {score[RADIUS_KM][best]:,.0f} TWh/yr\nwithin {RADIUS_KM} km", (lon_b, lat_b),
                xytext=(10, -4), textcoords="offset points", fontsize=7, color=st.TEXT, zorder=6,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
    ax.set_xlim(-74.5, -32.5)
    ax.set_ylim(-34.5, 6.0)
    ax.set_aspect(1 / np.cos(np.deg2rad(-14)))
    st.map_axes(ax)
    ax.set_title(f"Cable landing: {uf} coast, {score[RADIUS_KM][best]:,.0f} TWh/yr within {RADIUS_KM} km", loc="left")
    st.colorbar(fig, im, ax.inset_axes([0.05, 0.05, 0.5, 0.025]), "Land and offshore output, TWh/yr per 0.3° cell")
    fig.savefig(OUT / "landing_point.pdf")
    fig.savefig(OUT / "landing_point.png", dpi=300)
    print("saved", OUT / "landing_point.png")


if __name__ == "__main__":
    main()
