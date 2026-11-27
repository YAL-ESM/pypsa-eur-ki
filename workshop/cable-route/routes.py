import sys, json, numpy as np, yaml
from scipy import ndimage, sparse
from scipy.sparse.csgraph import dijkstra
cfg = yaml.safe_load(open(sys.argv[1])); out = sys.argv[2]
g = np.load("/tmp/cablecalc/grid05.npz"); z=g["z"]; lat=g["lat"]; lon=g["lon"]
ny,nx = z.shape; d = -z
inst = cfg["installation"]; dc = cfg["depth_classes"]
names = ["shelf","slope","deep","abyssal"]; bounds=[500,1500,3000,1e9]
def perkm(k):
    c=dc[k]; v = 2*c["supply_cost_eur_per_m"]*1e3 + c["burial_and_protection_eur_per_m"]*1e3 \
        + c["lay_spread_eur_per_day"]/c["lay_rate_km_per_day"]*(1+inst["weather_downtime_share"])
    return v*(1+inst["owners_cost_and_contingency"][k])/1e6
PK = {k:perkm(k) for k in names}
print("M EUR per route-km:", {k:round(v,2) for k,v in PK.items()})
cls = np.digitize(d, bounds)  # 0..3
water = z<0
def solve(src, dst, costcell, maxdepth=None):
    ok = water.copy()
    if maxdepth: ok &= d<=maxdepth
    id_ = -np.ones(z.shape, int); id_[ok]=np.arange(ok.sum())
    rows=[];cols=[];w=[]
    kmlat = 111.2*(lat[1]-lat[0]); 
    for di,dj in [(0,1),(1,0),(1,1),(1,-1)]:
        a = ok[max(0,-di):ny-max(0,di), max(0,-dj):nx-max(0,dj)]
        A = ok & np.roll(np.roll(ok,-di,0),-dj,1)
        A[ny-di:,:]=False
        if dj>0: A[:,nx-dj:]=False
        if dj<0: A[:,:-dj]=False
        ii,jj = np.where(A); i2,j2 = ii+di, jj+dj
        dx = 111.2*(lon[1]-lon[0])*np.cos(np.radians(lat[ii]))*dj; dy = kmlat*di
        L = np.hypot(dx,dy)
        cc = 0.5*(costcell[ii,jj]+costcell[i2,j2])*L
        rows+= [id_[ii,jj],id_[i2,j2]]; cols+=[id_[i2,j2],id_[ii,jj]]; w+=[cc,cc]
    G = sparse.csr_matrix((np.concatenate(w),(np.concatenate(rows),np.concatenate(cols))), shape=(ok.sum(),)*2)
    def node(p):
        i=np.abs(lat-p[0]).argmin(); j=np.abs(lon-p[1]).argmin()
        ii,jj=np.where(ok); k=np.argmin((ii-i)**2+(jj-j)**2); return id_[ii[k],jj[k]]
    s,t = node(src), node(dst)
    dist,pred = dijkstra(G, indices=s, return_predecessors=True)
    path=[t]
    while path[-1]!=s: path.append(pred[path[-1]])
    inv = np.argwhere(ok)
    return inv[path[::-1]]
def evaluate(p, name):
    ii,jj = p[:,0],p[:,1]
    la,lo = lat[ii],lon[jj]
    seg = np.hypot(np.diff(la)*111.2, np.diff(lo)*111.2*np.cos(np.radians(la[:-1])))
    dd = d[ii,jj]; c = np.digitize(dd,bounds)[:-1]
    km = {names[k]: float(seg[c==k].sum()) for k in range(4)}
    L = sum(km.values())
    cable = sum(km[k]*PK[k] for k in names)*1e6
    nj = int(L//inst["field_joint_every_km"])
    fixed = nj*inst["field_joint_cost_eur"] + 2*inst["landfall_cost_eur"] + (inst["deep_water_qualification_eur"] if km["abyssal"]>0 else 0)
    conv = 2*cfg["converter_stations"]["cost_eur_per_station"]
    R = sum(km[k]*dc[k]["dc_resistance_ohm_per_km"] for k in names)
    loss = 2*R*1905**2/1e6
    lay_days = sum(km[k]/dc[k]["lay_rate_km_per_day"] for k in names)*(1+inst["weather_downtime_share"]) + nj*inst["field_joint_days"]
    op = cfg["operation"]
    faults = sum(2*km[k]/100*op["faults_per_100_km_cable_year"][k] for k in names)
    halfdays = sum(2*km[k]/100*op["faults_per_100_km_cable_year"][k]*op["repair_days"][k] for k in names)
    # Rounded aggregates only. Never write converter, landfall, joint or per-class costs to the JSON
    # (it is committed; supplier figures are confidential).
    total = cable+fixed+conv
    part = {}  # cost parts per depth class incl. contingency, for shares and corridor
    sh = dict(supply=0., reserve=0., burial=0., lay=0.)
    for k in names:
        c_ = dc[k]; ct = inst["owners_cost_and_contingency"][k]
        sup = 2*c_["supply_cost_eur_per_m"]*1e3*km[k]; bur = c_["burial_and_protection_eur_per_m"]*1e3*km[k]
        lay = km[k]/c_["lay_rate_km_per_day"]*(1+inst["weather_downtime_share"])*c_["lay_spread_eur_per_day"]
        sh["supply"] += sup; sh["burial"] += bur; sh["lay"] += lay; sh["reserve"] += (sup+bur+lay)*ct
        part[k] = (sup+bur+lay)*(1+ct)
    share = {k: int(round(100*v/total)) for k, v in sh.items()}
    share["fixed"] = int(round(100*(fixed+conv)/total)); share["abyssal"] = int(round(100*part["abyssal"]/total))
    # cost corridor [A]: low/high factors per part (assumption, see slides)
    lo_f = {"shelf": .9, "slope": .9, "deep": .9, "abyssal": .85}; hi_f = {"shelf": 1.2, "slope": 1.2, "deep": 1.35, "abyssal": 1.6}
    corr_lo = sum(part[k]*lo_f[k] for k in names) + (fixed+conv)*.9
    corr_hi = sum(part[k]*hi_f[k] for k in names) + (fixed+conv)*1.3
    r = dict(name=name, length_km=round(L), km={k:round(v) for k,v in km.items()}, max_depth_m=int(dd.max()),
             total_bn=round(total/1e9,1), share_pct=share,
             corridor_bn=[int(round(corr_lo/1e9)), int(round(corr_hi/1e9))], loss_full_load_pct=round(100*loss/2000+0.86*2,1),
             loss_half_load_pct=round(100*loss/4/1000+0.86*2,1),
             lay_days=round(lay_days), faults_per_year=round(faults,2), half_power_days_per_year=round(halfdays,1),
             # OPEX aggregates, rounded (no unit prices): maintenance share of investment, repair call-outs per year
             fom_mio=int(round((op["cable_fom_share_per_year"]*(cable+fixed) + op["converter_fom_share_per_year"]*conv)/1e7)*10),
             repair_mio=int(round(faults*op["repair_mobilisation_eur"]/1e6)))
    print(json.dumps(r)); return r, np.c_[la,lo]
cost = np.vectorize(lambda k: PK[names[k]])(cls).astype(float)
# Brazilian landing chosen by role 2 (workshop/brazil/landing_location.txt): north coast of RN, Macau/Guamaré.
# Other points only for comparison (cost-optimal route each).
LAND = (-5.0667, -36.4517)
BR = {"Macau": LAND, "Touros":(-5.15,-35.45), "Pecem":(-3.55,-38.80), "SaoLuis":(-2.45,-44.0), "Caravelas":(-18.2775,-39.6499)}
DE = (53.85, 7.9)
res={}
for n,p in BR.items():
    res[f"cost_{n}"] = evaluate(solve(p,DE,cost), f"cost_{n}")
# shortest route (distance only): lowest losses
res["short"] = evaluate(solve(LAND,DE,np.ones_like(cost)), "short")
# minimax depth
lo_,hi_ = 3500,4600
def conn(T):
    lab,_ = ndimage.label(water&(d<=T), structure=np.ones((3,3)))
    def nw(p):
        i=np.abs(lat-p[0]).argmin(); j=np.abs(lon-p[1]).argmin(); ii,jj=np.where(lab>0); k=np.argmin((ii-i)**2+(jj-j)**2); return lab[ii[k],jj[k]]
    return nw(LAND)==nw(DE)
while hi_-lo_>25:
    m=(lo_+hi_)/2; (hi_:=m) if conn(m) else (lo_:=m)
print("minimax depth Macau->DE:", hi_)
res["shallow"] = evaluate(solve(LAND,DE,cost,maxdepth=hi_+150), "shallow")
# minimise abyssal km: heavy penalty on abyssal (risk weighting x4)
pen = cost.copy(); pen[cls==3]*=4
res["minabyss"] = evaluate(solve(LAND,DE,pen), "minabyss")
np.savez(out, **{k:v[1] for k,v in res.items()})
json.dump({k:v[0] for k,v in res.items()}, open(out.replace(".npz",".json"),"w"), indent=1)
