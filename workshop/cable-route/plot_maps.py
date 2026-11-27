"""Maps of the bathymetry files and of the three candidate routes."""
import sys, json, numpy as np, xarray as xr, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
datadir, routes, outdir = sys.argv[1:4]
INK, INK2, SURF, LAND = "#0b0b0b", "#52514e", "#fcfcfb", "#e4e1d9"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.edgecolor":INK2,"axes.labelcolor":INK2,
    "xtick.color":INK2,"ytick.color":INK2,"figure.facecolor":SURF,"axes.facecolor":SURF})
BLUES = plt.get_cmap("Blues")
def bathy(ax, z, lon, lat, step):
    zz = z[::step, ::step]; lo, la = lon[::step], lat[::step]
    sea = np.ma.masked_where(zz >= 0, -zz)
    m = ax.pcolormesh(lo, la, sea, cmap=BLUES, vmin=0, vmax=6500, shading="auto", rasterized=True)
    ax.pcolormesh(lo, la, np.ma.masked_where(zz < 0, zz), cmap=ListedColormap([LAND]), shading="auto", rasterized=True)
    cs = ax.contour(lo, la, -zz, levels=[500, 1500, 3000], colors=[INK2], linewidths=0.5, alpha=0.8)
    ax.clabel(cs, fmt="%d m", fontsize=7, colors=INK2)
    ax.set_aspect(1/np.cos(np.radians(np.mean(lat))))
    ax.set_xlabel("Längengrad"); ax.set_ylabel("Breitengrad")
    for s in ax.spines.values(): s.set_linewidth(0.5)
    return m
files = {"gebco_2025_atlantic_30s.nc":("Atlantik-Korridor (30″)", 8),
         "brazil_northeast.nc":("Nordost-Brasilien (15″)", 2),
         "europe_northsea.nc":("Nordsee (15″)", 2)}
for f,(title,step) in files.items():
    ds = xr.open_dataset(f"{datadir}/{f}")
    z = ds.elevation.values; lon, lat = ds.lon.values, ds.lat.values
    fig, ax = plt.subplots(figsize=(9, 8))
    m = bathy(ax, z, lon, lat, step)
    cb = fig.colorbar(m, ax=ax, shrink=0.7, label="Wassertiefe (m)"); cb.outline.set_linewidth(0.5)
    ax.set_title(f"Bathymetrie – {title}\nLinien: Grenzen der Kostenklassen 500 / 1.500 / 3.000 m", loc="left", color=INK)
    fig.tight_layout(); fig.savefig(f"{outdir}/map_{f.replace('.nc','')}.png", dpi=150); plt.close(fig)
# routes
R = np.load(routes); meta = json.load(open(routes.replace(".npz",".json")))
# all three start at the landing chosen by role 2 (Macau/Guamaré, RN); see routes.py
SEL = [("cost_Macau","A  kostenminimal","#2a78d6"),
       ("shallow","B  geringste Maximaltiefe","#eb6834"),
       ("minabyss","C  wenigste km tiefer als 3.000 m","#1baf7a")]
ds = xr.open_dataset(f"{datadir}/gebco_2025_atlantic_30s.nc")
z = ds.elevation.values; lon, lat = ds.lon.values, ds.lat.values
# depth-class map in neutral greys so routes stand out
fig, ax = plt.subplots(figsize=(10, 10))
st=8; zz=z[::st,::st]; d=-zz
cls = np.digitize(d,[0,500,1500,3000]).astype(float)  # 0 land, 1 shelf..4 abyssal
ax.pcolormesh(lon[::st],lat[::st],cls,cmap=ListedColormap([LAND,"#f1f1ef","#d6d5d0","#b3b1aa","#8a8880"]),
              norm=BoundaryNorm([-.5,.5,1.5,2.5,3.5,4.5],5),shading="auto",rasterized=True)
def de(x, nd=0): return f"{x:,.{nd}f}".replace(",","X").replace(".",",").replace("X",".")
# nested widths so overlapping sections stay visible (C widest underneath, A thinnest on top)
for (key,label,col),lw in zip(SEL[::-1],[7,4.5,2]):
    p = R[key]; r = meta[key]
    ax.plot(p[:,1],p[:,0],color="white",lw=lw+2.5,solid_capstyle="round")
    ax.plot(p[:,1],p[:,0],color=col,lw=lw,solid_capstyle="round",
            label=f"{label}: {de(r['length_km'])} km, {de(r['total_bn'],1)} Mrd. €, max. {de(r['max_depth_m'])} m")
h,l = ax.get_legend_handles_labels(); h,l = h[::-1],l[::-1]
for (la,lo,n) in [(-5.0667,-36.4517,"Macau/Guamaré (RN)"),(53.85,8.1,"Deutsche Bucht")]:
    ax.plot(lo,la,"o",ms=8,mfc=INK,mec="white",mew=2,zorder=5)
    ax.annotate(n,(lo,la),xytext=(8,-4),textcoords="offset points",color=INK,fontsize=9)
from matplotlib.patches import Patch
h += [Patch(fc=c,ec=INK2,lw=.3) for c in ["#f1f1ef","#d6d5d0","#b3b1aa","#8a8880"]]
l += ["Schelf 0–500 m (Kosten/km ×1,2)","Hang 500–1.500 m (×1,0)","Tiefsee 1.500–3.000 m (×1,25)","Abyssal > 3.000 m (×1,9, ungetestet)"]
ax.legend(h,l,loc="upper left",fontsize=8,frameon=True,facecolor=SURF,edgecolor=INK2,framealpha=.95)
ax.set_xlim(-50,15); ax.set_ylim(-9,60); ax.set_aspect(1/np.cos(np.radians(25)))
ax.set_xlabel("Längengrad"); ax.set_ylabel("Breitengrad")
ax.set_title("Drei Routen ab Macau/Guamaré (RN) – Deutsche Bucht (2 GW, 525 kV)", loc="left", color=INK)
fig.tight_layout(); fig.savefig(f"{outdir}/map_routes.png",dpi=150); plt.close(fig)
# depth profiles: small multiples, one axis each, shared scale
fig, axs = plt.subplots(3,1,figsize=(10,7),sharex=True,sharey=True)
for ax,(key,label,col) in zip(axs,SEL):
    p=R[key]; i=np.abs(lat[:,None]-p[:,0]).argmin(0); j=np.abs(lon[:,None]-p[:,1]).argmin(0)
    dep=np.clip(-z[i,j],0,None)
    s=np.r_[0,np.cumsum(np.hypot(np.diff(p[:,0])*111.2,np.diff(p[:,1])*111.2*np.cos(np.radians(p[:-1,0]))))]
    for y in [500,1500,3000]: ax.axhline(y,color=INK2,lw=.5,ls=(0,(2,3)))
    ax.fill_between(s,dep,0,color=col,alpha=.15,lw=0); ax.plot(s,dep,color=col,lw=2)
    ax.set_title(label,loc="left",fontsize=9,color=INK)
    ax.invert_yaxis() if ax is axs[0] else None
    ax.grid(axis="y",color="#e6e5e0",lw=.5); [sp.set_visible(False) for k,sp in ax.spines.items() if k in("top","right")]
axs[0].set_ylim(6500,0)
axs[1].set_ylabel("Wassertiefe (m)"); axs[-1].set_xlabel("Entfernung ab Brasilien (km)")
axs[0].text(1.0,1.03,"gestrichelt: 500 / 1.500 / 3.000 m – heutiger Rekord 2.150 m, typgeprüft bis 3.000 m",
            transform=axs[0].transAxes,ha="right",fontsize=8,color=INK2)
fig.suptitle("Tiefenprofile der drei Routen",x=0.06,ha="left",color=INK)
fig.tight_layout(); fig.savefig(f"{outdir}/depth_profiles.png",dpi=150); plt.close(fig)
