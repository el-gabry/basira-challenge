from __future__ import annotations

import pytest

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.orchestration.claim_sufficiency import (
    ClaimDependencyResolver,
    ClaimResolutionState,
    ClaimSufficiencyAssessment,
    ClaimSufficiencyContract,
    ClaimSufficiencyEvaluator,
    ClaimSufficiencyReason,
    ClaimSufficiencyState,
    SupportRequirement,
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
)


def node(
    *,
    evidence_id: str,
    domain: EvidenceDomain,
    reference: str = "2:255",
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=domain,
        text=f"text:{evidence_id}",
        source_id=f"source:{evidence_id}",
        reference=reference,
    )


def tafsir_structural(
    *,
    include_tafsir: bool = True,
):
    evidence = [
        node(
            evidence_id="quran",
            domain=EvidenceDomain.QURAN,
        ),
    ]

    if include_tafsir:
        evidence.append(
            node(
                evidence_id="tafsir",
                domain=(EvidenceDomain.TAFSIR),
            )
        )

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
        evidence=tuple(evidence),
    )


def relation_record(
    evidence_id: str,
    relation: ClaimEvidenceRelation,
) -> ClaimEvidenceRelationRecord:
    return ClaimEvidenceRelationRecord(
        task_id="claim:chair",
        evidence_id=evidence_id,
        relation=relation,
        origin=(RelationOrigin.DETERMINISTIC),
    )


def relation_assessment(
    structural,
    *,
    tafsir_relation: (ClaimEvidenceRelation) = ClaimEvidenceRelation.SUPPORTS,
):
    records = [
        relation_record(
            "quran",
            ClaimEvidenceRelation.CONTEXT_ONLY,
        ),
    ]

    if any(node_.evidence_id == "tafsir" for node_ in structural.accepted_evidence):
        records.append(
            relation_record(
                "tafsir",
                tafsir_relation,
            )
        )

    return ClaimEvidenceRelationGate().assess(
        task_id="claim:chair",
        evidence=(structural.accepted_evidence),
        records=tuple(records),
    )


def tafsir_contract() -> ClaimSufficiencyContract:
    return ClaimSufficiencyContract(
        task_id="claim:chair",
        support_requirements=(
            SupportRequirement(
                requirement_id=("tafsir-interpretation"),
                domains=frozenset(
                    {
                        EvidenceDomain.TAFSIR,
                    }
                ),
            ),
        ),
    )


def test_context_domain_is_not_forced_to_be_positive_support() -> None:
    structural = tafsir_structural()

    relations = relation_assessment(structural)

    result = ClaimSufficiencyEvaluator().assess(
        contract=tafsir_contract(),
        structural=structural,
        relations=relations,
    )

    assert result.state is ClaimSufficiencyState.SUFFICIENT

    assert result.satisfied_requirement_ids == ("tafsir-interpretation",)

    assert result.supporting_evidence_ids == ("tafsir",)


@pytest.mark.parametrize(
    "relation",
    (
        ClaimEvidenceRelation.IRRELEVANT,
        ClaimEvidenceRelation.PARTIAL,
        ClaimEvidenceRelation.UNKNOWN,
        ClaimEvidenceRelation.CONTEXT_ONLY,
    ),
)
def test_non_support_relation_never_satisfies_positive_support(
    relation: ClaimEvidenceRelation,
) -> None:
    structural = tafsir_structural()

    relations = relation_assessment(
        structural,
        tafsir_relation=relation,
    )

    result = ClaimSufficiencyEvaluator().assess(
        contract=tafsir_contract(),
        structural=structural,
        relations=relations,
    )

    assert result.state is ClaimSufficiencyState.NEEDS_MORE_EVIDENCE

    assert result.missing_requirement_ids == ("tafsir-interpretation",)

    assert ClaimSufficiencyReason.MISSING_REQUIRED_SUPPORT in result.reasons


def test_structural_failure_remains_insufficient_even_with_support_record() -> None:
    structural = tafsir_structural(include_tafsir=False)

    relations = ClaimEvidenceRelationGate().assess(
        task_id="claim:chair",
        evidence=(structural.accepted_evidence),
        records=(
            relation_record(
                "quran",
                ClaimEvidenceRelation.SUPPORTS,
            ),
        ),
    )

    result = ClaimSufficiencyEvaluator().assess(
        contract=tafsir_contract(),
        structural=structural,
        relations=relations,
    )

    assert result.state is ClaimSufficiencyState.NEEDS_MORE_EVIDENCE

    assert ClaimSufficiencyReason.STRUCTURAL_CONTRACT_UNSATISFIED in result.reasons


def test_contradiction_has_precedence_over_positive_support() -> None:
    structural = tafsir_structural()

    relations = ClaimEvidenceRelationGate().assess(
        task_id="claim:chair",
        evidence=(structural.accepted_evidence),
        records=(
            relation_record(
                "quran",
                ClaimEvidenceRelation.CONTRADICTS,
            ),
            relation_record(
                "tafsir",
                ClaimEvidenceRelation.SUPPORTS,
            ),
        ),
    )

    result = ClaimSufficiencyEvaluator().assess(
        contract=tafsir_contract(),
        structural=structural,
        relations=relations,
    )

    assert result.state is ClaimSufficiencyState.CONFLICT

    assert result.contradicting_evidence_ids == ("quran",)

    assert ClaimSufficiencyReason.EVIDENCE_CONTRADICTION in result.reasons


def test_relation_ledger_must_cover_exact_structurally_accepted_set() -> None:
    structural = tafsir_structural()

    relations = ClaimEvidenceRelationGate().assess(
        task_id="claim:chair",
        evidence=((structural.accepted_evidence[0]),),
        records=(
            relation_record(
                "quran",
                ClaimEvidenceRelation.CONTEXT_ONLY,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="exactly structurally accepted",
    ):
        (
            ClaimSufficiencyEvaluator().assess(
                contract=(tafsir_contract()),
                structural=structural,
                relations=relations,
            )
        )


def assessment(
    *,
    task_id: str,
    state: ClaimSufficiencyState,
) -> ClaimSufficiencyAssessment:
    reasons = (
        (ClaimSufficiencyReason.SUFFICIENT,)
        if state is ClaimSufficiencyState.SUFFICIENT
        else (ClaimSufficiencyReason.MISSING_REQUIRED_SUPPORT,)
        if state is ClaimSufficiencyState.NEEDS_MORE_EVIDENCE
        else (ClaimSufficiencyReason.EVIDENCE_CONTRADICTION,)
    )

    return ClaimSufficiencyAssessment(
        task_id=task_id,
        state=state,
        reasons=reasons,
        satisfied_requirement_ids=(),
        missing_requirement_ids=(),
        supporting_evidence_ids=(),
        contradicting_evidence_ids=(),
        unresolved_evidence_ids=(),
    )


def support_contract(
    *,
    task_id: str,
    dependencies: tuple[str, ...] = (),
) -> ClaimSufficiencyContract:
    return ClaimSufficiencyContract(
        task_id=task_id,
        support_requirements=(
            SupportRequirement(
                requirement_id=(f"{task_id}:support"),
                domains=frozenset(
                    {
                        EvidenceDomain.HADITH,
                    }
                ),
            ),
        ),
        dependency_task_ids=(dependencies),
    )


def test_dependent_claim_waits_for_unresolved_prerequisite() -> None:
    contracts = (
        support_contract(
            task_id=("claim:authenticity"),
        ),
        support_contract(
            task_id="claim:ruling",
            dependencies=("claim:authenticity",),
        ),
    )

    result = ClaimDependencyResolver().resolve(
        contracts=contracts,
        assessments=(
            assessment(
                task_id=("claim:authenticity"),
                state=(ClaimSufficiencyState.NEEDS_MORE_EVIDENCE),
            ),
            assessment(
                task_id="claim:ruling",
                state=(ClaimSufficiencyState.SUFFICIENT),
            ),
        ),
    )

    authenticity = result.for_task("claim:authenticity")

    ruling = result.for_task("claim:ruling")

    assert authenticity.state is ClaimResolutionState.NEEDS_MORE_EVIDENCE

    assert ruling.state is ClaimResolutionState.BLOCKED_BY_DEPENDENCY

    assert ruling.blocking_task_ids == ("claim:authenticity",)


def test_dependent_claim_becomes_ready_only_after_prerequisite_ready() -> None:
    contracts = (
        support_contract(
            task_id=("claim:authenticity"),
        ),
        support_contract(
            task_id="claim:ruling",
            dependencies=("claim:authenticity",),
        ),
    )

    result = ClaimDependencyResolver().resolve(
        contracts=contracts,
        assessments=(
            assessment(
                task_id=("claim:authenticity"),
                state=(ClaimSufficiencyState.SUFFICIENT),
            ),
            assessment(
                task_id="claim:ruling",
                state=(ClaimSufficiencyState.SUFFICIENT),
            ),
        ),
    )

    assert result.for_task("claim:authenticity").state is ClaimResolutionState.READY

    assert result.for_task("claim:ruling").state is ClaimResolutionState.READY


def test_dependency_conflict_blocks_downstream_claim() -> None:
    contracts = (
        support_contract(
            task_id=("claim:authenticity"),
        ),
        support_contract(
            task_id="claim:ruling",
            dependencies=("claim:authenticity",),
        ),
    )

    result = ClaimDependencyResolver().resolve(
        contracts=contracts,
        assessments=(
            assessment(
                task_id=("claim:authenticity"),
                state=(ClaimSufficiencyState.CONFLICT),
            ),
            assessment(
                task_id="claim:ruling",
                state=(ClaimSufficiencyState.SUFFICIENT),
            ),
        ),
    )

    assert result.for_task("claim:authenticity").state is ClaimResolutionState.CONFLICT

    assert (
        result.for_task("claim:ruling").state
        is ClaimResolutionState.BLOCKED_BY_DEPENDENCY
    )


def test_local_insufficiency_is_not_hidden_by_dependency_state() -> None:
    contracts = (
        support_contract(
            task_id="claim:a",
        ),
        support_contract(
            task_id="claim:b",
            dependencies=("claim:a",),
        ),
    )

    result = ClaimDependencyResolver().resolve(
        contracts=contracts,
        assessments=(
            assessment(
                task_id="claim:a",
                state=(ClaimSufficiencyState.NEEDS_MORE_EVIDENCE),
            ),
            assessment(
                task_id="claim:b",
                state=(ClaimSufficiencyState.NEEDS_MORE_EVIDENCE),
            ),
        ),
    )

    assert result.for_task("claim:b").state is ClaimResolutionState.NEEDS_MORE_EVIDENCE


def test_unknown_dependency_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="unknown dependency",
    ):
        (
            ClaimDependencyResolver().resolve(
                contracts=(
                    support_contract(
                        task_id="claim:a",
                        dependencies=("claim:missing",),
                    ),
                ),
                assessments=(
                    assessment(
                        task_id="claim:a",
                        state=(ClaimSufficiencyState.SUFFICIENT),
                    ),
                ),
            )
        )


def test_dependency_cycle_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="cycle",
    ):
        (
            ClaimDependencyResolver().resolve(
                contracts=(
                    support_contract(
                        task_id="claim:a",
                        dependencies=("claim:b",),
                    ),
                    support_contract(
                        task_id="claim:b",
                        dependencies=("claim:a",),
                    ),
                ),
                assessments=(
                    assessment(
                        task_id="claim:a",
                        state=(ClaimSufficiencyState.SUFFICIENT),
                    ),
                    assessment(
                        task_id="claim:b",
                        state=(ClaimSufficiencyState.SUFFICIENT),
                    ),
                ),
            )
        )


def test_exact_one_assessment_per_contract_is_required() -> None:
    with pytest.raises(
        ValueError,
        match="exactly one assessment",
    ):
        (
            ClaimDependencyResolver().resolve(
                contracts=(
                    support_contract(
                        task_id="claim:a",
                    ),
                    support_contract(
                        task_id="claim:b",
                    ),
                ),
                assessments=(
                    assessment(
                        task_id="claim:a",
                        state=(ClaimSufficiencyState.SUFFICIENT),
                    ),
                ),
            )
        )


def test_contract_rejects_self_dependency() -> None:
    with pytest.raises(
        ValueError,
        match="depend on itself",
    ):
        support_contract(
            task_id="claim:a",
            dependencies=("claim:a",),
        )


def test_support_requirement_is_explicit_and_non_empty() -> None:
    with pytest.raises(
        ValueError,
        match="at least one domain",
    ):
        SupportRequirement(
            requirement_id="bad",
            domains=frozenset(),
        )

    with pytest.raises(
        ValueError,
        match="at least one explicit",
    ):
        ClaimSufficiencyContract(
            task_id="claim:bad",
            support_requirements=(),
        )


def test_resolution_is_not_final_answer_permission() -> None:
    result = ClaimDependencyResolver().resolve(
        contracts=(
            support_contract(
                task_id="claim:a",
            ),
        ),
        assessments=(
            assessment(
                task_id="claim:a",
                state=(ClaimSufficiencyState.SUFFICIENT),
            ),
        ),
    )

    resolution = result.for_task("claim:a")

    assert resolution.state is ClaimResolutionState.READY

    for forbidden in (
        "answerable",
        "publish",
        "final_answer",
        "truth",
    ):
        assert not hasattr(
            resolution,
            forbidden,
        )
