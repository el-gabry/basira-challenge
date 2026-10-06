from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from basira.competition.dorar_hadith import (
    DorarHadithRecord,
    parse_dorar_api_payload,
)


ROOT = Path(__file__).resolve().parents[1]

SMOKE = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dorar"
    / "api-smoke.json"
)

ADV = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dorar"
    / "adversarial"
)

OUT = (
    ROOT
    / "data"
    / "competition"
    / "audits"
    / "hadith"
    / "dorar-adversarial-v1.json"
)


def load(path: Path) -> tuple[
    bytes,
    dict[str, Any],
]:
    raw = path.read_bytes()

    return (
        raw,
        json.loads(
            raw.decode("utf-8")
        ),
    )


def incomplete(
    records: list[DorarHadithRecord],
) -> list[dict[str, Any]]:

    problems = []

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
            problems.append({
                "record": index,
                "missing": missing,
            })

    return problems


def summarize(
    case_id: str,
    path: Path,
) -> dict[str, Any]:

    raw, payload = load(path)

    records = parse_dorar_api_payload(
        payload
    )

    verdicts = {
        record.verdict
        for record in records
        if record.verdict
    }

    narrators = {
        record.narrator
        for record in records
        if record.narrator
    }

    muhaddiths = {
        record.muhaddith
        for record in records
        if record.muhaddith
    }

    return {
        "case_id": case_id,
        "artifact": {
            "path":
                str(path.relative_to(ROOT)),
            "bytes":
                len(raw),
            "sha256":
                hashlib.sha256(
                    raw
                ).hexdigest(),
        },
        "record_count":
            len(records),
        "distinct_verdict_count":
            len(verdicts),
        "distinct_narrator_count":
            len(narrators),
        "distinct_muhaddith_count":
            len(muhaddiths),
        "incomplete_records":
            incomplete(records),
        "records": [
            record.model_dump(
                mode="json"
            )
            for record in records
        ],
    }


def main() -> None:
    smoke = summarize(
        "mixed_known_phrase",
        SMOKE,
    )

    weak = summarize(
        "weak_variant_phrase",
        ADV / "weak_variant_phrase.json",
    )

    nonce = summarize(
        "nonce_no_hit",
        ADV / "nonce_no_hit.json",
    )

    failures = []

    # --------------------------------------------------------
    # Existing real-world mixed search:
    # must preserve multiple individual attestations.
    # --------------------------------------------------------

    if smoke["record_count"] < 2:
        failures.append(
            "mixed query returned fewer than 2 records"
        )

    if smoke["distinct_verdict_count"] < 2:
        failures.append(
            "mixed query did not preserve verdict diversity"
        )

    if smoke["incomplete_records"]:
        failures.append(
            "mixed query lost attribution fields"
        )

    # --------------------------------------------------------
    # Weak/variant-prone phrase:
    # we require safe parsing, NOT a predetermined grading.
    # --------------------------------------------------------

    if weak["record_count"] < 1:
        failures.append(
            "weak/variant query returned no parseable records"
        )

    if weak["incomplete_records"]:
        failures.append(
            "weak/variant query lost attribution fields"
        )

    # --------------------------------------------------------
    # Nonsense query:
    # zero records is expected for this frozen audit query.
    #
    # IMPORTANT:
    # zero search hits != proof that no hadith exists.
    # --------------------------------------------------------

    if nonce["record_count"] != 0:
        failures.append(
            "nonce query unexpectedly produced hadith records"
        )

    report = {
        "audit_id":
            "dorar-adversarial-v1",

        "source_id":
            "dorar:hadith-api",

        "provider":
            "Dorar al-Sunniyyah",

        "checks": {
            "mixed_result_preservation":
                (
                    "PASS"
                    if (
                        smoke["record_count"] >= 2
                        and
                        smoke[
                            "distinct_verdict_count"
                        ] >= 2
                        and not smoke[
                            "incomplete_records"
                        ]
                    )
                    else "FAIL"
                ),

            "variant_attribution":
                (
                    "PASS"
                    if (
                        weak["record_count"] >= 1
                        and not weak[
                            "incomplete_records"
                        ]
                    )
                    else "FAIL"
                ),

            "no_result_fail_closed":
                (
                    "PASS"
                    if nonce["record_count"] == 0
                    else "FAIL"
                ),

            # Search result uniformity can NEVER establish
            # scholarly consensus.
            "consensus_inference_from_search":
                "PROHIBITED",

            # Empty search is an observation, not proof of
            # nonexistence in the religious corpus.
            "zero_result_semantics":
                "NO_HITS_FOR_QUERY",
        },

        "aggregation_policy":
            "PRESERVE_EACH_ATTESTATION",

        "majority_vote":
            "PROHIBITED",

        "cases": [
            smoke,
            weak,
            nonce,
        ],

        "failures":
            failures,

        "result":
            (
                "PASS"
                if not failures
                else "FAIL"
            ),

        "runtime_admission":
            "PENDING_SOURCE_PASSPORT",
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "Mixed records:",
        smoke["record_count"],
    )

    print(
        "Mixed distinct verdicts:",
        smoke["distinct_verdict_count"],
    )

    print(
        "Variant records:",
        weak["record_count"],
    )

    print(
        "Variant distinct verdicts:",
        weak["distinct_verdict_count"],
    )

    print(
        "Nonce records:",
        nonce["record_count"],
    )

    print(
        "Consensus inference:",
        "PROHIBITED",
    )

    print(
        "Zero-result semantics:",
        "NO_HITS_FOR_QUERY",
    )

    print()
    print(
        "ADVERSARIAL AUDIT:",
        report["result"],
    )

    if failures:
        print()

        for failure in failures:
            print(
                "FAIL:",
                failure,
            )

        raise SystemExit(1)


if __name__ == "__main__":
    main()
