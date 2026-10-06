from __future__ import annotations

from basira.answer.composer import (
    GroundedAnswerComposer,
)
from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceRequirementAssessment,
    EvidenceRequirementState,
)
from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionAction,
    EvidenceDecisionReason,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
)


def _node(
    *,
    evidence_id: str,
    text: str,
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=EvidenceDomain.TAFSIR,
        text=text,
        source_id=("surahapp-tafsir-saadi"),
        reference="2:153",
    )


def _answer_outcome(
    *nodes: EvidenceNode,
) -> EvidenceDecisionOutcome:
    bundle = EvidenceBundle(
        evidence=tuple(nodes),
        required_assessments=(
            EvidenceRequirementAssessment(
                need=EvidenceNeed.TAFSIR,
                state=(EvidenceRequirementState.SATISFIED),
                evidence_ids=tuple(node.evidence_id for node in nodes),
            ),
        ),
    )

    return EvidenceDecisionOutcome(
        bundle=bundle,
        decision=EvidenceDecision(
            action=(EvidenceDecisionAction.ANSWER),
            reasons=(EvidenceDecisionReason.COMPLETE_EVIDENCE,),
        ),
        expert_review=None,
    )


def test_answer_exposes_structured_claims_with_evidence_links() -> None:
    first = _node(
        evidence_id="tafsir-1",
        text="الصبر معونة للمؤمن عند الشدة.",
    )

    second = _node(
        evidence_id="tafsir-2",
        text="وفي الآية توجيه إلى الاستعانة بالله.",
    )

    answer = GroundedAnswerComposer().compose(
        question=("ماذا يقول التفسير عن الصبر؟"),
        outcome=_answer_outcome(
            first,
            second,
        ),
    )

    assert len(answer.claims) == 2

    assert answer.claims[0].claim_id == ("claim-1")

    assert answer.claims[0].axis_id == (EvidenceNeed.TAFSIR.value)

    assert answer.claims[0].evidence_ids == ("tafsir-1",)

    assert answer.claims[1].evidence_ids == ("tafsir-2",)


def test_claim_text_is_source_derived_not_newly_generated() -> None:
    source_text = "هذا نص تفسيري قصير مرتبط بالدليل."

    node = _node(
        evidence_id="tafsir-1",
        text=source_text,
    )

    answer = GroundedAnswerComposer().compose(
        question="سؤال",
        outcome=_answer_outcome(node),
    )

    assert answer.claims[0].text == (source_text)

    assert answer.claims[0].text in (answer.answer or "")


def test_every_claim_evidence_id_is_used_and_citable() -> None:
    nodes = (
        _node(
            evidence_id="tafsir-1",
            text="النص الأول.",
        ),
        _node(
            evidence_id="tafsir-2",
            text="النص الثاني.",
        ),
    )

    answer = GroundedAnswerComposer().compose(
        question="سؤال",
        outcome=_answer_outcome(*nodes),
    )

    used = set(answer.used_evidence_ids)

    cited = {citation.evidence_id for citation in answer.citations}

    for claim in answer.claims:
        assert claim.evidence_ids

        for evidence_id in claim.evidence_ids:
            assert evidence_id in used
            assert evidence_id in cited


def test_non_answer_action_has_no_claims() -> None:
    bundle = EvidenceBundle(
        evidence=(),
        required_assessments=(
            EvidenceRequirementAssessment(
                need=EvidenceNeed.TAFSIR,
                state=(EvidenceRequirementState.MISSING_EVIDENCE),
            ),
        ),
    )

    outcome = EvidenceDecisionOutcome(
        bundle=bundle,
        decision=EvidenceDecision(
            action=(EvidenceDecisionAction.RETRIEVE_MORE),
            reasons=(EvidenceDecisionReason.MISSING_REQUIRED_EVIDENCE,),
            unresolved_needs=(EvidenceNeed.TAFSIR,),
        ),
        expert_review=None,
    )

    answer = GroundedAnswerComposer().compose(
        question="سؤال",
        outcome=outcome,
    )

    assert answer.claims == ()


def test_resolved_absence_does_not_create_positive_claim() -> None:
    bundle = EvidenceBundle(
        evidence=(),
        required_assessments=(
            EvidenceRequirementAssessment(
                need=(EvidenceNeed.REVELATION_CONTEXT),
                state=(EvidenceRequirementState.NO_ATTESTED_ENTRY),
            ),
        ),
    )

    outcome = EvidenceDecisionOutcome(
        bundle=bundle,
        decision=EvidenceDecision(
            action=(EvidenceDecisionAction.ANSWER_WITH_LIMITATION),
            reasons=(EvidenceDecisionReason.RESOLVED_ABSENCE,),
            unresolved_needs=(EvidenceNeed.REVELATION_CONTEXT,),
        ),
        expert_review=None,
    )

    answer = GroundedAnswerComposer().compose(
        question="ما سبب النزول؟",
        outcome=outcome,
    )

    assert answer.claims == ()
    assert answer.used_evidence_ids == ()
