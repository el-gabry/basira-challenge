from __future__ import annotations

from collections import Counter
from pathlib import Path

from basira.sources.quran.kfgqpc_parser import (
    KfgqpcQuranParser,
)
from basira.sources.quran.tanzil.parser import (
    TanzilQuranParser,
)
from basira.verification.quran_orthography import (
    QuranOrthographyRelation,
    QuranScriptType,
    QuranSourceProfile,
)
from basira.verification.quran_orthography_segments import (
    QuranOrthographySegmentComparator,
    QuranOrthographySequenceRelation,
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


KFGQPC_PROFILE = QuranSourceProfile(
    source_id="kfgqpc-hafs-mirror-v18",
    source_name="KFGQPC Hafs Mirror v18",
    script=QuranScriptType.UTHMANI,
    narration="hafs",
)

TANZIL_PROFILE = QuranSourceProfile(
    source_id="tanzil-quran-v1.1-uthmani",
    source_name="Tanzil Quran Uthmani v1.1",
    script=QuranScriptType.UTHMANI,
    narration="hafs",
)


def index_verses(
    verses: tuple | list,
) -> dict[
    tuple[int, int],
    object,
]:
    return {
        (
            verse.surah_number,
            verse.ayah_number,
        ): verse
        for verse in verses
    }


def reference_text(
    reference: tuple[int, int],
) -> str:
    return (
        f"{reference[0]}:"
        f"{reference[1]}"
    )


def main() -> None:
    if not KFGQPC_PATH.exists():
        raise FileNotFoundError(
            "KFGQPC file not found: "
            f"{KFGQPC_PATH}"
        )

    if not TANZIL_UTHMANI_PATH.exists():
        raise FileNotFoundError(
            "Tanzil Uthmani file not found: "
            f"{TANZIL_UTHMANI_PATH}"
        )

    if not TANZIL_SIMPLE_PLAIN_PATH.exists():
        raise FileNotFoundError(
            "Tanzil Simple Plain file not found: "
            f"{TANZIL_SIMPLE_PLAIN_PATH}"
        )

    print(
        "Loading KFGQPC..."
    )

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

    print(
        "Loading Tanzil..."
    )

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

    if len(kfgqpc_verses) != 6236:
        raise ValueError(
            "Expected exactly 6236 "
            "KFGQPC verses."
        )

    if len(tanzil_verses) != 6236:
        raise ValueError(
            "Expected exactly 6236 "
            "Tanzil verses."
        )

    kfgqpc_index = index_verses(
        kfgqpc_verses
    )

    tanzil_index = index_verses(
        tanzil_verses
    )

    kfgqpc_refs = set(
        kfgqpc_index
    )

    tanzil_refs = set(
        tanzil_index
    )

    missing_from_kfgqpc = (
        tanzil_refs
        - kfgqpc_refs
    )

    missing_from_tanzil = (
        kfgqpc_refs
        - tanzil_refs
    )

    print()
    print(
        "Missing from KFGQPC:",
        len(missing_from_kfgqpc),
    )

    print(
        "Missing from Tanzil:",
        len(missing_from_tanzil),
    )

    references = sorted(
        kfgqpc_refs
        & tanzil_refs
    )

    comparator = (
        QuranOrthographySegmentComparator()
    )

    sequence_counts: Counter[
        QuranOrthographySequenceRelation
    ] = Counter()

    segment_counts: Counter[
        QuranOrthographyRelation
    ] = Counter()

    rule_counts: Counter[str] = Counter()

    unresolved_results: list[
        tuple[
            tuple[int, int],
            object,
        ]
    ] = []

    multi_rule_results: list[
        tuple[
            tuple[int, int],
            object,
        ]
    ] = []

    total_segments = 0

    print()
    print(
        "Running segment-level "
        "Uthmani ↔ Uthmani comparison..."
    )

    for reference in references:
        kfgqpc = (
            kfgqpc_index[
                reference
            ]
        )

        tanzil = (
            tanzil_index[
                reference
            ]
        )

        result = (
            comparator.compare(
                left_text=(
                    kfgqpc.text_uthmani
                ),
                right_text=(
                    tanzil.text_uthmani
                ),
                left_profile=(
                    KFGQPC_PROFILE
                ),
                right_profile=(
                    TANZIL_PROFILE
                ),
                surah_number=(
                    reference[0]
                ),
                ayah_number=(
                    reference[1]
                ),
            )
        )

        sequence_counts[
            result.relation
        ] += 1

        total_segments += len(
            result.segments
        )

        for segment in (
            result.segments
        ):
            segment_counts[
                segment.relation
            ] += 1

            if (
                segment.rule_id
                is not None
            ):
                rule_counts[
                    segment.rule_id.value
                ] += 1

        if (
            result.relation
            == QuranOrthographySequenceRelation
            .UNRESOLVED
        ):
            unresolved_results.append(
                (
                    reference,
                    result,
                )
            )

        if len(
            result.rule_ids
        ) > 1:
            multi_rule_results.append(
                (
                    reference,
                    result,
                )
            )

    print()
    print(
        "=" * 78
    )
    print(
        "QURAN ORTHOGRAPHY AUDIT"
    )
    print(
        "=" * 78
    )

    print(
        "References compared:",
        len(references),
    )

    print(
        "Missing from KFGQPC:",
        len(missing_from_kfgqpc),
    )

    print(
        "Missing from Tanzil:",
        len(missing_from_tanzil),
    )

    print(
        "Total aligned segments:",
        total_segments,
    )

    print()
    print(
        "SEQUENCE RESULTS"
    )
    print(
        "-" * 78
    )

    print(
        "Exact:",
        sequence_counts[
            QuranOrthographySequenceRelation
            .EXACT_MATCH
        ],
    )

    print(
        "Orthographically equivalent:",
        sequence_counts[
            QuranOrthographySequenceRelation
            .ORTHOGRAPHICALLY_EQUIVALENT
        ],
    )

    print(
        "Unresolved:",
        sequence_counts[
            QuranOrthographySequenceRelation
            .UNRESOLVED
        ],
    )

    print()
    print(
        "SEGMENT RESULTS"
    )
    print(
        "-" * 78
    )

    for relation, count in (
        segment_counts.most_common()
    ):
        print(
            f"{relation.value}: {count}"
        )

    print()
    print(
        "SOURCE-BACKED RULES USED"
    )
    print(
        "-" * 78
    )

    if rule_counts:
        for rule, count in (
            rule_counts.most_common()
        ):
            print(
                f"{rule}: {count}"
            )
    else:
        print(
            "No source-backed rules "
            "were required."
        )

    print()
    print(
        "Verses using multiple rules:",
        len(multi_rule_results),
    )

    print()
    print(
        "=" * 78
    )
    print(
        "FIRST UNRESOLVED VERSES"
    )
    print(
        "=" * 78
    )

    if not unresolved_results:
        print(
            "None."
        )

    for (
        reference,
        result,
    ) in unresolved_results[:30]:
        kfgqpc = (
            kfgqpc_index[
                reference
            ]
        )

        tanzil = (
            tanzil_index[
                reference
            ]
        )

        print()
        print(
            "-" * 78
        )

        print(
            "Reference:",
            reference_text(
                reference
            ),
        )

        print(
            "KFGQPC:"
        )

        print(
            kfgqpc.text_uthmani
        )

        print()

        print(
            "Tanzil:"
        )

        print(
            tanzil.text_uthmani
        )

        print()

        print(
            "Unresolved segments:"
        )

        for segment in (
            result.unresolved_segments
        ):
            print()

            print(
                "  Left:",
                repr(
                    segment.left_text
                ),
            )

            print(
                "  Right:",
                repr(
                    segment.right_text
                ),
            )

            print(
                "  Normalized left:",
                repr(
                    segment
                    .assessment
                    .normalized_left
                ),
            )

            print(
                "  Normalized right:",
                repr(
                    segment
                    .assessment
                    .normalized_right
                ),
            )

    print()
    print(
        "=" * 78
    )

    unresolved_count = (
        sequence_counts[
            QuranOrthographySequenceRelation
            .UNRESOLVED
        ]
    )

    if (
        not missing_from_kfgqpc
        and not missing_from_tanzil
        and unresolved_count == 0
    ):
        print(
            "RESULT: ALL REFERENCES "
            "ORTHOGRAPHICALLY ACCOUNTED FOR"
        )
    else:
        print(
            "RESULT: FURTHER REVIEW REQUIRED"
        )

        print(
            "No unresolved difference "
            "will be auto-classified as "
            "a Quran textual error."
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()