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

# --- sheet 2: losses per route ---------------------------------------------------------------
import json  # noqa: E402

R = json.loads((d / "routes.json").read_text())
wl = wb.create_sheet("Verluste")
wl["A1"] = "Netzverluste je Route (2 GW Bipol, 525 kV)"
wl["A1"].font = Font(bold=True, size=13)
wl["A2"] = "Rolle 1 · Kabel-Techno-Ökonomie · gelbe Zelle ist eine Eingabe und kann geändert werden"
wl.append([])
wl.append(["Kennzahl"] + [n for _, n in CO.ROUTES] + ["Einheit", "Herkunft", "Erläuterung"])
for c in wl[4]:
    c.font, c.fill = head, hfill
keys = [k for k, _ in CO.ROUTES]
L = [  # (Kennzahl, values or formula template with {c}, unit, Herkunft, Erläuterung, number format)
    ("Länge", [R[k]["length_km"] for k in keys], "km", "berechnet", "Kostengünstigster Weg auf dem 0,05°-Raster.", "#,##0"),
    ("Verlust bei Volllast (2 GW)", [R[k]["loss_full_load_pct"] for k in keys], "%", "berechnet",
     "Gleichstromwiderstand je Tiefenklasse aus den Kabeldaten × Länge, Nennstrom, zwei Kabel; plus Konverter.", "0.0"),
    ("davon Konverter (2 Stationen)", [1.72] * 3, "%", "direkt", "Konverterverlust je Station laut Kabeldaten, zwei Stationen.", "0.00"),
    ("davon Kabel", "={c}6-{c}7", "%", "berechnet", "Volllastverlust minus Konverter.", "0.0"),
    ("Kabelverlust je 1.000 km bei Volllast", "={c}8/{c}5*1000", "%", "berechnet", "Kabelverlust geteilt durch Länge.", "0.00"),
    ("Verlust bei halber Last (1 GW)", [R[k]["loss_half_load_pct"] for k in keys], "%", "berechnet",
     "Kabelverlust sinkt mit der Last (Strom halb, Verlust ein Viertel), Konverter bleiben.", "0.0"),
    ("Ankommende Leistung bei Volllast", "=2000*(1-{c}6/100)", "MW", "berechnet", "2.000 MW gesendet.", "#,##0"),
    ("Verlustleistung bei Volllast", "=2000*{c}6/100", "MW", "berechnet", "Wärme in Kabel und Konvertern.", "#,##0"),
    None,
    ("Eingabe: Auslastung (Anteil von 2 GW)", None, "–", "Annahme", "Frei wählbar, z. B. 0,5 für halbe Last.", "0.00"),
    ("Verlust bei dieser Auslastung", "={c}7+{c}8*$B$14", "%", "berechnet",
     "Konverter + Kabelverlust × Auslastung (relativer Kabelverlust ∝ Leistung).", "0.0"),
    ("Gesendete Leistung", "=2000*$B$14", "MW", "berechnet", "", "#,##0"),
    ("Ankommende Leistung", "={c}16*(1-{c}15/100)", "MW", "berechnet", "", "#,##0"),
]
for i, item in enumerate(L):
    r = 5 + i
    if item is None:
        wl.append([])
        continue
    name, vals, unit, hk, note, nf = item
    if vals is None:  # input row
        wl.append([name, 1.0, None, None, unit, "zusätzliche Annahme", note])
        wl[f"B{r}"].fill = PatternFill("solid", fgColor="FFF2B3")
        wl[f"B{r}"].font = bold
        wl[f"F{r}"].fill = PatternFill("solid", fgColor=HK_FILL["berechnet + Annahme"])
        wl[f"B{r}"].number_format = nf
        continue
    cells = [v.format(c=col) for v, col in zip([vals] * 3, "BCD")] if isinstance(vals, str) else vals
    wl.append([name, *cells, unit, HK_TEXT[hk], note])
    wl[f"F{r}"].fill = PatternFill("solid", fgColor=HK_FILL[hk])
    for col in "BCD":
        wl[f"{col}{r}"].number_format = nf
wl.append([])
wl.append(["Der Widerstand gilt bei maximaler Leitertemperatur; im Betrieb ist das Kabel oft kühler, die Verluste "
           "also eher etwas niedriger (Annahme)."])
wl.append(["Verluste sind nicht in € bewertet: Im PyPSA-Modell stecken sie im Wirkungsgrad der Verbindung "
           "(Wirkungsgrad = 1 − Verlust)."])
for col, w in zip("ABCDEFG", [40, 24, 26, 22, 9, 34, 80]):
    wl.column_dimensions[col].width = w
for row in wl.iter_rows(min_row=5, max_row=17):
    for c in row:
        c.alignment = Alignment(vertical="top", wrap_text=c.column_letter in "AG")
wl.freeze_panes = "B5"
out = d / "capex_opex.xlsx"
wb.save(out)
print(f"-> {out}")
