from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from basira.models.hadith import (
    HadithGradeCategory,
)
from basira.sources.hadith.hadeethenc.parser import (
    HadeethEncOfficialParser,
)
from basira.sources.hadith.hadeethenc.workbook import (
    load_hadeethenc_arabic_workbook,
    load_hadeethenc_english_workbook,
)

EXPECTED_ARABIC = 3_582
EXPECTED_ENGLISH = 2_328
EXPECTED_ARABIC_ONLY = (
    EXPECTED_ARABIC
    - EXPECTED_ENGLISH
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run full Basira smoke validation "
            "against official HadeethEnc XLSX releases."
        )
    )

    parser.add_argument(
        "--arabic",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--english",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    arabic_workbook = (
        load_hadeethenc_arabic_workbook(
            args.arabic
        )
    )

    english_workbook = (
        load_hadeethenc_english_workbook(
            args.english
        )
    )

    print("=" * 88)
    print(
        "BASIRA — HADEETHENC OFFICIAL FULL SMOKE"
    )
    print("=" * 88)

    print(
        "Arabic release:",
        arabic_workbook.release.version,
        "|",
        arabic_workbook.release.last_updated,
    )

    print(
        "English release:",
        english_workbook.release.version,
        "|",
        english_workbook.release.last_updated,
    )

    print()

    assert (
        len(arabic_workbook.rows)
        == EXPECTED_ARABIC
    )

    assert (
        len(english_workbook.rows)
        == EXPECTED_ENGLISH
    )

    arabic_by_id = {
        row.id: row
        for row in arabic_workbook.rows
    }

    english_by_id = {
        row.id: row
        for row in english_workbook.rows
    }

    assert (
        len(arabic_by_id)
        == EXPECTED_ARABIC
    ), "Duplicate Arabic HadeethEnc IDs."

    assert (
        len(english_by_id)
        == EXPECTED_ENGLISH
    ), "Duplicate English HadeethEnc IDs."

    english_only = (
        set(english_by_id)
        - set(arabic_by_id)
    )

    assert not english_only, (
        "English records exist without Arabic "
        f"primary records: {sorted(english_only)}"
    )

    parser = (
        HadeethEncOfficialParser()
    )

    record_ids: set[str] = set()

    parsed = 0
    english_paired = 0
    arabic_only = 0
    graded = 0

    grade_categories: Counter[
        str
    ] = Counter()

    cross_version_grade_conflicts: list[
        int
    ] = []

    for arabic in arabic_workbook.rows:
        english = english_by_id.get(
            arabic.id
        )

        record = parser.parse(
            arabic.model_dump(),
            arabic_release=(
                arabic_workbook.release
            ),
            english_payload=(
                english.model_dump()
                if english is not None
                else None
            ),
            english_release=(
                english_workbook.release
                if english is not None
                else None
            ),
        )

        variant = (
            record.text_variants[0]
        )

        assert (
            variant.arabic_text
            == arabic.hadith_text
        )

        if english is None:
            assert (
                variant.english_translation
                is None
            )

            arabic_only += 1

        else:
            assert (
                variant.english_translation
                == english.hadith_text
            )

            english_paired += 1

            if (
                record.notes is not None
                and "cross_version_grade_conflict"
                in record.notes
            ):
                cross_version_grade_conflicts.append(
                    arabic.id
                )

        assert (
            record.record_id
            not in record_ids
        )

        record_ids.add(
            record.record_id
        )

        if record.grade_assessments:
            graded += 1

            for assessment in (
                record.grade_assessments
            ):
                grade_categories[
                    assessment.category.value
                ] += 1

        parsed += 1

    assert parsed == EXPECTED_ARABIC

    assert (
        len(record_ids)
        == EXPECTED_ARABIC
    )

    assert (
        english_paired
        == EXPECTED_ENGLISH
    )

    assert (
        arabic_only
        == EXPECTED_ARABIC_ONLY
    )

    assert (
        cross_version_grade_conflicts
        == [65065]
    ), (
        "Unexpected cross-version grade conflicts: "
        f"{cross_version_grade_conflicts}"
    )

    print(
        "Official Arabic records:",
        f"{len(arabic_workbook.rows):,}",
    )

    print(
        "Official English records:",
        f"{len(english_workbook.rows):,}",
    )

    print(
        "Primary records parsed:",
        f"{parsed:,}",
    )

    print(
        "Unique record IDs:",
        f"{len(record_ids):,}",
    )

    print(
        "English representations paired:",
        f"{english_paired:,}",
    )

    print(
        "Arabic-only records:",
        f"{arabic_only:,}",
    )

    print(
        "Records with attributed grades:",
        f"{graded:,}",
    )

    print(
        "Cross-version grade conflicts:",
        len(
            cross_version_grade_conflicts
        ),
    )

    print(
        "Conflict IDs:",
        cross_version_grade_conflicts,
    )

    print()
    print(
        "NORMALIZED ARABIC GRADE CATEGORIES"
    )

    for category in HadithGradeCategory:
        print(
            f"  {category.value:10}"
            f"{grade_categories[category.value]:>8,}"
        )

    print()
    print("=" * 88)
    print(
        "HADEETHENC OFFICIAL RESULT: PASS"
    )
    print(
        "All 3,582 Arabic primary records parsed."
    )
    print(
        "2,328 English representations paired."
    )
    print(
        "1 cross-version grade conflict "
        "preserved for review."
    )
    print("=" * 88)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
