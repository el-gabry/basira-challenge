from __future__ import annotations

import basira.trust.runtime_constraints as runtime_constraints
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)


def _enable_constraint(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_constraints,
        "learned_constraint_enabled",
        lambda _constraint_id: True,
    )


def test_arabic_quran_verification_constraint(
    monkeypatch,
) -> None:
    _enable_constraint(
        monkeypatch,
    )

    assert (
        runtime_constraints
        .is_quran_verification_request(
            original_text=(
                "هل هذا النص القرآني صحيح: "
                "يا أيها الذين آمنوا"
            ),
            intent_text=(
                "هل هذا النص القراني صحيح "
                "يا ايها الذين امنوا"
            ),
        )
        is True
    )


def test_english_quran_verification_constraint(
    monkeypatch,
) -> None:
    _enable_constraint(
        monkeypatch,
    )

    assert (
        runtime_constraints
        .is_quran_verification_request(
            original_text=(
                "Is this Quran quotation correct: "
                "Seek help through patience and prayer; "
                "indeed Allah loves the patient?"
            ),
            intent_text=(
                "Is this Quran quotation correct "
                "Seek help through patience and prayer "
                "indeed Allah loves the patient"
            ),
        )
        is True
    )


def test_english_quran_meaning_is_not_quote_verification(
    monkeypatch,
) -> None:
    _enable_constraint(
        monkeypatch,
    )

    assert (
        runtime_constraints
        .is_quran_verification_request(
            original_text=(
                "What does Ayat al-Kursi mean?"
            ),
            intent_text=(
                "What does Ayat al-Kursi mean"
            ),
        )
        is False
    )


def test_english_quran_verification_routes_to_verification(
    monkeypatch,
) -> None:
    _enable_constraint(
        monkeypatch,
    )

    service = (
        BasiraQueryUnderstandingService()
    )

    result = service.understand(
        "Is this Quran quotation correct: "
        "Seek help through patience and prayer; "
        "indeed Allah loves the patient?"
    )

    assert (
        result.primary_intent
        is BasiraIntent.QUOTE_VERIFICATION
    )
