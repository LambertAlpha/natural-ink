"""Caveat alternates plus smooth, bounded contour deformation (OFL derivatives)."""

from __future__ import annotations

import hashlib
import math
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.varLib.instancer import instantiateVariableFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as PdfFont

from .randomness import rng_for


def font_bank(directory: Path, seed: int, strength: float, count: int = 24) -> list[str]:
    """Make renamed, embedded derivatives. No shared on-disk cache or hidden seed."""
    master = TTFont(str(files("natural_ink").joinpath("assets/Caveat.ttf")))
    instantiateVariableFont(master, {"wght": 400}, inplace=True)
    directory.mkdir(parents=True, exist_ok=True)
    token = hashlib.sha256(f"{seed}:{strength!r}:{count}".encode()).hexdigest()[:12]
    names: list[str] = []
    for variant in range(count):
        font = deepcopy(master)
        skeleton = variant % 3
        available = set(font.getGlyphOrder())
        for table in font["cmap"].tables:
            if table.isUnicode():
                for code, glyph in list(table.cmap.items()):
                    alternate = f"{glyph}.ss0{skeleton}"
                    if skeleton and alternate in available:
                        table.cmap[code] = alternate
        for glyph_name in set(font.getBestCmap().values()):
            glyph = font["glyf"][glyph_name]
            if glyph.isComposite() or glyph.numberOfContours <= 0:
                continue
            rng = rng_for(seed, "outline", variant, glyph_name)
            coords, _, _ = glyph.getCoordinates(font["glyf"])
            xs, ys = zip(*coords, strict=True)
            mid = (min(xs) + max(xs)) / 2
            height, width = max(max(ys) - min(ys), 200), max(max(xs) - min(xs), 150)
            sx, sy = rng.uniform(-0.21, 0.22), rng.uniform(-0.12, 0.14)
            shear, bow = rng.uniform(-0.17, 0.13), rng.uniform(-29, 29)
            curl, phase = rng.uniform(-22, 22), rng.uniform(-math.pi, math.pi)
            result = []
            for x, y in coords:
                v, u = (y - min(ys)) / height, (x - mid) / width
                dx = x * sx + shear * y + bow * math.sin(v * math.pi * 1.25 + phase)
                dy = y * sy + curl * math.sin(u * math.pi * 1.25 + phase)
                result.append((round(x + strength * dx), round(y + strength * dy)))
            glyph.coordinates = GlyphCoordinates(result)
            glyph.recalcBounds(font["glyf"])
            advance, _ = font["hmtx"][glyph_name]
            font["hmtx"][glyph_name] = (round(advance * (1 + strength * sx)), glyph.xMin)
        name = f"NaturalInk{token}V{variant}"
        for record in font["name"].names:
            if record.nameID in (1, 3, 4, 6):
                record.string = name.encode(record.getEncoding())
            elif record.nameID == 2:
                record.string = "Regular".encode(record.getEncoding())
        target = directory / f"{name}.ttf"
        font.recalcTimestamp = False
        font.save(target)
        pdfmetrics.registerFont(PdfFont(name, str(target)))
        names.append(name)
        font.close()
    master.close()
    return names
