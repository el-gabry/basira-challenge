from pathlib import Path

from basira.normalization.quran import (
    normalize_quran_search_text,
)
from basira.sources.quran.repository import QuranRepository
from basira.sources.quran.tanzil.parser import (
    TANZIL_SOURCE_ID,
    TanzilQuranParser,
)
from basira.verification.quran_verifier import (
    QuranQuoteStatus,
    QuranQuoteVerifier,
)

BASE = Path(
    "/mnt/c/Users/_/Downloads/tanzil"
)


def main() -> None:
    verses = TanzilQuranParser().parse_files(
        uthmani_path=BASE / "quran-uthmani.txt",
        simple_plain_path=(
            BASE / "quran-simple-plain.txt"
        ),
    )

    assert len(verses) == 6236

    repository = QuranRepository(
        verses
    )

    assert len(repository) == 6236

    verse = repository.require(
        2,
        153,
    )

    assert verse.reference == "2:153"
    assert verse.source_id == TANZIL_SOURCE_ID

    expected = normalize_quran_search_text(
        "إن الله مع الصابرين"
    )

    assert expected in (
        normalize_quran_search_text(
            verse.text_search
        )
    )

    verifier = QuranQuoteVerifier(
        repository
    )

    correct = verifier.verify(
        "يا أيها الذين آمنوا "
        "استعينوا بالصبر والصلاة "
        "إن الله مع الصابرين"
    )

    assert correct.status in {
        QuranQuoteStatus.EXACT_MATCH,
        QuranQuoteStatus.NORMALIZED_MATCH,
    }

    assert correct.candidates
    assert (
        correct.candidates[0].reference
        == "2:153"
    )

    ambiguous = verifier.verify(
        "إن الله مع الصابرين"
    )

    assert (
        ambiguous.status
        == QuranQuoteStatus.AMBIGUOUS
    )

    references = {
        candidate.reference
        for candidate in ambiguous.candidates
    }

    assert "2:153" in references
    assert "8:46" in references

    altered = verifier.verify(
        "يا أيها الذين آمنوا "
        "استعينوا بالصبر والصلاة "
        "إن الله يحب الصابرين"
    )

    assert (
        altered.status
        == QuranQuoteStatus.ALTERED_TEXT
    )

    assert altered.candidates
    assert (
        altered.candidates[0].reference
        == "2:153"
    )

    assert altered.has_substantive_difference

    print("Tanzil smoke: PASS")
    print("Verses:", len(repository))
    print(
        "Source:",
        verse.source_id,
    )
    print(
        "Correct quote:",
        correct.status.value,
    )
    print(
        "Ambiguous quote:",
        ambiguous.status.value,
    )
    print(
        "Altered quote:",
        altered.status.value,
    )
    print(
        "Closest altered reference:",
        altered.candidates[0].reference,
    )


if __name__ == "__main__":
    main()