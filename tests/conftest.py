"""Session-wide test setup. Order matters here: anything that must take effect before
`config.settings.settings` (a module-level singleton, read once at import time) or any
other app module gets imported for the first time has to run before those imports —
pytest loads this file before collecting test modules, so this is the only place that
reliably runs early enough.
"""

import os
from pathlib import Path

# Point DB-backed tests at a dedicated file, not the real dev DB at .env's
# DATABASE_URL — otherwise every test run would keep adding rows to (and growing)
# whatever the founder is using locally. Gitignored like the rest of data/processed/.
_TEST_DB_PATH = Path(__file__).parents[1] / "data" / "processed" / "test_suryasutra.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB_PATH.as_posix()}")

# Start each full test session with a clean DB file — AppState() re-runs migrations
# and re-seeds on every construction anyway, so this also doubles as a check that
# both of those genuinely work from nothing, not just incrementally on top of
# whatever was left over from a previous run.
_TEST_DB_PATH.unlink(missing_ok=True)

# The HF_HUB_OFFLINE fix for flaky Hugging Face Hub connectivity checks lives in
# suryasutra.retrieval.dense (it needs to apply to plain `uvicorn` startup too, not
# just pytest) — importing the package here triggers it early enough for every test.
import suryasutra.retrieval.dense  # noqa: F401
