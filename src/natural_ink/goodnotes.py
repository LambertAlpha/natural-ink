"""Experimental schema-24 archive writer based on observed public sample structures.

Writes new document/attachment/page identities and only user-supplied geometry.
It does not embed a sample archive. Successful decoding is NOT an app import test.
"""

from __future__ import annotations

import hashlib
import io
import statistics
import struct
import uuid
import zipfile
from pathlib import Path

import lz4.block
import pymupdf

from .model import InkDocument, Stroke
from .render import background_pdf

SCHEMA = 24
TPL_FORMAT = b"vuA(v)A(S(uu))A(S(uuuu))vA(f)\0"


def varint(value: int) -> bytes:
    if not 0 <= value < 2**64:
        raise ValueError("varint requires a uint64")
    out = bytearray()
    while value > 127:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def field(number: int, value: bytes | str | int) -> bytes:
    if number < 1:
        raise ValueError("field number must be positive")
    if isinstance(value, int):
        return varint(number << 3) + varint(value)
    raw = value.encode() if isinstance(value, str) else value
    return varint((number << 3) | 2) + varint(len(raw)) + raw


def float_field(number: int, value: float) -> bytes:
    return varint((number << 3) | 5) + struct.pack("<f", value)


def record(payload: bytes) -> bytes:
    return varint(len(payload)) + payload


def clock(counter: int) -> bytes:
    return field(1, 1) + field(2, counter)


def wrapped(value: str, counter: int = 1) -> bytes:
    return field(1, value) + field(2, clock(counter))


def encode_stroke(stroke: Stroke, identifier: str, counter: int) -> bytes:
    """Observed ballpoint form: one median width per synthesized path."""
    points = stroke.points
    width = statistics.median(p.width for p in points)
    first = points[0]
    # Keep one-point dots as a tiny ballpoint segment, not as a lost empty array.
    coords = [(p.x, p.y) for p in points]
    if len(coords) == 1:
        coords.append((first.x + 0.001, first.y))
    segments = list(zip(coords, coords[1:], strict=False))
    values = struct.pack("<HfI", 2, width, len(segments) + 1)
    values += struct.pack("<" + "H" * (len(segments) + 1), 0, *([1] * len(segments)))
    values += struct.pack("<Iff", 1, first.x, first.y)
    values += struct.pack("<I", len(segments))
    for a, b in segments:
        values += struct.pack("<ffff", *a, *b)
    values += struct.pack("<HI", 1, 0)
    tpl = b"tpl\0" + struct.pack("<I", 8 + len(TPL_FORMAT) + len(values)) + TPL_FORMAT + values
    compressed = lz4.block.compress(tpl, store_size=False)
    framed = b"bv41" + struct.pack("<II", len(tpl), len(compressed)) + compressed + b"bv4$"
    rgba = b"".join(
        float_field(i + 1, int(stroke.color[1 + 2 * i : 3 + 2 * i], 16) / 255) for i in range(3)
    ) + float_field(4, 1)
    metadata = (
        field(1, identifier)
        + field(2, clock(counter))
        + field(8, 1)
        + field(9, counter)
        + field(14, 1)
        + field(16, SCHEMA)
    )
    ink = (
        field(1, identifier)
        + field(2, framed)
        + field(4, rgba)
        + field(6, b"")
        + field(7, field(1, clock(counter)))
        + field(9, b"")
        + field(15, clock(counter))
        + field(20, b"")
        + field(21, SCHEMA)
    )
    return record(metadata) + record(field(7, ink))


def write_goodnotes(document: InkDocument, output: Path) -> dict[str, object]:
    digest = hashlib.sha256(document.model_dump_json().encode()).hexdigest()

    def identity(label: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"natural-ink:{digest}:{label}")).upper()

    doc_id = identity("document")
    document_event = (
        field(1, doc_id)
        + field(2, wrapped(document.title))
        + field(6, wrapped("P"))
        + field(9, "auto")
        + field(11, identity("document-event"))
        + field(13, 1)
        + field(14, 1)
        + field(20, SCHEMA)
    )
    events = record(field(1, doc_id) + field(30, document_event))
    notes_index, attachments_index = b"", b""
    members: dict[str, bytes] = {
        "schema.pb": field(1, SCHEMA),
        "document.info.pb": b"",
        "index.search.pb": b"",
    }
    for pi, page in enumerate(document.pages):
        page_id = identity(f"page-{pi}")
        # Observed page node and note stream IDs differ by one (least-significant bit).
        page_id = str(uuid.UUID(int=uuid.UUID(page_id).int & ~1)).upper()
        note_id = str(uuid.UUID(int=uuid.UUID(page_id).int + 1)).upper()
        attachment_id, template_id = identity(f"background-{pi}"), identity(f"template-{pi}")
        paper = background_pdf(page.width, page.height, page.background)
        members[f"attachments/{attachment_id}"] = paper
        attachments_index += record(
            field(1, attachment_id) + field(2, f"attachments/{attachment_id}")
        )
        notes_index += record(field(1, note_id) + field(2, f"notes/{note_id}"))
        attachment = (
            field(1, attachment_id)
            + field(2, attachment_id)
            + field(5, len(paper))
            + field(6, doc_id)
            + field(11, identity(f"attach-event-{pi}"))
            + field(12, clock(1))
            + field(14, 1)
            + field(15, 1)
            + field(16, SCHEMA)
        )
        template = (
            field(1, doc_id)
            + field(2, template_id)
            + field(4, attachment_id)
            + field(5, 1)
            + field(6, 1)
            + field(8, float_field(1, page.width) + float_field(2, page.height))
            + field(9, "Natural Ink paper")
            + field(11, identity(f"template-event-{pi}"))
            + field(15, 1)
            + field(16, 1)
            + field(21, SCHEMA)
        )
        page_event = (
            field(1, doc_id)
            + field(2, page_id)
            + field(3, wrapped(template_id))
            + field(4, wrapped(f"A{pi:06d}"))
            + field(11, identity(f"page-event-{pi}"))
            + field(13, 1)
            + field(14, 1)
            + field(15, SCHEMA)
        )
        for identifier, tag, event in (
            (attachment_id, 6, attachment),
            (template_id, 2, template),
            (page_id, 54, page_event),
        ):
            events += record(field(1, identifier) + field(tag, event))
        members[f"notes/{note_id}"] = b"".join(
            encode_stroke(s, identity(f"stroke-{pi}-{si}"), si + 1)
            for si, s in enumerate(page.strokes)
        )
    members["index.notes.pb"] = notes_index
    members["index.attachments.pb"] = attachments_index
    members["index.events.pb"] = events
    # Thumbnail shows the generated ink, never a borrowed sample image.
    from tempfile import TemporaryDirectory

    from .render import render_ink_pdf

    with TemporaryDirectory(prefix="natural-ink-preview-") as tmp:
        preview = Path(tmp) / "preview.pdf"
        render_ink_pdf(document, preview)
        with pymupdf.open(preview) as pdf:
            members["thumbnail.jpg"] = (
                pdf[0].get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5)).tobytes("jpeg")
            )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(buffer.getvalue())
    return {
        "experimental": True,
        "app_import_verified": False,
        "schema": SCHEMA,
        "pages": len(document.pages),
        "strokes": sum(len(p.strokes) for p in document.pages),
        "sha256": hashlib.sha256(buffer.getvalue()).hexdigest(),
        "width_policy": "median width per path; original variable widths retained in ink JSON",
    }
