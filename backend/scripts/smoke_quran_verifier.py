from __future__ import annotations

from pathlib import Path

from basira.sources.quran.kfgqpc_parser import KfgqpcQuranParser
from basira.sources.quran.repository import QuranRepository
from basira.verification.quran_verifier import (
    QuranDifferenceKind,
    QuranQuoteStatus,
    QuranQuoteVerifier,
)

DATASET = Path(
    "/mnt/c/Users/_/Downloads/"
    "kfgqpc-mirror/hafs/data/hafsData_v18.json"
)

CORRECT_QUOTE = (
    "يا أيها الذين آمنوا استعينوا بالصبر "
    "والصلاة إن الله مع الصابرين"
)

ALTERED_QUOTE = (
    "يا أيها الذين آمنوا استعينوا بالصبر "
    "والصلاة إن الله يحب الصابرين"
)

AMBIGUOUS_QUOTE = "إن الله مع الصابرين"


def main() -> None:
    print("Loading KFGQPC Quran corpus...")

    verses = KfgqpcQuranParser().parse_file(
        DATASET
    )

    assert len(verses) == 6236

    repository = QuranRepository(
        verses
    )

    verifier = QuranQuoteVerifier(
        repository
    )

    # ---------------------------------------------------------
    # 1. Correct quotation
    # ---------------------------------------------------------

    correct = verifier.verify(
        CORRECT_QUOTE
    )

    assert correct.status in {
        QuranQuoteStatus.EXACT_MATCH,
        QuranQuoteStatus.NORMALIZED_MATCH,
    }

    assert len(correct.candidates) == 1

    correct_candidate = correct.candidates[0]

    assert (
        correct_candidate.reference
        == "2:153"
    )

    assert (
        correct.has_substantive_difference
        is False
    )

    print()
    print("=== CORRECT QUOTE ===")
    print(
        "Status:",
        correct.status,
    )
    print(
        "Reference:",
        correct_candidate.reference,
    )
    print(
        "Source:",
        correct_candidate.source_id,
    )
    print(
        "Canonical:",
        correct_candidate.canonical_text,
    )

    if correct.differences:
        print(
            "Non-substantive differences:"
        )

        for difference in correct.differences:
            print(
                " -",
                difference.kind,
                difference.expected,
                "->",
                difference.received,
            )

    # ---------------------------------------------------------
    # 2. Ambiguous short quotation
    # ---------------------------------------------------------

    ambiguous = verifier.verify(
        AMBIGUOUS_QUOTE
    )

    assert (
        ambiguous.status
        is QuranQuoteStatus.AMBIGUOUS
    )

    references = {
        candidate.reference
        for candidate
        in ambiguous.candidates
    }

    assert "2:153" in references
    assert "8:46" in references

    print()
    print(
        "=== AMBIGUOUS SHORT QUOTE ==="
    )
    print(
        "Status:",
        ambiguous.status,
    )
    print(
        "Candidates:",
        sorted(references),
    )

    # ---------------------------------------------------------
    # 3. Deliberately altered quotation
    # ---------------------------------------------------------

    altered = verifier.verify(
        ALTERED_QUOTE
    )

    assert (
        altered.status
        is QuranQuoteStatus.ALTERED_TEXT
    )

    assert len(altered.candidates) == 1

    altered_candidate = (
        altered.candidates[0]
    )

    assert (
        altered_candidate.reference
        == "2:153"
    )

    assert (
        altered.has_substantive_difference
        is True
    )

    orthographic = tuple(
        difference
        for difference
        in altered.differences
        if not difference.is_substantive
    )

    substantive = tuple(
        difference
        for difference
        in altered.differences
        if difference.is_substantive
    )

    # KFGQPC may represent:
    #
    #   ياأيها
    #
    # while the user writes:
    #
    #   يا أيها
    #
    # This must be visible but classified
    # as non-substantive.
    assert any(
        difference.kind
        is QuranDifferenceKind.ORTHOGRAPHIC
        and difference.expected
        == ("ياايها",)
        and difference.received
        == ("يا", "ايها")
        for difference
        in orthographic
    )

    # This is the actual textual alteration
    # we deliberately introduced.
    assert any(
        difference.kind
        is QuranDifferenceKind.SUBSTITUTION
        and difference.expected
        == ("مع",)
        and difference.received
        == ("يحب",)
        for difference
        in substantive
    )

    print()
    print("=== ALTERED QUOTE ===")

    print(
        "Status:",
        altered.status,
    )

    print(
        "Closest reference:",
        altered_candidate.reference,
    )

    print(
        "Source:",
        altered_candidate.source_id,
    )

    print(
        "Similarity:",
        round(
            altered_candidate.score,
            4,
        ),
    )

    print(
        "Canonical:",
        altered_candidate.canonical_text,
    )

    print(
        "Received:",
        ALTERED_QUOTE,
    )

    print()
    print(
        "Orthographic differences:"
    )

    if not orthographic:
        print(" - None")

    for difference in orthographic:
        print(
            " -",
            difference.expected,
            "->",
            difference.received,
            f"[{difference.kind}]",
        )

    print()
    print(
        "Substantive differences:"
    )

    if not substantive:
        print(" - None")

    for difference in substantive:
        print(
            " -",
            difference.expected,
            "->",
            difference.received,
            f"[{difference.kind}]",
        )

    print()
    print(
        "Quran verification smoke: PASS"
    )


if __name__ == "__main__":
    main()