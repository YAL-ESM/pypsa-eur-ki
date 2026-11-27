"""Write routen_vergleich.xlsx: the three routes from Macau/Guamaré (RN) side by side.

Rounded aggregates from routes.json only (no supplier unit prices).
Usage: python make_routes_xlsx.py <cable-route dir>
"""
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

d = Path(sys.argv[1])
R = json.loads((d / "routes.json").read_text())
KEYS = [("cost_Macau", "A · kostenminimal"), ("shallow", "B · geringste Maximaltiefe"),
        ("minabyss", "C · wenigste km tiefer als 3.000 m")]
A, B, C = (R[k] for k, _ in KEYS)
SHORT = R["short"]


def de(x, nd=0):
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(r):
    return "" if r is A else f" (+{de(100 * (r['total_bn'] / A['total_bn'] - 1))} %)"


r5 = lambda x: int(5 * round(x / 5))
# (Kennzahl, values, unit, number format, Herkunft)
ROWS = [
    ("Länge", [r["length_km"] for r in (A, B, C)], "km", "#,##0", "berechnet"),
    ("Investition", [r["total_bn"] for r in (A, B, C)], "Mrd. €", "0.0", "berechnet"),
    ("Mehrkosten gegenüber A", [round(100 * (r["total_bn"] / A["total_bn"] - 1), 1) for r in (A, B, C)], "%", "0", "berechnet"),
    ("Maximale Tiefe", [r["max_depth_m"] for r in (A, B, C)], "m", "#,##0", "berechnet"),
    ("Strecke tiefer als 3.000 m", [r["km"]["abyssal"] for r in (A, B, C)], "km", "#,##0", "berechnet"),
    ("Verlust bei Volllast (2 GW)", [r["loss_full_load_pct"] for r in (A, B, C)], "%", "0", "berechnet"),
    ("Bauzeit mit 1 Verlegeschiff", [round(r["lay_days"] / 365, 1) for r in (A, B, C)], "Jahre", "0.0", "berechnet"),
]
TEXT = [
    ("Vorteil", ["am günstigsten, am kürzesten, geringste Verluste", f"am flachsten (max. {de(B['max_depth_m'])} m)",
                 "am wenigsten km tiefer als 3.000 m; meidet die tiefe Biskaya"]),
    ("Nachteil", [f"quert die Biskaya mit fast {de(r5(A['max_depth_m'] / 10) * 10)} m",
                  f"≈ {de(100 * (B['total_bn'] / A['total_bn'] - 1))} % teurer; mehr Flachwasser mit Schiffsverkehr (Annahme)",
                  f"≈ {de(100 * (C['total_bn'] / A['total_bn'] - 1))} % teurer, am längsten, höchste Verluste"]),
    ("Verlauf", ["quert die Biskaya im tiefen Teil", "quert die Biskaya weiter östlich bei ≈ 4.600 m",
                 "bleibt vor Frankreich auf dem Schelf, nutzt vor Brasilien flachere Rücken"]),
    ("Bewertung", [f"Rückfalloption, wenn ≈ {de(r5(A['max_depth_m'] / 10) * 10)} m qualifiziert werden",
                   "Vorschlag: geringste Tiefe, die qualifiziert werden muss",
                   "Alternative, wenn wenige Reparaturen in großer Tiefe wichtiger sind als Kosten"]),
]

bold, head = Font(bold=True), Font(bold=True, color="FFFFFF")
hfill, hl = PatternFill("solid", fgColor="2A78D6"), PatternFill("solid", fgColor="EEF4FC")
wb = Workbook()
ws = wb.active
ws.title = "Routenvergleich"
ws["A1"] = "HVDC-Kabel Brasilien – Deutschland: drei Routen ab Macau/Guamaré (RN) bis Deutsche Bucht"
ws["A1"].font = Font(bold=True, size=13)
ws["A2"] = "Rolle 1 · 2 GW Bipol, 525 kV · Preisbasis 2025 · gerundete Werte, keine Einzelpreise des Lieferanten"
ws.append([])
ws.append(["Kennzahl"] + [n for _, n in KEYS] + ["Einheit", "Herkunft"])
for c in ws[4]:
    c.font, c.fill = head, hfill
for name, vals, unit, nf, hk in ROWS:
    ws.append([name, *vals, unit, "aus den Daten berechnet"])
    r = ws.max_row
    for col in "BCD":
        ws[f"{col}{r}"].number_format = nf
    ws[f"A{r}"].font = bold
for name, vals in TEXT:
    ws.append([name, *vals, "", "Einschätzung"])
    r = ws.max_row
    ws[f"A{r}"].font = bold
    if name == "Bewertung":
        for c in ws[r][:4]:
            c.fill = hl
        ws[f"C{r}"].font = bold
last = ws.max_row
ws.append([])
notes = [
    f"Verworfen: die kürzeste Route ({de(SHORT['length_km'])} km, {de(SHORT['total_bn'], 1)} Mrd. €, "
    f"{de(SHORT['km']['abyssal'])} km tiefer als 3.000 m, max. {de(SHORT['max_depth_m'])} m).",
    "Anlandung Brasilien: workshop/brazil/landing_location.txt (Rolle 2). Routen: kostengünstigster Weg auf einem "
    "0,05°-Raster (GEBCO 2025); B mit Tiefengrenze ≈ 4.580 m, C zählt Strecken über 3.000 m vierfach.",
    "Quelle der Kennzahlen: workshop/cable-route/routes.json, erzeugt von routes.py mit den Kabeldaten. "
    "Bisher sind Kabel bis 2.150 m verlegt und bis 3.000 m typgeprüft; jede Route reicht tiefer.",
    "Verluste nicht in € bewertet: Im PyPSA-Modell stecken sie im Wirkungsgrad der Verbindung.",
]
for n in notes:
    ws.append([n])
for col, w in zip("ABCDEF", [30, 34, 34, 38, 9, 24]):
    ws.column_dimensions[col].width = w
for row in ws.iter_rows(min_row=4, max_row=last):
    for c in row:
        c.alignment = Alignment(vertical="top", wrap_text=True)
ws.freeze_panes = "B5"
out = d / "routen_vergleich.xlsx"
wb.save(out)
print(f"-> {out}")
