"""Avoid flaky Hugging Face Hub connectivity checks once the embedding model is
already cached locally — seen repeatedly as httpx.RemoteProtocolError during
SentenceTransformer loading, purely from an update-check round trip, not a code bug
(confirmed: tests pass clean and faster with HF_HUB_OFFLINE=1 once cached). D-27
CI-stability note. Only set once the model is actually cached, so a fresh machine's
first run still downloads normally.
"""

import os
from pathlib import Path

_MODEL_CACHE = Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-small-en-v1.5"

if _MODEL_CACHE.exists():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
