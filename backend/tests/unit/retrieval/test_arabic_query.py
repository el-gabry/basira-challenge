from __future__ import annotations

from basira.retrieval.arabic_query import (
    ArabicDialect,
    build_arabic_query,
    normalize_arabic_search_text,
)


def test_preserves_original_query() -> None:
    value = "وش صحة هالحديث؟"

    query = build_arabic_query(
        value
    )

    assert query.original_text == value


def test_search_normalization_removes_diacritics() -> None:
    assert (
        normalize_arabic_search_text(
            "إِنَّمَا الأَعْمَالُ"
        )
        == "انما الاعمال"
    )


def test_detects_egyptian_marker() -> None:
    query = build_arabic_query(
        "الحديث ده صح ولا ايه؟"
    )

    assert (
        query.dialect
        is ArabicDialect.EGYPTIAN
    )


def test_detects_gulf_marker() -> None:
    query = build_arabic_query(
        "وش صحة هالحديث"
    )

    assert (
        query.dialect
        is ArabicDialect.GULF
    )


def test_detects_levantine_marker() -> None:
    query = build_arabic_query(
        "شو صحة هاد الحديث"
    )

    assert (
        query.dialect
        is ArabicDialect.LEVANTINE
    )


def test_dialect_words_are_normalized_for_intent_only() -> None:
    query = build_arabic_query(
        "وش صحة هالحديث"
    )

    assert (
        query.search_text
        == "وش صحة هالحديث"
    )

    assert query.intent_text.startswith(
        "ما صحة"
    )


def test_unknown_when_no_dialect_signal() -> None:
    query = build_arabic_query(
        "ما صحة هذا الحديث؟"
    )

    assert (
        query.dialect
        is ArabicDialect.UNKNOWN
    )
