# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""
One PDF with the role-2 deck (Brazil renewables) and the cable-route deck.

The workspace has no LibreOffice, so the PPTX is drawn page by page with matplotlib: the decks built by
slides.py only use text boxes, pictures, one rule and simple tables, which are placed at their PPTX positions
(Libre Franklin from workshop/plotstyle/fonts). Edits made in PowerPoint with other shape types are not drawn;
the script warns about them. The cable-route PDF is appended as it is, scaled to the same page size.

    ~/.venvs/slides/bin/python workshop/brazil/combine_slides.py
    # needs python-pptx, pypdf and matplotlib in ~/.venvs/slides
"""

import io

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402
from PIL import Image  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE_TYPE  # noqa: E402
from pptx.enum.text import PP_ALIGN  # noqa: E402
from pypdf import PdfReader, PdfWriter, Transformation  # noqa: E402

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "workshop/plotstyle").is_dir())
DECK = ROOT / "workshop/slides/brazil_renewables.pptx"
CABLE = ROOT / "workshop/cable-route/folien/slides.pdf"
OUT = ROOT / "workshop/slides/combined_slides.pdf"
# combined pages 16-19 (cable-route pages 8-11): Wichtigste Faktoren 1/2 and 2/2, Datengrundlage, technische Machbarkeit
DROP_PAGES = [16, 17, 18, 19]
EMU = 914400  # per inch
for f in (ROOT / "workshop/plotstyle/fonts").glob("*.ttf"):
    font_manager.fontManager.addfont(str(f))
FONT = "Libre Franklin"


def rgb(font, default="#222222"):
    try:
        return "#" + str(font.color.rgb)
    except (AttributeError, TypeError):
        return default


def text_width(s, size, bold):
    """Width of a string in inches, measured with the real font."""
    prop = font_manager.FontProperties(family=FONT, weight="bold" if bold else "normal", size=size)
    return TextPath((0, 0), s, prop=prop).get_extents().width / 72


def wrap_measured(txt, width_in, size, bold, indent=""):
    """Greedy word wrap to a box width, measured with the font (as PowerPoint wraps)."""
    lines, cur = [], ""
    for word in txt.split(" "):
        trial = f"{cur} {word}" if cur else word
        if cur and text_width(trial, size, bold) > width_in:
            lines.append(cur)
            cur = indent + word
        else:
            cur = trial
    lines.append(cur)
    return lines


def draw_text(ax, sh, H):
    """Text box: paragraphs top-down, wrapped to the box width (approximate character width of the font)."""
    x, y, w = sh.left / EMU, sh.top / EMU, sh.width / EMU
    y_cur = y + 0.05
    for para in sh.text_frame.paragraphs:
        txt = "".join(r.text for r in para.runs)
        r0 = para.runs[0] if para.runs else None
        size = r0.font.size.pt if r0 is not None and r0.font.size else 18
        bold = bool(r0.font.bold) if r0 is not None else False
        color = rgb(r0.font) if r0 is not None else "#222222"
        if not txt.strip():
            y_cur += size / 72 * 1.2
            continue
        indent = "   " if txt.startswith("•") else ""
        lines = wrap_measured(txt, w - 0.2, size, bold, indent)
        ha = {PP_ALIGN.CENTER: "center", PP_ALIGN.RIGHT: "right"}.get(para.alignment, "left")
        xx = {"center": x + w / 2, "right": x + w}.get(ha, x + 0.1)
        for line in lines:
            ax.text(xx, H - y_cur, line, fontsize=size, fontweight="bold" if bold else "normal", color=color,
                    family=FONT, va="top", ha=ha)
            y_cur += size / 72 * 1.22
        y_cur += para.space_after.pt / 72 if para.space_after is not None else 0


def draw_table(ax, sh, H):
    tbl = sh.table
    x0, y0 = sh.left / EMU, sh.top / EMU
    widths = [c.width / EMU for c in tbl.columns]
    y = y0
    for i, row in enumerate(tbl.rows):
        h = row.height / EMU
        x = x0
        for j, cell in enumerate(row.cells):
            para = cell.text_frame.paragraphs[0]
            r0 = para.runs[0] if para.runs else None
            size = r0.font.size.pt if r0 is not None and r0.font.size else 12
            bold = bool(r0.font.bold) if r0 is not None else False
            right = para.alignment == PP_ALIGN.RIGHT
            ax.text(x + widths[j] - 0.06 if right else x + 0.06, H - (y + h / 2), cell.text, fontsize=size,
                    fontweight="bold" if bold else "normal", color=rgb(r0.font) if r0 is not None else "#222222",
                    family=FONT, va="center", ha="right" if right else "left")
            tcPr = cell._tc.tcPr
            for side, yy in (("lnT", y), ("lnB", y + h)):
                ln = tcPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}" + side) if tcPr is not None else None
                if ln is not None and ln.get("w", "0") != "0":
                    ax.plot([x, x + widths[j]], [H - yy, H - yy], color="#222222", lw=0.75)
            x += widths[j]
        y += h


def render_pptx(path):
    prs = Presentation(path)
    W, H = prs.slide_width / EMU, prs.slide_height / EMU
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        for n, slide in enumerate(prs.slides, 1):
            fig = plt.figure(figsize=(W, H))
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_xlim(0, W)
            ax.set_ylim(0, H)
            ax.axis("off")
            for sh in slide.shapes:
                x, y, w, h = (v / EMU for v in (sh.left, sh.top, sh.width, sh.height))
                if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    img = Image.open(io.BytesIO(sh.image.blob))
                    ax.imshow(img, extent=(x, x + w, H - y - h, H - y), interpolation="lanczos", zorder=1)
                elif sh.has_table if hasattr(sh, "has_table") else False:
                    draw_table(ax, sh, H)
                elif sh.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE and not sh.text_frame.text.strip():
                    try:
                        color = "#" + str(sh.fill.fore_color.rgb)
                    except (AttributeError, TypeError):
                        color = "#222222"
                    ax.add_patch(Rectangle((x, H - y - h), w, h, color=color, lw=0))
                elif sh.has_text_frame:
                    draw_text(ax, sh, H)
                else:
                    print(f"  warning: slide {n}: shape '{sh.name}' ({sh.shape_type}) not drawn")
            ax.set_aspect("auto")
            pdf.savefig(fig)
            plt.close(fig)
    buf.seek(0)
    return PdfReader(buf), (W * 72, H * 72), len(prs.slides)


def main():
    brazil, (pw, ph), n_b = render_pptx(DECK)
    cable = PdfReader(CABLE)
    out = PdfWriter()
    for page in brazil.pages:
        out.add_page(page)
    for src in cable.pages:  # scale the cable-route pages to the same page size, centred
        page = out.add_page(src)  # attach to the writer first, then transform
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        s = min(pw / w, ph / h)
        page.add_transformation(Transformation().scale(s, s).translate((pw - w * s) / 2, (ph - h * s) / 2))
        page.mediabox.lower_left, page.mediabox.upper_right = (0, 0), (pw, ph)
        page.cropbox.lower_left, page.cropbox.upper_right = (0, 0), (pw, ph)
    # pages left out of the combined deck (1-based, numbers of the combined PDF before removal)
    for i in sorted(DROP_PAGES, reverse=True):
        out.remove_page(i - 1)
    n_b_kept = n_b - sum(1 for i in DROP_PAGES if i <= n_b)
    out.add_outline_item(title="Role 2: Brazil renewable potential", page_number=0)
    out.add_outline_item(title="Cable route Brazil - Germany", page_number=n_b_kept)
    n_b, n_c = n_b_kept, len(out.pages) - n_b_kept
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "wb") as f:
        out.write(f)
    print(f"{OUT}: {n_b} + {n_c} = {n_b + n_c} pages")


if __name__ == "__main__":
    main()
