from __future__ import annotations

from pathlib import Path

from basira.sources.quran.kfgqpc_parser import (
    KfgqpcQuranParser,
)
from basira.sources.quran.repository import (
    QuranRepository,
)
from basira.sources.quran.tanzil.parser import (
    TanzilQuranParser,
)
from basira.verification.quran_integrity import (
    EXPECTED_QURAN_REFERENCE_COUNT,
    QuranCrossSourceIntegrityVerifier,
    QuranIntegrityReport,
    QuranIntegrityStatus,
)

KFGQPC_PATH = Path(
    "/mnt/c/Users/_/Downloads/"
    "kfgqpc-mirror/hafs/data/hafsData_v18.json"
)

TANZIL_BASE = Path(
    "/mnt/c/Users/_/Downloads/tanzil"
)

TANZIL_UTHMANI_PATH = (
    TANZIL_BASE
    / "quran-uthmani.txt"
)

TANZIL_SIMPLE_PLAIN_PATH = (
    TANZIL_BASE
    / "quran-simple-plain.txt"
)


def main() -> None:
    print("=" * 78)
    print(
        "BASIRA QURAN CROSS-SOURCE "
        "INTEGRITY SMOKE TEST"
    )
    print("=" * 78)

    _validate_files()

    print()
    print("Loading KFGQPC corpus...")

    kfgqpc_verses = (
        KfgqpcQuranParser()
        .parse_file(
            KFGQPC_PATH
        )
    )

    print(
        "KFGQPC verses:",
        len(kfgqpc_verses),
    )

    print()
    print("Loading Tanzil corpus...")

    tanzil_verses = (
        TanzilQuranParser()
        .parse_files(
            uthmani_path=(
                TANZIL_UTHMANI_PATH
            ),
            simple_plain_path=(
                TANZIL_SIMPLE_PLAIN_PATH
            ),
        )
    )

    print(
        "Tanzil verses:",
        len(tanzil_verses),
    )

    if (
        len(kfgqpc_verses)
        != EXPECTED_QURAN_REFERENCE_COUNT
    ):
        raise RuntimeError(
            "KFGQPC corpus does not contain "
            f"{EXPECTED_QURAN_REFERENCE_COUNT} "
            "references."
        )

    if (
        len(tanzil_verses)
        != EXPECTED_QURAN_REFERENCE_COUNT
    ):
        raise RuntimeError(
            "Tanzil corpus does not contain "
            f"{EXPECTED_QURAN_REFERENCE_COUNT} "
            "references."
        )

    kfgqpc_repository = QuranRepository(
        tuple(
            kfgqpc_verses
        )
    )

    tanzil_repository = QuranRepository(
        tuple(
            tanzil_verses
        )
    )

    print()
    print(
        "Running production cross-source "
        "integrity verifier..."
    )

    report = (
        QuranCrossSourceIntegrityVerifier()
        .compare(
            kfgqpc_repository,
            tanzil_repository,
        )
    )

    _print_report(
        report
    )

    _assert_expected_result(
        report=report,
    )


def _print_report(
    report: QuranIntegrityReport,
) -> None:
    print()
    print("=" * 78)
    print(
        "PRODUCTION INTEGRITY REPORT"
    )
    print("=" * 78)

    print(
        "Source A:",
        report.source_a_id,
    )

    print(
        "Source B:",
        report.source_b_id,
    )

    print()

    print(
        "Expected references:",
        report.expected_reference_count,
    )

    print(
        "References compared:",
        report.total_references,
    )

    print(
        "Coverage complete:",
        report.coverage_complete,
    )

    print()

    print(
        "Exact matches:",
        report.exact_matches,
    )

    print(
        "Orthographically equivalent:",
        report.orthographic_variants,
    )

    print(
        "Orthographically accounted for:",
        report.orthographically_accounted_for,
    )

    print(
        "Unresolved mismatches:",
        report.unresolved_mismatches,
    )

    print(
        "Unresolved segments:",
        report.unresolved_segments,
    )

    print(
        "Missing references:",
        report.missing_references,
    )

    print()

    print(
        "Corpus text agrees:",
        report.corpus_text_agrees,
    )

    print(
        "Cross-source verified:",
        report.cross_source_verified,
    )

    print(
        "Review required:",
        report.review_required,
    )

    _print_unresolved(
        report
    )

    _print_missing(
        report
    )

    print()
    print("=" * 78)

    if report.cross_source_verified:
        print(
            "RESULT: CROSS-SOURCE "
            "QURAN CORPUS VERIFIED"
        )

        print(
            "All expected Quran references "
            "are present and every observed "
            "cross-source text difference is "
            "deterministically accounted for."
        )

        print()

        print(
            "IMPORTANT:"
        )

        print(
            "This verifies corpus agreement only."
        )

        print(
            "It does NOT automatically grant "
            "runtime approval to either source."
        )

    else:
        print(
            "RESULT: REVIEW REQUIRED"
        )

        print(
            "Basira will not auto-resolve "
            "unexplained cross-source differences."
        )

    print("=" * 78)


def _print_unresolved(
    report: QuranIntegrityReport,
) -> None:
    unresolved = tuple(
        comparison
        for comparison
        in report.comparisons
        if (
            comparison.status
            == QuranIntegrityStatus
            .UNRESOLVED_MISMATCH
        )
    )

    if not unresolved:
        return

    print()
    print("=" * 78)
    print(
        "FIRST UNRESOLVED REFERENCES"
    )
    print("=" * 78)

    for comparison in unresolved[:20]:
        print()
        print(
            "Reference:",
            comparison.reference,
        )

        print(
            "Source A:",
            comparison.text_a,
        )

        print(
            "Source B:",
            comparison.text_b,
        )

        if (
            comparison.orthography
            is None
        ):
            continue

        for segment in (
            comparison
            .orthography
            .unresolved_segments
        ):
            print(
                "  Unresolved segment:"
            )

            print(
                "    Left:",
                repr(
                    segment.left_text
                ),
            )

            print(
                "    Right:",
                repr(
                    segment.right_text
                ),
            )

            print(
                "    Normalized left:",
                repr(
                    segment
                    .assessment
                    .normalized_left
                ),
            )

            print(
                "    Normalized right:",
                repr(
                    segment
                    .assessment
                    .normalized_right
                ),
            )


def _print_missing(
    report: QuranIntegrityReport,
) -> None:
    missing = tuple(
        comparison
        for comparison
        in report.comparisons
        if (
            comparison.status
            == QuranIntegrityStatus
            .REFERENCE_MISSING
        )
    )

    if not missing:
        return

    print()
    print("=" * 78)
    print(
        "MISSING REFERENCES"
    )
    print("=" * 78)

    for comparison in missing[:20]:
        print(
            comparison.reference,
            "A=",
            comparison.text_a is not None,
            "B=",
            comparison.text_b is not None,
        )


def _validate_files() -> None:
    paths = (
        KFGQPC_PATH,
        TANZIL_UTHMANI_PATH,
        TANZIL_SIMPLE_PLAIN_PATH,
    )

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(
                "Required Quran source file "
                f"not found: {path}"
            )


def _assert_expected_result(
    *,
    report: QuranIntegrityReport,
) -> None:
    """
    Fail the smoke test if the production integrity
    verifier does not reproduce the expected
    cross-source corpus result.
    """

    if (
        report.expected_reference_count
        != EXPECTED_QURAN_REFERENCE_COUNT
    ):
        raise AssertionError(
            "Unexpected Quran reference count."
        )

    if (
        report.total_references
        != EXPECTED_QURAN_REFERENCE_COUNT
    ):
        raise AssertionError(
            "Cross-source report does not contain "
            "all expected Quran references."
        )

    if not report.coverage_complete:
        raise AssertionError(
            "Quran corpus coverage is incomplete."
        )

    if report.missing_references != 0:
        raise AssertionError(
            "One Quran source is missing "
            "references."
        )

    if report.unresolved_mismatches != 0:
        raise AssertionError(
            "Unresolved Quran cross-source "
            "differences remain."
        )

    if report.unresolved_segments != 0:
        raise AssertionError(
            "Unresolved Quran orthography "
            "segments remain."
        )

    if (
        report.orthographically_accounted_for
        != EXPECTED_QURAN_REFERENCE_COUNT
    ):
        raise AssertionError(
            "Not all Quran references are "
            "orthographically accounted for."
        )

    if not report.corpus_text_agrees:
        raise AssertionError(
            "Corpus text agreement is false."
        )

    if not report.cross_source_verified:
        raise AssertionError(
            "Cross-source verification failed."
        )

    if report.review_required:
        raise AssertionError(
            "Cross-source report unexpectedly "
            "requires review."
        )


if __name__ == "__main__":
    main()