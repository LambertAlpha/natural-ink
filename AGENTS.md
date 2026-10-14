# Project conventions

- Use Python 3.12+ and uv. Keep source in `src/natural_ink/`; avoid machine-specific paths.
- Before committing, run `uv run ruff check src tests scripts`, `uv run ruff format --check src tests scripts`, `uv run mypy src scripts`, and `uv run pytest -q`.
- For visible changes, render `examples/demo.json` and inspect both the vector PDF and reconstructed ink. Preserve symbol identity and reading order; do not maximize randomness at the expense of legibility.
- Treat `.goodnotes` export as experimental until actual import, erase, lasso, and save/reopen have been verified in a stated app version. Independent decoding is a separate check, not proof of app compatibility.
- Keep foreground ink, backgrounds, and format adapters separate. Preserve deterministic seeds and the portable ink JSON.
- Do not commit personal notes, exam sheets, downloaded research samples, generated font caches, or files in `.local/` and `output/`.
- Keep Caveat and its derivatives under SIL OFL; retain third-party attribution.
