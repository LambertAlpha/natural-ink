"""Vector rendering for source layouts and portable ink documents."""

from __future__ import annotations

import io
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

from .fonts import font_bank
from .math_ink import rule_stroke, symbol_strokes
from .model import InkDocument, InkPage, Layout, RuleItem, Stroke, SymbolItem, TextItem
from .randomness import rng_for


def draw_stroke(canvas: Canvas, stroke: Stroke, height: float) -> None:
    canvas.setStrokeColor(HexColor(stroke.color))
    canvas.setFillColor(HexColor(stroke.color))
    canvas.setLineCap(1)
    canvas.setLineJoin(1)
    if len(stroke.points) == 1:
        p = stroke.points[0]
        canvas.circle(p.x, height - p.y, p.width / 2, stroke=0, fill=1)
    for a, b in zip(stroke.points, stroke.points[1:], strict=False):
        canvas.setLineWidth((a.width + b.width) / 2)
        canvas.line(a.x, height - a.y, b.x, height - b.y)


def background_pdf(width: float, height: float, color: str) -> bytes:
    buffer = io.BytesIO()
    c = Canvas(buffer, pagesize=(width, height), invariant=1)
    c.setFillColor(HexColor(color))
    c.rect(0, 0, width, height, stroke=0, fill=1)
    c.save()
    return buffer.getvalue()


def render_layout(layout: Layout, output: Path, seed: int = 183, variation: float = 0.4) -> None:
    if not math.isfinite(variation) or not 0 <= variation <= 1:
        raise ValueError("variation must be between 0 and 1")
    output.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with TemporaryDirectory(prefix="natural-ink-fonts-") as temporary:
        names = font_bank(Path(temporary), seed, variation)
        c = Canvas(buffer, invariant=1, pageCompression=1)
        c.setTitle(layout.title)
        c.setAuthor("Natural Ink")
        for pi, page in enumerate(layout.pages):
            c.setPageSize((page.width, page.height))
            c.setFillColor(HexColor(page.background))
            c.rect(0, 0, page.width, page.height, stroke=0, fill=1)
            if page.grid:
                c.setStrokeColor(HexColor("#e2e2d9"))
                c.setLineWidth(0.3)
                for grid_x in range(0, math.ceil(page.width), 18):
                    c.line(grid_x, 0, grid_x, page.height)
                for grid_y in range(0, math.ceil(page.height), 18):
                    c.line(0, grid_y, page.width, grid_y)
            for ii, item in enumerate(page.items):
                rng = rng_for(seed, "item", pi, ii)
                if isinstance(item, TextItem):
                    x = item.x
                    for ci, character in enumerate(item.text):
                        rng = rng_for(seed, "letter", pi, ii, ci)
                        name = names[rng.randrange(len(names))]
                        if ord(character) not in pdfmetrics.getFont(name).face.charWidths:
                            raise ValueError(
                                f"Caveat cannot render {character!r}; use a supported symbol item"
                            )
                        size = item.size * (1 + variation * rng.uniform(-0.1, 0.1))
                        advance = pdfmetrics.stringWidth(character, name, size)
                        if (
                            x < 0
                            or x + advance + size * 0.15 > page.width
                            or not size < item.y < page.height - size * 0.3
                        ):
                            raise ValueError(
                                f"Text item {ii} overflows page {pi + 1}; split it into shorter lines"
                            )
                        c.saveState()
                        c.setFillColor(HexColor(item.color))
                        c.translate(
                            x, page.height - item.y + variation * rng.uniform(-0.025, 0.025) * size
                        )
                        c.rotate(variation * rng.uniform(-4.5, 4.5))
                        c.setFont(name, size)
                        c.drawString(0, 0, character)
                        c.restoreState()
                        x += advance * (1 + variation * rng.uniform(-0.025, 0.035))
                else:
                    if isinstance(item, SymbolItem):
                        strokes = symbol_strokes(
                            item.symbol, item.x, item.y, item.width, item.height, item.color, rng
                        )
                    elif isinstance(item, RuleItem):
                        strokes = [
                            rule_stroke(item.x, item.y, item.length, item.width, item.color, rng)
                        ]
                    InkPage(width=page.width, height=page.height, strokes=strokes)
                    for stroke in strokes:
                        draw_stroke(c, stroke, page.height)
            c.showPage()
        c.save()
    output.write_bytes(buffer.getvalue())


def render_ink_pdf(document: InkDocument, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(output), invariant=1, pageCompression=1)
    c.setTitle(document.title)
    for page in document.pages:
        c.setPageSize((page.width, page.height))
        c.setFillColor(HexColor(page.background))
        c.rect(0, 0, page.width, page.height, stroke=0, fill=1)
        for stroke in page.strokes:
            draw_stroke(c, stroke, page.height)
        c.showPage()
    c.save()


def page_svg(page: InkPage, title: str = "Natural Ink") -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {page.width} {page.height}">',
        f"<title>{escape(title)}</title>",
        f'<rect width="100%" height="100%" fill="{page.background}"/>',
    ]
    for stroke in page.strokes:
        if len(stroke.points) == 1:
            p = stroke.points[0]
            parts.append(f'<circle cx="{p.x}" cy="{p.y}" r="{p.width / 2}" fill="{stroke.color}"/>')
        for a, b in zip(stroke.points, stroke.points[1:], strict=False):
            parts.append(
                f'<path d="M {a.x:.4f} {a.y:.4f} L {b.x:.4f} {b.y:.4f}" stroke="{stroke.color}" stroke-width="{(a.width + b.width) / 2:.4f}" stroke-linecap="round"/>'
            )
    return "\n".join([*parts, "</svg>"])
