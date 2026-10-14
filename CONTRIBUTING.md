# Contributing

Use Python 3.12+ and `uv sync --locked`. Before submitting changes, run Ruff, mypy, pytest, and `uv build` using the commands in the README.

For visual changes, render the neutral demo and inspect both the source PDF and reconstructed ink. Keep mathematical identity and legibility intact; more randomness is not automatically more natural.

For Goodnotes changes, include independent round-trip evidence and distinguish it from application testing. Do not claim compatibility based solely on the parser accepting an archive. A useful report includes the Goodnotes version, platform, import result, eraser/lasso behavior, and save/reopen result.

Use synthetic or self-authored examples. Do not commit personal notebooks, course sheets, downloaded sample archives, generated font caches, or machine-specific paths. `.local/` and `output/` are ignored for that reason.
