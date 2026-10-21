"""The HF_HUB_OFFLINE fix for flaky Hugging Face Hub connectivity checks now lives in
suryasutra.retrieval.dense (it needs to apply to plain `uvicorn` startup too, not just
pytest) — this file just needs to trigger that module's import early enough. Importing
the package here is enough; every test that uses DenseIndex imports it anyway.
"""

import suryasutra.retrieval.dense  # noqa: F401
