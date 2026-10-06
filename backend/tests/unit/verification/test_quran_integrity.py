import pytest

from basira.models.quran import QuranVerse
from basira.sources.quran.repository import (
    QuranRepository,
)
from basira.verification.quran_integrity import (
    QuranCrossSourceIntegrityVerifier,
    QuranIntegrityStatus,
)


def verse(
    *,
    source_id: str,
    surah: int,
    ayah: int,
    uthmani: str,
    search: str,
) -> QuranVerse:
    return QuranVerse(
        source_id=source_id,
        surah_number=surah,
        ayah_number=ayah,
        text_uthmani=uthmani,
        text_search=search,
    )


def verifier(
    expected_reference_count: int,
) -> QuranCrossSourceIntegrityVerifier:
    return QuranCrossSourceIntegrityVerifier(
        expected_reference_count=(
            expected_reference_count
        )
    )


def test_exact_match() -> None:
    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=1,
                ayah=1,
                uthmani="بسم الله",
                search="بسم الله",
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=1,
                ayah=1,
                uthmani="بسم الله",
                search="بسم الله",
            ),
        )
    )

    report = verifier(
        1
    ).compare(
        source_a,
        source_b,
    )

    comparison = (
        report.comparisons[0]
    )

    assert (
        comparison.status
        == QuranIntegrityStatus.EXACT_MATCH
    )

    assert report.total_references == 1
    assert report.exact_matches == 1

    assert (
        report.orthographic_variants
        == 0
    )

    assert (
        report
        .orthographically_accounted_for
        == 1
    )

    assert (
        report.unresolved_mismatches
        == 0
    )

    assert (
        report.unresolved_segments
        == 0
    )

    assert (
        report.missing_references
        == 0
    )

    assert report.coverage_complete
    assert report.corpus_text_agrees
    assert report.cross_source_verified

    assert not report.review_required


def test_search_text_does_not_change_integrity_verdict() -> None:
    """
    Corpus integrity is based on canonical
    text_uthmani.

    text_search belongs to retrieval and must not
    influence the cross-source integrity verdict.
    """

    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=2,
                ayah=1,
                uthmani="الٓمٓ",
                search="الم",
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=2,
                ayah=1,
                uthmani="الٓمٓ",
                search=(
                    "completely different "
                    "search representation"
                ),
            ),
        )
    )

    report = verifier(
        1
    ).compare(
        source_a,
        source_b,
    )

    assert (
        report.exact_matches
        == 1
    )

    assert (
        report.comparisons[0].status
        == QuranIntegrityStatus.EXACT_MATCH
    )

    assert report.corpus_text_agrees


def test_orthographically_equivalent() -> None:
    """
    Two Uthmani source representations may encode
    the same Quran word differently at Unicode level.

    This pair mirrors a real cross-source difference
    observed in the KFGQPC ↔ Tanzil audit:

        تلقايٕ
        تلقائ

    The orthography engine has already verified that
    these normalize to the same lexical Quran text.
    """

    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=10,
                ayah=15,
                uthmani="تِلۡقَآيِٕ",
                search="تلقاء",
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=10,
                ayah=15,
                uthmani="تِلْقَآئِ",
                search="تلقاء",
            ),
        )
    )

    report = verifier(
        1
    ).compare(
        source_a,
        source_b,
    )

    comparison = (
        report.comparisons[0]
    )

    assert (
        comparison.status
        == QuranIntegrityStatus
        .ORTHOGRAPHICALLY_EQUIVALENT
    )

    assert (
        comparison.orthography
        is not None
    )

    assert (
        comparison
        .orthographically_accounted_for
    )

    assert report.exact_matches == 0

    assert (
        report.orthographic_variants
        == 1
    )

    assert (
        report
        .orthographically_accounted_for
        == 1
    )

    assert (
        report.unresolved_mismatches
        == 0
    )

    assert (
        report.missing_references
        == 0
    )

    assert report.coverage_complete
    assert report.corpus_text_agrees
    assert report.cross_source_verified

    assert not report.review_required


def test_basmala_layout_is_accounted_for() -> None:
    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=2,
                ayah=1,
                uthmani="الٓمٓ",
                search="الم",
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=2,
                ayah=1,
                uthmani=(
                    "بِسْمِ ٱللَّهِ "
                    "ٱلرَّحْمَـٰنِ "
                    "ٱلرَّحِيمِ "
                    "الٓمٓ"
                ),
                search=(
                    "بسم الله الرحمن "
                    "الرحيم الم"
                ),
            ),
        )
    )

    report = verifier(
        1
    ).compare(
        source_a,
        source_b,
    )

    comparison = (
        report.comparisons[0]
    )

    assert (
        comparison.status
        == QuranIntegrityStatus
        .ORTHOGRAPHICALLY_EQUIVALENT
    )

    assert (
        comparison.orthography
        is not None
    )

    assert (
        report.orthographic_variants
        == 1
    )

    assert report.corpus_text_agrees
    assert report.cross_source_verified

    assert not report.review_required


def test_lexical_change_is_unresolved() -> None:
    """
    A real unexplained lexical change must not be
    hidden by the orthography layer.

    Basira also does not independently declare one
    Quran source wrong.

    It returns UNRESOLVED_MISMATCH for review.
    """

    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=2,
                ayah=153,
                uthmani=(
                    "إن الله مع الصابرين"
                ),
                search=(
                    "إن الله مع الصابرين"
                ),
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=2,
                ayah=153,
                uthmani=(
                    "إن الله يحب الصابرين"
                ),
                search=(
                    "إن الله يحب الصابرين"
                ),
            ),
        )
    )

    report = verifier(
        1
    ).compare(
        source_a,
        source_b,
    )

    comparison = (
        report.comparisons[0]
    )

    assert (
        comparison.status
        == QuranIntegrityStatus
        .UNRESOLVED_MISMATCH
    )

    assert comparison.requires_review

    assert not (
        comparison
        .orthographically_accounted_for
    )

    assert (
        comparison.orthography
        is not None
    )

    assert (
        comparison
        .unresolved_segment_count
        >= 1
    )

    assert (
        report.unresolved_mismatches
        == 1
    )

    assert (
        report.unresolved_segments
        >= 1
    )

    assert report.review_required

    assert not report.corpus_text_agrees

    assert not (
        report.cross_source_verified
    )


def test_missing_reference_requires_review() -> None:
    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=1,
                ayah=1,
                uthmani="first",
                search="first",
            ),
            verse(
                source_id="source-a",
                surah=1,
                ayah=2,
                uthmani="second",
                search="second",
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=1,
                ayah=1,
                uthmani="first",
                search="first",
            ),
        )
    )

    report = verifier(
        2
    ).compare(
        source_a,
        source_b,
    )

    assert (
        report.total_references
        == 2
    )

    # Union count is complete, but one source is
    # still missing one reference.
    assert report.coverage_complete

    assert (
        report.missing_references
        == 1
    )

    assert report.review_required

    assert not report.corpus_text_agrees

    assert not (
        report.cross_source_verified
    )

    missing = next(
        comparison
        for comparison
        in report.comparisons
        if comparison.reference
        == "1:2"
    )

    assert (
        missing.status
        == QuranIntegrityStatus
        .REFERENCE_MISSING
    )

    assert (
        missing.text_a
        == "second"
    )

    assert missing.text_b is None

    assert (
        missing.orthography
        is None
    )


def test_shared_missing_reference_detected_by_expected_count() -> None:
    """
    If both corpora omit the same reference, the
    union cannot expose that missing reference.

    expected_reference_count protects against this.
    """

    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=1,
                ayah=1,
                uthmani="first",
                search="first",
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=1,
                ayah=1,
                uthmani="first",
                search="first",
            ),
        )
    )

    report = verifier(
        2
    ).compare(
        source_a,
        source_b,
    )

    assert (
        report.total_references
        == 1
    )

    assert (
        report.missing_references
        == 0
    )

    assert not (
        report.coverage_complete
    )

    assert report.review_required

    assert not report.corpus_text_agrees

    assert not (
        report.cross_source_verified
    )


def test_comparison_does_not_depend_on_order() -> None:
    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=2,
                ayah=2,
                uthmani="second",
                search="second",
            ),
            verse(
                source_id="source-a",
                surah=2,
                ayah=1,
                uthmani="first",
                search="first",
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=2,
                ayah=1,
                uthmani="first",
                search="first",
            ),
            verse(
                source_id="source-b",
                surah=2,
                ayah=2,
                uthmani="second",
                search="second",
            ),
        )
    )

    report = verifier(
        2
    ).compare(
        source_a,
        source_b,
    )

    assert [
        comparison.reference
        for comparison
        in report.comparisons
    ] == [
        "2:1",
        "2:2",
    ]

    assert report.coverage_complete
    assert report.corpus_text_agrees
    assert report.cross_source_verified


def test_mixed_source_repository_is_rejected() -> None:
    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=1,
                ayah=1,
                uthmani="first",
                search="first",
            ),
            verse(
                source_id="another-source",
                surah=1,
                ayah=2,
                uthmani="second",
                search="second",
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=1,
                ayah=1,
                uthmani="first",
                search="first",
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="exactly one source",
    ):
        verifier(
            2
        ).compare(
            source_a,
            source_b,
        )


def test_empty_repository_is_rejected() -> None:
    source_a = QuranRepository(
        ()
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=1,
                ayah=1,
                uthmani="first",
                search="first",
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="empty Quran corpus",
    ):
        verifier(
            1
        ).compare(
            source_a,
            source_b,
        )


def test_invalid_expected_reference_count_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must be at least 1",
    ):
        QuranCrossSourceIntegrityVerifier(
            expected_reference_count=0
        )


def test_default_expected_reference_count_is_full_quran() -> None:
    """
    Production verifier defaults to the complete
    Hafs Quran reference count: 6236.
    """

    source_a = QuranRepository(
        (
            verse(
                source_id="source-a",
                surah=1,
                ayah=1,
                uthmani="same",
                search="same",
            ),
        )
    )

    source_b = QuranRepository(
        (
            verse(
                source_id="source-b",
                surah=1,
                ayah=1,
                uthmani="same",
                search="same",
            ),
        )
    )

    report = (
        QuranCrossSourceIntegrityVerifier()
        .compare(
            source_a,
            source_b,
        )
    )

    assert (
        report.expected_reference_count
        == 6236
    )

    assert (
        report.total_references
        == 1
    )

    assert not (
        report.coverage_complete
    )

    assert report.review_required

    assert not report.corpus_text_agrees