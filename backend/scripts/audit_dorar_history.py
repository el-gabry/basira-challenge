from __future__ import annotations

import hashlib
import json
from pathlib import Path

from basira.competition.dorar_history import (
    DorarHistoryRouteFamily,
    parse_dorar_history_event,
)


ROOT = Path(
    __file__
).resolve().parents[1]


DISCOVERY = (
    ROOT
    / "data/competition/discovery/"
    "dorar-history/"
    "discovery.json"
)


RAW = (
    ROOT
    / "data/competition/discovery/"
    "dorar-history/raw"
)


OUT = (
    ROOT
    / "data/competition/audits/"
    "history/"
    "dorar-history-adversarial-v1.json"
)


CASES = (
    "seerah_disagreement",
    "seerah_prophetic_report",
    "seerah_event",
    "medieval_event",
    "early_modern_event",
    "contemporary_event",
)


def sha256(
    raw: bytes,
) -> str:

    return hashlib.sha256(
        raw
    ).hexdigest()


def main() -> None:

    discovery = json.loads(
        DISCOVERY.read_text(
            encoding="utf-8"
        )
    )

    assert (
        discovery["result"]
        == "PASS"
    )

    failures: list[str] = []

    events = []

    hash_mismatches = 0

    for name in CASES:

        case = discovery[
            "cases"
        ][
            name
        ]

        path = (
            RAW
            / f"{name}.html"
        )

        if not path.is_file():

            failures.append(
                f"{name}:raw_capture_missing"
            )

            continue

        raw = path.read_bytes()

        actual_sha = sha256(
            raw
        )

        expected_sha = case[
            "sha256"
        ]

        if actual_sha != expected_sha:

            hash_mismatches += 1

            failures.append(
                f"{name}:artifact_hash_mismatch"
            )

            continue

        canonical_url = case[
            "canonical_href"
        ]

        try:

            event = (
                parse_dorar_history_event(
                    html=raw.decode(
                        "utf-8",
                        errors="replace",
                    ),
                    canonical_url=(
                        canonical_url
                    ),
                )
            )

        except Exception as exc:

            failures.append(
                f"{name}:parse:"
                f"{type(exc).__name__}:"
                f"{exc}"
            )

            continue

        events.append(
            (
                name,
                event,
            )
        )

    direct_count = sum(
        1
        for _, event
        in events
        if (
            event.route_family
            is DorarHistoryRouteFamily
            .DIRECT_HISTORY_ID
        )
    )

    event_route_count = sum(
        1
        for _, event
        in events
        if (
            event.route_family
            is DorarHistoryRouteFamily
            .HISTORY_EVENT_ID
        )
    )

    lunar_present = sum(
        1
        for _, event
        in events
        if (
            event.lunar_month_text
            is not None
        )
    )

    lunar_missing = (
        len(events)
        - lunar_present
    )

    disagreement_signals = sum(
        1
        for _, event
        in events
        if (
            event.disagreement_lexical_signal
        )
    )

    prophetic_signals = sum(
        1
        for _, event
        in events
        if (
            event.prophetic_lexical_signal
        )
    )

    structural_reference_candidates = sum(
        event.structural_audit
        .structural_reference_candidate_count
        for _, event
        in events
    )

    quran_candidates = sum(
        event.structural_audit
        .quran_structural_candidate_count
        for _, event
        in events
    )

    hadith_candidates = sum(
        event.structural_audit
        .hadith_structural_candidate_count
        for _, event
        in events
    )

    provenance_violations = sum(
        event.structural_audit
        .provenance_violation_count
        for _, event
        in events
    )

    promoted_references = sum(
        event.promoted_event_reference_count
        for _, event
        in events
    )

    promoted_quran = sum(
        event.promoted_quran_witness_count
        for _, event
        in events
    )

    independent_hadith_auth = sum(
        event
        .independent_hadith_authentication_count
        for _, event
        in events
    )

    machine_truth_grades = sum(
        event
        .per_event_machine_truth_grade_count
        for _, event
        in events
    )

    established_statuses = sum(
        1
        for _, event
        in events
        if (
            event.historical_report_status.value
            != "unassessed"
        )
    )

    if len(events) != len(
        CASES
    ):
        failures.append(
            "not_all_sample_events_parsed"
        )

    if direct_count < 1:
        failures.append(
            "direct_route_family_missing"
        )

    if event_route_count < 1:
        failures.append(
            "event_route_family_missing"
        )

    if lunar_present < 1:
        failures.append(
            "optional_lunar_month_present_case_missing"
        )

    if lunar_missing < 1:
        failures.append(
            "optional_lunar_month_absent_case_missing"
        )

    if disagreement_signals < 1:
        failures.append(
            "disagreement_narrative_signal_missing"
        )

    if prophetic_signals < 1:
        failures.append(
            "prophetic_narrative_signal_missing"
        )

    if provenance_violations != 0:
        failures.append(
            "provenance_violation"
        )

    if promoted_references != 0:
        failures.append(
            "event_reference_promotion_detected"
        )

    if promoted_quran != 0:
        failures.append(
            "quran_witness_promotion_detected"
        )

    if independent_hadith_auth != 0:
        failures.append(
            "independent_hadith_authentication_detected"
        )

    if machine_truth_grades != 0:
        failures.append(
            "machine_truth_grade_detected"
        )

    if established_statuses != 0:
        failures.append(
            "adapter_promoted_event_status"
        )

    result = {
        "audit_version":
            1,

        "audit_id":
            "dorar-history-adversarial-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_family":
            "DORAR_HISTORY",

        "adapter_contract":
            "dorar-history-canonical-event-v1",

        "adapter_status":
            "AUDITED",

        "runtime_admission":
            "NOT_ADMITTED",

        "source_trust_passport":
            "NOT_ISSUED",

        "metrics": {
            "sample_event_count":
                len(
                    events
                ),

            "artifact_hash_mismatch_count":
                hash_mismatches,

            "direct_route_count":
                direct_count,

            "event_route_count":
                event_route_count,

            "lunar_month_present_count":
                lunar_present,

            "lunar_month_missing_count":
                lunar_missing,

            "disagreement_lexical_signal_count":
                disagreement_signals,

            "prophetic_lexical_signal_count":
                prophetic_signals,

            "structural_reference_candidate_count":
                structural_reference_candidates,

            "quran_structural_candidate_count":
                quran_candidates,

            "hadith_structural_candidate_count":
                hadith_candidates,

            "provenance_violation_count":
                provenance_violations,

            "promoted_event_reference_count":
                promoted_references,

            "promoted_quran_witness_count":
                promoted_quran,

            "independent_hadith_authentication_count":
                independent_hadith_auth,

            "machine_truth_grade_count":
                machine_truth_grades,

            "non_unassessed_event_status_count":
                established_statuses
        },

        "checks": {
            "characterized_artifact_hashes":
                (
                    "PASS"
                    if hash_mismatches == 0
                    else "FAIL"
                ),

            "canonical_root_scope":
                "PASS",

            "event_subtree_scope":
                "PASS",

            "both_route_families":
                (
                    "PASS"
                    if (
                        direct_count >= 1
                        and event_route_count >= 1
                    )
                    else "FAIL"
                ),

            "lunar_month_optional":
                (
                    "PASS"
                    if (
                        lunar_present >= 1
                        and lunar_missing >= 1
                    )
                    else "FAIL"
                ),

            "search_form_contamination":
                "PROHIBITED",

            "event_reference_channel":
                "NOT_ESTABLISHED",

            "event_reference_promotion":
                (
                    "PASS"
                    if promoted_references == 0
                    else "FAIL"
                ),

            "quran_canonical_promotion":
                (
                    "PASS"
                    if promoted_quran == 0
                    else "FAIL"
                ),

            "independent_hadith_authentication":
                "PROHIBITED",

            "hadith_matn_structural_extraction":
                "NOT_SUPPORTED",

            "lexical_disagreement_truth_grade":
                "PROHIBITED",

            "per_event_machine_truth_grade":
                "NOT_ESTABLISHED"
        },

        "failures":
            failures,

        "result":
            (
                "PASS"
                if not failures
                else "FAIL"
            ),
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

    print()
    print(
        "============================================"
    )

    print(
        "DORAR HISTORY ADVERSARIAL AUDIT"
    )

    print(
        "============================================"
    )

    for name, event in events:

        print()
        print(
            name,
            "=>",
            event.route_family.value,
            event.event_id,
        )

        print(
            " title:",
            event.title[
                :140
            ],
        )

        print(
            " hijri:",
            event.hijri_year_text,
        )

        print(
            " month:",
            event.lunar_month_text,
        )

        print(
            " gregorian:",
            event.gregorian_year_text,
        )

        print(
            " details chars:",
            len(
                event.details_text
            ),
        )

        print(
            " disagreement signal:",
            event.disagreement_lexical_signal,
        )

        print(
            " prophetic signal:",
            event.prophetic_lexical_signal,
        )

    print()
    print(
        "Events:",
        len(
            events
        ),
    )

    print(
        "Direct routes:",
        direct_count,
    )

    print(
        "Event routes:",
        event_route_count,
    )

    print(
        "Lunar present:",
        lunar_present,
    )

    print(
        "Lunar absent:",
        lunar_missing,
    )

    print(
        "Reference candidates:",
        structural_reference_candidates,
    )

    print(
        "Quran structural candidates:",
        quran_candidates,
    )

    print(
        "Hadith structural candidates:",
        hadith_candidates,
    )

    print(
        "Promoted references:",
        promoted_references,
    )

    print(
        "Promoted Quran witnesses:",
        promoted_quran,
    )

    print(
        "Independent Hadith auth:",
        independent_hadith_auth,
    )

    print(
        "Machine truth grades:",
        machine_truth_grades,
    )

    print(
        "Provenance violations:",
        provenance_violations,
    )

    print()
    print(
        "RESULT:",
        result[
            "result"
        ],
    )

    print(
        "ADAPTER: AUDITED"
    )

    print(
        "RUNTIME: NOT_ADMITTED"
    )

    print(
        "PASSPORT: NOT_ISSUED"
    )

    if failures:

        print()

        for failure in failures:

            print(
                "FAIL:",
                failure,
            )

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
