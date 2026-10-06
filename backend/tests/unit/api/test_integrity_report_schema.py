from __future__ import annotations

from basira.api.schemas import (
    IntegrityReportResponse,
    QueryResponse,
)


def test_query_response_exposes_integrity_report() -> None:
    schema = QueryResponse.model_json_schema()

    assert "integrity_report" in schema["properties"]


def test_integrity_report_contract_is_explicitly_non_semantic() -> None:
    report = IntegrityReportResponse(
        literal_source_integrity=("passed"),
        claims_checked=1,
        claim_ids=[
            "claim-1",
        ],
        linked_evidence_ids=[
            "evidence-1",
        ],
        has_limitations=False,
        limitation_count=0,
        potential_source_conflict=False,
        conflict_count=0,
        conflict_types=[],
        conflict_group_ids=[],
        semantic_claim_verification=("not_enabled"),
    )

    assert report.semantic_claim_verification == "not_enabled"

    properties = IntegrityReportResponse.model_json_schema()["properties"]

    for forbidden in (
        "supported",
        "verified",
        "semantic_score",
    ):
        assert forbidden not in properties
