from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(
    __file__
).resolve().parents[3]

AUDIT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dawa-center"
    / "unit-structure.json"
)


def audit() -> dict:
    return json.loads(
        AUDIT.read_text(
            encoding="utf-8"
        )
    )


def test_canonical_entity_contract_is_frozen() -> None:
    contract = audit()[
        "canonical_entity_contract"
    ]

    assert (
        contract["status"]
        == "FROZEN"
    )

    assert (
        contract[
            "identity_fields"
        ]
        == [
            "entity_type",
            "entity_key",
        ]
    )

    assert (
        contract[
            "identity_semantics"
        ]
        == (
            "ONE_OFFICIAL_ENTITY_PER_"
            "TYPE_AND_CANONICAL_ROUTE_KEY"
        )
    )


def test_content_and_context_entities_are_distinct() -> None:
    contract = audit()[
        "entity_type_contract"
    ]

    assert (
        set(
            contract[
                "content_entities"
            ]
        )
        == {
            "file",
            "book",
        }
    )

    assert (
        set(
            contract[
                "context_entities"
            ]
        )
        == {
            "category",
            "language",
            "country",
            "people_group",
            "religion",
            "islamic_centre",
        }
    )


def test_route_key_semantics_do_not_overclaim_iso_contracts() -> None:
    entities = audit()[
        "entity_type_contract"
    ][
        "context_entities"
    ]

    assert (
        entities[
            "country"
        ][
            "key_shape"
        ]
        == (
            "OBSERVED_UPPERCASE_"
            "COUNTRY_CODE"
        )
    )

    assert (
        entities[
            "language"
        ][
            "key_shape"
        ]
        == "OBSERVED_LANGUAGE_CODE"
    )

    assert (
        entities[
            "islamic_centre"
        ][
            "key_shape"
        ]
        == (
            "OPAQUE_CANONICAL_"
            "PATH_SEGMENT"
        )
    )


def test_articles_listing_cannot_create_article_entity() -> None:
    contract = audit()[
        "listing_contract"
    ][
        "articles"
    ]

    assert (
        contract[
            "canonical_unit"
        ]
        is False
    )

    assert (
        contract[
            "observed_detail_entity_type"
        ]
        == "file"
    )

    assert (
        contract[
            "sample_article_detail_links"
        ]
        == 0
    )

    assert (
        contract[
            "sample_file_detail_links"
        ]
        == 9
    )


def test_localized_view_identity_is_not_prematurely_frozen() -> None:
    contract = audit()[
        "localized_view_contract"
    ]

    assert (
        contract["status"]
        == "NOT_YET_FROZEN"
    )

    assert (
        contract[
            "lang_query_links_observed"
        ]
        is True
    )

    assert (
        contract[
            "language_view_is_separate_entity"
        ]
        is False
    )

    assert (
        contract[
            "corpus_wide_localized_view_guarantee"
        ]
        is False
    )


def test_semantic_field_contract_is_frozen_from_census() -> None:
    contract = audit()[
        "content_field_contract"
    ]

    assert (
        contract["status"]
        == "FROZEN_FROM_CENSUS"
    )

    assert (
        contract["sample_size"]
        == 40
    )

    assert (
        contract[
            "mandatory_identity_fields"
        ]
        == [
            "entity_type",
            "entity_key",
            "source_url",
        ]
    )

    assert (
        contract[
            "universally_mandatory_semantic_field"
        ]
        is None
    )

    assert (
        contract[
            "corpus_wide_presence_guarantee"
        ]
        is False
    )

    assert (
        contract[
            "runtime_payload_contract_frozen"
        ]
        is True
    )

    assert (
        contract[
            "missing_required_runtime_payload_policy"
        ]
        == "FAIL_CLOSED"
    )

    assert (
        contract[
            "fabricate_missing_content"
        ]
        is False
    )


def test_hybrid_agent_roles_are_frozen() -> None:
    contract = audit()[
        "hybrid_agent_role_contract"
    ]

    assert (
        contract["status"]
        == "FROZEN"
    )

    assert set(
        contract[
            "content_evidence_candidates"
        ]
    ) == {
        "file",
        "book",
    }

    assert set(
        contract[
            "routing_context_entities"
        ]
    ) == {
        "category",
        "language",
        "country",
        "people_group",
        "religion",
        "islamic_centre",
    }

    assert (
        contract[
            "routing_context_is_answer_evidence"
        ]
        is False
    )

    assert (
        contract[
            "cross_domain_claims_require_primary_domain_routing"
        ]
        is True
    )

def test_dawah_authority_does_not_cross_domain_boundaries() -> None:
    boundary = audit()[
        "authority_boundary"
    ]

    assert (
        boundary[
            "universal_primary_evidence"
        ]
        is False
    )

    assert (
        boundary[
            "cross_domain_primary_evidence"
        ]
        is False
    )

    assert (
        boundary[
            "religions_sects_"
            "comparative_authority"
        ]
        is False
    )

    assert (
        boundary[
            "terminology_authority"
        ]
        is False
    )

    assert (
        boundary[
            "generic_shamela_fallback_allowed"
        ]
        is False
    )


def test_unit_characterization_does_not_admit_runtime() -> None:
    state = audit()[
        "runtime_state"
    ]

    assert (
        state[
            "runtime_admission"
        ]
        == "PENDING_AUDIT"
    )

    assert (
        state["adapter"]
        == "NOT_IMPLEMENTED"
    )

    assert (
        state[
            "source_trust_passport"
        ]
        == "NOT_ISSUED"
    )
