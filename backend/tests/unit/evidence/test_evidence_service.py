from dataclasses import replace

import pytest

from basira.evidence.decision import (
    EvidenceDecisionAction,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.evidence.service import (
    EvidenceDecisionService,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
    RiskTag,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)


def make_result(
    *,
    high_risk: bool = False,
) -> UnifiedRetrievalResult:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما معنى الآية 2:255؟"
        )
    )

    if high_risk:
        understanding = replace(
            understanding,
            risk_tags=frozenset(
                {
                    RiskTag.TAKFIR,
                    RiskTag.CONTEXT_SENSITIVE,
                }
            ),
        )

    plan = (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )

    return UnifiedRetrievalResult(
        plan=plan,
        evidence=(
            EvidenceNode(
                evidence_id="quran:2:255",
                domain=(
                    EvidenceDomain.QURAN
                ),
                text="نص الآية.",
                source_id="quran-source",
                reference="2:255",
            ),
            EvidenceNode(
                evidence_id="tafsir:2:255",
                domain=(
                    EvidenceDomain.TAFSIR
                ),
                text="نص التفسير.",
                source_id="tafsir-source",
                reference="2:255",
            ),
        ),
        unavailable_domains=frozenset(),
    )


def test_complete_evidence_returns_answer_without_expert_packet() -> None:
    outcome = (
        EvidenceDecisionService()
        .evaluate(
            retrieval_result=(
                make_result()
            )
        )
    )

    assert (
        outcome.decision.action
        == EvidenceDecisionAction.ANSWER
    )

    assert (
        outcome.expert_review
        is None
    )


def test_high_risk_case_creates_expert_review_packet() -> None:
    outcome = (
        EvidenceDecisionService()
        .evaluate(
            retrieval_result=(
                make_result(
                    high_risk=True
                )
            ),
            expert_case_id=(
                "BASIRA-1001"
            ),
        )
    )

    assert (
        outcome.decision.action
        == EvidenceDecisionAction
        .ESCALATE_TO_EXPERT
    )

    assert (
        outcome.expert_review
        is not None
    )

    assert (
        outcome.expert_review.case_id
        == "BASIRA-1001"
    )


def test_escalation_without_case_id_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="expert_case_id is required",
    ):
        (
            EvidenceDecisionService()
            .evaluate(
                retrieval_result=(
                    make_result(
                        high_risk=True
                    )
                )
            )
        )
