"""Render the slide deck as a 16:9 PDF with matplotlib only (no browser needed).

Usage: python make_slides_pdf.py <cable-route dir>
Content mirrors make_slides.py (HTML version).
"""
import json
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

d = Path(sys.argv[1])
R = json.loads((d / "routes.json").read_text())
INK, INK2, MUTED, LINE, ACC, WARN, HL = "#0b0b0b", "#52514e", "#8a8880", "#e6e5e0", "#2a78d6", "#b5560f", "#eef4fc"
W, H = 13.333, 7.5
plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})


def de(x, nd=0):
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


land = {"cost_Touros": "Touros/Natal", "cost_Pecem": "Pecém", "cost_SaoLuis": "São Luís"}
tots = [R[k]["total_bn"] for k in land]
A, B, C = R["cost_Touros"], R["shallow"], R["cost_Pecem"]
budget = 31.4
P = json.loads((d / "problems.json").read_text())
N_SLIDES = 14 + len(P["slides"])
LEGEND = ("[D] = aus den Workshop-Daten oder daraus berechnet   ·   "
          "[A] = allgemeines Fachwissen, nicht durch die Daten im Repo belegt")


class Slide:
    count = 0

    def __init__(self, pdf, n=None, title=None):  # n ignored, slides are numbered in order
        Slide.count += 1
        self.pdf, self.n = pdf, Slide.count
        n = self.n
        self.fig = plt.figure(figsize=(W, H))
        self.fig.patch.set_facecolor("#fcfcfb")
        self.ax = self.fig.add_axes([0, 0, 1, 1]); self.ax.axis("off")
        self.ax.set_xlim(0, W); self.ax.set_ylim(H, 0)  # inches, y downwards
        if title:
            self.ax.text(0.65, 0.55, title, fontsize=24, fontweight="bold", color=INK, va="top")
            self.ax.text(0.5, H - 0.2, LEGEND, fontsize=9, color=MUTED, va="bottom")
        self.ax.text(W - 0.3, H - 0.2, f"{n} / {N_SLIDES}", fontsize=9, color=MUTED, ha="right", va="bottom")

    def text(self, x, y, s, size=14, width=None, color=INK, weight="normal", lh=1.45):
        """Wrapped text block; returns y below it. width in inches."""
        cpi = 72 / (size * 0.55)  # rough characters per inch
        lines = []
        for para in s.split("\n"):
            lines += textwrap.wrap(para, int(width * cpi)) if width else [para]
        for ln in lines:
            self.ax.text(x, y, ln, fontsize=size, color=color, fontweight=weight, va="top")
            y += size / 72 * lh
        return y

    def bullets(self, x, y, items, size=15, width=11.5, gap=0.12, num=False):
        for k, it in enumerate(items):
            sub = isinstance(it, list)
            if sub:
                for s in it:
                    self.ax.text(x + 0.35, y, "–", fontsize=size - 1, color=INK2, va="top")
                    y = self.text(x + 0.6, y, s, size - 1, width - 0.6, INK2) + gap / 2
                continue
            self.ax.text(x, y, f"{k + 1}." if num else "•", fontsize=size, color=ACC, va="top", fontweight="bold")
            y = self.text(x + 0.35, y, it, size, width - 0.35) + gap
        return y

    def table(self, x, y, colw, rows, size=11.5, header=True, hl_rows=(), bold_cells=(), right=()):
        cpi = 72 / (size * 0.55)
        for r, row in enumerate(rows):
            bold = lambda r_, c_: (header and r_ == 0) or (r_, c_) in bold_cells
            cells = [textwrap.wrap(str(c), max(4, int((w - 0.2) * cpi * (0.85 if bold(r, k) else 1)))) or [""]
                     for k, (c, w) in enumerate(zip(row, colw))]
            h = max(len(c) for c in cells) * size / 72 * 1.4 + 0.16
            if r in hl_rows:
                self.ax.add_patch(plt.Rectangle((x, y), sum(colw), h, color=HL, lw=0))
            cx = x
            for c, (lines, w) in enumerate(zip(cells, colw)):
                isr = c in right and not (header and r == 0)
                for i, ln in enumerate(lines):
                    self.ax.text(cx + (w - 0.1 if isr else 0.1), y + 0.08 + i * size / 72 * 1.4, ln, fontsize=size,
                                 va="top", ha="right" if isr else "left",
                                 color=INK2 if (header and r == 0) else INK,
                                 fontweight="bold" if (header and r == 0) or (r, c) in bold_cells else "normal")
                cx += w
            y += h
            self.ax.plot([x, x + sum(colw)], [y, y], color=INK2 if (header and r == 0) else LINE,
                         lw=1.5 if (header and r == 0) else 0.7)
        return y + 0.1

    def image(self, name, x, y, w, h):
        im = mpimg.imread(d / name)
        ih, iw = im.shape[:2]
        s = min(w / iw, h / ih); pw, ph = iw * s, ih * s
        x0 = x + (w - pw) / 2
        a = self.fig.add_axes([x0 / W, 1 - (y + ph) / H, pw / W, ph / H]); a.imshow(im); a.axis("off")
        return y + ph

    def save(self):
        self.pdf.savefig(self.fig)
        if len(sys.argv) > 2:  # optional preview dir
            self.fig.savefig(Path(sys.argv[2]) / f"slide_{self.n:02d}.png", dpi=60)
        plt.close(self.fig)


with PdfPages(d / "slides.pdf") as pdf:
    # 1 title
    s = Slide(pdf, 1)
    s.ax.add_patch(plt.Rectangle((0, 0), 0.15, H, color=ACC, lw=0))
    s.ax.text(0.9, 2.6, "HVDC-Kabel Brasilien – Deutschland", fontsize=36, fontweight="bold", color=INK, va="top")
    s.ax.text(0.9, 3.5, "Route, Kosten und technische Machbarkeit", fontsize=20, color=INK2, va="top")
    s.text(0.9, 4.6, "Rolle 1 · Kabel-Techno-Ökonomie · Stand 27.11.2026\n"
                     "Basis: 2 GW Bipol, 525 kV · Preisbasis 2025 · Anlandepunkt in Brasilien noch offen", 13, color=INK2)
    s.save()

    # 2 key messages
    s = Slide(pdf, 2, "Kernaussagen")
    s.bullets(0.7, 1.6, [
        "Technisch nicht erprobt: Kein Seeweg bleibt unter 3.000 m. Das bestmögliche Maximum liegt bei ≈ 4.430 m, "
        "verlegt wurde bisher bis 2.150 m. [D]",
        f"Zu teuer: {de(min(tots),1)}–{de(max(tots),1)} Mrd. € je nach Anlandepunkt, das ist das "
        f"{de(min(tots)/budget,1)}–{de(max(tots)/budget,1)}-Fache der Budgetgrenze von {de(budget,1)} Mrd. €. [D]",
        "Hohe Verluste: Bei Volllast kommt nur etwa ⅔ der Leistung an (≈ 35 % Verlust). [D]",
        "Die Route ist nicht der Hebel: Die Varianten unterscheiden sich um wenige Prozent. [D] "
        "Entscheidend sind Spannung, Leistung und Tiefenqualifikation. [A]",
    ], size=18, width=11.8, gap=0.3, num=True)
    s.save()

    # implementation factors (problems.json)
    for ps in P["slides"]:
        s = Slide(pdf, None, ps["title"])
        y = s.table(0.5, 1.2, [2.3, 5.25, 4.75], [["Problem", "Warum ist das ein Problem?", "Mögliche Lösung"]] + ps["rows"],
                    size=9.6, bold_cells={(i, 0) for i in range(1, len(ps["rows"]) + 1)})
        s.save()

    # 3 bathymetry
    s = Slide(pdf, 3, "Datengrundlage: Tiefe des Atlantiks")
    y = s.image("map_gebco_2025_atlantic_30s.png", 0.65, 1.25, 12, 5.05)
    s.text(0.65, 6.4, "GEBCO 2025, 30″. Die Linien bei 500 / 1.500 / 3.000 m sind die Grenzen der Kostenklassen. "
                       "Der Mittelatlantische Rücken und die Inseln sind flacher, die Becken dazwischen 4.000–6.000 m tief. [D]",
           11, 12, INK2)
    s.save()

    # 4 feasibility
    s = Slide(pdf, 4, "Was die technische Machbarkeit bestimmt")
    s.table(0.65, 1.4, [2.6, 9.4], [
        ["Faktor", "Zusammenhang"],
        ["Wassertiefe", "Wichtigster Faktor. Verlegt wurde bis 2.150 m, typgeprüft bis 3.000 m; für 3.000–6.000 m gibt es "
                        "nur eine Designstudie. [D] Die Zugkraft beim Verlegen ≈ Gewicht im Wasser × Tiefe [A]: ~80 t heute, "
                        "~150 t pro Kabel bei 6.000 m. Dafür braucht es eine leichtere Armierung, die nicht erprobt ist. [D]"],
        ["Reparatur & Verfügbarkeit", "Ein Fehler legt einen Pol still, es bleibt halbe Leistung. Die Reparatur dauert je nach "
                                      "Tiefe Wochen (Schelf) bis mehrere Monate (Tiefsee). Ergebnis: ≈ 0,8–0,9 Fehler/Jahr und "
                                      "≈ 55 Tage/Jahr mit halber Leistung. [D]"],
        ["Bauzeit", "Je tiefer, desto langsamer wird verlegt; dazu kommen Wetterausfall und Muffen auf See. "
                    "Das sind ≈ 2.250–2.350 Verlegetage je nach Route, mit einem Schiff also gut 6 Jahre. [D]"],
        ["Nicht in den Daten", "Schiffsverkehr, bestehende Kabel und Schutzgebiete außerhalb Brasiliens. [D] Die Route quert die "
                               "Meereszonen von ≈ 10 Staaten, das ist auch eine politische Frage. [A]"],
    ], size=13, bold_cells={(i, 0) for i in range(1, 5)})
    s.save()

    # 5 cost
    s = Slide(pdf, 5, "Was die Kosten bestimmt")
    y = s.table(0.65, 1.4, [2.9, 3.0], [
        ["Tiefenklasse [D]", "Kosten je km Route, relativ"],
        ["Schelf 0–500 m", "×1,2"],
        ["Hang 500–1.500 m", "×1,0"],
        ["Tiefsee 1.500–3.000 m", "×1,25"],
        ["Abyssal > 3.000 m", "×1,9"],
    ], size=13, hl_rows=(2,), right=(1,), bold_cells={(4, 1)})
    s.text(0.65, y + 0.1, "Zwei Kabel inklusive Lieferung, Verlegung, Eingraben und Reserve. [D]", 11, 5.9, INK2)
    s.bullets(7.0, 1.45, [
        "Der Schelf ist teurer als der Hang, weil das Kabel eingegraben werden muss. [D]",
        "Für Abschnitte über 3.000 m kommen einmalige Kosten für die Qualifizierung hinzu. [D]",
        "Fixkosten: 2 Konverter, die Muffen auf See und 2 Anlandungen. [D]",
        "Faustregel: Die Kosten hängen fast nur von der Länge und dem Anteil der Abschnitte über 3.000 m ab. "
        "Das Kabel macht ≈ 95 % aus. [D]",
    ], size=14, width=5.8, gap=0.2)
    s.save()

    # 6 losses
    s = Slide(pdf, 6, "Was die Netzverluste bestimmt")
    s.ax.add_patch(plt.Rectangle((0.65, 1.4), 12, 0.65, color="#f1f1ef", lw=0))
    s.ax.text(0.85, 1.72, "Verlust ∝ Länge × Leiterwiderstand × Strom²   →   relativer Verlust ∝ Länge × Leistung / Spannung²   [A]",
              fontsize=16, va="center", color=INK)
    y = s.bullets(0.7, 2.5, [
        "Bei 2 GW und 525 kV: ≈ 4 % pro 1.000 km (Kupfer auf dem Schelf: 3,1 %), dazu 1,7 % in den Konvertern. [D]",
        "Bei ≈ 8.500–9.100 km sind das ≈ 34–36 % bei Volllast und ≈ 18–19 % bei halber Last. [D]",
        "Halbe Leistung ergibt halben relativen Verlust. [D] Ein größerer Leiterquerschnitt senkt den Widerstand. [A]",
        "Höhere Spannung, z. B. 800 statt 525 kV, ergäbe ≈ 43 % der Verluste. [A]",
    ], size=17, width=11.8, gap=0.25)
    s.text(1.05, y - 0.1, "Dafür gibt es keine Kabeldaten, das ist eine Annahme.", 15, 11, WARN)
    s.save()

    # 7 route map
    s = Slide(pdf, 7, "Drei Beispielrouten")
    s.image("map_routes.png", 0.5, 1.2, 6.2, 5.75)
    y = s.text(7.0, 1.6, "Berechnet als kostengünstigster Weg über ein Raster mit 0,05° Auflösung, gewichtet mit den "
                         "Kosten pro km der Tiefenklasse. [D]", 14, 5.8, INK2)
    y = s.text(7.0, y + 0.3, "Alle Routen führen an Westafrika und Portugal entlang und durch den Ärmelkanal. "
                             "Der afrikanische Kontinentalhang ist der günstigste Abschnitt. [D]", 14, 5.8, INK2)
    s.text(7.0, y + 0.3, "Die brasilianischen Anlandepunkte sind Beispiele, die Auswahl ist noch offen.", 14, 5.8, WARN, "bold")
    s.save()

    # 8 depth profiles
    s = Slide(pdf, 8, "Tiefenprofile")
    s.image("depth_profiles.png", 0.65, 1.2, 12, 5.1)
    s.text(0.65, 6.45, "Die tiefsten Abschnitte: das Becken zwischen Brasilien und Afrika (4.000–6.000 m) und die Biskaya "
                      "(≈ 4.900 m). Route B umgeht die Biskaya über die spanische Küste. [D]", 11, 12, INK2)
    s.save()

    # 9 comparison
    s = Slide(pdf, 9, "Routenvergleich")
    f = lambda r, k: de(r[k])
    y = s.table(0.65, 1.35, [2.7, 3.1, 3.1, 3.1], [
        ["[D] berechnet", "A · Touros, kostenminimal", "B · Touros, geringste Tiefe", "C · Pecém, kürzeste"],
        ["Länge", f"{f(A,'length_km')} km", f"{f(B,'length_km')} km", f"{f(C,'length_km')} km"],
        ["Investition", f"{de(A['total_bn'],1)} Mrd. €", f"{de(B['total_bn'],1)} Mrd. €", f"{de(C['total_bn'],1)} Mrd. €"],
        ["Maximale Tiefe", f"{f(A,'max_depth_m')} m", f"{f(B,'max_depth_m')} m", f"{f(C,'max_depth_m')} m"],
        ["Strecke tiefer als 3.000 m", f"{de(A['km']['abyssal'])} km", f"{de(B['km']['abyssal'])} km", f"{de(C['km']['abyssal'])} km"],
        ["Verlust Voll- / Halblast", *[f"{de(r['loss_full_load_pct'])} / {de(r['loss_half_load_pct'])} %" for r in (A, B, C)]],
        ["+ Vorteile", "am günstigsten, kürzeste Tiefseequerung nach Afrika", "umgeht die Biskaya, technisch am wenigsten extrem",
         "am kürzesten, geringste Verluste"],
        ["− Nachteile", "quert die Biskaya mit fast 4.900 m", "am längsten [D], mehr Schelfstrecke mit Schiffsverkehr und Fischerei [A]",
         "am tiefsten (5.900 m), fast 3.000 km auf freier Tiefsee"],
    ], size=12.5, bold_cells={(2, 1), (3, 2), (4, 2), (5, 3), (6, 0), (7, 0)})
    s.text(0.65, y + 0.1, f"Die Unterschiede in den Kosten liegen bei ≈ 2 %. Alle Varianten liegen über dem Doppelten der "
                          f"Budgetgrenze von {de(budget,1)} Mrd. €. [D]", 12, 12, INK2)
    s.save()

    # 10 landing point
    s = Slide(pdf, 10, "Anlandepunkt in Brasilien: noch offen")
    s.text(0.65, 1.4, "Kostenminimaler Weg je Anlandepunkt bis in die Deutsche Bucht [D]:", 13, 5.9, INK2)
    y = s.table(0.65, 2.2, [1.6, 1.15, 1.35, 1.1, 1.0],
                [["Anlandung", "Länge", "Investition", "max. Tiefe", "> 3.000 m"]] +
                [[n, f"{de(R[k]['length_km'])} km", f"{de(R[k]['total_bn'],1)} Mrd. €", f"{de(R[k]['max_depth_m'])} m",
                  f"{de(R[k]['km']['abyssal'])} km"] for k, n in land.items()],
                size=11.5, right=(1, 2, 3, 4))
    s.text(0.65, y + 0.1, f"Die Bandbreite beträgt ≈ {de(max(tots)-min(tots))} Mrd. € ({de(100*(max(tots)/min(tots)-1))} %). "
                          "Der Anlandepunkt verändert die Machbarkeit stärker als die Kosten. [D]", 11.5, 6.2, INK2)
    s.text(7.3, 1.4, "Kriterien für die Auswahl (gemeinsam mit Rolle 2):", 14, 5.5, weight="bold")
    s.bullets(7.3, 1.95, [
        "Nähe zu Afrika: Die Ostspitze bei Natal/Touros hat die kürzeste und flachste Tiefseequerung. [D]",
        "Nähe zur Erzeugung: Wind- und Solarstandorte in CE und RN (Shortlist). [D]",
        "Hafen & Logistik: Pecém, Natal (Shortlist). [D]",
        "Netz: Anschluss an das Netz im Nordosten für den Konverter. [A]",
        "Küste: Schutzgebiete und Schiffsverkehr (Daten liegen vor). [D]",
    ], size=13.5, width=5.5, gap=0.15)
    s.save()

    # 11 conclusions
    s = Slide(pdf, 11, "Folgerungen und Hebel")
    s.bullets(0.7, 1.5, [
        "Die Route ist weitgehend festgelegt (Westafrika → Iberien → Ärmelkanal); dort ist kaum etwas zu holen. [D]",
        "Machbarkeit erfordert ein Kabel, das für ≈ 4.500 m qualifiziert ist. Das ist die Voraussetzung für jede Variante. [D]",
        "Wirtschaftlichkeit: Die Verluste von ≈ ⅓ wiegen schwerer als die Wahl der Route. [D] Mögliche Hebel:",
        ["höhere Spannung oder größerer Querschnitt (Annahme, keine Daten) [A]",
         "geringere Leistung bzw. Teillastbetrieb [D]",
         "Teilstrecke über Land durch Afrika und Europa (nicht untersucht) [A]"],
        "Um die Budgetgrenze zu erreichen, müssten die Kosten pro km um mehr als die Hälfte sinken. [D]",
    ], size=17, width=11.8, gap=0.25)
    s.save()

    # 12 method
    s = Slide(pdf, 12, "Methode, Quellen und Grenzen")
    s.bullets(0.7, 1.45, [
        "Kabeldaten: workshop/inputs/cable_system_design.yaml (Preisbasis 2025, EUR).",
        "Budget: workshop/inputs/financing_term_sheet.md (Obergrenze 31,4 Mrd. €).",
        "Bathymetrie: GEBCO 2025, Atlantik-Korridor 30″; für die Routensuche auf 0,05° gemittelt.",
        "Routenwahl: kürzester Weg (Dijkstra), Kosten je km nach Tiefenklasse; Variante B mit Tiefengrenze ≈ 4.580 m.",
        "Verluste: Gleichstromwiderstand bei maximaler Temperatur, Nennstrom 1.905 A, Konverter je 0,86 %.",
        "Grenzen: grobes Raster, in Küstennähe ungenau; keine Daten zu Schiffsverkehr, Kabeln und Schutzgebieten "
        "außerhalb Brasiliens; Anlandung in Deutschland pauschal in der Deutschen Bucht; Kapitalkosten noch nicht annualisiert.",
        "Kennzeichnung: [D] steht für Zahlen und Aussagen aus den Dateien oben oder daraus berechnet; [A] für allgemeines "
        "Fachwissen ohne Beleg im Repo, vor Verwendung prüfen.",
        "Skripte: workshop/cable-route/ (grid.py, routes.py, plot_maps.py, make_slides.py, make_slides_pdf.py, problems.json).",
    ], size=14, width=11.8, gap=0.18)
    s.save()

    # 13-14 appendix
    for n, (t, f_) in enumerate([("Anhang: Küste Nordost-Brasilien", "map_brazil_northeast.png"),
                                 ("Anhang: Nordsee", "map_europe_northsea.png")], start=13):
        s = Slide(pdf, n, t)
        s.image(f_, 0.65, 1.2, 12, 5.7)
        s.save()

print("->", d / "slides.pdf")
