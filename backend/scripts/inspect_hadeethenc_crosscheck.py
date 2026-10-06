from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from compare_hadeethenc_quranlab import (
    by_id,
    load_quranlab,
    load_xlsx_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect differences between official "
            "HadeethEnc releases and QuranLab."
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

    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
    )

    return parser.parse_args()


def text_sha256(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def first_difference(
    left: str,
    right: str,
) -> int | None:
    limit = min(
        len(left),
        len(right),
    )

    for index in range(limit):
        if left[index] != right[index]:
            return index

    if len(left) != len(right):
        return limit

    return None


def context(
    value: str,
    *,
    index: int,
    radius: int = 60,
) -> str:
    start = max(
        0,
        index - radius,
    )

    end = min(
        len(value),
        index + radius,
    )

    return value[start:end]


def main() -> int:
    args = parse_args()

    _, official_ar_rows = (
        load_xlsx_rows(
            args.official_ar
        )
    )

    _, official_en_rows = (
        load_xlsx_rows(
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

    official_ar = by_id(
        official_ar_rows,
        field="id",
    )

    official_en = by_id(
        official_en_rows,
        field="id",
    )

    quranlab_ar = by_id(
        quranlab_ar_rows,
        field="hadeethenc_id",
    )

    quranlab_en = by_id(
        quranlab_en_rows,
        field="hadeethenc_id",
    )

    official_ar_ids = set(
        official_ar
    )

    quranlab_ar_ids = set(
        quranlab_ar
    )

    official_en_ids = set(
        official_en
    )

    quranlab_en_ids = set(
        quranlab_en
    )

    official_only_ar = sorted(
        official_ar_ids
        - quranlab_ar_ids,
        key=int,
    )

    quranlab_only_ar = sorted(
        quranlab_ar_ids
        - official_ar_ids,
        key=int,
    )

    official_only_en = sorted(
        official_en_ids
        - quranlab_en_ids,
        key=int,
    )

    quranlab_only_en = sorted(
        quranlab_en_ids
        - official_en_ids,
        key=int,
    )

    shared_ar = (
        official_ar_ids
        & quranlab_ar_ids
    )

    text_mismatches = []

    for hadith_id in sorted(
        shared_ar,
        key=int,
    ):
        official_text = official_ar[
            hadith_id
        ]["hadith_text"]

        quranlab_text = quranlab_ar[
            hadith_id
        ]["text"]

        if official_text == quranlab_text:
            continue

        index = first_difference(
            official_text,
            quranlab_text,
        )

        assert index is not None

        text_mismatches.append(
            {
                "id": hadith_id,
                "first_difference_index": index,
                "official_length": len(
                    official_text
                ),
                "quranlab_length": len(
                    quranlab_text
                ),
                "official_sha256": (
                    text_sha256(
                        official_text
                    )
                ),
                "quranlab_sha256": (
                    text_sha256(
                        quranlab_text
                    )
                ),
                "official_context": context(
                    official_text,
                    index=index,
                ),
                "quranlab_context": context(
                    quranlab_text,
                    index=index,
                ),
            }
        )

    conflict_id = "65065"

    conflict = {
        "id": conflict_id,
        "official_ar_grade": (
            official_ar
            .get(
                conflict_id,
                {},
            )
            .get("grade")
        ),
        "official_ar_takhrij": (
            official_ar
            .get(
                conflict_id,
                {},
            )
            .get("takhrij")
        ),
        "official_en_grade_ar": (
            official_en
            .get(
                conflict_id,
                {},
            )
            .get("grade_ar")
        ),
        "official_en_grade": (
            official_en
            .get(
                conflict_id,
                {},
            )
            .get("grade")
        ),
        "quranlab_ar_grade": (
            quranlab_ar
            .get(
                conflict_id,
                {},
            )
            .get("grade")
        ),
        "quranlab_en_grade": (
            quranlab_en
            .get(
                conflict_id,
                {},
            )
            .get("grade")
        ),
    }

    report = {
        "official_ar_count": len(
            official_ar
        ),
        "quranlab_ar_count": len(
            quranlab_ar
        ),
        "official_en_count": len(
            official_en
        ),
        "quranlab_en_count": len(
            quranlab_en
        ),
        "official_only_ar_ids": (
            official_only_ar
        ),
        "quranlab_only_ar_ids": (
            quranlab_only_ar
        ),
        "official_only_en_ids": (
            official_only_en
        ),
        "quranlab_only_en_ids": (
            quranlab_only_en
        ),
        "arabic_text_mismatches": (
            text_mismatches
        ),
        "known_grade_conflict": (
            conflict
        ),
    }

    print("=" * 88)
    print("HADEETHENC CROSSCHECK INSPECTION")
    print("=" * 88)

    print()
    print("ID COVERAGE")

    print(
        "Official-only Arabic:",
        len(official_only_ar),
        official_only_ar,
    )

    print(
        "QuranLab-only Arabic:",
        len(quranlab_only_ar),
        quranlab_only_ar,
    )

    print(
        "Official-only English:",
        len(official_only_en),
        official_only_en,
    )

    print(
        "QuranLab-only English:",
        len(quranlab_only_en),
        quranlab_only_en,
    )

    print()
    print(
        "ARABIC TEXT MISMATCHES:",
        len(text_mismatches),
    )

    for item in text_mismatches:
        print()
        print("-" * 88)
        print(
            "ID:",
            item["id"],
        )
        print(
            "First difference index:",
            item[
                "first_difference_index"
            ],
        )
        print(
            "Official length:",
            item[
                "official_length"
            ],
        )
        print(
            "QuranLab length:",
            item[
                "quranlab_length"
            ],
        )
        print(
            "Official SHA256:",
            item[
                "official_sha256"
            ],
        )
        print(
            "QuranLab SHA256:",
            item[
                "quranlab_sha256"
            ],
        )
        print(
            "Official context:",
            repr(
                item[
                    "official_context"
                ]
            ),
        )
        print(
            "QuranLab context:",
            repr(
                item[
                    "quranlab_context"
                ]
            ),
        )

        official_context = item[
            "official_context"
        ]
        quranlab_context = item[
            "quranlab_context"
        ]

        context_diff = first_difference(
            official_context,
            quranlab_context,
        )

        if context_diff is not None:
            official_char = (
                official_context[context_diff]
                if context_diff
                < len(official_context)
                else None
            )

            quranlab_char = (
                quranlab_context[context_diff]
                if context_diff
                < len(quranlab_context)
                else None
            )

            print(
                "Context difference index:",
                context_diff,
            )

            print(
                "Official character:",
                repr(official_char),
                (
                    f"U+{ord(official_char):04X}"
                    if official_char is not None
                    else "END"
                ),
            )

            print(
                "QuranLab character:",
                repr(quranlab_char),
                (
                    f"U+{ord(quranlab_char):04X}"
                    if quranlab_char is not None
                    else "END"
                ),
            )

    print()
    print("=" * 88)
    print("KNOWN GRADE CONFLICT 65065")
    print("=" * 88)

    for key, value in conflict.items():
        print(
            f"{key}:",
            repr(value),
        )

    if args.report_json is not None:
        args.report_json.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.report_json.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        print()
        print(
            "Report written:",
            args.report_json,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
