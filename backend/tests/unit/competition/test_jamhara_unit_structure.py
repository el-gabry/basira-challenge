from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

AUDIT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "jamhara"
    / "unit-structure.json"
)


def audit() -> dict:
    return json.loads(
        AUDIT.read_text(encoding="utf-8")
    )


def test_concept_identity_contract_is_frozen() -> None:
    contract = audit()[
        "canonical_concept_contract"
    ]

    assert contract["status"] == "FROZEN"

    assert (
        contract["identity_field"]
        == "word_id"
    )

    assert (
        contract["identity_semantics"]
        == (
            "ONE_CONCEPT_ID_WITH_"
            "LOCALIZED_LANGUAGE_VIEWS"
        )
    )


def test_localized_view_contract_is_frozen() -> None:
    contract = audit()[
        "localized_view_contract"
    ]

    assert contract["status"] == "FROZEN"

    assert contract["identity_fields"] == [
        "word_id",
        "language",
    ]

    assert (
        contract[
            "language_view_is_separate_concept"
        ]
        is False
    )


def test_sampled_cross_language_identity_is_preserved() -> None:
    sampled = audit()[
        "localized_view_contract"
    ][
        "sampled_cross_language_identity"
    ]

    assert sampled["2704"] == [
        "ar",
        "en",
        "fr",
    ]

    assert sampled["4892"] == [
        "ar",
        "en",
    ]


def test_content_field_contract_freezes_variability_not_presence() -> None:
    contract = audit()[
        "content_field_contract"
    ]

    assert (
        contract["status"]
        == "FROZEN_VARIABLE_FIELDS"
    )

    assert contract[
        "mandatory_identity_fields"
    ] == [
        "word_id",
        "language",
        "source_url",
    ]

    assert (
        contract[
            "semantic_fields_are_variable"
        ]
        is True
    )

    assert (
        contract[
            "universally_mandatory_semantic_field"
        ]
        is None
    )

    assert (
        contract[
            "canonical_arabic_term_requirement"
        ]
        == "PREFERRED_NOT_UNIVERSALLY_PROVEN"
    )

    assert (
        contract["missing_field_policy"]
        == "PRESERVE_AS_MISSING"
    )


def test_terminology_authority_cannot_become_primary_evidence() -> None:
    boundary = audit()[
        "authority_boundary"
    ]

    assert (
        boundary["universal_primary_evidence"]
        is False
    )

    assert (
        boundary["cross_domain_primary_evidence"]
        is False
    )

    assert (
        boundary["machine_translation_override"]
        is False
    )


def test_unit_characterization_does_not_admit_runtime() -> None:
    state = audit()["runtime_state"]

    assert (
        state["runtime_admission"]
        == "PENDING_AUDIT"
    )

    assert (
        state["adapter"]
        == "NOT_IMPLEMENTED"
    )

    assert (
        state["source_trust_passport"]
        == "NOT_ISSUED"
    )
