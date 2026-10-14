"""Stable, local random streams; never mutate Python's global random state."""

import hashlib
import json
import random


def rng_for(seed: int, *keys: str | int) -> random.Random:
    data = json.dumps([seed, *keys], ensure_ascii=False, separators=(",", ":")).encode()
    return random.Random(int.from_bytes(hashlib.sha256(data).digest()[:16], "big"))
