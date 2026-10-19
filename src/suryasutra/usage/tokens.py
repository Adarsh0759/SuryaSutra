"""Pre-generation token estimation.

D-22: provider-reported usage is the ground truth for cost; this estimate exists only
to budget *before* a generation call (chunk sizing, selector packing). Every value this
module returns is an estimate, not a billed count — callers must not report it as cost.
"""

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Estimate token count for budgeting. Not tied to any specific provider's tokenizer."""
    return len(_ENCODING.encode(text))
