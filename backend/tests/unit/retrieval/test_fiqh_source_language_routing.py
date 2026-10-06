from basira.retrieval.official_fiqh_retriever import (
    _is_english_fiqh_query,
)


def test_arabic_question_keeps_arabic_lane() -> None:
    assert not _is_english_fiqh_query(
        "ما حكم مس الفرج وهل ينقض الوضوء؟"
    )


def test_english_question_uses_english_lane() -> None:
    assert _is_english_fiqh_query(
        "Does touching the private part "
        "invalidate wudu?"
    )


def test_mixed_arabic_does_not_silently_switch_authority_lane() -> None:
    assert not _is_english_fiqh_query(
        "ما حكم wudu بعد لمس الفرج؟"
    )
