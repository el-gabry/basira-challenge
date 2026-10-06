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
    "dorar-aqeeda.json"
)


ARTIFACTS = (
    "src/basira/competition/"
    "aqeedah_policy.py",

    "src/basira/competition/"
    "aqeedah_authority.py",

    "src/basira/competition/"
    "dorar_aqeedah.py",

    "src/basira/competition/"
    "dorar_aqeedah_admission.py",

    "data/competition/manifests/"
    "aqeedah/"
    "official-aqeedah-policy-v1.json",

    "data/competition/manifests/"
    "aqeedah/"
    "dorar-aqeedah-runtime-v1.json",

    "data/competition/sources/"
    "aqeedah/"
    "aqeedah_source_registry.json",

    "data/competition/sources/"
    "aqeedah/"
    "aqeedah_authority_registry.json",

    "data/competition/discovery/"
    "dorar-aqeedah/"
    "discovery.json",

    "data/competition/audits/"
    "aqeedah/"
    "dorar-aqeedah-adversarial-v1.json",
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
        "aqeedah/"
        "dorar-aqeedah-adversarial-v1.json"
    )

    discovery = load(
        "data/competition/discovery/"
        "dorar-aqeedah/"
        "discovery.json"
    )

    runtime = load(
        "data/competition/manifests/"
        "aqeedah/"
        "dorar-aqeedah-runtime-v1.json"
    )

    official = load(
        "data/competition/manifests/"
        "aqeedah/"
        "official-aqeedah-policy-v1.json"
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

    assert (
        audit["runtime_admission"]
        == "NOT_ADMITTED"
    )

    # Historical audit MUST have happened before admission.
    assert (
        audit["source_trust_passport"]
        == "NOT_ISSUED"
    )

    assert (
        official[
            "runtime_state"
        ][
            "dorar_aqeeda"
        ]
        == "ELIGIBLE"
    )

    baseline = runtime[
        "baseline_artifact"
    ]

    assert (
        baseline["sha256"]
        == audit[
            "response_sha256"
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
                f"missing governed artifact: {relative}"
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
            "dorar-aqeeda-source-trust-v1",

        "source_id":
            "dorar-aqeeda-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_family":
            "dorar_aqeeda",

        "runtime_eligibility":
            "eligible",

        "admission_scope":
            "canonical_article_only",

        "canonical_origin":
            "https://dorar.net",

        "canonical_path":
            "/aqeeda/{positive_integer_id}",

        "adapter_contract":
            "dorar-aqeedah-canonical-article-v1",

        "admission_parent_commit":
            git_head(),

        "verification_evidence": {
            "live_characterization":
                "PASS",

            "adversarial_audit":
                "PASS",

            "adapter":
                "AUDITED",

            "baseline_url":
                baseline[
                    "url"
                ],

            "baseline_response_sha256":
                baseline[
                    "sha256"
                ]
        },

        "runtime_guarantees": {
            "exact_response_sha256_recorded":
                True,

            "baseline_artifact_drift_blocked":
                True,

            "canonical_structure_fail_closed":
                True,

            "provenance_routing_fail_closed":
                True
        },

        "hard_boundaries": {
            "quran_context_is_canonical_quran_witness":
                False,

            "quran_context_reference_force_pairing":
                False,

            "independent_hadith_authentication":
                False,

            "hadith_matn_inference_from_plain_prose":
                False,

            "bibliographic_citation_promotes_aqeedah_authority":
                False,

            "generic_shamela_fallback":
                False,

            "early_period_equals_aqeedah_authority":
                False
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
        "✅ Dorar Aqeedah passport generated"
    )

    print(
        "Admission parent:",
        passport[
            "admission_parent_commit"
        ],
    )

    print(
        "Baseline SHA:",
        baseline[
            "sha256"
        ],
    )


if __name__ == "__main__":
    main()
