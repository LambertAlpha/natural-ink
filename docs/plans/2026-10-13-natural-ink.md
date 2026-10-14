# Natural Ink implementation plan

**Goal:** Package deterministic handwritten text and mathematical gestures, and experimentally serialize native Goodnotes ink.

**Architecture:** Keep a portable page/ink representation separate from rendering and file-format adapters. Preserve source text and parameters in editable JSON. Generate PDF/SVG previews independently of the Goodnotes archive writer, and validate the archive against a separate parser. Reject unsupported inputs rather than silently flattening them and claiming editability.

**Tech stack:** Python, uv, fontTools, ReportLab, Pillow, pytest, Ruff, mypy; optional image tracing and research parser as needed.

## Alternatives
1. Rename/import PDF: preserves appearance but does not meet editable-ink requirements.
2. Depend entirely on the Goodnotes internals: native editing possible, but fragile and platform-specific.
3. Portable ink model with an experimental Goodnotes adapter (selected): independently usable outputs and explicit compatibility boundary.

## Tasks
1. Inspect format documentation and samples in ignored research storage. Record exact revisions and findings.
2. Implement typed page/stroke models and deterministic variation controls. Test content validation, reproducibility, and geometry bounds.
3. Extract font and math rendering independent of the course page layout. Add a neutral text/formula example and source attribution.
4. Implement the smallest editable Goodnotes sample supported by observed format. Independently decode geometry; preserve no third-party note content.
5. Expose CLI commands with clear unsupported-format errors. Add README and format limitations.
6. Run uv-based tests, Ruff, and mypy; render and inspect sample pages. Commit only after checks pass.
7. Create/push repository under the authenticated account; verify visibility and remote commit. Report app-level verification separately if the app is unavailable.
