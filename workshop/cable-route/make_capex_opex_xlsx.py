"""Write capex_opex.xlsx: CAPEX and OPEX per proposed route with provenance (rounded aggregates only).

Usage: python make_capex_opex_xlsx.py <cable-route dir>
"""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

d = Path(sys.argv[1])
sys.path.insert(0, str(d))
import capex_opex as CO  # noqa: E402

HK_FILL = {"direkt": "E3EEFB", "berechnet": "F1F1EF", "berechnet + Annahme": "FBE9DC"}
HK_TEXT = {"direkt": "direkt aus den Daten", "berechnet": "aus den Daten berechnet",
           "berechnet + Annahme": "berechnet, mit zusätzlicher Annahme"}
bold, head = Font(bold=True), Font(bold=True, color="FFFFFF")
hfill = PatternFill("solid", fgColor="2A78D6")

wb = Workbook()
ws = wb.active
ws.title = "CAPEX_OPEX"
ws["A1"] = "HVDC-Kabel Brasilien – Deutschland: CAPEX und OPEX je Route (2 GW Bipol, 525 kV, Preisbasis 2025)"
ws["A1"].font = Font(bold=True, size=13)
ws["A2"] = "Rolle 1 · Kabel-Techno-Ökonomie · gerundete Werte, keine Einzelpreise des Lieferanten"
hdr = ["Posten", "Art"] + [n for _, n in CO.ROUTES] + ["Einheit", "Herkunft", "Erläuterung"]
ws.append([])
ws.append(hdr)
for c in ws[4]:
    c.font, c.fill = head, hfill
rows = CO.rows(d)
first = 5
for i, (name, art, unit, vals, hk, note) in enumerate(rows):
    r = first + i
    ws.append([name, art, *vals, unit, HK_TEXT[hk], note])
    if name == "OPEX gesamt":  # formula: maintenance + repairs
        for col in "CDE":
            ws[f"{col}{r}"] = f"={col}{r-2}+{col}{r-1}"
    if name.startswith("OPEX über"):  # formula: OPEX total × lifetime / 1000
        for col in "CDE":
            ws[f"{col}{r}"] = f"=ROUND({col}{r-1}*{col}{r+1}/1000,1)"
    ws[f"G{r}"].fill = PatternFill("solid", fgColor=HK_FILL[hk])
    if art == "CAPEX" or name == "OPEX gesamt":
        for c in ws[r][:5]:
            c.font = bold
    for col in "CDE":
        ws[f"{col}{r}"].number_format = "0.0" if unit == "Mrd. €" else "0"
last = first + len(rows) - 1
ws.append([])
ws.append([CO.NOT_INCLUDED])
ws.append([])
ws.append(["Herkunft"])
ws[f"A{ws.max_row}"].font = bold
for k, v in HK_TEXT.items():
    ws.append([v])
    ws[f"A{ws.max_row}"].fill = PatternFill("solid", fgColor=HK_FILL[k])
ws.append([    "Quellen: workshop/inputs/cable_system_design.yaml (Kabeldaten); Routen: workshop/cable-route/routes.json."])
ws.append(["Verluste sind nicht in € bewertet: Im PyPSA-Modell stecken sie im Wirkungsgrad der Verbindung."])

for col, w in zip("ABCDEFGH", [52, 10, 22, 24, 20, 12, 34, 90]):
    ws.column_dimensions[col].width = w
for row in ws.iter_rows(min_row=4, max_row=last):
    for c in row:
        c.alignment = Alignment(vertical="top", wrap_text=c.column_letter in "AH")
ws.freeze_panes = "C5"
out = d / "capex_opex.xlsx"
wb.save(out)
print(f"-> {out}")
