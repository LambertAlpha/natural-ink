"""Hand-drawn math gestures adapted from the original handwriting experiment."""

from __future__ import annotations

import json
import math
import random
from importlib.resources import files

from .model import Point, Stroke

SHAPES: dict[str, list[str]] = json.loads(
    files("natural_ink").joinpath("assets/symbols.json").read_text()
)


def symbol_strokes(
    key: str,
    x: float,
    y: float,
    width: float,
    height: float,
    color: str,
    rng: random.Random,
    strength: float = 1,
) -> list[Stroke]:
    if key not in SHAPES:
        raise ValueError(f"Unsupported math symbol: {key!r}")
    paths = SHAPES[key]
    if key == "=":
        lengths = [rng.uniform(0.89, 0.99), rng.uniform(0.66, 0.78)]
        rng.shuffle(lengths)
        paths = [
            f"M {0.5 - d / 2} {v} L {0.5 + d / 2} {v}"
            for d, v in zip(lengths, (0.1, 0.9), strict=True)
        ]
    strokes = []
    for path in paths:
        tokens = iter(path.split())
        points: list[tuple[float, float]] = []
        current = (0.0, 0.0)
        for op in tokens:
            controls = [
                (x + float(next(tokens)) * width, y + float(next(tokens)) * height)
                for _ in range(3 if op == "C" else 1)
            ]
            end = controls[-1]
            if op == "M":
                current = end
                points.append(end)
                continue
            length = math.dist(current, end)
            bend = rng.uniform(0.012, 0.032) * max(width, height) * rng.choice((-1, 1)) * strength
            nx, ny = (
                -(end[1] - current[1]) / max(length, 0.001),
                (end[0] - current[0]) / max(length, 0.001),
            )
            for i in range(1, 25):
                t, s = i / 24, 1 - i / 24
                if op == "C":
                    p1, p2, p3 = controls
                    px = (
                        s**3 * current[0]
                        + 3 * s * s * t * p1[0]
                        + 3 * s * t * t * p2[0]
                        + t**3 * p3[0]
                    )
                    py = (
                        s**3 * current[1]
                        + 3 * s * s * t * p1[1]
                        + 3 * s * t * t * p2[1]
                        + t**3 * p3[1]
                    )
                else:
                    px, py = (
                        current[0] + (end[0] - current[0]) * t,
                        current[1] + (end[1] - current[1]) * t,
                    )
                points.append(
                    (px + nx * bend * math.sin(math.pi * t), py + ny * bend * math.sin(math.pi * t))
                )
            current = end
        nominal = max(0.3, max(width, height) * rng.uniform(0.058, 0.072))
        strokes.append(pressure_path(points, color, nominal, rng))
    return strokes


def pressure_path(
    points: list[tuple[float, float]],
    color: str,
    width: float,
    rng: random.Random,
) -> Stroke:
    phase = rng.uniform(-1, 1)
    result = []
    for i, (x, y) in enumerate(points):
        t = i / max(1, len(points) - 1)
        taper = (0.65 + 0.35 * (1 - math.exp(-t / 0.08))) * (
            0.6 + 0.4 * (1 - math.exp(-(1 - t) / 0.08))
        )
        result.append(
            Point(x=x, y=y, width=width * taper * (1 + 0.13 * math.sin(t * math.pi + phase)))
        )
    return Stroke(points=result, color=color)


def rule_stroke(
    x: float, y: float, length: float, width: float, color: str, rng: random.Random
) -> Stroke:
    bend = rng.choice((-1, 1)) * min(1.1, length * 0.015)
    points = [(x + length * i / 64, y + bend * math.sin(math.pi * i / 64)) for i in range(65)]
    return pressure_path(points, color, width, rng)
