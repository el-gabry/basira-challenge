from __future__ import annotations

import hashlib
import json
from pathlib import Path

from basira.competition.dorar_hadith import (
    parse_dorar_api_payload,
)


ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dorar"
    / "api-smoke.json"
)

OUT = (
    ROOT
    / "data"
    / "competition"
    / "audits"
    / "hadith"
    / "dorar-api-smoke.json"
)


def main() -> None:

    raw = SOURCE.read_bytes()

    payload = json.loads(
        raw.decode("utf-8")
    )

    records = (
        parse_dorar_api_payload(
            payload
        )
    )

    if not records:
        raise RuntimeError(
            "Dorar smoke query returned "
            "no parseable records"
        )

    incomplete = []

    for index, record in enumerate(
        records,
        1,
    ):
        required = {
            "hadith_text":
                record.hadith_text,
            "narrator":
                record.narrator,
            "muhaddith":
                record.muhaddith,
            "source":
                record.source,
            "page_or_number":
                record.page_or_number,
            "verdict":
                record.verdict,
        }

        missing = [
            key
            for key, value
            in required.items()
            if not value
        ]

        if missing:
            incomplete.append(
                {
                    "index": index,
                    "missing": missing,
                }
            )

    distinct_verdicts = sorted({
        record.verdict
        for record in records
        if record.verdict
    })

    distinct_narrators = sorted({
        record.narrator
        for record in records
        if record.narrator
    })

    result = {
        "source_id":
            "dorar:hadith-api",

        "provider":
            "Dorar al-Sunniyyah",

        "api_shape": {
            "top_level":
                "object",
            "ahadith":
                "object",
            "result":
                "html_string",
        },

        "artifact": {
            "bytes":
                len(raw),
            "sha256":
                hashlib.sha256(
                    raw
                ).hexdigest(),
        },

        "parsed_record_count":
            len(records),

        "incomplete_records":
            incomplete,

        "distinct_narrator_count":
            len(distinct_narrators),

        "distinct_verdict_count":
            len(distinct_verdicts),

        "preserve_result_separation":
            True,

        "adapter_status":
            (
                "PASS"
                if not incomplete
                else "PARTIAL"
            ),

        "admission_status":
            "NOT_YET_ADMITTED",

        "records": [
            record.model_dump(
                mode="json"
            )
            for record in records
        ],
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "Parsed records:",
        len(records),
    )

    print(
        "Distinct narrators:",
        len(distinct_narrators),
    )

    print(
        "Distinct verdicts:",
        len(distinct_verdicts),
    )

    print(
        "Incomplete records:",
        len(incomplete),
    )

    print()

    for record in records[:8]:
        print(
            f"#{record.rank}",
            "|",
            record.narrator,
            "|",
            record.muhaddith,
            "|",
            record.source,
            "|",
            record.verdict,
        )

    print()
    print(
        "Adapter status:",
        result["adapter_status"],
    )


if __name__ == "__main__":
    main()
