from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]


OUT = (
    ROOT
    / "data/competition/passports/"
    "dorar-history.json"
)


ARTIFACTS = (
    "src/basira/competition/"
    "history_policy.py",

    "src/basira/competition/"
    "history_entities.py",

    "src/basira/competition/"
    "history_retrieval.py",

    "src/basira/competition/"
    "dorar_history.py",

    "src/basira/competition/"
    "dorar_history_admission.py",

    "data/competition/manifests/"
    "history/"
    "official-history-policy-v1.json",

    "data/competition/manifests/"
    "history/"
    "dorar-history-dom-contract-v1.json",

    "data/competition/manifests/"
    "history/"
    "dorar-history-runtime-v1.json",

    "data/competition/sources/"
    "history/"
    "history_source_registry.json",

    "data/competition/sources/"
    "history/"
    "historical_entity_registry.json",

    "data/competition/discovery/"
    "dorar-history/"
    "discovery.json",

    "data/competition/audits/"
    "history/"
    "dorar-history-adversarial-v1.json",
)


def sha256(
    path: Path,
) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def git_head() -> str:

    return subprocess.run(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def load(
    relative: str,
) -> dict:

    return json.loads(
        (
            ROOT
            / relative
        ).read_text(
            encoding="utf-8"
        )
    )


def main() -> None:

    audit = load(
        "data/competition/audits/"
        "history/"
        "dorar-history-adversarial-v1.json"
    )

    discovery = load(
        "data/competition/discovery/"
        "dorar-history/"
        "discovery.json"
    )

    runtime = load(
        "data/competition/manifests/"
        "history/"
        "dorar-history-runtime-v1.json"
    )

    official = load(
        "data/competition/manifests/"
        "history/"
        "official-history-policy-v1.json"
    )


    assert (
        discovery["result"]
        == "PASS"
    )

    assert (
        audit["result"]
        == "PASS"
    )

    assert (
        audit["adapter_status"]
        == "AUDITED"
    )

    # Historical audit occurred before runtime admission.
    assert (
        audit["runtime_admission"]
        == "NOT_ADMITTED"
    )

    assert (
        audit[
            "source_trust_passport"
        ]
        == "NOT_ISSUED"
    )

    assert (
        official[
            "runtime_state"
        ][
            "dorar_history"
        ]
        == "ELIGIBLE"
    )

    assert (
        runtime[
            "runtime_eligibility"
        ]
        == "eligible"
    )


    baseline_map = {
        item[
            "canonical_url"
        ]:
            item[
                "sha256"
            ]
        for item in runtime[
            "audited_baselines"
        ]
    }


    assert len(
        baseline_map
    ) == 6


    for name in (
        "seerah_disagreement",
        "seerah_prophetic_report",
        "seerah_event",
        "medieval_event",
        "early_modern_event",
        "contemporary_event",
    ):

        case = discovery[
            "cases"
        ][
            name
        ]

        assert (
            baseline_map[
                case[
                    "canonical_href"
                ]
            ]
            == case[
                "sha256"
            ]
        )


    hashes = {}


    for relative in ARTIFACTS:

        path = (
            ROOT
            / relative
        )

        if not path.is_file():

            raise SystemExit(
                "missing governed artifact: "
                + relative
            )

        hashes[
            relative
        ] = sha256(
            path
        )


    passport = {
        "passport_version":
            1,

        "passport_id":
            "dorar-history-source-trust-v1",

        "source_id":
            "dorar-history-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_family":
            "dorar_history",

        "runtime_eligibility":
            "eligible",

        "admission_scope":
            "canonical_event_only",

        "canonical_origin":
            "https://dorar.net",

        "allowed_route_families": [
            "/history/{positive_integer_id}",
            "/history/event/{positive_integer_id}"
        ],

        "adapter_contract":
            "dorar-history-canonical-event-v1",

        "admission_parent_commit":
            git_head(),

        "verification_evidence": {
            "live_characterization":
                "PASS",

            "dom_route_probe":
                "PASS",

            "adversarial_audit":
                "PASS",

            "adapter":
                "AUDITED",

            "audited_baseline_count":
                len(
                    baseline_map
                )
        },

        "runtime_guarantees": {
            "exact_response_sha256_recorded":
                True,

            "audited_baseline_drift_blocked":
                True,

            "canonical_self_link_required":
                True,

            "canonical_structure_fail_closed":
                True,

            "nested_event_container_ambiguity_blocked":
                True,

            "provenance_routing_fail_closed":
                True
        },

        "semantic_guarantees": {
            "runtime_admission_equals_established_fact":
                False,

            "default_historical_report_status":
                "unassessed",

            "may_state_as_established_fact":
                False,

            "categorical_claim_requires_governed_report_assessment":
                True,

            "lexical_disagreement_is_truth_grade":
                False,

            "independent_hadith_authentication":
                False,

            "hadith_matn_inference_from_plain_history_prose":
                False,

            "history_quran_candidate_is_canonical_quran_witness":
                False,

            "event_reference_channel_established":
                False,

            "generic_shamela_fallback":
                False
        },

        "first_three_centuries_path": {
            "runtime_admitted":
                False,

            "authority_registry_state":
                "EMPTY_PENDING_SOURCE_AUDIT"
        },

        "historical_entity_registry": {
            "production_entity_count":
                0,

            "entity_resolution_role":
                "retrieval_only"
        },

        "governed_artifact_sha256":
            hashes,
    }


    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    OUT.write_text(
        json.dumps(
            passport,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )


    print(
        "✅ Dorar History passport generated"
    )

    print(
        "Admission parent:",
        passport[
            "admission_parent_commit"
        ],
    )

    print(
        "Audited baselines:",
        len(
            baseline_map
        ),
    )

    print(
        "Historical status default: UNASSESSED"
    )


if __name__ == "__main__":
    main()
