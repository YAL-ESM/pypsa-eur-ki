# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Map of the area in Brazil where wind and solar may be built.

Applies PyPSA-Eur's default exclusion rules (config.default.yaml, `renewable:`) to the Brazil layers in
data-brazil/layers, on a common 0.01 deg grid (~1.1 km). This is a screening map: the land cover is
resampled by majority to that grid, so areas are approximate. The model's availability matrices come
from atlite at full resolution.

    pixi run python workshop/brazil/plot_eligible_area.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import xarray as xr
from matplotlib.colors import ListedColormap
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy.ndimage import binary_dilation

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "workshop/plotstyle").is_dir())
sys.path.insert(0, str(ROOT / "workshop/plotstyle"))
import studystyle as st  # noqa: E402

DATA = ROOT / "data-brazil"
OUT = ROOT / "results/brazil"

# common grid: the box of the layers
RES = 0.01
WEST, EAST, SOUTH, NORTH = -74.9, -30.7, -35.0, 6.5
NX, NY = round((EAST - WEST) / RES), round((NORTH - SOUTH) / RES)
TRANSFORM = from_origin(WEST, NORTH, RES, RES)
LON = WEST + RES * (np.arange(NX) + 0.5)
LAT = NORTH - RES * (np.arange(NY) + 0.5)

# PyPSA-Eur rules for Copernicus LC100 (scripts/determine_availability_matrix_MD_UA.py)
ONWIND_CODES = [20, 30, 40, 60, 100]
SOLAR_CODES = [20, 30, 40, 50, 60, 90, 100]
URBAN, URBAN_DISTANCE_PX = 50, 1  # onwind keeps 1 km from urban land
# offshore (config.default.yaml): fixed down to 60 m, floating 60-1000 m, ships above 400 * 8760 * 6
FIXED_MAX_DEPTH, FLOAT_MAX_DEPTH = 60, 1000
SHIP_LIMIT = 400 * 8760 * 6


def read_resampled(path, resampling):
    with rasterio.open(path) as src:
        return src.read(1, out_shape=(NY, NX), resampling=resampling), src.nodata


def burn(geoms):
    return rasterize(((g, 1) for g in geoms), out_shape=(NY, NX), transform=TRANSFORM, dtype="uint8").astype(bool)


def main():
    states = gpd.read_file(f"zip://{DATA}/raw/gadm/gadm41_BRA_1.json.zip")
    states["geometry"] = states.make_valid().buffer(0)
    brazil = burn(states.geometry)

    lc, _ = read_resampled(DATA / "layers/copernicus_lc100.tif", Resampling.mode)
    # WDPA point records come as circles about 100x too large in area (e.g. Parque Estadual Cristalino II:
    # 117,810 km2 for 118,000 ha), so they are left out; the 3,663 polygons are kept
    wdpa = gpd.read_file(DATA / "layers/wdpa_brazil.gpkg")
    protected = burn(wdpa.geometry[wdpa.source_kind == "polygons"])
    eez = burn(gpd.read_file(DATA / "layers/eez_brazil.gpkg").geometry)

    with rasterio.open(DATA / "layers/shipdensity_brazil.tif") as src:  # 0.005 deg: max over 2 x 2 blocks
        ships = src.read(1)
        busy = (ships != src.nodata) & (ships > SHIP_LIMIT)
    busy = busy.reshape(NY, 2, NX, 2).any(axis=(1, 3))
    del ships

    elev = xr.open_dataset(DATA / "layers/gebco_brazil.nc")["elevation"]
    elev = elev.sel(lat=xr.DataArray(LAT, dims="y"), lon=xr.DataArray(LON, dims="x"), method="nearest").values
    depth = -elev.astype("float32")

    urban_buffer = binary_dilation(lc == URBAN, iterations=URBAN_DISTANCE_PX)
    land = brazil & ~protected
    onwind = land & np.isin(lc, ONWIND_CODES) & ~urban_buffer
    solar = land & np.isin(lc, SOLAR_CODES)
    sea = eez & ~brazil & ~protected & ~busy & (depth > 0)
    fixed = sea & (depth <= FIXED_MAX_DEPTH)
    floating = sea & (depth > FIXED_MAX_DEPTH) & (depth <= FLOAT_MAX_DEPTH)

    # categories: 0 nothing, 1 excluded land, 2 solar only, 3 wind and solar, 4 offshore fixed, 5 floating
    cat = np.zeros((NY, NX), "uint8")
    cat[brazil] = 1
    cat[solar] = 2
    cat[onwind] = 3  # onshore wind land is a subset of solar land, up to the urban buffer
    cat[fixed] = 4
    cat[floating] = 5

    km2 = (RES * 111.32) ** 2 * np.cos(np.deg2rad(LAT))[:, None] * np.ones((1, NX))
    area = {k: km2[cat == k].sum() / 1e3 for k in range(1, 6)}  # thousand km2
    for k, name in [(1, "excluded land"), (2, "solar only"), (3, "wind and solar"),
                    (4, "offshore fixed"), (5, "offshore floating")]:
        print(f"{name:>18}: {area[k]:7,.0f} thousand km2")

    st.use()
    colors = ["#ffffff", st.LAND, st.YELLOW, st.SKY, st.NAVY, "#8a9fb9"]  # floating = navy, lighter
    fig, ax = plt.subplots(figsize=(5.6, 5.6))
    ax.imshow(np.ma.masked_equal(cat, 0), cmap=ListedColormap(colors), vmin=0, vmax=5,
              extent=(WEST, EAST, SOUTH, NORTH), interpolation="nearest")
    states.simplify(0.02).boundary.plot(ax=ax, color=st.TEXT, linewidth=0.3)
    ax.set_xlim(WEST, -32.5)
    ax.set_ylim(-36.0, 6.0)
    ax.set_aspect(1 / np.cos(np.deg2rad(-14)))
    st.map_axes(ax)
    ax.set_title("Where wind and solar may be built in Brazil, thousand km²", loc="left")
    st.legend_squares(ax, [
        (st.SKY, f"Onshore wind and solar  {area[3]:,.0f}"),
        (st.YELLOW, f"Solar only  {area[2]:,.0f}"),
        (st.NAVY, f"Offshore wind, fixed (≤ 60 m)  {area[4]:,.0f}"),
        (colors[5], f"Offshore wind, floating (60–1000 m)  {area[5]:,.0f}"),
        (st.LAND, f"Excluded: forest, water, protected  {area[1]:,.0f}"),
    ], loc="lower left", bbox_to_anchor=(0, 0.035), fontsize=7.5)
    ax.text(0, 0, "PyPSA-Eur default exclusions on Copernicus LC100, WDPA, GEBCO, ship density; 0.01° grid",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=6.5, color=st.FAINT)

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "eligible_area.pdf")
    fig.savefig(OUT / "eligible_area.png", dpi=300)
    print("saved", OUT / "eligible_area.png")


if __name__ == "__main__":
    main()
