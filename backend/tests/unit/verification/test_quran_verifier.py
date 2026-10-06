import pytest

from basira.models.quran import QuranVerse
from basira.sources.quran.repository import QuranRepository
from basira.verification.quran_verifier import (
    QuranDifferenceKind,
    QuranQuoteStatus,
    QuranQuoteVerifier,
)


@pytest.fixture
def repository() -> QuranRepository:
    verses = (
        QuranVerse(
            source_id="test-quran-source",
            surah_number=2,
            ayah_number=153,
            surah_name_ar="البقرة",
            surah_name_en="Al-Baqarah",
            juz_number=2,
            page_number=23,
            text_uthmani=(
                "ياأيها الذين آمنوا "
                "استعينوا بالصبر والصلاة "
                "إن الله مع الصابرين"
            ),
            text_search=(
                "ياأيها الذين آمنوا "
                "استعينوا بالصبر والصلاة "
                "إن الله مع الصابرين"
            ),
        ),
        QuranVerse(
            source_id="test-quran-source",
            surah_number=8,
            ayah_number=46,
            surah_name_ar="الأنفال",
            surah_name_en="Al-Anfal",
            juz_number=10,
            page_number=183,
            text_uthmani=(
                "وأطيعوا الله ورسوله "
                "ولا تنازعوا فتفشلوا "
                "وتذهب ريحكم واصبروا "
                "إن الله مع الصابرين"
            ),
            text_search=(
                "وأطيعوا الله ورسوله "
                "ولا تنازعوا فتفشلوا "
                "وتذهب ريحكم واصبروا "
                "إن الله مع الصابرين"
            ),
        ),
    )

    return QuranRepository(verses)


@pytest.fixture
def verifier(
    repository: QuranRepository,
) -> QuranQuoteVerifier:
    return QuranQuoteVerifier(repository)


def test_correct_full_quote_matches_expected_verse(
    verifier: QuranQuoteVerifier,
) -> None:
    result = verifier.verify(
        "يا أيها الذين آمنوا "
        "استعينوا بالصبر والصلاة "
        "إن الله مع الصابرين"
    )

    assert result.status in {
        QuranQuoteStatus.EXACT_MATCH,
        QuranQuoteStatus.NORMALIZED_MATCH,
    }

    assert len(result.candidates) == 1
    assert result.candidates[0].reference == "2:153"
    assert (
        result.candidates[0].source_id
        == "test-quran-source"
    )


def test_short_quote_is_ambiguous_between_two_verses(
    verifier: QuranQuoteVerifier,
) -> None:
    result = verifier.verify(
        "إن الله مع الصابرين"
    )

    assert (
        result.status
        == QuranQuoteStatus.AMBIGUOUS
    )

    references = {
        candidate.reference
        for candidate in result.candidates
    }

    assert references == {
        "2:153",
        "8:46",
    }


def test_exact_full_match_wins_over_partial_overlap(
    verifier: QuranQuoteVerifier,
) -> None:
    quote = (
        "وأطيعوا الله ورسوله "
        "ولا تنازعوا فتفشلوا "
        "وتذهب ريحكم واصبروا "
        "إن الله مع الصابرين"
    )

    result = verifier.verify(
        quote
    )

    assert (
        result.status
        == QuranQuoteStatus.EXACT_MATCH
    )

    assert len(result.candidates) == 1
    assert (
        result.candidates[0].reference
        == "8:46"
    )


def test_altered_quote_detects_substantive_substitution(
    verifier: QuranQuoteVerifier,
) -> None:
    result = verifier.verify(
        "يا أيها الذين آمنوا "
        "استعينوا بالصبر والصلاة "
        "إن الله يحب الصابرين"
    )

    assert (
        result.status
        == QuranQuoteStatus.ALTERED_TEXT
    )

    assert result.candidates
    assert (
        result.candidates[0].reference
        == "2:153"
    )

    assert result.has_substantive_difference

    substitutions = [
        difference
        for difference in result.differences
        if (
            difference.kind
            == QuranDifferenceKind.SUBSTITUTION
        )
    ]

    assert substitutions

    assert any(
        difference.expected == ("مع",)
        and difference.received == ("يحب",)
        and difference.is_substantive
        for difference in substitutions
    )


def test_spacing_difference_is_orthographic(
    verifier: QuranQuoteVerifier,
) -> None:
    result = verifier.verify(
        "يا أيها الذين آمنوا "
        "استعينوا بالصبر والصلاة "
        "إن الله مع الصابرين"
    )

    assert result.status in {
        QuranQuoteStatus.EXACT_MATCH,
        QuranQuoteStatus.NORMALIZED_MATCH,
    }

    assert result.candidates
    assert (
        result.candidates[0].reference
        == "2:153"
    )

    orthographic_differences = [
        difference
        for difference in result.differences
        if (
            difference.kind
            == QuranDifferenceKind.ORTHOGRAPHIC
        )
    ]

    assert orthographic_differences

    assert all(
        not difference.is_substantive
        for difference
        in orthographic_differences
    )


def test_unrelated_text_is_not_found(
    verifier: QuranQuoteVerifier,
) -> None:
    result = verifier.verify(
        "هذا نص مختلف لا علاقة له بالآيات"
    )

    assert (
        result.status
        == QuranQuoteStatus.NOT_FOUND
    )

    assert result.candidates == ()


def test_empty_text_is_not_found(
    verifier: QuranQuoteVerifier,
) -> None:
    result = verifier.verify(
        "   "
    )

    assert (
        result.status
        == QuranQuoteStatus.NOT_FOUND
    )

    assert result.candidates == ()


def test_short_unmatched_text_is_not_marked_as_altered(
    verifier: QuranQuoteVerifier,
) -> None:
    result = verifier.verify(
        "نص قصير مختلف"
    )

    assert (
        result.status
        == QuranQuoteStatus.NOT_FOUND
    )

    assert result.candidates == ()


def test_verifier_supports_source_without_surah_names() -> None:
    verse = QuranVerse(
        source_id="independent-source",
        surah_number=2,
        ayah_number=153,
        text_uthmani=(
            "يَا أَيُّهَا الَّذِينَ آمَنُوا "
            "اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ "
            "إِنَّ اللَّهَ مَعَ الصَّابِرِينَ"
        ),
        text_search=(
            "يَا أَيُّهَا الَّذِينَ آمَنُوا "
            "اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ "
            "إِنَّ اللَّهَ مَعَ الصَّابِرِينَ"
        ),
    )

    repository = QuranRepository(
        (verse,)
    )

    verifier = QuranQuoteVerifier(
        repository
    )

    result = verifier.verify(
        "يا أيها الذين آمنوا "
        "استعينوا بالصبر والصلاة "
        "إن الله مع الصابرين"
    )

    assert result.candidates
    assert (
        result.candidates[0].reference
        == "2:153"
    )

    assert (
        result.candidates[0].surah_name_ar
        is None
    )

    assert (
        result.candidates[0].surah_name_en
        is None
    )