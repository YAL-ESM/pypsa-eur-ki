"""CAPEX and OPEX per proposed route, rounded aggregates only (no supplier unit prices).

Used by make_slides.py, make_slides_pdf.py and make_capex_opex_xlsx.py.
Herkunft: "direkt" = steht so in den Workshop-Daten, "berechnet" = aus den Daten gerechnet,
"Annahme" = zusätzliche Annahme ohne Beleg in den Daten.
"""
import json
from pathlib import Path

# All three routes start at the landing chosen by role 2: Macau/Guamaré (RN), see routes.py.
ROUTES = [("cost_Macau", "A · kostenminimal"), ("shallow", "B · geringste Maximaltiefe"),
          ("minabyss", "C · wenigste km > 3.000 m")]
LIFE = 40


def rows(d):
    R = json.loads((Path(d) / "skripte" / "routes.json").read_text())
    r = [R[k] for k, _ in ROUTES]
    FOM = {k: R[k]["fom_mio"] for k, _ in ROUTES}        # Mio. EUR/a, rounded to 10 in routes.py
    REPAIR = {k: R[k]["repair_mio"] for k, _ in ROUTES}  # Mio. EUR/a, rounded in routes.py
    opex = [FOM[k] + REPAIR[k] for k, _ in ROUTES]
    # (Posten, Art, Einheit, values, Herkunft, Erläuterung)
    return [
        ("Investition (Kabel, Konverter, Muffen, Anlandung, Reserve)", "CAPEX", "Mrd. €",
         [x["total_bn"] for x in r], "berechnet",
         "Route je Tiefenklasse × Kosten je km aus den Kabeldaten, dazu Fixkosten und die Reserve aus den Daten."),
        ("Laufende Wartung (ohne Reparaturen)", "OPEX", "Mio. €/Jahr", [FOM[k] for k, _ in ROUTES], "berechnet",
         "Fester Prozentsatz der Investition laut Kabeldaten, gerundet."),
        ("Reparatureinsätze", "OPEX", "Mio. €/Jahr", [REPAIR[k] for k, _ in ROUTES], "berechnet + Annahme",
         "Fehlerrate und Kosten je Einsatz aus den Kabeldaten. Annahme: Ersatzkabel und reserviertes Schiff "
         "sind nicht enthalten, weil die Daten dafür nichts angeben."),
        ("OPEX gesamt", "OPEX", "Mio. €/Jahr", opex, "berechnet", "Summe der beiden Zeilen darüber."),
        (f"OPEX über {LIFE} Jahre, nicht abgezinst", "OPEX", "Mrd. €", [round(o * LIFE / 1000, 1) for o in opex],
         "berechnet", f"Lebensdauer {LIFE} Jahre laut Kabeldaten."),
        ("Lebensdauer Kabel und Konverter", "Kennzahl", "Jahre", [LIFE] * 3, "direkt", "Kabeldaten."),
        ("Preisbasis", "Kennzahl", "Jahr", [2025] * 3, "direkt", "Kabeldaten."),
        ("Verluste bei Volllast", "Kennzahl", "%", [round(x["loss_full_load_pct"]) for x in r],
         "berechnet", "Leiterwiderstand und Konverterverluste aus den Kabeldaten. Bei halber Last etwa halb so hoch. "
         "Nicht in € bewertet: im Modell über den Wirkungsgrad erfasst."),
        ("Tage mit halber Leistung", "Kennzahl", "Tage/Jahr", [round(x["half_power_days_per_year"]) for x in r],
         "berechnet", "Fehlerrate × Reparaturdauer je Tiefenklasse aus den Kabeldaten."),
    ]


NOT_INCLUDED = ("Nicht enthalten: Finanzierungskosten während der Bauzeit, Preissteigerung ab 2025, Netzanschluss an Land in "
                "Deutschland, Erlösausfall bei Reparaturen (Umsatz, keine Kosten).")
