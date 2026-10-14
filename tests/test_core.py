import random

import pytest
from pydantic import ValidationError

from natural_ink.math_ink import symbol_strokes
from natural_ink.model import InkDocument, InkPage, Point, Stroke
from natural_ink.randomness import rng_for
from natural_ink.render import page_svg


def test_random_streams_are_reproducible_local_and_distinct():
    state = random.getstate()
    assert rng_for(2, "a").random() == rng_for(2, "a").random()
    assert rng_for(2, "a").random() != rng_for(3, "a").random()
    assert rng_for(2, "a").random() != rng_for(2, "b").random()
    assert random.getstate() == state


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 0])
def test_invalid_width_rejected(bad):
    with pytest.raises(ValidationError):
        Point(x=1, y=1, width=bad)


def test_page_rejects_outside_ink_and_json_roundtrips():
    stroke = Stroke(points=[Point(x=10, y=20, width=1)])
    with pytest.raises(ValidationError):
        InkPage(width=5, strokes=[stroke])
    doc = InkDocument(pages=[InkPage(strokes=[stroke])])
    assert InkDocument.model_validate_json(doc.model_dump_json()) == doc


def test_equals_has_unequal_curved_lines():
    strokes = symbol_strokes("=", 20, 20, 30, 12, "#42067a", rng_for(183))
    lengths = [abs(s.points[-1].x - s.points[0].x) for s in strokes]
    assert min(lengths) / max(lengths) < 0.9
    for stroke in strokes:
        assert max(p.y for p in stroke.points) - min(p.y for p in stroke.points) > 0.1
        assert len({p.width for p in stroke.points}) > 3


def test_svg_escapes_title():
    svg = page_svg(InkPage(), "<script>&")
    assert "<script>" not in svg
    assert "&lt;script&gt;&amp;" in svg
