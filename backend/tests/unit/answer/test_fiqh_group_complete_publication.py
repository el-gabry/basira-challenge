from basira.answer.composer import (
    GroundedAnswerComposer,
)
from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceConflict,
    EvidenceConflictType,
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


class _PublishAllComposer(
    GroundedAnswerComposer,
):
    @staticmethod
    def _may_publish(
        node: EvidenceNode,
    ) -> bool:
        return True


def _node(
    *,
    evidence_id: str,
    claim_type: str,
    text: str,
    madhhab: str,
    related_fiqh=(),
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=EvidenceDomain.FIQH,
        text=text,
        source_id="test-fiqh-source",
        claim_type=claim_type,
        authority_scope=madhhab,
        related_fiqh=tuple(
            related_fiqh
        ),
    )


def _position_group(
    prefix: str,
    madhhab: str,
) -> tuple[
    EvidenceNode,
    ...,
]:
    position_id = (
        f"{prefix}:position"
    )

    return (
        _node(
            evidence_id=position_id,
            claim_type=(
                "fiqh_position"
            ),
            text=(
                f"النص الفقهي {madhhab}"
            ),
            madhhab=madhhab,
        ),
        _node(
            evidence_id=(
                f"{prefix}:ruling"
            ),
            claim_type=(
                "fiqh_ruling"
            ),
            text=(
                f"الحكم {madhhab}"
            ),
            madhhab=madhhab,
            related_fiqh=(
                position_id,
            ),
        ),
        _node(
            evidence_id=(
                f"{prefix}:dalil"
            ),
            claim_type=(
                "fiqh_dalil"
            ),
            text=(
                f"الدليل {madhhab}"
            ),
            madhhab=madhhab,
            related_fiqh=(
                position_id,
            ),
        ),
        _node(
            evidence_id=(
                f"{prefix}:wajh"
            ),
            claim_type=(
                "fiqh_wajh_al_dalala"
            ),
            text=(
                f"وجه الدلالة {madhhab}"
            ),
            madhhab=madhhab,
            related_fiqh=(
                position_id,
            ),
        ),
        _node(
            evidence_id=(
                f"{prefix}:condition:1"
            ),
            claim_type=(
                "fiqh_condition"
            ),
            text=(
                f"الشرط {madhhab}"
            ),
            madhhab=madhhab,
            related_fiqh=(
                position_id,
            ),
        ),
        _node(
            evidence_id=(
                f"{prefix}:exception:1"
            ),
            claim_type=(
                "fiqh_exception"
            ),
            text=(
                f"الاستثناء {madhhab}"
            ),
            madhhab=madhhab,
            related_fiqh=(
                position_id,
            ),
        ),
        _node(
            evidence_id=(
                f"{prefix}:disagreement"
            ),
            claim_type=(
                "fiqh_disagreement"
            ),
            text=(
                f"الخلاف {madhhab}"
            ),
            madhhab=madhhab,
            related_fiqh=(
                position_id,
            ),
        ),
    )


def _outcome() -> EvidenceDecisionOutcome:
    groups = (
        _position_group(
            "hanafi",
            "hanafi",
        )
        + _position_group(
            "maliki",
            "maliki",
        )
        + _position_group(
            "shafii",
            "shafii",
        )
        + _position_group(
            "hanbali",
            "hanbali",
        )
    )

    primary_ids = tuple(
        node.evidence_id
        for node in groups
        if node.claim_type
        in {
            "fiqh_position",
            "fiqh_ruling",
        }
    )

    bundle = EvidenceBundle(
        evidence=groups,
        required_assessments=(
            EvidenceRequirementAssessment(
                need=(
                    EvidenceNeed
                    .FIQH_EVIDENCE
                ),
                state=(
                    EvidenceRequirementState
                    .SATISFIED
                ),
                evidence_ids=(
                    primary_ids
                ),
            ),
        ),
        conflicts=(
            EvidenceConflict(
                conflict_type=(
                    EvidenceConflictType
                    .FIQH_POSITION
                ),
                group_id=(
                    "fiqh:test-issue"
                ),
                evidence_ids=(
                    "hanafi:ruling",
                    "maliki:ruling",
                    "shafii:ruling",
                    "hanbali:ruling",
                ),
            ),
        ),
    )

    return EvidenceDecisionOutcome(
        bundle=bundle,
        decision=EvidenceDecision(
            action=(
                EvidenceDecisionAction
                .ANSWER_WITH_LIMITATION
            ),
            reasons=(
                EvidenceDecisionReason
                .COMPLETE_EVIDENCE,
                EvidenceDecisionReason
                .EVIDENCE_CONFLICT,
            ),
        ),
        expert_review=None,
    )


def test_fiqh_publication_is_not_cut_by_generic_node_limit():
    answer = _PublishAllComposer(
        max_evidence_nodes=1,
    ).compose(
        question=(
            "ما أقوال المذاهب؟"
        ),
        outcome=_outcome(),
    )

    # 4 positions × 7 structural nodes.
    assert len(
        answer.used_evidence_ids
    ) == 28


def test_fiqh_publication_preserves_all_four_madhhabs():
    answer = _PublishAllComposer(
        max_evidence_nodes=1,
    ).compose(
        question=(
            "ما أقوال المذاهب؟"
        ),
        outcome=_outcome(),
    )

    assert answer.answer is not None

    for label in (
        "المذهب الحنفي",
        "المذهب المالكي",
        "المذهب الشافعي",
        "المذهب الحنبلي",
    ):
        assert label in answer.answer


def test_fiqh_publication_preserves_full_structural_roles():
    answer = _PublishAllComposer(
        max_evidence_nodes=1,
    ).compose(
        question=(
            "ما أقوال المذاهب؟"
        ),
        outcome=_outcome(),
    )

    assert answer.answer is not None

    for label in (
        "الحكم:",
        "الدليل:",
        "وجه الدلالة:",
        "الشرط:",
        "الاستثناء:",
        "بيان الخلاف:",
    ):
        assert label in answer.answer


def test_fiqh_disagreement_publication_states_no_automated_tarjih():
    answer = _PublishAllComposer(
        max_evidence_nodes=1,
    ).compose(
        question=(
            "ما أقوال المذاهب؟"
        ),
        outcome=_outcome(),
    )

    limitation_text = " ".join(
        answer.limitations
    )

    assert (
        "من دون ترجيح آلي"
        in limitation_text
    )

    assert (
        "تصويت بالأغلبية"
        in limitation_text
    )


def test_fiqh_group_selector_preserves_parent_child_relationship():
    outcome = _outcome()

    composer = (
        _PublishAllComposer(
            max_evidence_nodes=1,
        )
    )

    assessment = (
        outcome.bundle
        .assessment_for(
            EvidenceNeed
            .FIQH_EVIDENCE
        )
    )

    assert assessment is not None

    nodes = (
        composer
        ._fiqh_publication_nodes(
            bundle=outcome.bundle,
            primary_assessment=(
                assessment
            ),
        )
    )

    ids = {
        node.evidence_id
        for node in nodes
    }

    assert (
        "shafii:position"
        in ids
    )

    assert (
        "shafii:ruling"
        in ids
    )

    assert (
        "shafii:dalil"
        in ids
    )

    assert (
        "shafii:wajh"
        in ids
    )

    assert (
        "shafii:condition:1"
        in ids
    )

    assert (
        "shafii:exception:1"
        in ids
    )

    assert (
        "shafii:disagreement"
        in ids
    )
