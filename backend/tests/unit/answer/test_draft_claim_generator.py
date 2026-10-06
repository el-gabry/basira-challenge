from __future__ import annotations

from basira.answer.composer import (
    GroundedAnswerComposer,
)
from basira.answer.draft_claims import (
    DeterministicDraftClaimGenerator,
    DraftClaimGenerator,
)
from basira.answer.final_output import (
    FinalOutputDraft,
)
from basira.answer.models import (
    StructuredClaim,
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


def node() -> EvidenceNode:
    return EvidenceNode(
        evidence_id="tafsir-1",
        domain=EvidenceDomain.TAFSIR,
        text="نص المصدر.",
        source_id="surahapp-tafsir-saadi",
        reference="2:153",
    )


def outcome(
    evidence: EvidenceNode,
) -> EvidenceDecisionOutcome:
    return EvidenceDecisionOutcome(
        bundle=EvidenceBundle(
            evidence=(evidence,),
            required_assessments=(
                EvidenceRequirementAssessment(
                    need=EvidenceNeed.TAFSIR,
                    state=(EvidenceRequirementState.SATISFIED),
                    evidence_ids=(evidence.evidence_id,),
                ),
            ),
        ),
        decision=EvidenceDecision(
            action=EvidenceDecisionAction.ANSWER,
            reasons=(EvidenceDecisionReason.COMPLETE_EVIDENCE,),
        ),
        expert_review=None,
    )


class FakeDraftClaimGenerator:
    def generate(
        self,
        *,
        question: str,
        primary_need: EvidenceNeed | None,
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> FinalOutputDraft:
        del question
        del primary_need

        return FinalOutputDraft(
            claims=(
                StructuredClaim(
                    axis_id="tafsir",
                    claim_id="injected-claim",
                    text=evidence[0].text,
                    evidence_ids=(evidence[0].evidence_id,),
                ),
            )
        )


def accepts_generator(
    generator: DraftClaimGenerator,
) -> DraftClaimGenerator:
    return generator


def test_generator_contract_returns_claim_draft_not_free_text():
    generator = accepts_generator(FakeDraftClaimGenerator())

    evidence = node()

    draft = generator.generate(
        question="ما معنى الآية؟",
        primary_need=EvidenceNeed.TAFSIR,
        evidence=(evidence,),
    )

    assert isinstance(
        draft,
        FinalOutputDraft,
    )

    assert draft.claims[0].claim_id == "injected-claim"

    assert draft.claims[0].evidence_ids == ("tafsir-1",)


def test_deterministic_adapter_delegates_to_existing_builder():
    evidence = node()

    calls: list[
        tuple[
            EvidenceNeed | None,
            tuple[EvidenceNode, ...],
        ]
    ] = []

    def builder(
        *,
        primary_need: EvidenceNeed | None,
        nodes: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> tuple[
        StructuredClaim,
        ...,
    ]:
        calls.append(
            (
                primary_need,
                nodes,
            )
        )

        return (
            StructuredClaim(
                axis_id="tafsir",
                claim_id="claim-1",
                text=nodes[0].text,
                evidence_ids=(nodes[0].evidence_id,),
            ),
        )

    generator = DeterministicDraftClaimGenerator(
        builder=builder,
    )

    draft = generator.generate(
        question="ignored by deterministic path",
        primary_need=EvidenceNeed.TAFSIR,
        evidence=(evidence,),
    )

    assert calls == [
        (
            EvidenceNeed.TAFSIR,
            (evidence,),
        )
    ]

    assert draft.claims[0].text == evidence.text


def test_composer_uses_injected_draft_claim_generator():
    evidence = node()

    composer = GroundedAnswerComposer(draft_claim_generator=(FakeDraftClaimGenerator()))

    answer = composer.compose(
        question="ما معنى الآية؟",
        outcome=outcome(evidence),
    )

    assert answer.has_answer

    assert len(answer.claims) == 1

    assert answer.claims[0].claim_id == "injected-claim"

    assert "[1] نص المصدر." in (answer.answer or "")
