# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Slide "Ergebnis" (role 4): project economics from role 3's model results, for the combined deck.

Inputs (nothing is typed in by hand):
  workshop/trade/cable2050_comparison.csv   role 3: system cost with/without the cable, 2050
  workshop/cable-route/skripte/routes.json  role 1: route A CAPEX, FOM, repairs; capex_opex.py: lifetime

The model annualises the cable at its own 7 %. The study rate (2 %, band 1-3 %) is applied here, on the
results: the cable is re-annualised at 1, 2 and 3 % while the system benefit from the model is kept as it is.

Writes workshop/economics/results_slide.pdf and project_economics.csv, and puts the slide into
workshop/slides/combined_slides.pdf in front of the appendix (replaces an earlier copy, so the script can be
run again; run it again after combine_slides.py, which rebuilds the deck from its sources).

    ~/.venvs/slides/bin/python workshop/economics/results_slide.py
"""

import csv
import importlib.util
import json
import logging
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.text import Text  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "workshop/plotstyle").is_dir())
sys.path.insert(0, str(ROOT / "workshop/plotstyle"))
import studystyle as st  # noqa: E402

OUT = ROOT / "workshop/economics/results_slide.pdf"
CSV_OUT = ROOT / "workshop/economics/project_economics.csv"
DECK = ROOT / "workshop/slides/combined_slides.pdf"
MODEL_CSV = ROOT / "workshop/trade/cable2050_comparison.csv"
ROUTES = ROOT / "workshop/cable-route/skripte/routes.json"
CAPEX_OPEX = ROOT / "workshop/cable-route/skripte/capex_opex.py"
ROUTE = "cost_Macau"  # route A, the cheapest; role 3's cable cost (5.35 bn/yr) is 7.8 % of its CAPEX
CASE, EARLIER = "de10-trade-cable-fast", "de10-trade-cable2050"
FONT = "Libre Franklin"
TEXT, LABEL, FAINT = "#222222", "#444444", "#aaaaaa"
W, H, M = 13.333, 7.5, 0.5  # inches, as the main deck
OUTLINE = "Ergebnis: Wirtschaftlichkeit"
BEFORE = "Anhang"  # the slide goes in front of this chapter
RATES = (0.01, 0.02, 0.03)
BUILD_YEARS = 7  # role 1: 6-7 years
MODEL_RATE = 0.07


def de(x, nd=0):
    """German number format with a real minus sign."""
    s = f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s.replace("-", "\u2212")


def annuity(rate, years):
    return rate / (1 - (1 + rate) ** -years)


def load_inputs():
    rows = {r["metric"]: r for r in csv.DictReader(open(MODEL_CSV))}
    m = {k: float(v[CASE]) for k, v in rows.items() if k != "metric"}
    earlier_net = float(rows["net_benefit"][EARLIER])
    route = json.loads(ROUTES.read_text())[ROUTE]
    spec = importlib.util.spec_from_file_location("capex_opex", CAPEX_OPEX)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return m, earlier_net, route, mod.LIFE


def economics():
    m, earlier_net, route, life = load_inputs()
    capex = route["total_bn"]
    opex = (route["fom_mio"] + route["repair_mio"]) / 1e3  # bn EUR/yr
    gross = m["gross_benefit_before_cable_cost"]
    deliv = m["cable_delivery_to_germany"]  # TWh/yr
    out = {"m": m, "earlier_net": earlier_net, "capex": capex, "opex": opex, "life": life}

    def rate_row(r):
        cost = capex * annuity(r, life) + opex
        be = gross / (annuity(r, life) + opex / capex)
        pv_capex = sum(capex / BUILD_YEARS / (1 + r) ** k for k in range(1, BUILD_YEARS + 1))
        pv_ops = sum((gross - opex) / (1 + r) ** k for k in range(BUILD_YEARS + 1, BUILD_YEARS + life + 1))
        return {"rate": r, "cable_cost": cost, "net": gross - cost, "break_even": be,
                "npv": pv_ops - pv_capex, "coverage": gross / cost, "cost_per_MWh": cost / deliv * 1e3}

    out["rows"] = [rate_row(r) for r in RATES]
    model_cost = m["annual_cable_cost"]
    out["model"] = {"cable_cost": model_cost, "net": m["net_benefit"], "break_even": m["break_even_cable_investment"],
                    "coverage": gross / model_cost, "cost_per_MWh": model_cost / deliv * 1e3}
    # role 3's 5.35 bn/yr against a rebuild of route A at the model rate (a check, not a result)
    out["rebuild_7pct"] = capex * annuity(MODEL_RATE, life) + opex
    return out


def write_csv(e):
    with open(CSV_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["basis", "discount_rate", "cable_cost_bn_per_yr", "net_benefit_bn_per_yr",
                    "break_even_capex_bn", "npv_2025_bn", "benefit_covers_cost_share", "cable_cost_EUR_per_MWh"])
        mo = e["model"]
        w.writerow(["model (role 3, 2050)", MODEL_RATE, f"{mo['cable_cost']:.2f}", f"{mo['net']:.2f}",
                    f"{mo['break_even']:.2f}", "", f"{mo['coverage']:.3f}", f"{mo['cost_per_MWh']:.0f}"])
        for r in e["rows"]:
            w.writerow(["re-annualised route A (role 4)", r["rate"], f"{r['cable_cost']:.2f}", f"{r['net']:.2f}",
                        f"{r['break_even']:.2f}", f"{r['npv']:.1f}", f"{r['coverage']:.3f}", f"{r['cost_per_MWh']:.0f}"])


for f in (ROOT / "workshop/plotstyle/fonts").glob("*.ttf"):
    font_manager.fontManager.addfont(str(f))


def width_in(s, size, bold=False):
    prop = font_manager.FontProperties(family=FONT, weight="bold" if bold else "normal", size=size)
    return TextPath((0, 0), s, prop=prop).get_extents().width / 72


def wrap(s, max_w, size, bold=False):
    lines, cur = [], ""
    for word in s.split(" "):
        trial = f"{cur} {word}".strip()
        if cur and width_in(trial, size, bold) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    return lines


def t(ax, x, y, s, size=13, bold=False, color=TEXT, ha="left", va="top"):
    return ax.text(x, H - y, s, fontsize=size, fontweight="bold" if bold else "normal", color=color, family=FONT,
                   ha=ha, va=va)


def rule(ax, x0, x1, y):
    ax.plot([x0, x1], [H - y, H - y], color=TEXT, lw=0.75, solid_capstyle="butt")


def build(e):
    st.use()
    m, mo = e["m"], e["model"]
    fig = plt.figure(figsize=(W, H), layout="none")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    gross, cost, net = m["gross_benefit_before_cable_cost"], mo["cable_cost"], mo["net"]
    title = f"Ergebnis: Nutzen {de(gross, 2)} Mrd. €/a gegen Kosten von {de(cost, 2)} Mrd. €/a"
    assert width_in(title, 26, True) < W - 2 * M - 0.2, "title too wide"
    t(ax, M + 0.1, 0.4, title, size=26, bold=True)

    # left: bars, one y axis, direct labels
    x0, top = M + 0.1, 1.25
    t(ax, x0, top, "Nutzen und Kosten des Kabels, 2050, Mrd. €/a", size=14, bold=True)
    cx0, cy0, cw, ch = 0.75, 1.7, 5.75, 3.75  # chart box in inches from the top left
    cax = fig.add_axes([cx0 / W, (H - cy0 - ch) / H, cw / W, ch / H])
    vals = [gross, -cost, net]
    colors = [st.NEUTRAL, st.GROUPS["Brazil cable"], TEXT]
    cax.bar(range(3), vals, width=0.62, color=colors, linewidth=0, zorder=2)
    cax.axhline(0, color=TEXT, lw=0.8, zorder=3)
    cax.spines["bottom"].set_visible(False)
    cax.set_xticks([])
    cax.set_ylim(-6.6, 1.5)
    cax.set_xlim(-0.6, 2.6)
    cax.set_yticks([-6, -4, -2, 0])
    cax.set_yticklabels([de(v) for v in (-6, -4, -2, 0)])
    cax.tick_params(axis="y", labelsize=10)
    names = ["Nutzen im deutschen\nSystem", "Kabelkosten\n(Annuität + Betrieb)", "Netto"]
    for i, (v, name) in enumerate(zip(vals, names)):
        lab = ("+" if v > 0 else "") + de(v, 2)
        if v > 0:
            cax.annotate(lab, (i, v), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                         fontsize=11, fontweight="bold", color=TEXT)
            cax.annotate(name, (i, 0), xytext=(0, -5), textcoords="offset points", ha="center", va="top",
                         fontsize=9.5, color=LABEL)
        else:
            cax.annotate(lab, (i, v), xytext=(0, -4), textcoords="offset points", ha="center", va="top",
                         fontsize=11, fontweight="bold", color=TEXT)
            cax.annotate(name, (i, 0), xytext=(0, 5), textcoords="offset points", ha="center", va="bottom",
                         fontsize=9.5, color=LABEL)
    stats = [f"Geliefert {de(m['cable_delivery_to_germany'], 1)} TWh/a bei {de(m['cable_utilisation'])} % Auslastung, "
             f"Verluste {de(m['cable_losses'], 1)} TWh/a",
             f"Marktwert des gelieferten Stroms in DE: {de(m['delivered_electricity_market_value'])} €/MWh"]
    for k, line in enumerate(stats):
        t(ax, x0, cy0 + ch + 0.2 + k * 0.24, line, size=11, color=LABEL)

    # right: the study-rate re-calculation
    xr = 7.25
    t(ax, xr, top, "Nachrechnung mit Studienrate, Route A", size=14, bold=True)
    cols = [xr + 0.06, 9.6, 10.7, 11.85, 12.85]
    head = ("Zinssatz", "Kabelkosten", "Netto", "Break-even", "Kapitalwert")
    unit = ("real", "Mrd. €/a", "Mrd. €/a", "CAPEX, Mrd. €", "2025, Mrd. €")
    y = top + 0.45
    rh = 0.38
    for j, (h_, u_) in enumerate(zip(head, unit)):
        ha = "left" if j == 0 else "right"
        t(ax, cols[j], y, h_, size=12, bold=True, color=LABEL, ha=ha)
        t(ax, cols[j], y + 0.24, u_, size=10, color=LABEL, ha=ha)
    y += 0.58
    rule(ax, cols[0] - 0.06, cols[-1] + 0.06, y)
    table_rows = [(f"{de(100 * r['rate'])} %" + ("  (Studie)" if abs(r["rate"] - 0.02) < 1e-9 else ""),
                   de(r["cable_cost"], 2), de(r["net"], 2), de(r["break_even"], 1), de(r["npv"], 1),
                   abs(r["rate"] - 0.02) < 1e-9) for r in e["rows"]]
    # role 3's own figures at the model rate, unchanged (no net present value: the model solves one year)
    table_rows.append(("7 %  (Modell)", de(mo["cable_cost"], 2), de(mo["net"], 2), de(mo["break_even"], 1),
                       "–", False))
    for *vals_, bold_ in table_rows:
        for j, v in enumerate(vals_):
            t(ax, cols[j], y + rh / 2, v, size=13, bold=bold_, ha="left" if j == 0 else "right", va="center")
        y += rh
    rule(ax, cols[0] - 0.06, cols[-1] + 0.06, y)

    # right: three findings
    rows = e["rows"]
    cov_lo, cov_hi = mo["coverage"], rows[0]["coverage"]
    be_lo, be_hi = mo["break_even"], rows[0]["break_even"]
    pm_lo, pm_hi = rows[0]["cost_per_MWh"], mo["cost_per_MWh"]
    findings = [
        (f"Der Nutzen deckt nur {de(100 * cov_lo)}–{de(100 * cov_hi)} % der Kabelkosten.", True),
        (f"Kabelkosten je gelieferter MWh: {de(pm_lo)} € bei 1 % bis {de(pm_hi)} € im Modell (7 %), ohne "
         f"Erzeugung in Brasilien, gegen einen Marktwert von {de(m['delivered_electricity_market_value'])} €/MWh.",
         False),
        (f"Break-even-Investition: {de(be_lo)}–{de(be_hi)} Mrd. € gegen {de(e['capex'], 1)} Mrd. € für Route\u00a0A.", False),
    ]
    y += 0.4
    for s, bold in findings:
        for ln in wrap(s, W - M - xr - 0.1, 13, bold):
            t(ax, xr, y, ln, size=13, bold=bold)
            y += 0.26
        y += 0.14

    # bottom note, wrapped to the slide width
    note = (
        f"Modell: Annuitäten mit 7 %; Studienrate 2 % (Band 1–3 %): Kabel Route A (Rolle 1) neu annuitisiert, Nutzen aus "
        f"dem Modell unverändert. Kapitalwert: Investition gleichmäßig über {BUILD_YEARS} Baujahre, danach {e['life']} Jahre "
        f"Betrieb mit dem 2050-Nutzen in jedem Jahr (optimistisch: nur 2050 gerechnet, kein Mehrjahreslauf mit Kabel). "
        f"2050 mit bindender CO2-Grenze (Schattenpreis ≈ 33.000 €/t): Nutzen eher überschätzt. Offen: ob Batterie und "
        f"Anbindung in Brasilien im Nutzen enthalten sind; sonst Ergebnis schlechter. Vorläuferlauf: Netto "
        f"{de(e['earlier_net'], 2)} Mrd. €/a. Brasilien: europäische Kosten als Platzhalter."
    )
    lines = wrap(note, W - 2 * M - 0.2, 10)
    yn = H - 0.3 - 0.2 * len(lines)
    for i, line in enumerate(lines):
        t(ax, M + 0.1, yn + i * 0.2, line, size=10, color=FAINT)
    return fig


def check_layout(fig):
    """No text outside the slide, no two texts overlapping (we cannot look at the page, so measure it)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    fw, fh = fig.canvas.get_width_height()
    items = [(x, x.get_window_extent(r)) for x in fig.findobj(Text) if x.get_visible() and x.get_text().strip()]
    problems = []
    for x, b in items:
        if b.x0 < 0 or b.y0 < 0 or b.x1 > fw or b.y1 > fh:
            problems.append(f"outside: {x.get_text()[:50]!r}")
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i][1], items[j][1]
            if a.x0 < b.x1 - 1 and b.x0 < a.x1 - 1 and a.y0 < b.y1 - 1 and b.y0 < a.y1 - 1:
                problems.append(f"overlap: {items[i][0].get_text()[:35]!r} / {items[j][0].get_text()[:35]!r}")
    return len(items), problems


def insert_into_deck(slide_pdf):
    logging.disable(logging.CRITICAL)
    deck = PdfWriter(clone_from=DECK)
    marks, before_ref = [], None
    for o in deck.outline:
        if isinstance(o, list) or o.title == OUTLINE:
            continue
        i = deck.get_destination_page_number(o)
        if i is not None:
            ref = deck.pages[i].indirect_reference
            marks.append((o.title, ref))
            if o.title == BEFORE:
                before_ref = ref
    for i in reversed(range(len(deck.pages))):  # drop an earlier copy of this slide
        txt = deck.pages[i].extract_text() or ""
        if txt.startswith("Ergebnis: Nutzen") and "Nachrechnung mit Studienrate" in txt:
            if deck.pages[i].indirect_reference == before_ref:
                before_ref = None
            deck.remove_page(i)
    refs = [p.indirect_reference for p in deck.pages]
    position = refs.index(before_ref) if before_ref in refs else len(deck.pages)
    deck.insert_page(PdfReader(slide_pdf).pages[0], position)
    refs = [p.indirect_reference for p in deck.pages]
    marks = [(t_, refs.index(ref)) for t_, ref in marks if ref in refs] + [(OUTLINE, position)]
    del deck._root_object["/Outlines"]
    for t_, i in sorted(marks, key=lambda m_: m_[1]):
        deck.add_outline_item(title=t_, page_number=i)
    with open(DECK, "wb") as f:
        deck.write(f)
    return position + 1, len(deck.pages)


def main():
    e = economics()
    write_csv(e)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # a missing glyph would print a tofu box: make it an error
        fig = build(e)
        n_text, problems = check_layout(fig)
        fig.savefig(OUT)
    plt.close(fig)
    print(f"layout check: {n_text} texts, {len(problems)} problems")
    for p in problems:
        print("  ", p)
    if problems:
        sys.exit("fix the layout first; deck not touched")
    mo = e["model"]
    print(f"model (role 3):     cost {mo['cable_cost']:.2f}  net {mo['net']:.2f}  break-even {mo['break_even']:.2f}"
          f"   | rebuild of route A at 7 %: {e['rebuild_7pct']:.2f}")
    for r in e["rows"]:
        print(f"re-annualised {r['rate']:.0%}:   cost {r['cable_cost']:.2f}  net {r['net']:.2f}  "
              f"break-even {r['break_even']:.2f}  NPV {r['npv']:.1f}  covers {r['coverage']:.0%}  "
              f"{r['cost_per_MWh']:.0f} EUR/MWh")
    page, n = insert_into_deck(OUT)
    print(f"{OUT}\n{CSV_OUT}\n{DECK}: slide at page {page} of {n}")


if __name__ == "__main__":
    main()
