from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]


DISCOVERY = (
    ROOT
    / "data/competition/discovery/"
    "dorar-tafsir/discovery.json"
)

AUDIT = (
    ROOT
    / "data/competition/audits/"
    "tafsir/"
    "dorar-tafsir-adversarial-v1.json"
)

MANIFEST = (
    ROOT
    / "data/competition/manifests/"
    "tafsir/"
    "dorar-tafsir-runtime-v1.json"
)

PASSPORT = (
    ROOT
    / "data/competition/passports/"
    "dorar-tafsir.json"
)


ARTIFACTS = (
    "src/basira/competition/tafsir_policy.py",
    "src/basira/competition/dorar_tafsir.py",
    "data/competition/discovery/dorar-tafsir/discovery.json",
    "data/competition/audits/tafsir/dorar-tafsir-adversarial-v1.json",
    "data/competition/manifests/tafsir/dorar-tafsir-runtime-v1.json",
)


def sha256(
    path: Path,
) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def git(
    *args: str,
) -> str:

    return subprocess.check_output(
        [
            "git",
            *args,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def main() -> None:

    discovery = json.loads(
        DISCOVERY.read_text(
            encoding="utf-8"
        )
    )

    audit = json.loads(
        AUDIT.read_text(
            encoding="utf-8"
        )
    )

    manifest = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    assert (
        discovery["result"]
        == "PASS"
    )

    assert (
        audit["result"]
        == "PASS"
    )

    # Historical audit must prove that admission happened
    # AFTER verification, not before it.
    assert (
        audit["runtime_admission"]
        == "PENDING_AUDIT"
    )

    assert (
        audit["source_trust_passport"]
        == "NOT_ISSUED"
    )

    assert (
        manifest["runtime_eligibility"]
        == "eligible"
    )

    assert (
        manifest["scope"]
        == "canonical_passage_only"
    )

    assert (
        audit["metrics"][
            "quran_provenance_violation_count"
        ]
        == 0
    )

    checks = audit[
        "checks"
    ]

    required_checks = {
        "canonical_sections":
            "PASS",

        "canonical_article_ids":
            "PASS",

        "quran_tafsir_boundary":
            "PASS",

        "quran_reference_preservation":
            "PASS",

        "citation_preservation":
            "PASS",

        "narration_source_preservation":
            "PASS",

        "reported_grading_provenance":
            "PASS",

        "independent_isnad_grading":
            "PROHIBITED",

        "authenticity_from_frequency":
            "PROHIBITED",

        "tafsir_as_canonical_quran":
            "PROHIBITED",

        "direct_fiqh_ruling_from_tafsir":
            "PROHIBITED",
    }

    for key, expected in (
        required_checks.items()
    ):
        assert (
            checks[key]
            == expected
        ), (
            key,
            checks[key],
            expected,
        )

    artifact_hashes = {
        relative:
            sha256(
                ROOT
                / relative
            )
        for relative in ARTIFACTS
    }

    current_commit = git(
        "rev-parse",
        "HEAD",
    )

    passport = {
        "passport_version": 1,

        "passport_id":
            "dorar-tafsir-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_family":
            "dorar_tafsir",

        "runtime_eligibility":
            "eligible",

        "runtime_scope":
            "canonical_passage_only",

        "canonical_origin":
            "https://dorar.net",

        "canonical_path_contract":
            "/tafseer/{surah}/{passage}",

        "adapter_contract":
            "dorar-tafsir-canonical-passages-v1",

        "characterization_result":
            discovery["result"],

        "adversarial_audit_result":
            audit["result"],

        "characterization_commit":
            "7f3ae0e",

        "adapter_audit_commit":
            current_commit,

        "baseline_response_sha256":
            audit["response_sha256"],

        "artifact_sha256":
            artifact_hashes,

        "guardrails":
            manifest["guardrails"],

        "limitations":
            manifest["limitations"],
    }

    PASSPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    PASSPORT.write_text(
        json.dumps(
            passport,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "✅ Dorar Tafsir passport generated"
    )

    print(
        "passport:",
        PASSPORT.relative_to(
            ROOT
        ),
    )

    print(
        "admission parent commit:",
        current_commit,
    )

    print(
        "baseline response sha256:",
        audit["response_sha256"],
    )


if __name__ == "__main__":
    main()
