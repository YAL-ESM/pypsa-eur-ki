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
sys.path.insert(0, str(d))
import capex_opex as CO  # noqa: E402
R = json.loads((d / "routes.json").read_text())
INK, INK2, MUTED, LINE, ACC, WARN, HL = "#0b0b0b", "#52514e", "#8a8880", "#e6e5e0", "#2a78d6", "#b5560f", "#eef4fc"
W, H = 13.333, 7.5
plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})


def de(x, nd=0):
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Landing chosen by role 2 (workshop/brazil/landing_location.txt); A, B, C all start there.
land = {"cost_Macau": "Macau/Guamaré (RN), gewählt", "cost_Touros": "Touros/Natal (RN)", "cost_Pecem": "Pecém (CE)",
        "cost_SaoLuis": "São Luís (MA)", "cost_Caravelas": "Caravelas (BA)"}
A, B, C = R["cost_Macau"], R["shallow"], R["minabyss"]
ABC = (A, B, C)
SHORT = R["short"]
HDR = ["A · kostenminimal", "B · geringste Maximaltiefe", "C · wenigste km > 3.000 m"]
HDR_S = ["A · günstig", "B · flach", "C · wenig Tiefsee"]
tots = [r["total_bn"] for r in ABC]
rng = lambda key, nd=0: f"{de(min(r[key] for r in ABC), nd)}–{de(max(r[key] for r in ABC), nd)}"
dpct = lambda r: de(100 * (r["total_bn"] / A["total_bn"] - 1))  # cost difference to A in %
r5 = lambda x: int(5 * round(x / 5))
P = json.loads((d / "problems.json").read_text())
N_SLIDES = 17 + len(P["slides"])
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
                     "Basis: 2 GW Bipol, 525 kV · Preisbasis 2025 · Anlandung in Brasilien: Macau/Guamaré (RN)", 13, color=INK2)
    s.save()

    # 1 key messages, conclusions and levers
    s = Slide(pdf, 2, "Kernaussagen, Folgerungen und Hebel")
    s.text(0.7, 1.35, "Kernaussagen", 17, color=ACC, weight="bold")
    s.bullets(0.7, 1.9, [
        f"Technisch nicht erprobt: Jede Route ist tiefer als 3.000 m, selbst die flachste bis ≈ {de(B['max_depth_m'])} m. "
        "Verlegt wurde bisher bis 2.150 m. [D]",
        f"Hohe Kosten: {de(min(tots),1)}–{de(max(tots),1)} Mrd. € Investition für Kabel und Konverter. [D]",
        "Hohe Verluste: Bei Volllast kommt nur ≈ ⅔ der Leistung an. [D]",
        "Lange Bauzeit: mit einem Verlegeschiff gut 6 Jahre. [D]",
    ], size=14.5, width=5.8, gap=0.25, num=True)
    s.text(7.0, 1.35, "Folgerungen und Hebel", 17, color=ACC, weight="bold")
    s.bullets(7.0, 1.9, [
        f"Anlandung Macau/Guamaré (RN) steht fest (Rolle 2). Die Routen ab dort unterscheiden sich um ≈ {dpct(C)} % in den Kosten. [D]",
        "Voraussetzung für jede Variante: ein Kabel, das für ≈ 4.500 m qualifiziert ist. [D]",
        "Verluste senken: höhere Spannung oder größerer Querschnitt [A], Teillastbetrieb [D].",
        "Bauzeit: mehrere Schiffe parallel, Bau in Abschnitten. [A]",
    ], size=14.5, width=5.8, gap=0.25)
    s.save()

    # 2 biggest risks
    s = Slide(pdf, 3, "Die größten Risiken")
    RISKS = [
        ["Tiefe über 3.000 m", "Für 3.000–6.000 m gibt es nur eine Designstudie; jede Route reicht tiefer. [D]",
         "Qualifizierung für ≈ 4.500 m; flachste Route B. [D]"],
        ["Kosten und Finanzierung", f"{de(min(tots),1)}–{de(max(tots),1)} Mrd. € Investition für Kabel und Konverter. [D]",
         "Öffentliche Förderung und Garantien prüfen; geringere Leistung oder Bau in Stufen. [A]"],
        ["Verluste", f"≈ {rng('loss_full_load_pct')} % bei Volllast, ≈ {rng('loss_half_load_pct')} % bei halber Last. [D]",
         "Höhere Spannung oder größerer Querschnitt [A]; Teillastbetrieb. [D]"],
        ["Bauzeit und Verzug", "Gut 6 Jahre mit einem Schiff; ein längerer Verzug gefährdet die Abnahme. [D] "
         "Schiffe und Fertigung sind knapp. [A]",
         "Mehrere Schiffe, Bau in Abschnitten, Kapazitäten früh sichern. [A]"],
        ["Schäden und Reparaturen", "≈ 55–60 Tage/Jahr mit halber Leistung. [D] Anker und Fischerei im Flachwasser, "
         "Hangrutschungen, Sabotage; im Bündel fallen beide Pole zugleich aus. [A]",
         "Reparaturvertrag mit reserviertem Schiff, Ersatzteile auf Lager; Pole im Flachen getrennt verlegen; Überwachung. [A]"],
        ["Genehmigung in ≈ 10 Staaten", "Eigenes Recht und Umweltprüfung je Staat; Transitstaaten haben keinen Nutzen; "
         "umstrittene Gewässer. [A]",
         "Staatsvertrag DE–BR mit Transitstaaten; Netzabzweig als Nutzen; EU-Förderstatus (PCI/PMI). [A]"],
    ]
    y = s.table(0.65, 1.3, [2.5, 5.1, 4.5], [["Risiko", "Was droht", "Gegenmaßnahme"]] + RISKS,
                size=12, bold_cells={(i, 0) for i in range(1, len(RISKS) + 1)})
    s.text(0.65, y + 0.05, "Ausführlich: Folien „Wichtigste Faktoren“ im hinteren Teil.", 11, 12, INK2)
    s.save()

    # 3 proposed routes with assessment
    s = Slide(pdf, 4, "Vorgeschlagene Routen und Bewertung")
    s.image("map_routes.png", 0.4, 1.15, 5.2, 5.8)
    y = s.table(5.75, 1.2, [1.45, 1.95, 1.95, 1.85], [
        ["[D]", *HDR],
        ["Länge", *[f"{de(r['length_km'])} km" for r in ABC]],
        ["Investition", *[f"{de(r['total_bn'],1)} Mrd. €" for r in ABC]],
        ["Max. Tiefe", *[f"{de(r['max_depth_m'])} m" for r in ABC]],
        ["> 3.000 m", *[f"{de(r['km']['abyssal'])} km" for r in ABC]],
        ["Verlust Volllast", *[f"{de(r['loss_full_load_pct'])} %" for r in ABC]],
        ["Bauzeit, 1 Schiff", *[f"{de(r['lay_days']/365,1)} Jahre" for r in ABC]],
        ["+", "am günstigsten, am kürzesten, geringste Verluste", f"am flachsten (max. {de(B['max_depth_m'])} m)",
         "am wenigsten km > 3.000 m; meidet die tiefe Biskaya"],
        ["−", f"quert die Biskaya mit fast {de(r5(A['max_depth_m']/10)*10)} m",
         f"≈ {dpct(B)} % teurer; mehr Flachwasser mit Schiffsverkehr [A]",
         f"≈ {dpct(C)} % teurer, am längsten, höchste Verluste"],
        ["Bewertung", f"Rückfalloption, wenn ≈ {de(r5(A['max_depth_m']/10)*10)} m qualifiziert werden",
         f"Vorschlag: geringste Tiefe, die qualifiziert werden muss; ≈ {dpct(B)} % teurer",
         "Alternative, wenn wenige Reparaturen in großer Tiefe wichtiger sind als Kosten"],
    ], size=9.5, hl_rows=(9,), bold_cells={(7, 0), (8, 0), (9, 0), (9, 2)})
    s.text(5.75, y, f"2 GW Bipol, 525 kV, ab Macau/Guamaré (RN). Verworfen: kürzeste Route, {de(SHORT['length_km'])} km, "
                    f"{de(SHORT['total_bn'],1)} Mrd. €, {de(SHORT['km']['abyssal'])} km > 3.000 m. [D]", 9.5, 7.4, INK2)
    s.save()

    # 3b cost breakdown and corridor (rounded aggregates only, no supplier prices)
    s = Slide(pdf, None, "Woher die Kosten kommen und wie unsicher sie sind (2 GW)")
    s.text(0.65, 1.25, "Anteile an der Investition, gerundet [D]", 12.5, 6, weight="bold")
    y = s.table(0.65, 1.6, [2.6, 1.15, 1.25, 1.1], [
        ["Kostenart", *HDR_S],
        ["Kabel: Lieferung", *[f"≈ {r5(r['share_pct']['supply'])} %" for r in ABC]],
        ["Reserve (in den Daten enthalten)", *[f"≈ {r5(r['share_pct']['reserve'])} %" for r in ABC]],
        ["Eingraben auf dem Schelf", *[f"≈ {r['share_pct']['burial']} %" for r in ABC]],
        ["Verlegung", *[f"≈ {r['share_pct']['lay']} %" for r in ABC]],
        ["Konverter, Muffen, Anlandung", *[f"≈ {r['share_pct']['fixed']} %" for r in ABC]],
        ["davon Abschnitte > 3.000 m", *[f"≈ {r5(r['share_pct']['abyssal'])} %" for r in ABC]],
    ], size=11, bold_cells={(i, 0) for i in range(1, 7)} | {(6, 1 + max(range(3), key=lambda i: ABC[i]['share_pct']['abyssal']))})
    s.bullets(0.65, y + 0.15, [
        "Fast alles ist Kabellieferung. Verlegung und Konverter sind kaum ein Hebel. [D]",
        "Der größte Block sind die Abschnitte über 3.000 m, für die es nur eine Designstudie gibt. [D]",
    ], size=12.5, width=6.1, gap=0.12)
    s.text(7.1, 1.25, "Kostenkorridor in Mrd. € [A, Basis D]", 12.5, 6, weight="bold")
    CORR = [(n, r["corridor_bn"][0], r, r["corridor_bn"][1]) for n, r in zip("ABC", ABC)]
    up = [100 * (hi / r["total_bn"] - 1) for _, _, r, hi in CORR]
    worst = max(range(3), key=lambda i: up[i])
    y = s.table(7.1, 1.6, [0.9, 1.15, 1.15, 1.3, 1.25],
                [["Route", "günstig", "Basis", "ungünstig", "Aufschlag"]] +
                [[n, f"≈ {lo}", de(r["total_bn"], 1), f"≈ {hi}", f"+{de(100*(hi/r['total_bn']-1))} %"] for n, lo, r, hi in CORR],
                size=11, right=(1, 2, 3, 4), bold_cells={(i, 0) for i in range(1, 4)} | {(i, 2) for i in range(1, 4)})
    y = s.table(7.1, y + 0.05, [3.55, 1.1, 1.1], [
        ["Annahme je Teil [A]", "günstig", "ungünstig"],
        ["Kabel bis 1.500 m, im Betrieb erprobt", "−10 %", "+20 %"],
        ["Kabel 1.500–3.000 m, typgeprüft", "−10 %", "+35 %"],
        ["Kabel > 3.000 m, nur Designstudie", "−15 %", "+60 %"],
        ["Konverter, Muffen, Anlandung", "−10 %", "+30 %"],
    ], size=10.5, right=(1, 2))
    y = s.text(7.1, y + 0.05, f"Ungünstiger Fall ≈ +{de(min(up))}–{de(max(up))} %, also "
                              f"{min(c[3] for c in CORR)}–{max(c[3] for c in CORR)} Mrd. €.", 11, 5.8, weight="bold")
    s.text(7.1, y, f"Route {'ABC'[worst]} trifft es relativ am stärksten, weil bei ihr der größte Anteil der Kosten "
                   f"(≈ {r5(ABC[worst]['share_pct']['abyssal'])} %) über 3.000 m liegt. [A] "
                   "Die Spanne liegt im üblichen Rahmen einer Schätzung in der Machbarkeitsphase. [A] Die Reserve von ≈ 15 % "
                   "ist schon in der Basis enthalten. [D] Nicht enthalten: Finanzierungskosten während der Bauzeit, Preissteigerung ab 2025, "
                   "Netzanschluss an Land in Deutschland. [D]", 10, 5.8, INK2)
    s.save()

    # 3c repairs (rounded annual aggregates only)
    s = Slide(pdf, None, "Reparaturen: wie oft und was sie kosten (2 GW)")
    REP = [(r, r["repair_mio"], de(40 * r["repair_mio"] / 1000, 1)) for r in ABC]
    y = s.table(0.65, 1.35, [2.5, 1.35, 1.35, 1.35], [
        ["[D]", *HDR_S],
        ["Fehler pro Jahr", *[de(r["faults_per_year"], 1) for r, *_ in REP]],
        ["Fehler in 40 Jahren", *[f"≈ {de(40*r['faults_per_year'])}" for r, *_ in REP]],
        ["Tage/Jahr mit halber Leistung", *[f"≈ {de(r['half_power_days_per_year'])}" for r, *_ in REP]],
        ["Reparatureinsätze", *[f"≈ {a} Mio. €/Jahr" for _, a, _c in REP]],
        ["Reparatureinsätze über 40 Jahre, nicht abgezinst", *[f"≈ {c} Mrd. €" for *_, c in REP]],
    ], size=11.5, right=(1, 2, 3))
    s.text(0.65, y + 0.05, "Gerundete Jahreswerte. Fehlerraten und Reparaturdauer je Tiefenklasse aus den Kabeldaten.", 10, 6.5, INK2)
    s.bullets(7.5, 1.4, [
        "Etwa ein Fehler pro Jahr. Pro km fällt das Kabel im Flachwasser deutlich häufiger aus als in der Tiefsee, "
        "die Reparatur in der Tiefsee dauert aber Monate statt Wochen. [D]",
        "Die Reparaturen selbst sind ein kleiner Posten. Gewichtiger ist der Strom, der bei halber Leistung fehlt; "
        "dieser Erlösausfall ist hier nicht in € bewertet. [A]",
        "Nicht enthalten: laufende Wartung, Ersatzkabel auf Lager, ein reserviertes Reparaturschiff. [D] "
        "Fallen im Bündel beide Pole aus (z. B. Anker), steht die ganze Leistung still. [A]",
    ], size=13, width=5.3, gap=0.2)
    s.save()

    # 3d CAPEX / OPEX with provenance
    s = Slide(pdf, None, "CAPEX und OPEX der drei Routen (2 GW, Preisbasis 2025)")
    HK = {"direkt": "direkt aus den Daten", "berechnet": "aus den Daten berechnet", "berechnet + Annahme": "berechnet, mit Annahme"}
    fmt = lambda v, u: de(v, 1) if u == "Mrd. €" else (str(v) if u == "Jahr" else de(v))
    CR = CO.rows(d)
    y = s.table(0.5, 1.25, [4.1, 0.95, 1.2, 1.4, 1.2, 1.35, 2.1],
                [["Posten", "Art", *HDR_S, "Einheit", "Herkunft"]] +
                [[n, a, *[fmt(v, u) for v in vals], u, HK[hk]] for n, a, u, vals, hk, _ in CR],
                size=10.5, right=(2, 3, 4), hl_rows=(4,),
                bold_cells={(1, k) for k in range(5)} | {(4, k) for k in range(5)})
    s.bullets(0.55, y + 0.1, [
        "Herkunft: direkt = steht so in den Daten; berechnet = mit den Daten gerechnet; mit Annahme = zusätzlich eine "
        "eigene Annahme nötig.",
        "Reparaturen: Fehlerrate und Kosten je Einsatz stammen aus den Kabeldaten. Annahme: Ersatzkabel auf Lager und ein "
        "reserviertes Reparaturschiff kosten nichts extra, weil die Daten dafür nichts angeben.",
        "Verluste nicht in €: Im Modell stecken sie im Wirkungsgrad, sonst wären sie doppelt gezählt.",
        CO.NOT_INCLUDED + " Alle Werte gerundet, Excel: capex_opex.xlsx.",
    ], size=10.5, width=12.2, gap=0.06)
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
                                      "≈ 55–60 Tage/Jahr mit halber Leistung. [D]"],
        ["Bauzeit", "Je tiefer, desto langsamer wird verlegt; dazu kommen Wetterausfall und Muffen auf See. "
                    "Das sind ≈ 2.250–2.400 Verlegetage je nach Route, mit einem Schiff also gut 6 Jahre. [D]"],
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
        f"Bei {rng('length_km')} km sind das ≈ {rng('loss_full_load_pct')} % bei Volllast und ≈ {rng('loss_half_load_pct')} % bei halber Last. [D]",
        "Halbe Leistung ergibt halben relativen Verlust. [D] Ein größerer Leiterquerschnitt senkt den Widerstand. [A]",
        "Höhere Spannung, z. B. 800 statt 525 kV, ergäbe ≈ 43 % der Verluste. [A]",
    ], size=17, width=11.8, gap=0.25)
    s.text(1.05, y - 0.1, "Dafür gibt es keine Kabeldaten, das ist eine Annahme.", 15, 11, WARN)
    s.save()

    # 6b capacity other than 2 GW
    s = Slide(pdf, None, "Mehr oder weniger als 2 GW: Was ändert sich?")
    s.bullets(0.7, 1.45, [
        "2 GW gilt für das ganze System: ein Bipol aus zwei Kabeln mit je ≈ 1 GW. Fällt ein Kabel aus, bleibt halbe Leistung. [D]",
        "Kostendaten gibt es nur für dieses eine Design. Wie sich die Kosten mit der Leistung ändern, ist aus den Daten "
        "nicht ablesbar. [D]",
        "Das Kabel macht ≈ 95 % der Kosten aus [D]. Sein Preis hängt vor allem vom Leiterquerschnitt ab, also vom Strom. [A]",
        "PyPSA-Eur rechnet linear in MW (HVDC submarine: 3.220 €/MW/km, DEA 2025). Bei 2 GW liegt das in derselben "
        "Größenordnung wie unsere Daten. [D] Wählt das Modell die Leistung selbst, unterstellt es eine Skalierung, "
        "die für dieses Kabel nicht belegt ist. [A]",
    ], size=13.5, width=5.6, gap=0.2)
    y = s.table(6.9, 1.4, [1.9, 4.2], [
        ["Leistung", "Kosten und Verluste"],
        ["Weniger, z. B. 1 GW", "Dünnere Kabel, also billiger, aber kaum halb so teuer: Isolierung, Armierung, Verlegung und "
                                "Muffen bleiben. Verluste in % bei passendem Querschnitt etwa gleich. [A]"],
        ["2 GW-Kabel, halb ausgelastet", f"Investition gleich, Verluste ≈ {rng('loss_half_load_pct')} statt ≈ {rng('loss_full_load_pct')} %. [D]"],
        ["Mehr, z. B. 3–4 GW", "Bei 525 kV sind die Querschnitte schon nahe am Maximum; schwerere Kabel sind in der Tiefsee "
                               "kritisch. [A] Wege: höhere Spannung (keine Kabeldaten) oder ein zweiter Bipol, ≈ doppelte "
                               "Kabelkosten, also annähernd linear. [A]"],
    ], size=11.5, bold_cells={(1, 0), (2, 0), (3, 0)})
    s.text(6.9, y + 0.15, "Nächster Schritt: Angebote für andere Leistungen anfragen, z. B. 1 GW und 640 kV, "
                          "bevor das Modell die Leistung frei wählt. [A]", 11.5, 6.1, WARN)
    s.save()

    # 8 depth profiles
    s = Slide(pdf, 8, "Tiefenprofile")
    s.image("depth_profiles.png", 0.65, 1.2, 12, 5.1)
    s.text(0.65, 6.45, "Die tiefsten Abschnitte: das Becken zwischen Brasilien und Afrika (bis ≈ 4.600 m) und die Biskaya "
                      "(≈ 4.900 m). B quert die Biskaya weiter östlich bei ≈ 4.600 m, C bleibt dort auf dem französischen "
                      "Schelf und nutzt vor Brasilien flachere Rücken. [D]", 11, 12, INK2)
    s.save()

    # 10 landing point
    s = Slide(pdf, 10, "Anlandepunkt in Brasilien: Macau/Guamaré (RN)")
    s.text(0.65, 1.4, "Vergleich: kostenminimaler Weg je Anlandepunkt bis in die Deutsche Bucht [D]:", 13, 5.9, INK2)
    y = s.table(0.65, 2.2, [1.6, 1.15, 1.35, 1.1, 1.0],
                [["Anlandung", "Länge", "Investition", "max. Tiefe", "> 3.000 m"]] +
                [[n, f"{de(R[k]['length_km'])} km", f"{de(R[k]['total_bn'],1)} Mrd. €", f"{de(R[k]['max_depth_m'])} m",
                  f"{de(R[k]['km']['abyssal'])} km"] for k, n in land.items()],
                size=11.5, right=(1, 2, 3, 4))
    M, T, Cv = R["cost_Macau"], R["cost_Touros"], R["cost_Caravelas"]
    s.text(0.65, y + 0.1, f"Macau kostet ≈ {de(M['total_bn']-T['total_bn'],1)} Mrd. € mehr als Touros/Natal (< 1 %). "
                          f"Die frühere Wahl in Südbahia (Caravelas) wäre ≈ {de(Cv['total_bn']-M['total_bn'])} Mrd. € teurer "
                          f"und ≈ {de(r5((Cv['length_km']-M['length_km'])/10)*10)} km länger. [D]", 11.5, 6.2, INK2)
    s.text(7.3, 1.4, "Warum Macau/Guamaré (Rolle 2):", 14, 5.5, weight="bold")
    s.bullets(7.3, 1.95, [
        "Nordküste von Rio Grande do Norte, der Teil Brasiliens, der Afrika am nächsten liegt. [D]",
        "Anlagen im Umkreis von 150 km liefern in jeder Stunde von 2013 mindestens 2 GW: 8,7 GW Photovoltaik, "
        "3,5 GW Wind an Land, Batterie 3,2 GW / 30 GWh. [D]",
        "Erzeugung ≈ 76 €/MWh frei Kabel, gerechnet mit europäischen Kosten für 2035. [D]",
        "Netz: Anschluss des Konverters an das Netz im Nordosten noch prüfen. [A]",
    ], size=13.5, width=5.5, gap=0.15)
    s.text(7.3, 6.6, "Quelle: workshop/brazil/landing_location.txt (Rolle 2).", 10, 5.5, INK2)
    s.save()

    # 12 method
    s = Slide(pdf, 12, "Methode, Quellen und Grenzen")
    s.bullets(0.7, 1.45, [
        "Kabeldaten: workshop/inputs/cable_system_design.yaml (Preisbasis 2025, EUR).",
        "Bathymetrie: GEBCO 2025, Atlantik-Korridor 30″; für die Routensuche auf 0,05° gemittelt.",
        "Anlandung Brasilien: Macau/Guamaré (RN), Rolle 2 (workshop/brazil/landing_location.txt).",
        "Routenwahl: kürzester Weg (Dijkstra), Kosten je km nach Tiefenklasse; Variante B mit Tiefengrenze ≈ 4.580 m; "
        "Variante C zählt Strecken über 3.000 m vierfach.",
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
