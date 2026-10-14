"""Command line interface; native export requires an explicit experimental flag."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .goodnotes import write_goodnotes
from .model import InkDocument, Layout
from .render import page_svg, render_ink_pdf, render_layout
from .trace import DEFAULT_PALETTE, trace_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="natural-ink")
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser(
        "render", help="Render a source layout to a handwritten vector PDF"
    )
    render.add_argument("source", type=Path)
    render.add_argument("-o", "--output", type=Path, required=True)
    render.add_argument("--seed", type=int, default=183)
    render.add_argument(
        "--variation",
        type=float,
        default=0.4,
        help="Body distortion from 0 to 1; math stays independently varied",
    )
    trace = commands.add_parser(
        "trace", help="Approximately reconstruct colored PDF ink as centerlines"
    )
    trace.add_argument("source", type=Path)
    trace.add_argument("-o", "--output", type=Path, required=True)
    trace.add_argument("--scale", type=float, default=4)
    trace.add_argument(
        "--palette",
        default=",".join(DEFAULT_PALETTE),
        help="Comma-separated #RRGGBB colors; nearest-color assignment",
    )
    export = commands.add_parser(
        "export", help="EXPERIMENTAL: encode ink JSON into a native .goodnotes archive"
    )
    export.add_argument("source", type=Path)
    export.add_argument("-o", "--output", type=Path, required=True)
    export.add_argument(
        "--experimental",
        action="store_true",
        help="Acknowledge that Goodnotes app import/editability has not been verified",
    )
    preview = commands.add_parser("preview", help="Preview ink JSON as PDF or one SVG page")
    preview.add_argument("source", type=Path)
    preview.add_argument("-o", "--output", type=Path, required=True)
    preview.add_argument("--page", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        if args.source.resolve() == args.output.resolve():
            raise ValueError("Input and output must be different files")
        if args.command == "render":
            if args.output.suffix.lower() != ".pdf":
                raise ValueError("render output must end in .pdf")
            layout = Layout.model_validate_json(args.source.read_text())
            render_layout(layout, args.output, args.seed, args.variation)
            result = {
                "output": str(args.output),
                "pages": len(layout.pages),
                "seed": args.seed,
                "variation": args.variation,
            }
        elif args.command == "trace":
            if args.output.suffix.lower() != ".json":
                raise ValueError("trace output must end in .json")
            doc = trace_pdf(
                args.source, args.scale, tuple(c.strip() for c in args.palette.split(","))
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(doc.model_dump_json())
            result = {
                "output": str(args.output),
                "pages": len(doc.pages),
                "strokes": sum(len(p.strokes) for p in doc.pages),
                "approximate": True,
            }
        elif args.command == "export":
            if not args.experimental:
                raise ValueError(
                    "Native export is experimental. Pass --experimental; test import, erasing, and lasso in Goodnotes before relying on it."
                )
            if args.output.suffix.lower() != ".goodnotes":
                raise ValueError("export output must end in .goodnotes")
            doc = InkDocument.model_validate_json(args.source.read_text())
            result = write_goodnotes(doc, args.output)
            result["output"] = str(args.output)
        else:
            doc = InkDocument.model_validate_json(args.source.read_text())
            if args.output.suffix.lower() == ".pdf":
                render_ink_pdf(doc, args.output)
            elif args.output.suffix.lower() == ".svg":
                if not 1 <= args.page <= len(doc.pages):
                    raise ValueError("page is outside the document")
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(page_svg(doc.pages[args.page - 1], doc.title))
            else:
                raise ValueError("preview output must end in .pdf or .svg")
            result = {"output": str(args.output)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"natural-ink: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
