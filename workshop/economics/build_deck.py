# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: CC0-1.0
"""Build the role 4 discussion deck: project economics, decisions to make.

A multi-page PDF, one slide per figure, drawn with the workshop plot style so it
fits the group's final presentation.

    pixi run python workshop/economics/build_deck.py
"""

import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workshop/plotstyle"))
import studystyle as st  # noqa: E402

st.use()

PAGE = (13.333, 7.5)  # 16:9
OUT = Path(__file__).with_name("economics_decisions.pdf")
KICKER = "Role 4 · Project economics · Brazilian–German HVDC interconnector"


def text_slide(pdf, title, bullets, kicker=KICKER, x=0.06, y=0.80, width=88, ax=None):
    """A text slide. If `ax` is given, text fills the left 54% and the axes sits on the right."""
    fig = plt.figure(figsize=PAGE, layout="none")
    fig.text(x, 0.93, title, fontsize=25, fontweight="bold", color=st.TEXT, va="top")
    if kicker:
        fig.text(x, 0.875, kicker, fontsize=11.5, color=st.TEXT, va="top", alpha=0.75)
    fig.lines.append(plt.Line2D([x, x + (0.49 if ax else 0.94)], [0.855, 0.855],
                                color=st.FAINT, lw=0.8, transform=fig.transFigure))
    wrap = width if ax is None else round(width * 0.54)
    cy = y
    for b in bullets:
        if isinstance(b, tuple):  # (text, emphasis) - emphasis rendered bold/ink
            b, bold = b
        else:
            bold = False
        lines = textwrap.wrap(b, wrap) or [""]
        fig.text(x + 0.012, cy + 0.012, "▪", fontsize=11, color=st.GROUPS["Brazil cable"], va="top")
        fig.text(x + 0.032, cy, "\n".join(lines), fontsize=14.5,
                 color=st.TEXT if bold else "#333333", fontweight="bold" if bold else "normal",
                 va="top", linespacing=1.35)
        cy -= 0.052 * len(lines) + 0.035
        if cy < 0.07:
            break
    if ax is not None:
        ax.set_position([0.57, 0.12, 0.38, 0.68])
    pdf.savefig(fig)
    plt.close(fig)


def price_and_cap_axes(fig):
    """Two panels: price peaks (EUR/MWh) and the cap's add-on (EUR/t) in 2040-2050."""
    years = [2040, 2045, 2050]
    price = [1427, 430, 2957]
    cap = [43, 488, 24341]

    ax1 = fig.add_axes([0.60, 0.56, 0.35, 0.24])
    ax2 = fig.add_axes([0.60, 0.17, 0.35, 0.24])
    for ax in (ax1, ax2):
        ax.grid(axis="y", color=st.GRID, lw=0.5, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(length=0, labelsize=9, labelcolor=st.TICK)

    st.bars(ax1, years, price, color=st.NEUTRAL)
    ax1.set_title("Highest electricity price, EUR/MWh", loc="left", fontsize=10.5)
    ax1.set_xticks(years, [str(y) for y in years])

    st.bars(ax2, years, cap, color=st.GROUPS["Brazil cable"])
    ax2.set_title("CO$_2$ cap's price add-on, EUR/t", loc="left", fontsize=10.5)
    ax2.set_xticks(years, [str(y) for y in years])


def build():
    with PdfPages(OUT) as pdf:
        # 1 - title
        fig = plt.figure(figsize=PAGE, layout="none")
        fig.text(0.06, 0.66, "Project economics:", fontsize=40, fontweight="bold", color=st.TEXT, va="top")
        fig.text(0.06, 0.55, "the decisions we need to make", fontsize=40, fontweight="bold",
                 color=st.GROUPS["Brazil cable"], va="top")
        fig.text(0.06, 0.40, "Decisions made, and what is still open", fontsize=18, color="#333333", va="top")
        fig.text(0.06, 0.16, "PyPSA x AI workshop · Brazilian–German interconnector",
                 fontsize=12, color=st.FAINT, va="top")
        pdf.savefig(fig)
        plt.close(fig)

        # 2 - what role 4 owns
        text_slide(pdf, "What role 4 owns", [
            "The study design: what is compared with what, and in which years.",
            "Harmonised economics: discount rate, cost year, currency, lifetimes — one set for Germany, Brazil and the cable.",
            "The scenarios: with and without the cable, plus the sensitivities that matter.",
            "The results: one postprocessing pipeline over every run — system cost, cable flows, prices, emissions, and who gains and who loses.",
            "We work in config files and postprocessing, not in model code.",
        ])

        # 3 - overview of decisions
        text_slide(pdf, "The decisions we are working through", [
            ("A · Study type — decided: cost-benefit analysis, no capacity expansion.", True),
            ("B · Which years? Which five-year steps, and how does 2050 enter the result?", True),
            ("C · Harmonised economic parameters?", True),
            ("D · Which scenarios and sensitivities fit in the day?", True),
            ("E · What does 'value' mean, and who gains?", True),
            "The next slides take them one at a time; the last one lists what we need from each role and what to decide today.",
        ])

        # 4 - settled decisions
        text_slide(pdf, "Settled so far", [
            ("Study type: a cost-benefit analysis — no capacity expansion.", True),
            ("Base year: 2025.", True),
            ("Currency: EUR throughout.", True),
            ("German landing node: 08 (North).", True),
            ("Cable construction time: 6–7 years.", True),
            ("Discount rate: one convention, applied to Germany, Brazil and the cable alike.", True),
            "The rest of the deck works from these.",
        ])

        # 5 - study type
        text_slide(pdf, "A · Study type — decided", [
            ("Decided: a cost-benefit analysis, not capacity expansion.", True),
            "We fix the cable — role 1's size — and compare the system with it against the system without it.",
            "Capacity expansion (letting the model choose whether and how much to build) is out of scope.",
            "The counterfactual is the no-cable island baseline; more German renewables and storage, or imports from elsewhere, are sensitivities.",
        ])

        # 6 - horizon and 2050
        fig = plt.figure(figsize=PAGE, layout="none")
        fig.text(0.06, 0.93, "B · Which years, and how to handle 2050",
                 fontsize=25, fontweight="bold", color=st.TEXT, va="top")
        fig.text(0.06, 0.875, KICKER, fontsize=11.5, color=st.TEXT, va="top", alpha=0.75)
        fig.lines.append(plt.Line2D([0.06, 0.55], [0.855, 0.855], color=st.FAINT, lw=0.8,
                                    transform=fig.transFigure))
        bullets = [
            "Base year is 2025. The baseline runs 2025–2050 in 5-year myopic steps; 2025 is today's fleet, dispatch only.",
            "The CO₂ cap falls to zero in 2050. There it adds about 24,000 €/t on top of the CO₂ price and prices peak near 3,000 €/MWh.",
            "Against that, any clean power looks enormous — the cable included. A result that rests on 2050 says more about the cap than about the cable.",
            "Options: make 2030–2045 the headline and keep 2050 as a stress case; or soften the 2050 cap (a model-side choice for role 3).",
            ("Decide together with role 3; this changes how every other number reads.", True),
        ]
        cy = 0.80
        for b in bullets:
            bold = isinstance(b, tuple)
            if bold:
                b = b[0]
            lines = textwrap.wrap(b, 60) or [""]
            fig.text(0.072, cy + 0.012, "▪", fontsize=11, color=st.GROUPS["Brazil cable"], va="top")
            fig.text(0.092, cy, "\n".join(lines), fontsize=13,
                     color=st.TEXT if bold else "#333333", fontweight="bold" if bold else "normal",
                     va="top", linespacing=1.32)
            cy -= 0.047 * len(lines) + 0.028
            if cy < 0.06:
                break
        price_and_cap_axes(fig)
        pdf.savefig(fig)
        plt.close(fig)

        # 7 - harmonised economics
        text_slide(pdf, "C · Harmonised economic parameters", [
            ("Decided: one discount-rate convention for Germany, Brazil and the cable alike — not asset-specific costs of capital.", True),
            "Currency is always EUR, on a single 2025 base year, for every role and asset.",
            "The baseline offered a 2% social rate and a 7% technology rate; we settle on one and use it everywhere.",
            "The model turns investment cost into an annual cost from a lifetime and a discount rate — role 1's cable costs must match it.",
            "Cable construction takes 6–7 years (interest during construction, first operational year); cable and converters are designed for 40 years.",
        ])

        # 8 - scenarios
        text_slide(pdf, "D · Scenarios and sensitivities", [
            "Fixed by the decisions: German landing node 08 (North); the cable size is role 1's; base year 2025 and one discount rate.",
            "Core pair: with the cable versus without it. The two runs differ in one thing only.",
            "No run may overwrite another: each scenario is a config layered on the baseline with its own run name (and its own inputs).",
            "Sensitivities: cable size; Brazilian region and technology; the discount-rate value; the 2050 treatment; Brazil as export-only site versus integrated with its grid.",
            "Time budget: all six horizons take about 20 minutes. Role 3 knows what can be varied from config and how long a run takes.",
        ])

        # 8 - value and pipeline
        text_slide(pdf, "E · What 'value' means, and the results pipeline", [
            "Metrics: total system cost, cable utilisation and flows, prices, emissions — and the distribution: Germany versus Brazil versus the cable company and its customer.",
            "Build the results pipeline on the baseline first, before any cable run exists.",
            "One postprocessing over every run produces the figures for the final presentation.",
            "Report what the result depends on, and where it does not hold — that is part of the result.",
        ])

        # 10 - asks
        text_slide(pdf, "What we need, and what is still open", [
            ("From role 1: cable CAPEX, FOM and VOM as ranges, in the model's cost convention, for a 6–7 year build.", True),
            ("From role 2: Brazilian generation cost and hourly profiles, in EUR, comparable with the German ones.", True),
            ("From role 3: which assumptions are config-tunable, run time per scenario, and a view on the 2050 cap.", True),
            ("Still to settle: the value of the single discount rate; the headline years and the 2050 treatment; the first with/without scenario pair.", True),
        ])

    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
