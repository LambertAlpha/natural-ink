import struct
import zipfile

import lz4.block
import pytest

from natural_ink.cli import main
from natural_ink.goodnotes import TPL_FORMAT, encode_stroke, varint, write_goodnotes
from natural_ink.model import InkDocument, InkPage, Point, Stroke


def sample():
    return InkDocument(
        pages=[
            InkPage(
                strokes=[Stroke(points=[Point(x=20, y=30, width=2), Point(x=25, y=34, width=2)])]
            )
        ]
    )


def test_native_archive_is_deterministic_and_contains_no_borrowed_assets(tmp_path):
    a, b = tmp_path / "a.goodnotes", tmp_path / "b.goodnotes"
    result = write_goodnotes(sample(), a)
    write_goodnotes(sample(), b)
    assert a.read_bytes() == b.read_bytes()
    assert result["app_import_verified"] is False
    with zipfile.ZipFile(a) as z:
        assert z.testzip() is None
        assert z.read("schema.pb") == b"\x08\x18"
        notes = [n for n in z.namelist() if n.startswith("notes/")]
        assert len(notes) == 1
        assert b"bv41" in z.read(notes[0])
        attachments = [n for n in z.namelist() if n.startswith("attachments/")]
        assert len(attachments) == 1
        assert z.read(attachments[0]).startswith(b"%PDF")


def test_stroke_payload_lengths_and_coordinates():
    blob = encode_stroke(sample().pages[0].strokes[0], "00000000-0000-4000-8000-000000000001", 1)
    start = blob.index(b"bv41")
    size, compressed_size = struct.unpack_from("<II", blob, start + 4)
    raw = lz4.block.decompress(
        blob[start + 12 : start + 12 + compressed_size], uncompressed_size=size
    )
    assert raw[:4] == b"tpl\0"
    assert struct.unpack_from("<I", raw, 4)[0] == len(raw)
    assert raw[8 : 8 + len(TPL_FORMAT)] == TPL_FORMAT
    assert struct.pack("<ffff", 20, 30, 25, 34) in raw


def test_experimental_opt_in_required(tmp_path, capsys):
    source = tmp_path / "ink.json"
    source.write_text(sample().model_dump_json())
    out = tmp_path / "ink.goodnotes"
    assert main(["export", str(source), "-o", str(out)]) == 2
    assert not out.exists()
    assert "experimental" in capsys.readouterr().err


def test_varint_rejects_negative_and_overflow():
    for value in (-1, 2**64):
        with pytest.raises(ValueError):
            varint(value)
