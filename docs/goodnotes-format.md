# Experimental Goodnotes adapter

This is an observed-format prototype, not an implementation of an official format specification. App import and editing are unverified. The public parser used as an independent oracle is [Kaih1825/parser-for-goodnotes](https://github.com/Kaih1825/parser-for-goodnotes/tree/66028455fd7fc61b7931679915d811a25485e3ad), at the linked commit.

## Portable representation

`natural-ink/1` JSON contains a title, provenance string, and pages. Each page has dimensions, a background color, and strokes. Each stroke has a color and points with `x`, `y`, and `width`. Coordinates use a top-left origin, in points; width is the full diameter, not a pressure ratio. Non-finite numbers, non-positive sizes, unknown fields, and centers outside a page are rejected.

The representation is independent of the source layout and Goodnotes internals. An ink file may be edited directly or consumed by a future adapter.

## Archive construction

The writer creates a fresh ZIP with these members:

| Member | Generated content |
| --- | --- |
| `schema.pb` | Protobuf field 1 = 24, the version observed in the reference sample |
| `document.info.pb`, `index.search.pb` | Empty; no recovered OCR/search content |
| `index.notes.pb` | Length-delimited records mapping note UUIDs to members |
| `index.attachments.pb` | Generated background PDFs only |
| `index.events.pb` | Fresh document, attachment, template, and page events |
| `notes/<UUID>` | New metadata/ink records for each reconstructed path |
| `attachments/<UUID>` | Plain paper PDF with exact page dimensions |
| `thumbnail.jpg` | Preview rendered from the generated ink |

Identifiers use UUIDv5 derived from the serialized document and object role. ZIP timestamps are fixed. No user's note file is opened or modified by the writer, and no sample archive or attachment is embedded. The page-node/note-stream ID relationship follows the observed even/next-ID convention. Event field assignments are inferred from samples and may be incomplete for the current application.

## Stroke records

The minimal observed ballpoint representation is:

```text
note stream
  record: metadata (UUID, counters, schema)
  record: protobuf field 7
    field 1: stroke UUID
    field 2: bv41 + sizes + LZ4(TPL) + bv4$
    field 4: RGBA float32 message
    other observed metadata fields
```

TPL format string: `vuA(v)A(S(uu))A(S(uuuu))vA(f)`.

The payload stores type 2, float32 width bits, visibility flags, one start point, line-segment endpoint pairs, and empty trailing timing data. The serializer uses **median width per path**. This choice matches a known ballpoint schema; it does not preserve all pressure variation or prove editable fountain-pen compatibility. Single-point dots are encoded as tiny 0.001 pt segments.

## What remains uncertain

- Whether current Goodnotes versions accept the generated document and page-event metadata.
- Whether partial erase, recolor, lasso, save/reopen, and cross-device sync behave correctly.
- Whether dense documents with tens of thousands of reconstructed paths perform acceptably.
- Whether a future adapter can write richer per-point pressure without relying on heuristic schema guesses.

An independently decoded archive proves geometry can be read, not that the target application accepts the object lifecycle. Keep that distinction in README, CLI output, and release notes until app-level evidence exists.

## Input tracing limitations

Foreground detection selects dark or saturated ink on light paper, maps it to the supplied palette, and discards light grids. Connected components are skeletonized; the graph is split at junctions while retaining loops and dots. Distance-to-background estimates the local width. This may split a handwritten letter into several paths and introduces rasterization error. It cannot recover pen order, handwriting recognition metadata, or source PDF text semantics.
