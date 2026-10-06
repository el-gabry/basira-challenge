from __future__ import annotations

from basira.api.schemas import (
    QueryResponse,
    StructuredClaimResponse,
)


def test_structured_claim_response_preserves_provenance_links() -> None:
    claim = StructuredClaimResponse(
        axis_id="tafsir",
        claim_id="claim-1",
        text="نص تفسيري",
        evidence_ids=[
            "evidence-1",
        ],
    )

    assert claim.axis_id == "tafsir"
    assert claim.claim_id == "claim-1"

    assert claim.evidence_ids == [
        "evidence-1",
    ]


def test_query_response_schema_exposes_claims() -> None:
    schema = QueryResponse.model_json_schema()

    assert "claims" in schema["properties"]


def test_claim_schema_does_not_claim_semantic_verification() -> None:
    schema = StructuredClaimResponse.model_json_schema()

    properties = schema["properties"]

    assert "supported" not in properties

    assert "verified" not in properties

    assert "verification_status" not in properties
