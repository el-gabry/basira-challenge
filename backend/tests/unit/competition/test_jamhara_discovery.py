from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

DISCOVERY = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "jamhara"
    / "discovery.json"
)

CONTENT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "jamhara"
    / "content-contract.json"
)

CENSUS = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "jamhara"
    / "field-census.json"
)


def load(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def test_jamhara_source_family_is_explicit() -> None:
    d = load(DISCOVERY)

    assert (
        d["source_family"]
        == "AL_JAMHARA_ISLAMIC_TERMINOLOGY"
    )

    assert (
        d["domain"]
        == "translation_terminology"
    )


def test_word_id_is_canonical_concept_identity() -> None:
    surface = load(DISCOVERY)["surface"]

    assert (
        surface["canonical_concept_identity"]
        == "word_id"
    )

    assert surface["localized_view_identity"] == [
        "word_id",
        "language",
    ]


def test_multilingual_route_surface_is_explicit() -> None:
    surface = load(DISCOVERY)["surface"]

    assert {
        "ar",
        "en",
        "fr",
    }.issubset(
        set(
            surface[
                "advertised_language_routes"
            ]
        )
    )

    assert (
        surface["route_characterization"]
        == (
            "STRUCTURALLY_STABLE_"
            "ON_SAMPLED_ROUTES"
        )
    )


def test_machine_readable_surface_is_not_overclaimed() -> None:
    findings = load(DISCOVERY)[
        "machine_readable_findings"
    ]

    assert findings["json_ld_observed"] is True
    assert findings["next_data_observed"] is False
    assert findings["nuxt_payload_observed"] is False
    assert findings["content_api_observed"] is False


def test_jamhara_is_terminology_not_universal_evidence() -> None:
    role = load(DISCOVERY)[
        "source_role_findings"
    ]

    assert role["terminology_authority"] is True

    assert (
        role["universal_primary_evidence"]
        is False
    )

    assert (
        role[
            "cross_domain_claims_require_"
            "primary_domain_routing"
        ]
        is True
    )


def test_content_authority_boundary_is_explicit() -> None:
    contract = load(CONTENT)

    prohibited = set(
        contract[
            "authority_scope"
        ][
            "prohibited_inferences"
        ]
    )

    assert "UNIVERSAL_PRIMARY_EVIDENCE" in prohibited

    assert (
        "FIQH_AUTHORITY_FROM_TERMINOLOGY_ENTRY"
        in prohibited
    )

    assert (
        "AQEEDAH_AUTHORITY_FROM_TERMINOLOGY_ENTRY"
        in prohibited
    )


def test_discovery_does_not_admit_runtime() -> None:
    d = load(DISCOVERY)

    assert (
        d["runtime_admission"]
        == "PENDING_AUDIT"
    )

    assert d["adapter"] == "NOT_IMPLEMENTED"

    assert (
        d["source_trust_passport"]
        == "NOT_ISSUED"
    )



def test_jamhara_field_census_is_frozen() -> None:
    census = load(CENSUS)

    assert (
        census[
            "candidate_discovery"
        ][
            "deduplicated_candidate_word_id_count"
        ]
        == 4382
    )

    assert (
        census["sampling"]["sample_size"]
        == 30
    )

    assert (
        census[
            "route_results"
        ][
            "arabic_http_200"
        ]
        == "30/30"
    )

    assert (
        census[
            "route_results"
        ][
            "english_http_200"
        ]
        == "30/30"
    )

    assert (
        census[
            "route_results"
        ][
            "corpus_wide_ar_en_guarantee_proven"
        ]
        is False
    )


def test_jamhara_census_proves_content_fields_are_variable() -> None:
    census = load(CENSUS)

    assert (
        census[
            "field_prevalence"
        ]["ar"]["definition"]
        == "26/30"
    )

    assert (
        census[
            "field_prevalence"
        ]["en"]["definition"]
        == "24/30"
    )

    assert (
        census[
            "conclusions"
        ][
            "any_single_semantic_content_field_universally_mandatory"
        ]
        is False
    )

    assert (
        len(
            census[
                "known_marker_anomalies"
            ]
        )
        == 6
    )


def test_frozen_content_contract_does_not_fabricate_missing_fields() -> None:
    contract = load(CONTENT)

    assert contract["status"] == "FROZEN"

    fields = contract[
        "field_contract"
    ]

    assert (
        fields["status"]
        == "FROZEN_VARIABLE_CONTENT"
    )

    assert fields[
        "mandatory_identity_fields"
    ] == [
        "word_id",
        "language",
        "source_url",
    ]

    assert (
        fields[
            "universally_mandatory_semantic_field"
        ]
        is None
    )

    assert (
        fields["fabricate_missing_content"]
        is False
    )

    assert (
        fields["missing_field_policy"]
        == "PRESERVE_AS_MISSING"
    )


def test_field_census_does_not_admit_runtime() -> None:
    census = load(CENSUS)

    assert (
        census["runtime_admission"]
        == "PENDING_AUDIT"
    )

    assert (
        census[
            "conclusions"
        ][
            "census_grants_runtime_admission"
        ]
        is False
    )



def test_jamhara_candidate_count_provenance_is_explicit() -> None:
    census = load(CENSUS)

    candidate = census[
        "candidate_discovery"
    ]

    assert (
        candidate[
            "candidate_construction"
        ]
        == (
            "SEED_DISCOVERED_UNION_"
            "CHARACTERIZED_WORD_IDS"
        )
    )

    assert (
        candidate[
            "seed_discovered_word_id_count"
        ]
        == 4381
    )

    assert (
        candidate[
            "characterized_word_ids_added_to_candidate_set"
        ]
        == [
            1197,
            2704,
            4892,
        ]
    )

    assert (
        candidate[
            "characterized_word_ids_missing_from_seed"
        ]
        == [
            4892,
        ]
    )

    assert (
        candidate[
            "deduplicated_candidate_word_id_count"
        ]
        == 4382
    )
