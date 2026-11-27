import sys, numpy as np, xarray as xr
from scipy import ndimage
ds = xr.open_dataset(sys.argv[1])
print(ds)
f = 6  # 30" -> 3' (0.05 deg)
e = ds.elevation.coarsen(lat=f, lon=f, boundary="trim").mean()
np.savez_compressed("/tmp/cablecalc/grid05.npz", z=e.values.astype("float32"), lat=e.lat.values, lon=e.lon.values)
z = e.values; lat=e.lat.values; lon=e.lon.values
def idx(la, lo): return np.abs(lat-la).argmin(), np.abs(lon-lo).argmin()
def near_water(la,lo,T):
    i,j = idx(la,lo); w = (z<0)&(-z<=T)
    ii,jj = np.where(w[max(0,i-20):i+20, max(0,j-20):j+20])
    k = np.argmin((ii-20)**2+(jj-20)**2); return ii[k]+max(0,i-20), jj[k]+max(0,j-20)
for T in [2000,2500,3000,3500,4000,4500,5000,5500,6000,7000]:
    lab,_ = ndimage.label((z<0)&(-z<=T), structure=np.ones((3,3)))
    a = lab[near_water(-3.6,-38.7,T)]; b = lab[near_water(53.8,8.0,T)]
    print(T, "connected" if a==b and a>0 else "NOT connected")
