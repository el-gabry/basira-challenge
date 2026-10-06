from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

CONTRACT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "jamhara"
    / "snapshot-contract.json"
)


def contract() -> dict:
    return json.loads(
        CONTRACT.read_text(
            encoding="utf-8"
        )
    )


def test_snapshot_identity_and_order_are_frozen() -> None:
    d = contract()

    assert d["unit_identity"] == [
        "word_id",
        "language",
    ]

    assert d["canonical_order"] == [
        "word_id ASC",
        "language ASC",
    ]

    assert (
        d["duplicate_identity_policy"]
        == "REJECT"
    )


def test_snapshot_identity_fields_match_content_contract() -> None:
    d = contract()

    assert (
        d["required_identity_fields"]
        == [
            "word_id",
            "language",
            "source_url",
        ]
    )


def test_http_success_alone_does_not_admit_view() -> None:
    d = contract()

    assert (
        d[
            "http_200_alone_establishes_usable_view"
        ]
        is False
    )

    assert (
        d["localized_view_acceptance"]
        == (
            "REQUIRES_NONEMPTY_LOCALIZED_"
            "LEXICAL_OR_EXPLANATORY_PAYLOAD"
        )
    )


def test_candidate_corpus_is_not_overclaimed() -> None:
    evidence = contract()[
        "candidate_word_id_evidence"
    ]

    assert (
        evidence["candidate_count"]
        == 4382
    )

    assert (
        evidence[
            "corpus_completeness_proven"
        ]
        is False
    )


def test_snapshot_has_not_been_built_or_admitted() -> None:
    d = contract()

    assert (
        d["build_state"]
        == "NOT_BUILT"
    )

    assert (
        d["snapshot_hash_state"]
        == "NOT_FROZEN"
    )

    assert (
        d["runtime_admission"]
        == "PENDING_AUDIT"
    )


def test_snapshot_never_grants_primary_evidence_authority() -> None:
    authority = contract()[
        "authority_boundary"
    ]

    assert (
        authority[
            "terminology_authority"
        ]
        is True
    )

    assert (
        authority[
            "universal_primary_evidence"
        ]
        is False
    )

    assert (
        authority[
            "cross_domain_primary_evidence"
        ]
        is False
    )


def test_snapshot_builder_contract_is_frozen() -> None:
    d = contract()

    assert (
        d["builder"]
        == (
            "src/basira/competition/"
            "jamhara_snapshot.py"
        )
    )

    build = d["build_contract"]

    assert (
        build["candidate_order"]
        == "WORD_ID_ASCENDING"
    )

    assert (
        build["localized_view_order"]
        == "LANGUAGE_ASCENDING"
    )

    assert (
        build[
            "snapshot_hash_algorithm"
        ]
        == "sha256"
    )

    assert (
        "ZERO_FETCH_FAILURES"
        in build["freeze_requires"]
    )

    assert (
        "SECOND_BUILD_FROM_FROZEN_CACHE_MATCHES_SHA256"
        in build["freeze_requires"]
    )


def test_raw_html_hash_is_audit_only_not_snapshot_identity() -> None:
    contract_data = contract()

    provenance = contract_data[
        "provenance_hash_contract"
    ]

    assert (
        provenance[
            "canonical_unit_hash_field"
        ]
        == "content_sha256"
    )

    assert (
        provenance[
            "raw_response_sha256_location"
        ]
        == "BUILD_REPORT_ONLY"
    )

    assert (
        provenance[
            "raw_response_sha256_part_of_snapshot"
        ]
        is False
    )

    assert (
        provenance[
            "dynamic_html_must_not_change_snapshot_sha256_when_extracted_content_is_unchanged"
        ]
        is True
    )
