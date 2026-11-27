# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Slide "Studiendesign und Annahmen" (role 4) for the combined deck.

Content from workshop/economics/project_analysis.txt; look of the main deck (workshop/brazil/slides.py):
Libre Franklin, bold title top left, flat tables with a thin rule under the header, grey note at the bottom.
Writes workshop/economics/assumptions_slide.pdf and puts it into workshop/slides/combined_slides.pdf
after the title page (replaces an earlier copy of this slide, so the script can be run again).

    ~/.venvs/slides/bin/python workshop/economics/assumptions_slide.py
"""

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "workshop/plotstyle").is_dir())
OUT = ROOT / "workshop/economics/assumptions_slide.pdf"
DECK = ROOT / "workshop/slides/combined_slides.pdf"
POSITION = 2  # page number of the slide in the combined deck
for f in (ROOT / "workshop/plotstyle/fonts").glob("*.ttf"):
    font_manager.fontManager.addfont(str(f))
FONT = "Libre Franklin"
TEXT, LABEL, FAINT = "#222222", "#444444", "#aaaaaa"
W, H, M = 13.333, 7.5, 0.5  # inches, as the main deck

OUTLINE = "Studiendesign und Annahmen"  # bookmark in the combined PDF
TITLE = "Studiendesign: Kosten-Nutzen-Analyse eines festen 2-GW-Kabels"

DESIGN = [
    ("Studientyp", "Kosten-Nutzen-Analyse eines gegebenen Kabels:", "fest 2 GW, kein Zubau, nur Einsatz"),
    ("Vergleich", "System mit Kabel gegen System ohne Kabel,", "sonst identisch"),
    ("Deutsches System", "DE mit FR, NL, PL, DK, AT, CH: 17 Knoten,", "3-h-Auflösung, 2025–2050"),
    ("2050", "CO2-Null-Grenze gelockert, 2050 bleibt", "Zieljahr; Ergebnisse mit 2050 markiert"),
    ("Kabel", "2 GW Bipol, 525 kV, 40 Jahre, Bauzeit 6–7 J.;", "Anlandung DE-Knoten 08 (Norden)"),
    ("Brasilien", "reiner Exportstandort Macau/Guamaré (RN):", "kein Bedarf, kein Netz; Wetterjahr 2013"),
    ("Preisbasis", "EUR, real 2025, für DE, Brasilien und Kabel", ""),
    ("Diskontierung", "Kapitalwert mit 2 % real (Band 1–3 %);", "Annuitäten im Modell mit 7 %"),
]

CABLE_HEAD = ("Route", "Länge", "CAPEX", "Verluste", "Annuität")
CABLE_UNIT = ("", "km", "Mrd. €", "Volllast", "Mrd. €/a")
CABLE_ROWS = [
    ("A  kostengünstig", "8.956", "68,6", "36,0 %", "5,45"),
    ("B  flach", "9.139", "69,7", "36,4 %", "5,53"),
    ("C  min. Tiefsee", "9.710", "71,9", "38,6 %", "5,71"),
]

BR_HEAD = ("Anlage", "Leistung", "€/kW/a")
BR_ROWS = [
    ("Photovoltaik", "8,7 GW", "58,3"),
    ("Wind an Land", "3,5 GW", "135,6"),
    ("Batterie, Speicher", "30 GWh", "22,4 ¹"),
    ("Batterie, Umrichter", "3,2 GW", "41,7"),
]

NOTE = (
    "Kabel-Annuität mit 7 % über 40 Jahre, inkl. Betrieb und 38 Mio. €/a Anbindung des Anlandepunkts; ohne "
    "Bauzeitzinsen, Preissteigerung nach 2025 und Netzanschluss an Land in DE. Im Modell: Wirkungsgrad aus den "
    "Volllastverlusten, Verfügbarkeit aus 55–59 Reparaturtagen/a mit halber Leistung. Brasilien: europäische "
    "Kostendaten als Platzhalter, Anbindung noch auf Basis 2035.   ¹ €/kWh/a"
)


def t(ax, x, y, s, size=13, bold=False, color=TEXT, ha="left", va="top"):
    ax.text(x, H - y, s, fontsize=size, fontweight="bold" if bold else "normal", color=color, family=FONT,
            ha=ha, va=va)


def rule(ax, x0, x1, y):
    ax.plot([x0, x1], [H - y, H - y], color=TEXT, lw=0.75, solid_capstyle="butt")


def table(ax, x, y, cols, head, rows, unit=None, rh=0.38):
    """cols: right edges (or left edge for column 0) in inches; first column left-aligned, the rest right."""
    def row(vals, yy, bold=False, color=TEXT, size=13):
        for j, v in enumerate(vals):
            t(ax, cols[j], yy, v, size=size, bold=bold, color=color, ha="left" if j == 0 else "right", va="center")

    row(head, y + rh / 2, bold=True, color=LABEL, size=12)
    if unit:
        y += rh * 0.6
        row(unit, y + rh / 2, color=LABEL, size=11)
    y += rh
    rule(ax, cols[0] - 0.06, cols[-1] + 0.06, y)
    for r in rows:
        row(r, y + rh / 2)
        y += rh
    return y


def build():
    fig = plt.figure(figsize=(W, H), layout="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    t(ax, M + 0.1, 0.4, TITLE, size=26, bold=True)

    # left: study design as label / text pairs
    x0, top = M + 0.1, 1.25
    t(ax, x0, top, "Aufbau der Studie", size=14, bold=True)
    y = top + 0.55
    for label, l1, l2 in DESIGN:
        t(ax, x0, y, label, size=13, bold=True)
        t(ax, x0 + 1.85, y, l1, size=13)
        if l2:
            t(ax, x0 + 1.85, y + 0.25, l2, size=13)
        y += 0.6 if l2 else 0.42

    # right: consolidated costs
    xr = 7.25
    t(ax, xr, top, "Kabel: drei Routen, Macau/Guamaré – DE-Knoten 08", size=14, bold=True)
    y = table(ax, xr, top + 0.4, [xr + 0.06, 9.75, 10.85, 11.85, 12.75], CABLE_HEAD, CABLE_ROWS, CABLE_UNIT)

    y += 0.35
    t(ax, xr, y, "Brasilien: stetige 2 GW ins Kabel (Variante A)", size=14, bold=True)
    table(ax, xr, y + 0.4, [xr + 0.06, 11.0, 12.75], BR_HEAD, BR_ROWS)

    # grey note at the bottom, wrapped by hand to the slide width
    prop = font_manager.FontProperties(family=FONT, size=10)
    words, lines, cur = NOTE.split(" "), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if TextPath((0, 0), trial, prop=prop).get_extents().width / 72 > W - 2 * M - 0.2:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    yn = H - 0.3 - 0.2 * len(lines)
    for i, line in enumerate(lines):
        t(ax, M + 0.1, yn + i * 0.2, line, size=10, color=FAINT)
    return fig


def main():
    fig = build()
    fig.savefig(OUT)
    fig.savefig(OUT.with_suffix(".png"), dpi=110)
    plt.close(fig)

    deck = PdfWriter(clone_from=DECK)
    # remember the (flat) outline by page object, so it survives removing and inserting pages
    marks = []
    for o in deck.outline:
        if isinstance(o, list) or o.title == OUTLINE:
            continue
        i = deck.get_destination_page_number(o)
        if i is not None:
            marks.append((o.title, deck.pages[i].indirect_reference))
    # drop an earlier copy of this slide
    for i in reversed(range(len(deck.pages))):
        if TITLE.split(":")[0] in (deck.pages[i].extract_text() or "")[:200] and "Aufbau der Studie" in (
            deck.pages[i].extract_text() or ""
        ):
            deck.remove_page(i)
    slide = PdfReader(OUT).pages[0]
    deck.insert_page(slide, POSITION - 1)
    refs = [p.indirect_reference for p in deck.pages]
    marks = [(t_, refs.index(ref)) for t_, ref in marks if ref in refs] + [(OUTLINE, POSITION - 1)]
    del deck._root_object["/Outlines"]
    for t_, i in sorted(marks, key=lambda m: m[1]):
        deck.add_outline_item(title=t_, page_number=i)
    with open(DECK, "wb") as f:
        deck.write(f)
    print(f"{OUT}\n{DECK}: slide at page {POSITION}, {len(deck.pages)} pages")


if __name__ == "__main__":
    main()
