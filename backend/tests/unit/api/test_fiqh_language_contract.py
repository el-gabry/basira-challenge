from __future__ import annotations

from basira.api.schemas import QueryRequest


def test_fiqh_request_defaults_to_arabic() -> None:
    request = QueryRequest(
        question="ما حكم مس المرأة فرجها؟"
    )

    assert request.language == "ar"


def test_fiqh_request_accepts_english() -> None:
    request = QueryRequest(
        question="Does touching the private part invalidate wudu?",
        language="en",
    )

    assert request.language == "en"


def test_language_is_presentation_only() -> None:
    ar = QueryRequest(
        question="ما حكم مس المرأة فرجها؟",
        language="ar",
    )

    en = QueryRequest(
        question="ما حكم مس المرأة فرجها؟",
        language="en",
    )

    assert ar.question == en.question
    assert ar.language != en.language
