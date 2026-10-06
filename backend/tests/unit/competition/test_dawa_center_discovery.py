from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(
    __file__
).resolve().parents[3]

DISCOVERY = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dawa-center"
    / "discovery.json"
)

CONTENT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dawa-center"
    / "content-contract.json"
)


def load(
    path: Path,
) -> dict:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def test_dawa_center_source_family_is_explicit() -> None:
    discovery = load(
        DISCOVERY
    )

    assert (
        discovery["source_family"]
        == "DAWA_CENTER"
    )

    assert (
        discovery["domain"]
        == "dawah_general_content"
    )

    assert (
        discovery["official_locator"]
        == "https://dawa.center/"
    )


def test_canonical_entity_identity_is_explicit() -> None:
    surface = load(
        DISCOVERY
    )["surface"]

    assert (
        surface[
            "canonical_entity_identity"
        ]
        == [
            "entity_type",
            "entity_key",
        ]
    )

    assert {
        "file",
        "book",
    } == set(
        surface[
            "content_entity_types"
        ]
    )


def test_dawah_route_families_are_frozen_from_observation() -> None:
    routes = load(
        DISCOVERY
    )["surface"][
        "canonical_route_templates"
    ]

    assert routes[
        "file"
    ] == (
        "https://dawa.center/"
        "file/{numeric_id}"
    )

    assert routes[
        "book"
    ] == (
        "https://dawa.center/"
        "book/{numeric_id}"
    )

    assert routes[
        "country"
    ] == (
        "https://dawa.center/"
        "country/{country_code}"
    )

    assert routes[
        "language"
    ] == (
        "https://dawa.center/"
        "language/{language_code}"
    )

    assert routes[
        "people_group"
    ] == (
        "https://dawa.center/"
        "people-group/{numeric_id}"
    )

    assert routes[
        "religion"
    ] == (
        "https://dawa.center/"
        "religion/{numeric_id}"
    )


def test_articles_is_listing_not_canonical_unit() -> None:
    surface = load(
        DISCOVERY
    )["surface"]

    assert (
        surface[
            "articles_listing_is_canonical_unit"
        ]
        is False
    )

    assert (
        surface[
            "articles_listing_detail_identity"
        ]
        == "file"
    )


def test_sitemap_observation_is_recorded_not_overgeneralized() -> None:
    sitemap = load(
        DISCOVERY
    )["sitemap_observation"]

    assert (
        sitemap[
            "observed_url_count"
        ]
        == 37563
    )

    counts = sitemap[
        "route_family_counts"
    ]

    assert counts["book"] == 9953
    assert counts["file"] == 9516
    assert counts["country"] == 250
    assert counts["language"] == 205
    assert counts["category"] == 84

    assert (
        sitemap[
            "people_group_detail_routes"
        ]
        == (
            "OBSERVED_FROM_LISTING_"
            "NOT_COUNTED_IN_SITEMAP_CENSUS"
        )
    )


def test_machine_readable_surface_is_not_overclaimed() -> None:
    findings = load(
        DISCOVERY
    )[
        "machine_readable_findings"
    ]

    assert (
        findings[
            "json_ld_observed"
        ]
        is True
    )

    assert (
        findings[
            "content_api_observed"
        ]
        is False
    )

    assert (
        findings[
            "html_is_current_extraction_surface"
        ]
        is True
    )


def test_robots_sensitive_routes_remain_outside_characterized_surface() -> None:
    boundaries = load(
        DISCOVERY
    )[
        "retrieval_boundaries"
    ]

    assert (
        boundaries[
            "download_artifact_body_characterized"
        ]
        is False
    )

    assert (
        boundaries[
            "search_endpoint_characterized"
        ]
        is False
    )

    prohibited = set(
        boundaries[
            "robots_sensitive_routes_not_used"
        ]
    )

    assert "/search" in prohibited
    assert "*/download" in prohibited
    assert "*/preview" in prohibited
    assert "/storage/files/" in prohibited


def test_dawa_center_authority_is_dawah_specific() -> None:
    role = load(
        DISCOVERY
    )[
        "source_role_findings"
    ]

    assert (
        role[
            "primary_dawah_general_content_source"
        ]
        is True
    )

    assert (
        role[
            "universal_primary_evidence"
        ]
        is False
    )

    assert (
        role[
            "religion_facet_grants_"
            "comparative_religion_authority"
        ]
        is False
    )

    assert (
        role[
            "jamhara_terminology_runtime_"
            "remains_separate"
        ]
        is True
    )


def test_content_authority_boundary_is_explicit() -> None:
    contract = load(
        CONTENT
    )

    prohibited = set(
        contract[
            "authority_scope"
        ][
            "prohibited_inferences"
        ]
    )

    assert (
        "UNIVERSAL_PRIMARY_EVIDENCE"
        in prohibited
    )

    assert (
        "AQEEDAH_PRIMARY_AUTHORITY_"
        "FROM_DAWAH_PAGE"
        in prohibited
    )

    assert (
        "RELIGIONS_SECTS_COMPARATIVE_"
        "AUTHORITY_FROM_DAWAH_FACET"
        in prohibited
    )

    assert (
        "TERMINOLOGY_AUTHORITY_"
        "FROM_DAWAH_PAGE"
        in prohibited
    )


def test_jamhara_dependency_does_not_launder_authority() -> None:
    boundary = load(
        CONTENT
    )[
        "dependency_boundary"
    ]

    assert (
        boundary[
            "jamhara_may_supply_"
            "governed_terminology"
        ]
        is True
    )

    assert (
        boundary[
            "jamhara_may_supply_general_"
            "dawah_content_authority"
        ]
        is False
    )

    assert (
        boundary[
            "dawa_center_may_replace_"
            "jamhara_terminology_authority"
        ]
        is False
    )


def test_discovery_does_not_admit_runtime() -> None:
    discovery = load(
        DISCOVERY
    )

    assert (
        discovery[
            "runtime_admission"
        ]
        == "PENDING_AUDIT"
    )

    assert (
        discovery["adapter"]
        == "NOT_IMPLEMENTED"
    )

    assert (
        discovery[
            "source_trust_passport"
        ]
        == "NOT_ISSUED"
    )


def test_dawa_center_field_census_is_deterministic() -> None:
    census_path = (
        ROOT
        / "data"
        / "competition"
        / "discovery"
        / "dawa-center"
        / "field-census.json"
    )

    census = load(
        census_path
    )

    assert (
        census["source"]
        == "DAWA_CENTER"
    )

    assert (
        census["domain"]
        == "dawah_general_content"
    )

    sampling = census[
        "sampling"
    ]

    assert (
        sampling[
            "sample_per_entity_type"
        ]
        == 5
    )

    assert (
        sampling[
            "entity_type_count"
        ]
        == 8
    )

    assert (
        sampling["sample_size"]
        == 40
    )

    assert (
        sampling["samples"]["file"]
        == [
            "https://dawa.center/file/10",
            "https://dawa.center/file/3083",
            "https://dawa.center/file/549",
            "https://dawa.center/file/778",
            "https://dawa.center/file/9999",
        ]
    )


def test_sampled_core_fields_are_stable_across_all_families() -> None:
    census = load(
        ROOT
        / "data"
        / "competition"
        / "discovery"
        / "dawa-center"
        / "field-census.json"
    )

    required = {
        "canonical_url",
        "title",
        "meta_description",
        "json_ld",
        "json_ld_type",
        "json_ld_name",
        "json_ld_description",
        "h2",
    }

    prevalence = census[
        "field_prevalence"
    ]

    for family, fields in prevalence.items():
        assert (
            required.issubset(
                fields
            )
        )

        for field in required:
            assert (
                fields[field]
                == "5/5"
            ), (
                family,
                field,
                fields[field],
            )

    findings = census[
        "cross_family_findings"
    ]

    assert (
        findings[
            "sampled_stable_fields_count"
        ]
        == "40/40"
    )

    assert (
        findings["h1_presence"]
        == "10/40"
    )

    assert (
        findings[
            "h1_is_runtime_requirement"
        ]
        is False
    )

    assert (
        findings[
            "corpus_wide_field_guarantee_proven"
        ]
        is False
    )


def test_relationship_links_are_optional_expansion_not_authority() -> None:
    census = load(
        ROOT
        / "data"
        / "competition"
        / "discovery"
        / "dawa-center"
        / "field-census.json"
    )

    relations = census[
        "relationship_prevalence"
    ]

    assert (
        relations[
            "people_group"
        ][
            "related_file_links"
        ]
        == "5/5"
    )

    assert (
        relations[
            "religion"
        ][
            "related_file_links"
        ]
        == "5/5"
    )

    assert (
        relations[
            "category"
        ][
            "related_file_links"
        ]
        == "4/5"
    )

    assert (
        relations[
            "country"
        ][
            "related_file_links"
        ]
        == "0/5"
    )

    assert (
        census[
            "field_semantics"
        ][
            "relationship_links_are"
        ]
        == (
            "OPTIONAL_RETRIEVAL_"
            "EXPANSION_NOT_EVIDENTIARY_"
            "AUTHORITY"
        )
    )


def test_hybrid_agent_content_and_context_roles_are_explicit() -> None:
    contract = load(
        CONTENT
    )[
        "hybrid_agent_contract"
    ]

    assert (
        contract["status"]
        == "FROZEN"
    )

    roles = contract[
        "role_map"
    ]

    assert (
        roles["file"]
        == "CONTENT_EVIDENCE_CANDIDATE"
    )

    assert (
        roles["book"]
        == "CONTENT_EVIDENCE_CANDIDATE"
    )

    for entity_type in (
        "category",
        "language",
        "country",
        "people_group",
        "religion",
        "islamic_centre",
    ):
        assert (
            roles[entity_type]
            == "ROUTING_CONTEXT"
        )

    assert (
        contract[
            "dawa_center_may_override_"
            "jamhara_terminology"
        ]
        is False
    )

    assert (
        contract[
            "religion_context_may_grant_"
            "comparative_religion_authority"
        ]
        is False
    )


def test_field_census_does_not_admit_runtime() -> None:
    census = load(
        ROOT
        / "data"
        / "competition"
        / "discovery"
        / "dawa-center"
        / "field-census.json"
    )

    assert (
        census[
            "runtime_admission"
        ]
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
