from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from basira.answer.composer import (
    GroundedAnswerComposer,
)
from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceRequirementAssessment,
    EvidenceRequirementState,
)
from basira.evidence.decision import (
    EvidenceDecisionAction,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
)


@dataclass(
    frozen=True,
    slots=True,
)
class _Decision:
    action: EvidenceDecisionAction


def _outcome(
    *,
    action: EvidenceDecisionAction,
    bundle: EvidenceBundle,
    expert_review: Any = None,
) -> EvidenceDecisionOutcome:
    return EvidenceDecisionOutcome(
        bundle=bundle,
        decision=cast(
            Any,
            _Decision(action=action),
        ),
        expert_review=cast(
            Any,
            expert_review,
        ),
    )


def _bundle(
    *,
    evidence: tuple[
        EvidenceNode,
        ...,
    ],
    assessments: tuple[
        EvidenceRequirementAssessment,
        ...,
    ],
) -> EvidenceBundle:
    return EvidenceBundle(
        evidence=evidence,
        required_assessments=(assessments),
    )


def test_answer_uses_only_resolvable_evidence_citations() -> None:
    node = EvidenceNode(
        evidence_id="hadith:1",
        domain=EvidenceDomain.HADITH,
        text="نص حديث موثّق للاختبار.",
        source_id="hadeethenc-official",
        source_version="test-v1",
        reference="1",
        source_url=("https://hadeethenc.com/"),
    )

    bundle = _bundle(
        evidence=(node,),
        assessments=(
            EvidenceRequirementAssessment(
                need=(EvidenceNeed.HADITH_TEXT),
                state=(EvidenceRequirementState.SATISFIED),
                evidence_ids=(node.evidence_id,),
            ),
        ),
    )

    result = GroundedAnswerComposer().compose(
        question="ما نص الحديث؟",
        outcome=_outcome(
            action=(EvidenceDecisionAction.ANSWER),
            bundle=bundle,
        ),
    )

    assert result.has_answer

    assert "نص حديث موثّق للاختبار." in result.answer

    assert len(result.citations) == 1

    citation = result.citations[0]

    assert citation.marker == "[1]"

    assert citation.evidence_id == node.evidence_id

    assert result.used_evidence_ids == (node.evidence_id,)


def test_no_attested_revelation_entry_is_worded_conservatively() -> None:
    quran = EvidenceNode(
        evidence_id="quran:2:255",
        domain=EvidenceDomain.QURAN,
        text="نص الآية للاختبار.",
        source_id=("tanzil-quran-v1.1-uthmani"),
        reference="2:255",
    )

    tafsir = EvidenceNode(
        evidence_id="tafsir:2:255:saadi",
        domain=EvidenceDomain.TAFSIR,
        text="تفسير معتمد للاختبار.",
        source_id="surahapp-tafsir-saadi",
        reference="2:255",
        work_title="تفسير السعدي",
    )

    bundle = _bundle(
        evidence=(quran, tafsir),
        assessments=(
            EvidenceRequirementAssessment(
                need=(EvidenceNeed.CANONICAL_TEXT),
                state=(EvidenceRequirementState.SATISFIED),
                evidence_ids=(quran.evidence_id,),
            ),
            EvidenceRequirementAssessment(
                need=EvidenceNeed.TAFSIR,
                state=(EvidenceRequirementState.SATISFIED),
                evidence_ids=(tafsir.evidence_id,),
            ),
            EvidenceRequirementAssessment(
                need=(EvidenceNeed.REVELATION_CONTEXT),
                state=(EvidenceRequirementState.NO_ATTESTED_ENTRY),
            ),
        ),
    )

    result = GroundedAnswerComposer().compose(
        question=("ما سبب نزول الآية 2:255؟"),
        outcome=_outcome(
            action=(EvidenceDecisionAction.ANSWER_WITH_LIMITATION),
            bundle=bundle,
        ),
    )

    assert result.has_answer

    assert any("لا يوجد مدخل مُثبت" in limitation for limitation in result.limitations)

    assert any("لا يعني" in limitation for limitation in result.limitations)

    assert "لا يوجد سبب نزول لهذه الآية" not in result.answer


def test_source_without_user_facing_permission_is_not_published() -> None:
    node = EvidenceNode(
        evidence_id="quranlab:1",
        domain=EvidenceDomain.HADITH,
        text="نص غير مصرح بعرضه كسلطة.",
        source_id="quranlab-hadith",
    )

    bundle = _bundle(
        evidence=(node,),
        assessments=(
            EvidenceRequirementAssessment(
                need=(EvidenceNeed.HADITH_TEXT),
                state=(EvidenceRequirementState.SATISFIED),
                evidence_ids=(node.evidence_id,),
            ),
        ),
    )

    result = GroundedAnswerComposer().compose(
        question="اختبار",
        outcome=_outcome(
            action=(EvidenceDecisionAction.ANSWER),
            bundle=bundle,
        ),
    )

    assert not result.has_answer
    assert result.citations == ()
    assert result.used_evidence_ids == ()


@pytest.mark.parametrize(
    "action",
    (
        EvidenceDecisionAction.RETRIEVE_MORE,
        EvidenceDecisionAction.ABSTAIN,
    ),
)
def test_non_answer_actions_never_generate_substantive_answer(
    action: EvidenceDecisionAction,
) -> None:
    node = EvidenceNode(
        evidence_id="hadith:1",
        domain=EvidenceDomain.HADITH,
        text="نص موجود.",
        source_id="hadeethenc-official",
    )

    bundle = _bundle(
        evidence=(node,),
        assessments=(),
    )

    result = GroundedAnswerComposer().compose(
        question="اختبار",
        outcome=_outcome(
            action=action,
            bundle=bundle,
        ),
    )

    assert not result.has_answer
    assert result.answer is None
    assert result.citations == ()


def test_expert_escalation_never_generates_autonomous_answer() -> None:
    packet = object()

    bundle = _bundle(
        evidence=(),
        assessments=(),
    )

    result = GroundedAnswerComposer().compose(
        question="سؤال عالي الخطورة",
        outcome=_outcome(
            action=(EvidenceDecisionAction.ESCALATE_TO_EXPERT),
            bundle=bundle,
            expert_review=packet,
        ),
    )

    assert not result.has_answer

    assert result.answer is None

    assert result.expert_review is packet

    assert result.citations == ()
