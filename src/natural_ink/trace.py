"""Approximate PDF ink centerlines; never claim recovery of original pen history."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pymupdf
from scipy import ndimage
from skimage.morphology import skeletonize

from .model import InkDocument, InkPage, Point, Stroke

Pixel = tuple[int, int]
DEFAULT_PALETTE = ("#42067a", "#035296", "#046b4f", "#000000")


def edge_key(a: Pixel, b: Pixel) -> tuple[Pixel, Pixel]:
    return (a, b) if a < b else (b, a)


def skeleton_paths(mask: np.ndarray) -> list[list[Pixel]]:
    """Walk every skeleton edge once, splitting at junctions and retaining loops."""
    pixels: set[Pixel] = set(zip(*np.nonzero(skeletonize(mask)), strict=True))
    adjacency: dict[Pixel, list[Pixel]] = {}
    for y, x in sorted(pixels):
        neighbours = []
        for dy, dx in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)):
            q = (y + dy, x + dx)
            if q not in pixels:
                continue
            # A diagonal would cut across a cardinal connection and form tiny false cycles.
            if dy and dx and ((y + dy, x) in pixels or (y, x + dx) in pixels):
                continue
            neighbours.append(q)
        adjacency[(y, x)] = neighbours
    visited: set[tuple[Pixel, Pixel]] = set()
    paths: list[list[Pixel]] = []

    def walk(start: Pixel, neighbour: Pixel) -> list[Pixel]:
        path = [start, neighbour]
        visited.add(edge_key(start, neighbour))
        prev, current = start, neighbour
        while len(adjacency[current]) == 2:
            nxt = next(p for p in adjacency[current] if p != prev)
            edge = edge_key(current, nxt)
            if edge in visited:
                break
            visited.add(edge)
            path.append(nxt)
            prev, current = current, nxt
        return path

    for p, neighbours in adjacency.items():
        if not neighbours:
            paths.append([p])
        elif len(neighbours) != 2:
            for q in neighbours:
                if edge_key(p, q) not in visited:
                    paths.append(walk(p, q))
    for p, neighbours in adjacency.items():
        for q in neighbours:
            if edge_key(p, q) not in visited:
                paths.append(walk(p, q))
    return paths


def trace_pdf(
    source: Path, scale: float = 4, palette: tuple[str, ...] = DEFAULT_PALETTE
) -> InkDocument:
    if not 2 <= scale <= 8:
        raise ValueError("trace scale must be between 2 and 8")
    if not 1 <= len(palette) <= 32:
        raise ValueError("palette must contain 1 to 32 colors")
    for color in palette:
        Stroke(points=[Point(x=1, y=1, width=1)], color=color)
    colors = np.array([[int(c[i : i + 2], 16) for i in (1, 3, 5)] for c in palette], dtype=float)
    pages = []
    with pymupdf.open(source) as pdf:
        if pdf.needs_pass:
            raise ValueError("Encrypted PDFs are not supported")
        for page in pdf:
            if page.rect.width * page.rect.height * scale**2 > 35_000_000:
                raise ValueError("Page exceeds tracing pixel budget; reduce scale")
            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False
            )
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            low, high = rgb.min(axis=2), rgb.max(axis=2)
            foreground = ((low < 180) & ((high.astype(int) - low) > 35)) | (high < 125)
            coords = np.nonzero(foreground)
            labels_by_color = np.full(foreground.shape, -1, dtype=np.int8)
            if len(coords[0]):
                # Antialiasing mixes ink with paper. Use paper-to-ink color rays;
                # raw RGB distance can mislabel pale purple edges as blue.
                paper_color = np.percentile(rgb.reshape(-1, 3)[::32], 95, axis=0)
                directions = paper_color - colors
                directions /= np.maximum(np.linalg.norm(directions, axis=1, keepdims=True), 1e-9)
                ink_vectors = paper_color - rgb[coords].astype(float)
                ink_vectors /= np.maximum(np.linalg.norm(ink_vectors, axis=1, keepdims=True), 1e-9)
                labels_by_color[coords] = (ink_vectors @ directions.T).argmax(axis=1)
            strokes = []
            for ci, color in enumerate(palette):
                components, _ = ndimage.label(labels_by_color == ci, structure=np.ones((3, 3)))
                for li, box in enumerate(ndimage.find_objects(components), 1):
                    if box is None:
                        continue
                    mask = components[box] == li
                    if mask.sum() < 2:
                        continue
                    # Padding gives edge pixels a real background distance.
                    padded = np.pad(mask, 1)
                    radii = ndimage.distance_transform_edt(padded)
                    for path in skeleton_paths(padded):
                        points = []
                        for y, x in path:
                            points.append(
                                Point(
                                    x=(box[1].start + x - 0.5) / scale,
                                    y=(box[0].start + y - 0.5) / scale,
                                    width=max(0.15, (2 * radii[y, x] - 0.6) / scale),
                                )
                            )
                        # Preserve all graph vertices: simplification can erase dots or tiny operators.
                        strokes.append(Stroke(points=points, color=color))
            pages.append(InkPage(width=page.rect.width, height=page.rect.height, strokes=strokes))
    return InkDocument(
        title=source.stem,
        provenance=f"PDF centerline reconstruction at {scale:g}x; approximate geometry; no original pen order",
        pages=pages,
    )
