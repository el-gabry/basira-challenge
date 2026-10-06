from __future__ import annotations

import pytest

from basira.answer.models import (
    StructuredClaim,
)
from basira.answer.semantic_verification import (
    GeneratedClaimEvidenceRecord,
    GeneratedClaimSemanticVerifier,
    GeneratedClaimVerificationAction,
)
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
    AnchorOrigin,
    AnchorStrength,
    EvidenceAcceptanceReason,
    EvidenceAnchor,
    RetrievalShape,
    SourceDiversityRequirement,
    TaskEvidenceAcceptanceContract,
    TaskEvidenceAcceptanceGate,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
    ClaimEvidenceRelationGate,
    ClaimEvidenceRelationRecord,
    RelationOrigin,
)


def evidence(
    *,
    evidence_id: str,
    domain: EvidenceDomain,
    reference: str | None = None,
    source_id: str | None = None,
    text: str | None = None,
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=domain,
        text=(text or f"source text: {evidence_id}"),
        source_id=(source_id or f"source:{evidence_id}"),
        reference=reference,
    )


def relation(
    *,
    task_id: str,
    evidence_id: str,
    relation: ClaimEvidenceRelation,
) -> ClaimEvidenceRelationRecord:
    return ClaimEvidenceRelationRecord(
        task_id=task_id,
        evidence_id=evidence_id,
        relation=relation,
        origin=(RelationOrigin.DETERMINISTIC),
    )


def sufficiency_assessment(
    *,
    task_id: str,
    state: ClaimSufficiencyState,
) -> ClaimSufficiencyAssessment:
    if state is ClaimSufficiencyState.SUFFICIENT:
        reasons = (ClaimSufficiencyReason.SUFFICIENT,)
    elif state is ClaimSufficiencyState.CONFLICT:
        reasons = (ClaimSufficiencyReason.EVIDENCE_CONTRADICTION,)
    else:
        reasons = (ClaimSufficiencyReason.MISSING_REQUIRED_SUPPORT,)

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


def simple_support_contract(
    *,
    task_id: str,
    domain: EvidenceDomain,
    dependencies: tuple[str, ...] = (),
) -> ClaimSufficiencyContract:
    return ClaimSufficiencyContract(
        task_id=task_id,
        support_requirements=(
            SupportRequirement(
                requirement_id=(f"{task_id}:support"),
                domains=frozenset(
                    {
                        domain,
                    }
                ),
            ),
        ),
        dependency_task_ids=dependencies,
    )


class SemanticMapEvaluator:
    def __init__(
        self,
        mapping: dict[
            tuple[str, str],
            ClaimEvidenceRelation,
        ],
    ) -> None:
        self.mapping = mapping
        self.calls: list[tuple[str, str]] = []

    def evaluate(
        self,
        *,
        claim: StructuredClaim,
        evidence: EvidenceNode,
    ) -> GeneratedClaimEvidenceRecord:
        key = (
            claim.claim_id,
            evidence.evidence_id,
        )

        self.calls.append(key)

        return GeneratedClaimEvidenceRecord(
            claim_id=claim.claim_id,
            evidence_id=evidence.evidence_id,
            relation=self.mapping[key],
            origin=RelationOrigin.MODEL,
            confidence=0.9,
        )


def test_scenario_quran_tafsir_wrong_anchor_is_rejected_before_semantics() -> None:
    task_id = "claim:chair"

    anchor = EvidenceAnchor(
        reference="2:255",
        domains=frozenset(
            {
                EvidenceDomain.QURAN,
                EvidenceDomain.TAFSIR,
            }
        ),
        kind=AnchorKind.QURAN_AYAH,
        origin=(AnchorOrigin.CANONICAL_TEXT_MATCH),
        strength=AnchorStrength.HARD,
    )

    contract = TaskEvidenceAcceptanceContract(
        task_id=task_id,
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
        anchors=(anchor,),
    )

    structural = TaskEvidenceAcceptanceGate().evaluate(
        contract=contract,
        evidence=(
            evidence(
                evidence_id="quran:2:255",
                domain=EvidenceDomain.QURAN,
                reference="2:255",
            ),
            evidence(
                evidence_id="tafsir:right",
                domain=EvidenceDomain.TAFSIR,
                reference="2:255",
            ),
            evidence(
                evidence_id="tafsir:wrong",
                domain=EvidenceDomain.TAFSIR,
                reference="2:43",
            ),
        ),
    )

    assert {node.evidence_id for node in structural.accepted_evidence} == {
        "quran:2:255",
        "tafsir:right",
    }

    rejected = {
        record.evidence_id: record.reason
        for record in structural.records
        if not record.accepted
    }

    assert rejected["tafsir:wrong"] is EvidenceAcceptanceReason.HARD_ANCHOR_MISMATCH


def test_scenario_correct_anchor_but_irrelevant_tafsir_is_not_sufficient() -> None:
    task_id = "claim:chair"

    contract = TaskEvidenceAcceptanceContract(
        task_id=task_id,
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

    structural = TaskEvidenceAcceptanceGate().evaluate(
        contract=contract,
        evidence=(
            evidence(
                evidence_id="quran",
                domain=EvidenceDomain.QURAN,
                reference="2:255",
            ),
            evidence(
                evidence_id="tafsir",
                domain=EvidenceDomain.TAFSIR,
                reference="2:255",
            ),
        ),
    )

    relations = ClaimEvidenceRelationGate().assess(
        task_id=task_id,
        evidence=(structural.accepted_evidence),
        records=(
            relation(
                task_id=task_id,
                evidence_id="quran",
                relation=(ClaimEvidenceRelation.CONTEXT_ONLY),
            ),
            relation(
                task_id=task_id,
                evidence_id="tafsir",
                relation=(ClaimEvidenceRelation.IRRELEVANT),
            ),
        ),
    )

    sufficiency = ClaimSufficiencyEvaluator().assess(
        contract=(
            ClaimSufficiencyContract(
                task_id=task_id,
                support_requirements=(
                    SupportRequirement(
                        requirement_id=("meaning-of-chair"),
                        domains=frozenset(
                            {
                                EvidenceDomain.TAFSIR,
                            }
                        ),
                    ),
                ),
            )
        ),
        structural=structural,
        relations=relations,
    )

    assert sufficiency.state is ClaimSufficiencyState.NEEDS_MORE_EVIDENCE

    assert sufficiency.missing_requirement_ids == ("meaning-of-chair",)


def test_scenario_quran_context_plus_tafsir_support_is_sufficient() -> None:
    task_id = "claim:chair"

    structural = TaskEvidenceAcceptanceGate().evaluate(
        contract=(
            TaskEvidenceAcceptanceContract(
                task_id=task_id,
                retrieval_shape=(RetrievalShape.HYBRID),
                allowed_domains=(
                    frozenset(
                        {
                            EvidenceDomain.QURAN,
                            EvidenceDomain.TAFSIR,
                        }
                    )
                ),
                required_domains=(
                    frozenset(
                        {
                            EvidenceDomain.QURAN,
                            EvidenceDomain.TAFSIR,
                        }
                    )
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
        ),
        evidence=(
            evidence(
                evidence_id="quran",
                domain=EvidenceDomain.QURAN,
                reference="2:255",
            ),
            evidence(
                evidence_id="tafsir",
                domain=EvidenceDomain.TAFSIR,
                reference="2:255",
            ),
        ),
    )

    relations = ClaimEvidenceRelationGate().assess(
        task_id=task_id,
        evidence=(structural.accepted_evidence),
        records=(
            relation(
                task_id=task_id,
                evidence_id="quran",
                relation=(ClaimEvidenceRelation.CONTEXT_ONLY),
            ),
            relation(
                task_id=task_id,
                evidence_id="tafsir",
                relation=(ClaimEvidenceRelation.SUPPORTS),
            ),
        ),
    )

    result = ClaimSufficiencyEvaluator().assess(
        contract=(
            ClaimSufficiencyContract(
                task_id=task_id,
                support_requirements=(
                    SupportRequirement(
                        requirement_id=("tafsir-support"),
                        domains=frozenset(
                            {
                                EvidenceDomain.TAFSIR,
                            }
                        ),
                    ),
                ),
            )
        ),
        structural=structural,
        relations=relations,
    )

    assert result.sufficient
    assert result.supporting_evidence_ids == ("tafsir",)


def test_scenario_hadith_authenticity_conflict_blocks_fiqh_dependency() -> None:
    contracts = (
        simple_support_contract(
            task_id="claim:authenticity",
            domain=EvidenceDomain.HADITH,
        ),
        simple_support_contract(
            task_id="claim:ruling",
            domain=EvidenceDomain.FIQH,
            dependencies=("claim:authenticity",),
        ),
    )

    resolutions = ClaimDependencyResolver().resolve(
        contracts=contracts,
        assessments=(
            sufficiency_assessment(
                task_id=("claim:authenticity"),
                state=(ClaimSufficiencyState.CONFLICT),
            ),
            sufficiency_assessment(
                task_id="claim:ruling",
                state=(ClaimSufficiencyState.SUFFICIENT),
            ),
        ),
    )

    assert (
        resolutions.for_task("claim:authenticity").state
        is ClaimResolutionState.CONFLICT
    )

    ruling = resolutions.for_task("claim:ruling")

    assert ruling.state is ClaimResolutionState.BLOCKED_BY_DEPENDENCY

    assert ruling.blocking_task_ids == ("claim:authenticity",)


def test_unresolved_hadith_blocks_ruling_with_fiqh_support() -> None:
    contracts = (
        simple_support_contract(
            task_id="claim:authenticity",
            domain=EvidenceDomain.HADITH,
        ),
        simple_support_contract(
            task_id="claim:ruling",
            domain=EvidenceDomain.FIQH,
            dependencies=("claim:authenticity",),
        ),
    )

    resolutions = ClaimDependencyResolver().resolve(
        contracts=contracts,
        assessments=(
            sufficiency_assessment(
                task_id=("claim:authenticity"),
                state=(ClaimSufficiencyState.NEEDS_MORE_EVIDENCE),
            ),
            sufficiency_assessment(
                task_id="claim:ruling",
                state=(ClaimSufficiencyState.SUFFICIENT),
            ),
        ),
    )

    assert (
        resolutions.for_task("claim:ruling").state
        is ClaimResolutionState.BLOCKED_BY_DEPENDENCY
    )


def test_duplicate_tafsir_source_fails_diversity() -> None:
    task_id = "claim:compare-tafsir"

    structural = TaskEvidenceAcceptanceGate().evaluate(
        contract=(
            TaskEvidenceAcceptanceContract(
                task_id=task_id,
                retrieval_shape=(RetrievalShape.EXACT_ANCHOR),
                allowed_domains=frozenset(
                    {
                        EvidenceDomain.TAFSIR,
                    }
                ),
                required_domains=frozenset(
                    {
                        EvidenceDomain.TAFSIR,
                    }
                ),
                anchors=(
                    EvidenceAnchor(
                        reference="2:255",
                        domains=frozenset(
                            {
                                EvidenceDomain.TAFSIR,
                            }
                        ),
                        kind=(AnchorKind.QURAN_AYAH),
                    ),
                ),
                source_diversity=(
                    SourceDiversityRequirement(
                        domain=(EvidenceDomain.TAFSIR),
                        min_distinct_sources=2,
                    ),
                ),
            )
        ),
        evidence=(
            evidence(
                evidence_id="tafsir:a",
                domain=EvidenceDomain.TAFSIR,
                reference="2:255",
                source_id="same-source",
            ),
            evidence(
                evidence_id="tafsir:b",
                domain=EvidenceDomain.TAFSIR,
                reference="2:255",
                source_id="same-source",
            ),
        ),
    )

    assert not (structural.structural_contract_satisfied)

    assert structural.missing_source_diversity == ("tafsir:1/2",)


def test_scenario_planner_inference_cannot_be_promoted_to_hard_anchor() -> None:
    with pytest.raises(
        ValueError,
        match="planner inference",
    ):
        EvidenceAnchor(
            reference="2:255",
            domains=frozenset(
                {
                    EvidenceDomain.TAFSIR,
                }
            ),
            kind=AnchorKind.QURAN_AYAH,
            origin=(AnchorOrigin.PLANNER_INFERENCE),
            strength=AnchorStrength.HARD,
        )


def test_scenario_generated_overclaim_requests_regeneration() -> None:
    generated = StructuredClaim(
        axis_id="tafsir",
        claim_id="claim:generated",
        text=("الكرسي يعني قطعًا معنى واحدًا لا خلاف فيه."),
        evidence_ids=("tafsir:1",),
    )

    evaluator = SemanticMapEvaluator(
        {
            (
                "claim:generated",
                "tafsir:1",
            ): (ClaimEvidenceRelation.PARTIAL),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(generated,),
        evidence=(
            evidence(
                evidence_id="tafsir:1",
                domain=EvidenceDomain.TAFSIR,
                reference="2:255",
            ),
        ),
    )

    assert result.action is GeneratedClaimVerificationAction.REGENERATE


def test_scenario_generated_claim_cited_contradiction_blocks_publication() -> None:
    generated = StructuredClaim(
        axis_id="hadith",
        claim_id="claim:generated",
        text="الحديث ثابت بلا خلاف.",
        evidence_ids=(
            "hadith:support",
            "hadith:contradiction",
        ),
    )

    evaluator = SemanticMapEvaluator(
        {
            (
                "claim:generated",
                "hadith:support",
            ): (ClaimEvidenceRelation.SUPPORTS),
            (
                "claim:generated",
                "hadith:contradiction",
            ): (ClaimEvidenceRelation.CONTRADICTS),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(generated,),
        evidence=(
            evidence(
                evidence_id=("hadith:support"),
                domain=EvidenceDomain.HADITH,
            ),
            evidence(
                evidence_id=("hadith:contradiction"),
                domain=EvidenceDomain.HADITH,
            ),
        ),
    )

    assert result.action is GeneratedClaimVerificationAction.BLOCK


def test_scenario_generated_claim_may_not_borrow_uncited_support() -> None:
    generated = StructuredClaim(
        axis_id="tafsir",
        claim_id="claim:generated",
        text="generated claim",
        evidence_ids=("cited:weak",),
    )

    evaluator = SemanticMapEvaluator(
        {
            (
                "claim:generated",
                "cited:weak",
            ): (ClaimEvidenceRelation.UNKNOWN),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(generated,),
        evidence=(
            evidence(
                evidence_id="cited:weak",
                domain=EvidenceDomain.TAFSIR,
            ),
            evidence(
                evidence_id="uncited:strong",
                domain=EvidenceDomain.TAFSIR,
            ),
        ),
    )

    assert result.action is GeneratedClaimVerificationAction.REGENERATE

    assert evaluator.calls == [
        (
            "claim:generated",
            "cited:weak",
        )
    ]


def test_scenario_domain_taxonomy_does_not_collapse_specialties_to_general() -> None:
    required_names = (
        "AQIDAH",
        "HISTORY",
        "LANGUAGE",
    )

    for name in required_names:
        domain = getattr(
            EvidenceDomain,
            name,
            None,
        )

        assert domain is not None, f"EvidenceDomain.{name} missing"

        assert domain is not EvidenceDomain.GENERAL

    sirah = getattr(
        EvidenceDomain,
        "SIRAH",
        None,
    )

    if sirah is None:
        sirah = getattr(
            EvidenceDomain,
            "SIRA",
            None,
        )

    assert sirah is not None
    assert sirah is not EvidenceDomain.GENERAL


def test_scenario_matrix_preserves_layer_boundaries() -> None:
    """
    Architectural guardrail:
    no single result object is allowed to impersonate
    the next layer's responsibility.
    """

    assert not hasattr(
        TaskEvidenceAcceptanceGate(),
        "semantic_score",
    )

    assert not hasattr(
        ClaimEvidenceRelationGate(),
        "final_answer",
    )

    assert not hasattr(
        ClaimSufficiencyEvaluator(),
        "publish",
    )

    assert not hasattr(
        ClaimDependencyResolver(),
        "source_authority",
    )

    assert not hasattr(
        GeneratedClaimSemanticVerifier(),
        "religious_ruling",
    )
