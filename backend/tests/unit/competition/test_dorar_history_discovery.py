from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[3]


DISCOVERY = (
    ROOT
    / "data/competition/discovery/"
    "dorar-history/"
    "discovery.json"
)


def data():
    return json.loads(
        DISCOVERY.read_text(
            encoding="utf-8"
        )
    )


def test_characterization_passes() -> None:
    d = data()

    assert d["result"] == "PASS"

    assert (
        d["source_family"]
        == "DORAR_HISTORY"
    )


def test_runtime_is_not_prematurely_admitted() -> None:
    d = data()

    assert (
        d["runtime_admission"]
        == "PENDING_AUDIT"
    )

    assert (
        d["adapter"]
        == "NOT_IMPLEMENTED"
    )

    assert (
        d[
            "source_trust_passport"
        ]
        == "NOT_ISSUED"
    )


def test_core_history_methodology() -> None:
    f = data()["findings"]

    assert (
        f[
            "methodology_requires_reliable_source"
        ]
        is True
    )

    assert (
        f[
            "methodology_requires_scientific_editing"
        ]
        is True
    )


def test_history_specific_review_evidence() -> None:
    f = data()["findings"]

    assert (
        f[
            "methodology_review_process_observed"
        ]
        is True
    )

    assert (
        f[
            "history_review_section_observed"
        ]
        is True
    )

    assert (
        f[
            "history_specialist_reviewers_observed"
        ]
        is True
    )

    assert (
        f[
            "history_researcher_qualification_observed"
        ]
        is True
    )

    assert (
        f[
            "history_professor_qualification_count"
        ]
        >= 3
    )


def test_absent_generic_review_phrases_remain_absent() -> None:
    f = data()["findings"]

    assert (
        f[
            "generic_methodology_adoption_phrase_observed"
        ]
        is False
    )

    assert (
        f[
            "generic_application_verification_phrase_observed"
        ]
        is False
    )


def test_other_encyclopedia_review_text_cannot_satisfy_history() -> None:
    assert (
        data()[
            "findings"
        ][
            "global_cross_encyclopedia_review_text_is_history_evidence"
        ]
        is False
    )


def test_disagreement_is_preserved_not_graded() -> None:
    f = data()["findings"]

    assert (
        f[
            "textual_disagreement_inside_event_observed"
        ]
        is True
    )

    assert (
        f[
            "lexical_disagreement_marker_equals_truth_grade"
        ]
        is False
    )


def test_prophetic_report_requires_cross_domain_boundary() -> None:
    assert (
        data()[
            "findings"
        ][
            "prophetic_report_inside_history_event_observed"
        ]
        is True
    )


def test_both_event_route_families_are_preserved() -> None:
    f = data()["findings"]

    assert (
        f[
            "direct_history_id_route_observed"
        ]
        is True
    )

    assert (
        f[
            "history_event_id_route_observed"
        ]
        is True
    )

    assert (
        f[
            "route_contract_frozen"
        ]
        is False
    )


def test_no_per_event_truth_grade_is_invented() -> None:
    assert (
        data()[
            "findings"
        ][
            "per_event_machine_truth_grade_observed"
        ]
        is False
    )


def test_search_is_locator_only() -> None:
    assert (
        data()[
            "findings"
        ][
            "search_is_locator_only"
        ]
        is True
    )


def test_reference_catalog_is_governance_metadata() -> None:
    assert (
        data()[
            "findings"
        ][
            "reference_catalog_is_governance_metadata"
        ]
        is True
    )


def test_generic_shamela_fallback_is_prohibited() -> None:
    assert (
        data()[
            "findings"
        ][
            "generic_shamela_fallback_allowed"
        ]
        is False
    )
