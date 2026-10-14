"""Check exported ink with an independent parser, without claiming app compatibility.

uv run python scripts/validate_goodnotes.py source.ink.json output.goodnotes \
    --parser-root /path/to/parser-for-goodnotes
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import statistics
import sys
from pathlib import Path

from natural_ink.model import InkDocument


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--parser-root", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.parser_root.resolve() / "src"))
    module = importlib.import_module("goodnotes_re")
    expected = InkDocument.model_validate_json(args.source.read_text())
    maximum_error = 0.0
    with module.GoodNotesDocument.open(str(args.archive)) as archive:
        actual = archive.pages()
        assert len(actual) == len(expected.pages), "page count"
        for original, decoded in zip(expected.pages, actual, strict=True):
            assert math.isclose(original.width, decoded.dimensions.width, abs_tol=0.001)
            assert math.isclose(original.height, decoded.dimensions.height, abs_tol=0.001)
            assert len(original.strokes) == len(decoded.strokes), "stroke count"
            for a, b in zip(original.strokes, decoded.strokes, strict=True):
                assert a.color.lower() == b.color_hex.lower(), "color"
                assert math.isclose(
                    statistics.median(p.width for p in a.points), b.width, abs_tol=0.0001
                )
                if len(a.points) == 1:
                    assert 1 <= len(b.points) <= 2
                    error = math.dist(
                        (a.points[0].x, a.points[0].y), (b.points[0].x, b.points[0].y)
                    )
                    maximum_error = max(maximum_error, error)
                else:
                    assert len(a.points) == len(b.points), "point count"
                    for x, y in zip(a.points, b.points, strict=True):
                        maximum_error = max(maximum_error, math.dist((x.x, x.y), (y.x, y.y)))
        assert maximum_error < 0.001, "coordinate precision"
    print(
        json.dumps(
            {
                "independent_decode": "passed",
                "pages": len(expected.pages),
                "strokes": sum(len(p.strokes) for p in expected.pages),
                "maximum_coordinate_error_pt": maximum_error,
                "goodnotes_app_import": "unverified",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
