from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

from basira.sources.hadith.hadeethenc.parser import (
    HadeethEncOfficialParser,
)
from basira.sources.hadith.hadeethenc.verification import (
    detect_cross_version_grade_conflict,
)
from basira.sources.hadith.hadeethenc.workbook import (
    load_hadeethenc_arabic_workbook,
    load_hadeethenc_english_workbook,
)
from basira.sources.hadith.quranlab.parser import (
    QuranLabSnapshotParser,
)
from basira.verification.hadith_cross_source import (
    HadithCoverageRelation,
    HadithCrossSourceVerifier,
    HadithGradeRelation,
    HadithTextRelation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run full HadeethEnc official ↔ QuranLab "
            "cross-source Hadith verification."
        )
    )

    parser.add_argument(
        "--official-ar",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--official-en",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--quranlab-root",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def load_quranlab(
    root: Path,
    config: str,
) -> list[dict]:
    files = sorted(
        (root / config).glob(
            "*.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No Parquet files for {config}"
        )

    rows: list[dict] = []

    for file in files:
        rows.extend(
            pq.read_table(
                file
            ).to_pylist()
        )

    return rows


def main() -> int:
    args = parse_args()

    official_ar = (
        load_hadeethenc_arabic_workbook(
            args.official_ar
        )
    )

    official_en = (
        load_hadeethenc_english_workbook(
            args.official_en
        )
    )

    quranlab_ar_rows = load_quranlab(
        args.quranlab_root,
        "hadeethenc-ar",
    )

    quranlab_en_rows = load_quranlab(
        args.quranlab_root,
        "hadeethenc-en",
    )

    official_en_by_id = {
        row.id: row
        for row in official_en.rows
    }

    quranlab_ar_by_id = {
        int(row["hadeethenc_id"]): row
        for row in quranlab_ar_rows
    }

    quranlab_en_by_id = {
        int(row["hadeethenc_id"]): row
        for row in quranlab_en_rows
    }

    official_parser = (
        HadeethEncOfficialParser()
    )

    quranlab_parser = (
        QuranLabSnapshotParser()
    )

    verifier = (
        HadithCrossSourceVerifier(
            primary_source_id=(
                "hadeethenc-official"
            ),
            secondary_source_id=(
                "quranlab-hadith"
            ),
        )
    )

    coverage = Counter()
    text_relations = Counter()
    grade_relations = Counter()

    cross_source_review_ids: list[
        int
    ] = []

    cross_version_conflict_ids: list[
        int
    ] = []

    official_ids = {
        row.id
        for row in official_ar.rows
    }

    quranlab_ids = set(
        quranlab_ar_by_id
    )

    all_ids = sorted(
        official_ids
        | quranlab_ids
    )

    official_ar_by_id = {
        row.id: row
        for row in official_ar.rows
    }

    for hadith_id in all_ids:
        official_row = (
            official_ar_by_id.get(
                hadith_id
            )
        )

        quranlab_row = (
            quranlab_ar_by_id.get(
                hadith_id
            )
        )

        official_record = None
        quranlab_record = None

        if official_row is not None:
            english = (
                official_en_by_id.get(
                    hadith_id
                )
            )

            official_record = (
                official_parser.parse(
                    official_row.model_dump(),
                    arabic_release=(
                        official_ar.release
                    ),
                    english_payload=(
                        english.model_dump()
                        if english is not None
                        else None
                    ),
                    english_release=(
                        official_en.release
                        if english is not None
                        else None
                    ),
                )
            )

            if english is not None:
                conflict = (
                    detect_cross_version_grade_conflict(
                        official_row,
                        english,
                        arabic_release=(
                            official_ar.release
                        ),
                        english_release=(
                            official_en.release
                        ),
                    )
                )

                if conflict is not None:
                    cross_version_conflict_ids.append(
                        hadith_id
                    )

        if quranlab_row is not None:
            quranlab_english = (
                quranlab_en_by_id.get(
                    hadith_id
                )
            )

            quranlab_record = (
                quranlab_parser.parse(
                    config="hadeethenc-ar",
                    payload=quranlab_row,
                    paired_payload=(
                        quranlab_english
                    ),
                )
            )

        result = verifier.verify(
            primary=official_record,
            secondary=quranlab_record,
        )

        coverage[
            result.coverage_relation.value
        ] += 1

        text_relations[
            result.text_relation.value
        ] += 1

        grade_relations[
            result.grade_relation.value
        ] += 1

        if result.review_required:
            cross_source_review_ids.append(
                hadith_id
            )

    assert coverage[
        HadithCoverageRelation.SHARED.value
    ] == 3_574

    assert coverage[
        HadithCoverageRelation.PRIMARY_ONLY.value
    ] == 8

    assert coverage[
        HadithCoverageRelation.SECONDARY_ONLY.value
    ] == 0

    assert text_relations[
        HadithTextRelation.EXACT.value
    ] == 3_573

    assert text_relations[
        HadithTextRelation.DIACRITIC_VARIANT.value
    ] == 1

    assert text_relations[
        HadithTextRelation.TEXT_VARIANT.value
    ] == 0

    assert text_relations[
        HadithTextRelation.NOT_COMPARABLE.value
    ] == 8

    assert grade_relations[
        HadithGradeRelation.MATCH.value
    ] == 3_574

    assert grade_relations[
        HadithGradeRelation.CONFLICT.value
    ] == 0

    assert grade_relations[
        HadithGradeRelation.INSUFFICIENT.value
    ] == 8

    assert (
        cross_version_conflict_ids
        == [65065]
    )

    combined_review_ids = sorted(
        set(cross_source_review_ids)
        | set(
            cross_version_conflict_ids
        )
    )

    assert combined_review_ids == [
        65065,
        65585,
        65960,
        65990,
        66108,
        66109,
        66117,
        66285,
        66286,
    ]

    print("=" * 88)
    print(
        "BASIRA — HADITH CROSS-SOURCE VERIFIER"
    )
    print("=" * 88)

    print()
    print("COVERAGE")
    print(
        " Shared:",
        coverage["shared"],
    )
    print(
        " Official-only:",
        coverage["primary_only"],
    )
    print(
        " QuranLab-only:",
        coverage["secondary_only"],
    )

    print()
    print("TEXT RELATIONS")
    print(
        " Exact:",
        text_relations["exact"],
    )
    print(
        " Diacritic variants:",
        text_relations[
            "diacritic_variant"
        ],
    )
    print(
        " Material variants:",
        text_relations["text_variant"],
    )
    print(
        " Not comparable:",
        text_relations[
            "not_comparable"
        ],
    )

    print()
    print("GRADE RELATIONS")
    print(
        " Match:",
        grade_relations["match"],
    )
    print(
        " Conflict:",
        grade_relations["conflict"],
    )
    print(
        " Insufficient:",
        grade_relations["insufficient"],
    )

    print()
    print(
        "Cross-version grade conflicts:",
        cross_version_conflict_ids,
    )

    print(
        "Combined review IDs:",
        combined_review_ids,
    )

    print()
    print("=" * 88)
    print(
        "HADITH CROSS-SOURCE RESULT: PASS"
    )
    print(
        "3,574 shared records verified."
    )
    print(
        "1 diacritic-only text variant detected."
    )
    print(
        "0 material shared text variants detected."
    )
    print(
        "1 cross-version grade conflict preserved."
    )
    print(
        "8 official-only additions preserved."
    )
    print("=" * 88)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
