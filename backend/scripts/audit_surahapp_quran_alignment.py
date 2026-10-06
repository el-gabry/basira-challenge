from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from basira.sources.quran.tanzil.parser import (
    TanzilQuranParser,
)
from basira.verification.quran_orthography import (
    QuranScriptType,
    QuranSourceProfile,
)
from basira.verification.quran_orthography_segments import (
    QuranOrthographySegmentComparator,
    QuranOrthographySequenceRelation,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SourceConfig:
    slug: str
    coverage_mode: str


SOURCES = {
    config.slug: config
    for config in (
        SourceConfig(
            slug="tafsir-katheer",
            coverage_mode="complete_quran",
        ),
        SourceConfig(
            slug="tafsir-saadi",
            coverage_mode="complete_quran",
        ),
        SourceConfig(
            slug="tafsir-mokhtasar",
            coverage_mode="complete_quran",
        ),
        SourceConfig(
            slug="ayat-nozool",
            coverage_mode="sparse",
        ),
    )
}


def load_json(
    path: Path,
) -> object:
    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def write_json(
    path: Path,
    value: object,
) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def build_tanzil_index(
    *,
    uthmani_path: Path,
    simple_plain_path: Path,
) -> dict[
    tuple[int, int],
    str,
]:
    verses = (
        TanzilQuranParser()
        .parse_files(
            uthmani_path,
            simple_plain_path,
        )
    )

    index = {
        (
            verse.surah_number,
            verse.ayah_number,
        ): verse.text_uthmani
        for verse in verses
    }

    if len(index) != 6_236:
        raise ValueError(
            "Expected 6236 Tanzil verses, "
            f"received {len(index)}."
        )

    return index


def load_surahapp_corpus(
    path: Path,
) -> dict[
    tuple[int, int],
    dict[str, object],
]:
    payload = load_json(
        path
    )

    if not isinstance(
        payload,
        list,
    ):
        raise ValueError(
            f"{path}: corpus must be a list."
        )

    index: dict[
        tuple[int, int],
        dict[str, object],
    ] = {}

    for row in payload:
        if not isinstance(
            row,
            dict,
        ):
            raise ValueError(
                f"{path}: row must be an object."
            )

        reference = (
            int(
                str(
                    row["sura_number"]
                )
            ),
            int(
                str(
                    row["aya_number"]
                )
            ),
        )

        if reference in index:
            raise ValueError(
                "Duplicate Surah App reference: "
                f"{reference[0]}:"
                f"{reference[1]}"
            )

        index[
            reference
        ] = row

    return index


def audit_source(
    *,
    config: SourceConfig,
    corpus_path: Path,
    tanzil_index: dict[
        tuple[int, int],
        str,
    ],
    comparator: (
        QuranOrthographySegmentComparator
    ),
    output_dir: Path,
) -> dict[str, object]:
    source_index = (
        load_surahapp_corpus(
            corpus_path
        )
    )

    canonical_refs = set(
        tanzil_index
    )

    source_refs = set(
        source_index
    )

    extra_refs = sorted(
        source_refs
        - canonical_refs
    )

    if extra_refs:
        raise ValueError(
            f"{config.slug}: references outside "
            "canonical Quran universe: "
            f"{extra_refs[:20]}"
        )

    unattested_refs = sorted(
        canonical_refs
        - source_refs
    )

    if (
        config.coverage_mode
        == "complete_quran"
        and unattested_refs
    ):
        raise ValueError(
            f"{config.slug}: complete source is "
            "missing canonical references: "
            f"{unattested_refs[:20]}"
        )

    tanzil_profile = (
        QuranSourceProfile(
            source_id=(
                "tanzil-quran-v1.1-uthmani"
            ),
            source_name=(
                "Tanzil Quran Uthmani"
            ),
            script=(
                QuranScriptType.UTHMANI
            ),
            narration="hafs",
        )
    )

    source_profile = (
        QuranSourceProfile(
            source_id=(
                f"surahapp-{config.slug}"
            ),
            source_name=(
                f"Surah App {config.slug}"
            ),
            source_url=(
                "https://surahapp.com/"
            ),
            script=(
                QuranScriptType.UTHMANI
            ),
            narration="hafs",
        )
    )

    counts: Counter[str] = (
        Counter()
    )

    unresolved: list[
        dict[str, object]
    ] = []

    samples: list[
        dict[str, object]
    ] = []

    references_to_check = sorted(
        source_refs
    )

    total = len(
        references_to_check
    )

    for index, reference in enumerate(
        references_to_check,
        start=1,
    ):
        surah, ayah = reference

        canonical_text = (
            tanzil_index[
                reference
            ]
        )

        source_text = str(
            source_index[
                reference
            ]["aya_text"]
        )

        if (
            canonical_text
            == source_text
        ):
            counts[
                "exact_match"
            ] += 1
            continue

        assessment = (
            comparator.compare(
                left_text=(
                    canonical_text
                ),
                right_text=(
                    source_text
                ),
                left_profile=(
                    tanzil_profile
                ),
                right_profile=(
                    source_profile
                ),
                surah_number=surah,
                ayah_number=ayah,
            )
        )

        relation = (
            assessment.relation.value
        )

        counts[
            relation
        ] += 1

        if (
            assessment.relation
            == QuranOrthographySequenceRelation
            .ORTHOGRAPHICALLY_EQUIVALENT
        ):
            if len(samples) < 20:
                samples.append(
                    {
                        "reference": (
                            f"{surah}:{ayah}"
                        ),
                        "canonical_text": (
                            canonical_text
                        ),
                        "source_text": (
                            source_text
                        ),
                    }
                )
        else:
            unresolved.append(
                {
                    "reference": (
                        f"{surah}:{ayah}"
                    ),
                    "canonical_text": (
                        canonical_text
                    ),
                    "source_text": (
                        source_text
                    ),
                    "relation": (
                        relation
                    ),
                    "unresolved_segments": [
                        {
                            "left_text": (
                                segment.left_text
                            ),
                            "right_text": (
                                segment.right_text
                            ),
                            "relation": (
                                segment
                                .relation
                                .value
                            ),
                        }
                        for segment
                        in (
                            assessment
                            .unresolved_segments
                        )
                    ],
                }
            )

        if index % 500 == 0:
            print(
                f"[{config.slug}] "
                f"{index}/{total}"
            )

    exact = counts[
        "exact_match"
    ]

    equivalent = counts[
        "orthographically_equivalent"
    ]

    unresolved_count = len(
        unresolved
    )

    accounted_for = (
        exact
        + equivalent
    )

    report = {
        "source_slug": (
            config.slug
        ),
        "coverage_mode": (
            config.coverage_mode
        ),
        "canonical_source": (
            "tanzil-quran-v1.1-uthmani"
        ),
        "script_comparison": (
            "uthmani_to_uthmani"
        ),
        "narration": "hafs",
        "canonical_reference_count": (
            len(canonical_refs)
        ),
        "source_reference_count": (
            len(source_refs)
        ),
        "unattested_reference_count": (
            len(unattested_refs)
        ),
        "exact_matches": exact,
        "orthographically_equivalent": (
            equivalent
        ),
        "orthographically_accounted_for": (
            accounted_for
        ),
        "unresolved_reference_count": (
            unresolved_count
        ),
        "relation_counts": dict(
            sorted(
                counts.items()
            )
        ),
        "status": (
            "PASS"
            if unresolved_count == 0
            else "REVIEW_REQUIRED"
        ),
        "orthographic_samples": (
            samples
        ),
        "unresolved": (
            unresolved
        ),
    }

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / (
            f"{config.slug}"
            "-quran-alignment.json"
        )
    )

    write_json(
        output_path,
        report,
    )

    print()
    print("=" * 72)
    print(config.slug)
    print("=" * 72)
    print(
        "Coverage mode:",
        config.coverage_mode,
    )
    print(
        "Canonical references:",
        len(canonical_refs),
    )
    print(
        "Source references:",
        len(source_refs),
    )

    if (
        config.coverage_mode
        == "sparse"
    ):
        print(
            "No source entry:",
            len(unattested_refs),
            "(allowed for sparse source)",
        )

    print(
        "Exact Uthmani matches:",
        exact,
    )
    print(
        "Orthographically equivalent:",
        equivalent,
    )
    print(
        "Accounted for:",
        accounted_for,
    )
    print(
        "Unresolved:",
        unresolved_count,
    )
    print(
        "STATUS:",
        report["status"],
    )
    print(
        "Report:",
        output_path,
    )

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--uthmani",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--simple-plain",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--snapshot-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        default=None,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    requested = (
        args.sources
        if args.sources
        else list(SOURCES)
    )

    unknown = (
        set(requested)
        - set(SOURCES)
    )

    if unknown:
        raise ValueError(
            "Unknown source(s): "
            f"{sorted(unknown)}"
        )

    tanzil_index = (
        build_tanzil_index(
            uthmani_path=(
                args.uthmani
            ),
            simple_plain_path=(
                args.simple_plain
            ),
        )
    )

    comparator = (
        QuranOrthographySegmentComparator()
    )

    output_dir = (
        args.snapshot_root
        / "audits"
        / "quran-alignment"
    )

    reports = []

    for source_slug in requested:
        config = (
            SOURCES[
                source_slug
            ]
        )

        corpus_path = (
            args.snapshot_root
            / source_slug
            / "corpus.json"
        )

        if not corpus_path.exists():
            raise FileNotFoundError(
                corpus_path
            )

        reports.append(
            audit_source(
                config=config,
                corpus_path=(
                    corpus_path
                ),
                tanzil_index=(
                    tanzil_index
                ),
                comparator=(
                    comparator
                ),
                output_dir=(
                    output_dir
                ),
            )
        )

    summary = {
        "sources": [
            {
                "source_slug": (
                    report[
                        "source_slug"
                    ]
                ),
                "coverage_mode": (
                    report[
                        "coverage_mode"
                    ]
                ),
                "source_reference_count": (
                    report[
                        "source_reference_count"
                    ]
                ),
                "exact_matches": (
                    report[
                        "exact_matches"
                    ]
                ),
                "orthographically_equivalent": (
                    report[
                        "orthographically_equivalent"
                    ]
                ),
                "unresolved_reference_count": (
                    report[
                        "unresolved_reference_count"
                    ]
                ),
                "status": (
                    report[
                        "status"
                    ]
                ),
            }
            for report in reports
        ],
    }

    write_json(
        output_dir
        / "summary.json",
        summary,
    )

    print()
    print("=" * 88)
    print(
        "SURAH APP QURAN ALIGNMENT SUMMARY"
    )
    print("=" * 88)

    for report in reports:
        print(
            report["source_slug"],
            "→",
            report["status"],
            "| refs:",
            report[
                "source_reference_count"
            ],
            "| exact:",
            report["exact_matches"],
            "| orthographic:",
            report[
                "orthographically_equivalent"
            ],
            "| unresolved:",
            report[
                "unresolved_reference_count"
            ],
        )

    return (
        0
        if all(
            report["status"]
            == "PASS"
            for report in reports
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
