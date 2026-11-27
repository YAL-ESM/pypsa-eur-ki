# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
Append a slide with a figure to the role-2 deck (16:9, workshop plot style).

The deck is created with a title slide on first use; after that slides are only appended, so edits
made in PowerPoint stay. Close the file in PowerPoint before running this.

    ~/.venvs/slides/bin/python workshop/brazil/slides.py results/brazil/eligible_area.png \
        --title "A third of Brazil's land is open to wind and solar" \
        --bullet "3.2 million km2 of land ..." --bullet "..." --note "Source: ..."

A chapter opener (big title, subtitle, nothing else) goes in at a given slide position (1 = first):

    ~/.venvs/slides/bin/python workshop/brazil/slides.py --chapter "Role 2: Brazil renewable potential" \
        --subtitle "Where in Brazil ..." --position 2

Needs only python-pptx (kept outside the pixi environment: uv venv ~/.venvs/slides;
uv pip install --python ~/.venvs/slides/bin/python python-pptx).
"""

import argparse
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "workshop/plotstyle").is_dir())
DECK = ROOT / "workshop/slides/brazil_renewables.pptx"

FONT = "Libre Franklin"  # falls back to the system sans if not installed
TEXT, LABEL, FAINT = RGBColor(0x22, 0x22, 0x22), RGBColor(0x44, 0x44, 0x44), RGBColor(0xAA, 0xAA, 0xAA)
W, H, M = 13.333, 7.5, 0.5  # slide width, height, margin (inches)
BLANK = 6  # layout index of the blank layout in the default template


def text(slide, x, y, w, h, lines, size, color, bold=False, bullets=False):
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {line}" if bullets else line
        p.space_after = Pt(size * 0.8) if bullets else Pt(0)
        for r in p.runs:
            r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), bold, color
    return tf


def new_deck(title, subtitle):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    s = prs.slides.add_slide(prs.slide_layouts[BLANK])
    text(s, M + 0.3, 2.6, W - 2 * M, 1.2, [title], 36, TEXT, bold=True)
    text(s, M + 0.3, 3.8, W - 2 * M, 1.0, [subtitle], 18, LABEL)
    return prs


def add_chapter(prs, title, subtitle=None, position=None):
    """Chapter opener: same look as the title slide, with an orange-red rule (the cable colour)."""
    s = prs.slides.add_slide(prs.slide_layouts[BLANK])
    bar = s.shapes.add_shape(1, Inches(M + 0.3), Inches(2.35), Inches(1.2), Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = RGBColor(0xD5, 0x5E, 0x00)
    bar.line.fill.background()
    text(s, M + 0.3, 2.6, W - 2 * M, 1.2, [title], 36, TEXT, bold=True)
    if subtitle:
        text(s, M + 0.3, 3.8, W - 2 * M, 1.0, [subtitle], 18, LABEL)
    if position:  # python-pptx appends; move the new slide to the requested place
        ids = prs.slides._sldIdLst
        el = ids[-1]
        ids.remove(el)
        ids.insert(position - 1, el)
    return s


def add_figure(prs, image, title, bullets=(), note=None):
    s = prs.slides.add_slide(prs.slide_layouts[BLANK])
    text(s, M, 0.35, W - 2 * M, 0.8, [title], 26, TEXT, bold=True)
    top, bottom = 1.25, H - (0.55 if note else 0.3)
    # figure on the left (whole width without bullets), scaled to fit and keep its aspect ratio
    box_w = (W - 2 * M) * (0.55 if bullets else 1.0)
    iw, ih = Image.open(image).size
    scale = min(box_w / iw, (bottom - top) / ih)
    pic_w = iw * scale
    s.shapes.add_picture(str(image), Inches(M), Inches(top), Inches(pic_w), Inches(ih * scale))
    if bullets:
        x = M + pic_w + 0.4
        text(s, x, top + 0.4, W - M - x, bottom - top - 0.4, bullets, 16, TEXT, bullets=True)
    if note:
        text(s, M, H - 0.5, W - 2 * M, 0.35, [note], 10, FAINT)
    return s


def add_figure_table(prs, image, title, table_csv, note=None, bold_rows=(), caption=None):
    """Figure on the left, a table from a CSV on the right (flat, no frame, thin rules; bold rows for totals)."""
    import csv

    from pptx.enum.text import PP_ALIGN
    from pptx.oxml.ns import qn

    s = prs.slides.add_slide(prs.slide_layouts[BLANK])
    text(s, M, 0.35, W - 2 * M, 0.8, [title], 26, TEXT, bold=True)
    top, bottom = 1.25, H - (0.55 if note else 0.3)
    iw, ih = Image.open(image).size
    scale = min((W - 2 * M) * 0.45 / iw, (bottom - top) / ih)
    pic_w = iw * scale
    s.shapes.add_picture(str(image), Inches(M), Inches(top), Inches(pic_w), Inches(ih * scale))

    rows = list(csv.reader(open(table_csv, encoding="utf8")))
    x = M + pic_w + 0.4
    tw = W - M - x
    widths = [0.36, 0.22, 0.13, 0.15, 0.14]
    y0 = top + 0.3
    if caption:
        text(s, x, top, tw, 0.35, [caption], 14, TEXT, bold=True)
        y0 = top + 0.5
    rh = 0.42
    shape = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y0), Inches(tw), Inches(rh * len(rows)))
    tbl = shape.table
    # plain table: drop the template style and its banding
    tblPr = shape._element.graphic.graphicData.tbl.tblPr
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
    style = tblPr.find(qn("a:tableStyleId"))
    if style is not None:
        style.text = "{5940675A-B579-460E-94D1-54222C63F5DA}"  # "No Style, Table Grid"
    for j, wfrac in enumerate(widths[:len(rows[0])]):
        tbl.columns[j].width = Inches(tw * wfrac)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(rh)
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.background()
            cell.margin_left = cell.margin_right = Inches(0.06)
            tf = cell.text_frame
            tf.text = val
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.RIGHT
            for r in p.runs:
                r.font.name, r.font.size = FONT, Pt(13 if i else 12)
                r.font.bold = i == 0 or val and row[0] in bold_rows
                r.font.color.rgb = LABEL if i == 0 else TEXT
            # thin rule under the header and above the total rows, nothing else
            tcPr = cell._tc.get_or_add_tcPr()
            for side in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
                ln = tcPr.find(qn(side))
                if ln is not None:
                    tcPr.remove(ln)
            for k, (side, on) in enumerate((("a:lnL", False), ("a:lnR", False),
                             ("a:lnT", i > 0 and row[0] in bold_rows and rows[i - 1][0] not in bold_rows),
                             ("a:lnB", i == 0))):
                ln = tcPr.makeelement(qn(side), {"w": "9525" if on else "0"})
                if on:
                    fill = ln.makeelement(qn("a:solidFill"), {})
                    clr = fill.makeelement(qn("a:srgbClr"), {"val": "222222"})
                    fill.append(clr)
                    ln.append(fill)
                else:
                    ln.append(ln.makeelement(qn("a:noFill"), {}))
                tcPr.insert(k, ln)
    if note:
        text(s, M, H - 0.5, W - 2 * M, 0.35, [note], 10, FAINT)
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", type=Path, nargs="?")
    ap.add_argument("--title")
    ap.add_argument("--chapter", help="add a chapter opener with this title instead of a figure slide")
    ap.add_argument("--subtitle", help="chapter opener: line under the title")
    ap.add_argument("--position", type=int, help="chapter opener: slide number to insert at (default: end)")
    ap.add_argument("--bullet", action="append", default=[], help="repeat for several")
    ap.add_argument("--note", help="small grey line at the bottom, e.g. sources")
    ap.add_argument("--table", type=Path, help="CSV shown as a table right of the figure (instead of bullets)")
    ap.add_argument("--caption", help="table: bold line above it")
    ap.add_argument("--bold-row", action="append", default=[], help="table: first-column value of a total row")
    ap.add_argument("--deck", type=Path, default=DECK)
    a = ap.parse_args()

    if a.deck.exists():
        prs = Presentation(a.deck)
    else:
        a.deck.parent.mkdir(parents=True, exist_ok=True)
        prs = new_deck("Renewable potential in Brazil",
                       "Role 2 · PyPSA-Eur workshop: an HVDC cable from Brazil to Germany")
    if a.chapter:
        add_chapter(prs, a.chapter, a.subtitle, a.position)
    elif a.image and a.title and a.table:
        add_figure_table(prs, a.image, a.title, a.table, a.note, a.bold_row, a.caption)
    elif a.image and a.title:
        add_figure(prs, a.image, a.title, a.bullet, a.note)
    else:
        ap.error("give an image and --title, or --chapter")
    prs.save(a.deck)
    print(f"{a.deck}: {len(prs.slides)} slides")


if __name__ == "__main__":
    main()
