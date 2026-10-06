from basira.api.governed_runtime import (
    _project_public_hadith_admissibility,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.orchestration.contracts import (
    ClaimTask,
    ContextRequirement,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
    ClaimEvidenceRelationRecord,
    RelationOrigin,
    TaskEvidenceRelationAssessment,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)


def _task(
    *,
    require_grade: bool = False,
) -> ClaimTask:
    required = {
        EvidenceNeed.HADITH_TEXT,
        EvidenceNeed.SOURCE_PROVENANCE,
    }

    if require_grade:
        required.add(
            EvidenceNeed.HADITH_GRADE
        )

    return ClaimTask(
        task_id="claim:hadith",
        claim_text="ما فضل الصلاة في السنة؟",
        frame=ReligiousReasoningFrame(
            frame_id="frame:hadith",
            question="ما فضل الصلاة في السنة؟",
            primary_discipline=(
                ReligiousDiscipline.HADITH
            ),
            reasoning_mode=(
                ReasoningMode.DIRECT_GROUNDING
            ),
        ),
        context_requirement=ContextRequirement(
            required=frozenset(required),
        ),
    )


def _evidence(
    grade: str | None,
) -> tuple[EvidenceNode, ...]:
    text_id = "hadith:1:text"

    nodes = [
        EvidenceNode(
            evidence_id=text_id,
            domain=EvidenceDomain.HADITH,
            text="فضل الصلاة ...",
            source_id="dorar-hadith-live-v1",
            reference="ref-1",
            claim_type="hadith_text",
        )
    ]

    if grade is not None:
        nodes.append(
            EvidenceNode(
                evidence_id="hadith:1:grade",
                domain=EvidenceDomain.HADITH,
                text=grade,
                source_id=(
                    "dorar-hadith-live-v1"
                ),
                reference="ref-1",
                claim_type="hadith_grade",
                topic=grade,
                related_hadith=(text_id,),
            )
        )

    return tuple(nodes)


def _assessment(
    evidence: tuple[EvidenceNode, ...],
) -> TaskEvidenceRelationAssessment:
    return TaskEvidenceRelationAssessment(
        task_id="claim:hadith",
        records=tuple(
            ClaimEvidenceRelationRecord(
                task_id="claim:hadith",
                evidence_id=node.evidence_id,
                relation=(
                    ClaimEvidenceRelation.SUPPORTS
                ),
                origin=(
                    RelationOrigin.DETERMINISTIC
                ),
            )
            for node in evidence
        ),
    )


def _relation_map(
    result: TaskEvidenceRelationAssessment,
) -> dict[str, ClaimEvidenceRelation]:
    return {
        record.evidence_id: record.relation
        for record in result.records
    }


def test_sahih_text_may_remain_positive_support():
    evidence = _evidence("sahih")

    result = _project_public_hadith_admissibility(
        task=_task(),
        evidence=evidence,
        assessment=_assessment(evidence),
    )

    relations = _relation_map(result)

    assert (
        relations["hadith:1:text"]
        is ClaimEvidenceRelation.SUPPORTS
    )

    assert (
        relations["hadith:1:grade"]
        is ClaimEvidenceRelation.CONTEXT_ONLY
    )


def test_mawdu_text_cannot_positive_support():
    evidence = _evidence("mawdu")

    result = _project_public_hadith_admissibility(
        task=_task(),
        evidence=evidence,
        assessment=_assessment(evidence),
    )

    relations = _relation_map(result)

    assert (
        relations["hadith:1:text"]
        is ClaimEvidenceRelation.IRRELEVANT
    )

    assert (
        relations["hadith:1:grade"]
        is ClaimEvidenceRelation.CONTEXT_ONLY
    )


def test_ungraded_text_fails_conservative():
    evidence = _evidence(None)

    result = _project_public_hadith_admissibility(
        task=_task(),
        evidence=evidence,
        assessment=_assessment(evidence),
    )

    assert (
        _relation_map(result)["hadith:1:text"]
        is ClaimEvidenceRelation.IRRELEVANT
    )


def test_conflicting_positive_and_negative_grades_do_not_silently_pass():
    text_node = _evidence(None)[0]

    evidence = (
        text_node,
        EvidenceNode(
            evidence_id="hadith:1:sahih",
            domain=EvidenceDomain.HADITH,
            text="صحيح",
            source_id="dorar-hadith-live-v1",
            claim_type="hadith_grade",
            topic="sahih",
            related_hadith=(
                text_node.evidence_id,
            ),
        ),
        EvidenceNode(
            evidence_id="hadith:1:daif",
            domain=EvidenceDomain.HADITH,
            text="ضعيف",
            source_id="dorar-hadith-live-v1",
            claim_type="hadith_grade",
            topic="daif",
            related_hadith=(
                text_node.evidence_id,
            ),
        ),
    )

    result = _project_public_hadith_admissibility(
        task=_task(),
        evidence=evidence,
        assessment=_assessment(evidence),
    )

    assert (
        _relation_map(result)[
            text_node.evidence_id
        ]
        is ClaimEvidenceRelation.CONTRADICTS
    )


def test_authenticity_claim_keeps_existing_grade_pipeline():
    evidence = _evidence("mawdu")
    original = _assessment(evidence)

    result = _project_public_hadith_admissibility(
        task=_task(
            require_grade=True,
        ),
        evidence=evidence,
        assessment=original,
    )

    assert result is original
