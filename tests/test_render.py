from pathlib import Path

import pymupdf
import pytest

from natural_ink import render
from natural_ink.fonts import font_bank
from natural_ink.model import Layout


def test_layout_preserves_text_and_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(
        render,
        "font_bank",
        lambda folder, seed, strength: font_bank(folder, seed, strength, count=3),
    )
    layout = Layout.model_validate(
        {"pages": [{"items": [{"type": "text", "text": "hello hello", "x": 40, "y": 70}]}]}
    )
    paths = [tmp_path / "a.pdf", tmp_path / "b.pdf"]
    for path in paths:
        render.render_layout(layout, path)
    assert paths[0].read_bytes() == paths[1].read_bytes()
    with pymupdf.open(paths[0]) as pdf:
        assert pdf[0].get_text().strip() == "hello hello"
        assert pdf[0].rect.width == 612


def test_variation_validation_runs_before_writing(tmp_path):
    layout = Layout.model_validate({"pages": [{"items": []}]})
    output: Path = tmp_path / "invalid.pdf"
    with pytest.raises(ValueError, match="variation"):
        render.render_layout(layout, output, variation=float("nan"))
    assert not output.exists()
