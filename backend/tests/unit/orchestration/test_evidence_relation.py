from __future__ import annotations

import pytest

from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
    EvidenceNode,
)
from basira.orchestration.contracts import (
    ClaimTask,
)
from basira.orchestration.evidence_acceptance import (
    AnchorKind,
    EvidenceAnchor,
    RetrievalShape,
    TaskEvidenceAcceptanceContract,
    TaskEvidenceAcceptanceGate,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
    ClaimEvidenceRelationGate,
    ClaimEvidenceRelationRecord,
    RelationOrigin,
    TaskEvidenceRelationService,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)


def task() -> ClaimTask:
    text = "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟"

    return ClaimTask(
        task_id="claim:chair",
        claim_text=text,
        frame=ReligiousReasoningFrame(
            frame_id="frame:chair",
            question=text,
            primary_discipline=(ReligiousDiscipline.QURAN),
            reasoning_mode=(ReasoningMode.INTERPRETATION),
        ),
        context_requirement=(ContextRequirement()),
    )


def node(
    *,
    evidence_id: str,
    domain: EvidenceDomain = (EvidenceDomain.TAFSIR),
    reference: str = "2:255",
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=domain,
        text=f"text:{evidence_id}",
        source_id=f"source:{evidence_id}",
        reference=reference,
    )


def structural_result():
    contract = TaskEvidenceAcceptanceContract(
        task_id="claim:chair",
        retrieval_shape=(RetrievalShape.HYBRID),
        allowed_domains=frozenset(
            {
                EvidenceDomain.QURAN,
                EvidenceDomain.TAFSIR,
            }
        ),
        required_domains=frozenset(
            {
                EvidenceDomain.QURAN,
                EvidenceDomain.TAFSIR,
            }
        ),
        anchors=(
            EvidenceAnchor(
                reference="2:255",
                domains=frozenset(
                    {
                        EvidenceDomain.QURAN,
                        EvidenceDomain.TAFSIR,
                    }
                ),
                kind=(AnchorKind.QURAN_AYAH),
            ),
        ),
    )

    return TaskEvidenceAcceptanceGate().evaluate(
        contract=contract,
        evidence=(
            node(
                evidence_id="quran:2:255",
                domain=(EvidenceDomain.QURAN),
            ),
            node(
                evidence_id="tafsir:right",
            ),
            node(
                evidence_id="tafsir:wrong",
                reference="2:43",
            ),
        ),
    )


def record(
    evidence_id: str,
    relation: ClaimEvidenceRelation,
    *,
    origin: RelationOrigin = (RelationOrigin.DETERMINISTIC),
) -> ClaimEvidenceRelationRecord:
    return ClaimEvidenceRelationRecord(
        task_id="claim:chair",
        evidence_id=evidence_id,
        relation=relation,
        origin=origin,
    )


def test_missing_relation_is_unknown_fail_closed() -> None:
    evidence = (
        node(evidence_id="a"),
        node(evidence_id="b"),
    )

    result = ClaimEvidenceRelationGate().assess(
        task_id="claim:chair",
        evidence=evidence,
        records=(
            record(
                "a",
                ClaimEvidenceRelation.SUPPORTS,
            ),
        ),
    )

    assert result.supporting_evidence_ids == ("a",)

    assert result.unknown_evidence_ids == ("b",)

    assert result.has_positive_support
    assert result.has_unresolved_relations

    assert result.usable_evidence_ids == ("a",)


def test_context_is_not_positive_support() -> None:
    result = ClaimEvidenceRelationGate().assess(
        task_id="claim:chair",
        evidence=(
            node(
                evidence_id="quran",
                domain=(EvidenceDomain.QURAN),
            ),
        ),
        records=(
            record(
                "quran",
                ClaimEvidenceRelation.CONTEXT_ONLY,
            ),
        ),
    )

    assert not result.has_positive_support

    assert result.context_only_evidence_ids == ("quran",)

    assert result.usable_evidence_ids == ("quran",)


def test_partial_does_not_become_support() -> None:
    result = ClaimEvidenceRelationGate().assess(
        task_id="claim:chair",
        evidence=(node(evidence_id="partial"),),
        records=(
            record(
                "partial",
                ClaimEvidenceRelation.PARTIAL,
            ),
        ),
    )

    assert not result.has_positive_support
    assert result.has_unresolved_relations

    assert result.partial_evidence_ids == ("partial",)


def test_contradiction_is_preserved_not_silently_dropped() -> None:
    result = ClaimEvidenceRelationGate().assess(
        task_id="claim:chair",
        evidence=(
            node(evidence_id="support"),
            node(evidence_id="opposes"),
        ),
        records=(
            record(
                "support",
                ClaimEvidenceRelation.SUPPORTS,
            ),
            record(
                "opposes",
                ClaimEvidenceRelation.CONTRADICTS,
            ),
        ),
    )

    assert result.has_positive_support
    assert result.has_contradiction

    assert result.contradicting_evidence_ids == ("opposes",)

    assert result.usable_evidence_ids == (
        "support",
        "opposes",
    )


def test_irrelevant_is_not_usable() -> None:
    result = ClaimEvidenceRelationGate().assess(
        task_id="claim:chair",
        evidence=(
            node(evidence_id="relevant"),
            node(evidence_id="noise"),
        ),
        records=(
            record(
                "relevant",
                ClaimEvidenceRelation.SUPPORTS,
            ),
            record(
                "noise",
                ClaimEvidenceRelation.IRRELEVANT,
            ),
        ),
    )

    assert result.irrelevant_evidence_ids == ("noise",)

    assert result.usable_evidence_ids == ("relevant",)


def test_duplicate_relation_fails_closed() -> None:
    evidence = (node(evidence_id="a"),)

    with pytest.raises(
        ValueError,
        match="duplicate relation",
    ):
        (
            ClaimEvidenceRelationGate().assess(
                task_id="claim:chair",
                evidence=evidence,
                records=(
                    record(
                        "a",
                        ClaimEvidenceRelation.SUPPORTS,
                    ),
                    record(
                        "a",
                        ClaimEvidenceRelation.IRRELEVANT,
                    ),
                ),
            )
        )


def test_unknown_evidence_relation_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="unknown evidence",
    ):
        (
            ClaimEvidenceRelationGate().assess(
                task_id="claim:chair",
                evidence=(node(evidence_id="a"),),
                records=(
                    record(
                        "missing",
                        ClaimEvidenceRelation.SUPPORTS,
                    ),
                ),
            )
        )


def test_wrong_task_relation_fails_closed() -> None:
    bad = ClaimEvidenceRelationRecord(
        task_id="claim:other",
        evidence_id="a",
        relation=(ClaimEvidenceRelation.SUPPORTS),
        origin=(RelationOrigin.DETERMINISTIC),
    )

    with pytest.raises(
        ValueError,
        match="different task",
    ):
        (
            ClaimEvidenceRelationGate().assess(
                task_id="claim:chair",
                evidence=(node(evidence_id="a"),),
                records=(bad,),
            )
        )


def test_unassessed_cannot_claim_support() -> None:
    with pytest.raises(
        ValueError,
        match="unassessed relation",
    ):
        ClaimEvidenceRelationRecord(
            task_id="claim:chair",
            evidence_id="a",
            relation=(ClaimEvidenceRelation.SUPPORTS),
            origin=(RelationOrigin.UNASSESSED),
        )


def test_confidence_is_bounded() -> None:
    with pytest.raises(
        ValueError,
        match="confidence",
    ):
        ClaimEvidenceRelationRecord(
            task_id="claim:chair",
            evidence_id="a",
            relation=(ClaimEvidenceRelation.SUPPORTS),
            origin=RelationOrigin.MODEL,
            confidence=1.1,
        )


class RecordingEvaluator:
    def __init__(
        self,
    ) -> None:
        self.evidence_ids: list[str] = []

    def evaluate(
        self,
        *,
        task: ClaimTask,
        evidence: EvidenceNode,
    ) -> ClaimEvidenceRelationRecord:
        self.evidence_ids.append(evidence.evidence_id)

        relation = (
            ClaimEvidenceRelation.CONTEXT_ONLY
            if evidence.domain is EvidenceDomain.QURAN
            else ClaimEvidenceRelation.SUPPORTS
        )

        return ClaimEvidenceRelationRecord(
            task_id=task.task_id,
            evidence_id=(evidence.evidence_id),
            relation=relation,
            origin=(RelationOrigin.DETERMINISTIC),
        )


def test_service_never_evaluates_structurally_rejected_evidence() -> None:
    structural = structural_result()

    assert {item.evidence_id for item in structural.accepted_evidence} == {
        "quran:2:255",
        "tafsir:right",
    }

    assert {item.evidence_id for item in structural.rejected_evidence} == {
        "tafsir:wrong",
    }

    evaluator = RecordingEvaluator()

    result = TaskEvidenceRelationService(
        evaluator=evaluator,
    ).evaluate(
        task=task(),
        structural=structural,
    )

    assert set(evaluator.evidence_ids) == {
        "quran:2:255",
        "tafsir:right",
    }

    assert "tafsir:wrong" not in evaluator.evidence_ids

    assert result.supporting_evidence_ids == ("tafsir:right",)

    assert result.context_only_evidence_ids == ("quran:2:255",)


def test_default_service_is_semantically_fail_closed() -> None:
    result = TaskEvidenceRelationService().evaluate(
        task=task(),
        structural=structural_result(),
    )

    assert set(result.unknown_evidence_ids) == {
        "quran:2:255",
        "tafsir:right",
    }

    assert not result.has_positive_support
    assert result.has_unresolved_relations


def test_relation_result_does_not_claim_truth_or_answerability() -> None:
    result = TaskEvidenceRelationService().evaluate(
        task=task(),
        structural=structural_result(),
    )

    for forbidden in (
        "answerable",
        "truth",
        "verified",
        "religious_ruling",
        "hadith_grade",
    ):
        assert not hasattr(
            result,
            forbidden,
        )
