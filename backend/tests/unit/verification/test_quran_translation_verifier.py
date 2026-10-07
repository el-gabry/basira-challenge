from __future__ import annotations

from pathlib import Path

from basira.competition.quranpedia_translation_adapter import (
    QURANPEDIA_TRANSLATION_SOURCE_ID,
    QuranpediaTranslationEvidenceAdapter,
)
from basira.verification.quran_translation_verifier import (
    QuranTranslationQuoteVerifier,
)
from basira.verification.quran_verifier import (
    QuranDifferenceKind,
    QuranQuoteStatus,
)

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)


def verifier() -> (
    QuranTranslationQuoteVerifier
):
    return QuranTranslationQuoteVerifier(
        QuranpediaTranslationEvidenceAdapter(
            repo_root=PROJECT_ROOT,
        )
    )


def test_governed_english_source_detects_altered_translation() -> None:
    adapter = (
        QuranpediaTranslationEvidenceAdapter(
            repo_root=PROJECT_ROOT,
        )
    )

    source = adapter.get(
        surah=2,
        ayah=153,
    )

    assert source is not None

    assert (
        source.source_id
        == QURANPEDIA_TRANSLATION_SOURCE_ID
    )

    assert "is with" in source.text

    altered = source.text.replace(
        "is with",
        "loves",
        1,
    )

    result = verifier().verify(
        altered
    )

    assert (
        result.status
        is QuranQuoteStatus.ALTERED_TEXT
    )

    assert len(
        result.candidates
    ) == 1

    assert (
        result.candidates[0].reference
        == "2:153"
    )

    assert (
        result.candidates[0].source_id
        == QURANPEDIA_TRANSLATION_SOURCE_ID
    )

    assert any(
        difference.kind
        is QuranDifferenceKind.SUBSTITUTION
        and "loves"
        in difference.received
        for difference
        in result.differences
    )


def test_current_competition_english_wording_resolves_to_2153() -> None:
    result = verifier().verify(
        "Seek help through patience and prayer; "
        "indeed Allah loves the patient"
    )

    assert (
        result.status
        is QuranQuoteStatus.ALTERED_TEXT
    )

    assert len(
        result.candidates
    ) == 1

    assert (
        result.candidates[0].reference
        == "2:153"
    )

    assert (
        result.candidates[0].source_id
        == QURANPEDIA_TRANSLATION_SOURCE_ID
    )


def test_unrelated_english_text_fails_closed() -> None:
    result = verifier().verify(
        "This sentence is unrelated to the Quran "
        "quotation being checked by the system."
    )

    assert (
        result.status
        is QuranQuoteStatus.NOT_FOUND
    )

    assert (
        result.candidates
        == ()
    )



def test_partial_quote_ignores_unquoted_boundary_context() -> None:
    result = verifier().verify(
        "Seek help through patience and prayer; "
        "indeed Allah loves the patient"
    )

    assert (
        result.status
        is QuranQuoteStatus.ALTERED_TEXT
    )

    substantive = [
        difference
        for difference
        in result.differences
        if difference.is_substantive
    ]

    assert len(substantive) == 1

    difference = substantive[0]

    assert (
        difference.kind
        is QuranDifferenceKind.SUBSTITUTION
    )

    assert difference.received == (
        "loves",
    )

    assert difference.expected == (
        "is",
        "with",
    )


def test_internal_omission_remains_a_difference() -> None:
    differences = (
        QuranTranslationQuoteVerifier
        ._differences(
            expected=(
                "alpha beta gamma delta"
            ),
            received=(
                "alpha beta delta"
            ),
        )
    )

    assert any(
        difference.kind
        is QuranDifferenceKind.DELETION
        and difference.expected
        == ("gamma",)
        for difference
        in differences
    )
