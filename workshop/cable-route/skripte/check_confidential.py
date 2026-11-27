"""Check files for the cable supplier's confidential figures before anything goes to git.

Confidential (must never be committed): supply cost, lay rate and vessel day rate
(lay spread) per depth class, converter, landfall and repair costs, and the
project reference. The values are read from the YAML at run time, so this
script itself contains none of them.

Usage:
  python check_confidential.py                # checks files staged in git
  python check_confidential.py <path> ...     # checks the given files/directories
Exit code 1 if anything is found or a file cannot be checked (images, PDFs).
"""
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]  # workshop/cable-route/skripte/ -> repo
YAML = REPO / "workshop" / "inputs" / "cable_system_design.yaml"
cfg = yaml.safe_load(YAML.read_text())
ref = re.search(r"Reference\s+(\S+)", YAML.read_text()).group(1)
inst, dc, op = cfg["installation"], cfg["depth_classes"], cfg["operation"]


def fmt(v):
    """Spellings of a number as it may appear in code, text or German slides."""
    out = {repr(v), f"{v:,}", f"{v:,}".replace(",", "X").replace(".", ",").replace("X", ".")}
    if isinstance(v, float):
        out.add(f"{v}".replace(".", ","))
    return {o for o in out if len(o.replace(".", "").replace(",", "")) >= 3}  # skip 1-2 digit values


def de(x, nd):
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


needles = {ref: "project reference", ref.lower(): "project reference"}
for k, c in dc.items():
    for key in ("supply_cost_eur_per_m", "lay_rate_km_per_day", "lay_spread_eur_per_day"):
        for f in fmt(c[key]):
            needles[f] = f"{key} ({k})"
    # derived all-in cost per route-km of the depth class, as shown on slides
    v = (2 * c["supply_cost_eur_per_m"] * 1e3 + c["burial_and_protection_eur_per_m"] * 1e3
         + c["lay_spread_eur_per_day"] / c["lay_rate_km_per_day"] * (1 + inst["weather_downtime_share"])
         ) * (1 + inst["owners_cost_and_contingency"][k]) / 1e6
    needles[f"{de(v, 1)} Mio"] = f"derived cost per km ({k})"
    needles[f"({de(v, 1)} Mio €/km"] = f"derived cost per km ({k})"
conv = cfg["converter_stations"]["cost_eur_per_station"]
for v, what in [(conv, "converter cost"), (inst["landfall_cost_eur"], "landfall cost"),
                (op["repair_mobilisation_eur"], "repair mobilisation cost")]:
    for f in fmt(v):
        needles[f] = what
needles[f"{de(2 * conv / 1e9, 2)} Mrd"] = "converter cost (derived total)"
needles[f"{de(conv / 1e6, 0)} Mio"] = "converter cost (derived)"
needles[f"{de(inst['landfall_cost_eur'] / 1e6, 0)} Mio"] = "landfall cost (derived)"
needles[f"{de(op['repair_mobilisation_eur'] / 1e6, 1)} Mio"] = "repair mobilisation cost (derived)"
# machine-readable outputs (JSON, CSV): field names and English number format of the same derived values
for field in ("converters_bn", "converter_bn", "joints_landfall_qual_bn", "landfall_bn", "cable_bn",
              "cost_per_km", "eur_per_km", "mio_eur_per_km"):
    needles[f'"{field}"'] = f"field with confidential cost part ({field})"
needles[f": {2 * conv / 1e9:.2f}"] = "converter cost (derived total, JSON)"
needles[f",{2 * conv / 1e9:.2f}"] = "converter cost (derived total, CSV)"
for k, days in op["repair_days"].items():
    needles[f"{days} Tage"] = f"repair days ({k})"
for k, c in dc.items():
    needles[f"{de(c['lay_rate_km_per_day'], 1 if c['lay_rate_km_per_day'] % 1 else 0)} km/Tag"] = f"lay rate ({k})"

BINARY = {".png", ".jpg", ".jpeg", ".pdf", ".pptx", ".nc", ".npz", ".zip", ".gif", ".svg"}

if len(sys.argv) > 1:
    paths = [Path(p) for p in sys.argv[1:]]
else:
    out = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=REPO, capture_output=True, text=True).stdout
    paths = [REPO / p for p in out.split()]
    if not paths:
        print("Nothing staged in git. Pass paths to check files directly.")
files = [f for p in paths for f in ([p] if p.is_file() else sorted(p.rglob("*")) if p.is_dir() else []) if f.is_file()]

hits, unchecked = 0, []
for f in files:
    if f.resolve() == YAML.resolve():
        print(f"BLOCK  {f}: this is the supplier data file itself")
        hits += 1
        continue
    if f.resolve() == Path(__file__).resolve():  # contains only search terms, no values
        continue
    if f.suffix.lower() in BINARY:
        unchecked.append(f)
        continue
    try:
        text = f.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        unchecked.append(f)
        continue
    embedded = re.compile(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]{200,}")
    if embedded.search(text):  # embedded images cannot be scanned
        unchecked.append(f)
        text = embedded.sub("", text)
    for n, line in enumerate(text.splitlines(), 1):
        for what in sorted({w for needle, w in needles.items() if needle in line}):
            hits += 1
            print(f"HIT    {f}:{n}: {what}: …{line.strip()[:110]}…")
for f in unchecked:
    print(f"CHECK  {f}: image/PDF content cannot be scanned. If it was made from the cable data, assume it contains the figures.")
print(f"\n{len(files)} files, {hits} hits, {len(unchecked)} not scannable.")
sys.exit(1 if hits or unchecked else 0)
