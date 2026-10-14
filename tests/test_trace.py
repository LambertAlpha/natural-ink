import numpy as np
import pymupdf

from natural_ink.trace import skeleton_paths, trace_pdf


def test_skeleton_retains_isolated_dots_and_closed_loops():
    mask = np.zeros((12, 12), dtype=bool)
    mask[1, 1] = True
    mask[4:9, 4] = mask[4:9, 8] = True
    mask[4, 4:9] = mask[8, 4:9] = True
    paths = skeleton_paths(mask)
    assert [(1, 1)] in paths
    assert any(len(p) > 8 and p[0] == p[-1] for p in paths)


def test_trace_ignores_light_grid_and_retains_purple_stroke(tmp_path):
    source = tmp_path / "source.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=100, height=100)
        page.draw_line((0, 40), (100, 40), color=(0.85, 0.85, 0.85), width=0.3)
        page.draw_line((20, 20), (70, 20), color=(0.26, 0.025, 0.48), width=2)
        # Pale purple, as seen at antialiased edges, must not become blue.
        page.draw_line((20, 21), (70, 21), color=(0.63, 0.5125, 0.74), width=0.2)
        pdf.save(source)
    doc = trace_pdf(source)
    assert doc.pages[0].strokes
    assert all(18 < p.y < 22 for s in doc.pages[0].strokes for p in s.points)
    assert all(s.color == "#42067a" for s in doc.pages[0].strokes)
