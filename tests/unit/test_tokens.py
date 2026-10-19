from suryasutra.usage.tokens import count_tokens


def test_count_tokens_empty_string_is_zero() -> None:
    assert count_tokens("") == 0


def test_count_tokens_is_positive_for_nonempty_text() -> None:
    assert count_tokens("Isolate the DC side before opening the enclosure.") > 0


def test_count_tokens_is_deterministic() -> None:
    text = "Check insulation resistance between PV+ and ground."
    assert count_tokens(text) == count_tokens(text)


def test_count_tokens_grows_with_text_length() -> None:
    short = "Fault code 548."
    long = short * 20
    assert count_tokens(long) > count_tokens(short)
