from __future__ import annotations

import pytest

from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.evidence.requirements import (
    evidence_domain_for_need,
)
from basira.orchestration.contracts import (
    ClaimTask,
)
from basira.orchestration.evidence_acceptance import (
    AnchorKind,
    AnchorOrigin,
    EvidenceAcceptanceReason,
    RetrievalShape,
    TaskEvidenceAcceptanceGate,
)
from basira.orchestration.evidence_contract_compiler import (
    TaskEvidenceContractCompiler,
    UnresolvedEvidenceIdentityError,
)
from basira.orchestration.quran_anchor_resolution import (
    AnchorResolutionDisposition,
    QuranAnchorResolution,
    VerifiedCanonicalAnchor,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)
from basira.reasoning.routing import (
    evidence_domains_for_discipline,
    evidence_domains_for_frame,
)


def quran_interpretation_task() -> ClaimTask:
    text = "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟"

    return ClaimTask(
        task_id="claim:chair",
        claim_text=text,
        frame=(
            ReligiousReasoningFrame(
                frame_id="frame:chair",
                question=text,
                primary_discipline=(ReligiousDiscipline.QURAN),
                secondary_disciplines=(ReligiousDiscipline.TAFSIR,),
                reasoning_mode=(ReasoningMode.INTERPRETATION),
            )
        ),
        context_requirement=(
            ContextRequirement(
                required=frozenset(
                    {
                        EvidenceNeed.CANONICAL_TEXT,
                        EvidenceNeed.TAFSIR,
                        EvidenceNeed.SOURCE_PROVENANCE,
                    }
                )
            )
        ),
    )


def resolved_2_255() -> QuranAnchorResolution:
    return QuranAnchorResolution(
        disposition=(AnchorResolutionDisposition.RESOLVED),
        anchors=(
            VerifiedCanonicalAnchor(
                reference="2:255",
                kind=(AnchorKind.QURAN_AYAH),
                origin=(AnchorOrigin.CANONICAL_TEXT_MATCH),
                matched_text=("وسع كرسيه السماوات والارض"),
            ),
        ),
        reason=("unique_canonical_quran_text_match"),
    )


def no_quran_anchor() -> QuranAnchorResolution:
    return QuranAnchorResolution(
        disposition=(AnchorResolutionDisposition.NO_ANCHOR),
        reason=("no_verified_quran_anchor"),
    )


def test_need_domain_mapping_is_shared_contract():
    assert evidence_domain_for_need(EvidenceNeed.CANONICAL_TEXT) is EvidenceDomain.QURAN

    assert evidence_domain_for_need(EvidenceNeed.HADITH_GRADE) is EvidenceDomain.HADITH

    assert (
        evidence_domain_for_need(EvidenceNeed.RELATED_HADITH) is EvidenceDomain.HADITH
    )

    assert evidence_domain_for_need(EvidenceNeed.SOURCE_PROVENANCE) is None


def test_public_frame_domain_projection():
    task = quran_interpretation_task()

    assert evidence_domains_for_discipline(ReligiousDiscipline.QURAN) == (
        EvidenceDomain.QURAN,
    )

    assert evidence_domains_for_frame(task.frame) == (
        EvidenceDomain.QURAN,
        EvidenceDomain.TAFSIR,
    )


def test_interpretation_with_verified_anchor_is_hybrid():
    contract = TaskEvidenceContractCompiler().compile(
        task=(quran_interpretation_task()),
        quran_resolution=(resolved_2_255()),
    )

    assert contract.retrieval_shape is RetrievalShape.HYBRID

    assert contract.allowed_domains == frozenset(
        {
            EvidenceDomain.QURAN,
            EvidenceDomain.TAFSIR,
        }
    )

    assert contract.required_domains == frozenset(
        {
            EvidenceDomain.QURAN,
            EvidenceDomain.TAFSIR,
        }
    )

    assert len(contract.anchors) == 1

    anchor = contract.anchors[0]

    assert anchor.reference == "2:255"

    assert anchor.domains == (
        frozenset(
            {
                EvidenceDomain.QURAN,
                EvidenceDomain.TAFSIR,
            }
        )
    )


def test_compiled_contract_closes_2_43_structurally():
    contract = TaskEvidenceContractCompiler().compile(
        task=(quran_interpretation_task()),
        quran_resolution=(resolved_2_255()),
    )

    result = TaskEvidenceAcceptanceGate().evaluate(
        contract=contract,
        evidence=(
            EvidenceNode(
                evidence_id=("quran:2:255"),
                domain=(EvidenceDomain.QURAN),
                text=("وسع كرسيه السماوات والأرض"),
                source_id=("quran:canonical"),
                reference="2:255",
            ),
            EvidenceNode(
                evidence_id=("tafsir:2:43"),
                domain=(EvidenceDomain.TAFSIR),
                text=("trusted but wrong ayah"),
                source_id=("dorar-tafsir"),
                reference="2:43",
            ),
            EvidenceNode(
                evidence_id=("tafsir:2:255"),
                domain=(EvidenceDomain.TAFSIR),
                text=("correct ayah tafsir"),
                source_id=("dorar-tafsir"),
                reference="2:255",
            ),
        ),
    )

    assert tuple(node.evidence_id for node in result.accepted_evidence) == (
        "quran:2:255",
        "tafsir:2:255",
    )

    rejected = next(
        record for record in result.records if (record.evidence_id == "tafsir:2:43")
    )

    assert rejected.reason is EvidenceAcceptanceReason.HARD_ANCHOR_MISMATCH

    assert result.structural_contract_satisfied


def test_interpretation_without_verified_anchor_stays_conceptual():
    contract = TaskEvidenceContractCompiler().compile(
        task=(quran_interpretation_task()),
        quran_resolution=(no_quran_anchor()),
    )

    assert contract.retrieval_shape is RetrievalShape.CONCEPTUAL

    assert contract.anchors == ()


def test_direct_quran_grounding_requires_verified_identity():
    text = "هات نص الآية"

    task = ClaimTask(
        task_id="claim:quran-direct",
        claim_text=text,
        frame=(
            ReligiousReasoningFrame(
                frame_id=("frame:quran-direct"),
                question=text,
                primary_discipline=(ReligiousDiscipline.QURAN),
                reasoning_mode=(ReasoningMode.DIRECT_GROUNDING),
            )
        ),
        context_requirement=(
            ContextRequirement(
                required=frozenset(
                    {
                        EvidenceNeed.CANONICAL_TEXT,
                    }
                )
            )
        ),
    )

    with pytest.raises(
        UnresolvedEvidenceIdentityError,
        match="verified",
    ):
        (
            TaskEvidenceContractCompiler().compile(
                task=task,
                quran_resolution=(no_quran_anchor()),
            )
        )


def test_direct_grounding_with_verified_anchor_is_exact():
    text = "هات نص الآية 2:255"

    task = ClaimTask(
        task_id="claim:quran-exact",
        claim_text=text,
        frame=(
            ReligiousReasoningFrame(
                frame_id=("frame:quran-exact"),
                question=text,
                primary_discipline=(ReligiousDiscipline.QURAN),
                reasoning_mode=(ReasoningMode.DIRECT_GROUNDING),
            )
        ),
        context_requirement=(
            ContextRequirement(
                required=frozenset(
                    {
                        EvidenceNeed.CANONICAL_TEXT,
                    }
                )
            )
        ),
    )

    contract = TaskEvidenceContractCompiler().compile(
        task=task,
        quran_resolution=(resolved_2_255()),
    )

    assert contract.retrieval_shape is RetrievalShape.EXACT_ANCHOR


def test_quran_identity_ambiguity_blocks_quran_claim():
    ambiguous = QuranAnchorResolution(
        disposition=(AnchorResolutionDisposition.BOUNDED_BRANCH),
        candidate_references=(
            "3:1",
            "4:1",
        ),
        reason=("canonical_text_matches_multiple_quran_verses"),
    )

    with pytest.raises(
        UnresolvedEvidenceIdentityError,
        match="unresolved",
    ):
        (
            TaskEvidenceContractCompiler().compile(
                task=(quran_interpretation_task()),
                quran_resolution=(ambiguous),
            )
        )


def test_quran_ambiguity_does_not_constrain_independent_fiqh_claim():
    text = "ما حكم هذه المسألة؟"

    task = ClaimTask(
        task_id="claim:fiqh",
        claim_text=text,
        frame=(
            ReligiousReasoningFrame(
                frame_id="frame:fiqh",
                question=text,
                primary_discipline=(ReligiousDiscipline.FIQH),
                reasoning_mode=(ReasoningMode.LEGAL_RULING),
            )
        ),
        context_requirement=(
            ContextRequirement(
                required=frozenset(
                    {
                        EvidenceNeed.FIQH_EVIDENCE,
                    }
                )
            )
        ),
    )

    ambiguous = QuranAnchorResolution(
        disposition=(AnchorResolutionDisposition.ASK_USER),
        candidate_references=(
            "2:43",
            "2:255",
        ),
        reason="quran_identity_conflict",
    )

    contract = TaskEvidenceContractCompiler().compile(
        task=task,
        quran_resolution=(ambiguous),
    )

    assert contract.retrieval_shape is RetrievalShape.CONCEPTUAL

    assert contract.allowed_domains == frozenset(
        {
            EvidenceDomain.FIQH,
        }
    )

    assert contract.anchors == ()


@pytest.mark.parametrize(
    (
        "discipline",
        "expected",
    ),
    (
        (
            ReligiousDiscipline.AQIDAH,
            EvidenceDomain.AQIDAH,
        ),
        (
            ReligiousDiscipline.SIRAH,
            EvidenceDomain.SIRA,
        ),
    ),
)
def test_new_taxonomy_survives_contract_compilation(
    discipline,
    expected,
):
    text = "claim"

    task = ClaimTask(
        task_id=(f"claim:{discipline.value}"),
        claim_text=text,
        frame=(
            ReligiousReasoningFrame(
                frame_id=(f"frame:{discipline.value}"),
                question=text,
                primary_discipline=(discipline),
                reasoning_mode=(ReasoningMode.INTERPRETATION),
            )
        ),
        context_requirement=(
            ContextRequirement(
                required=frozenset(
                    {
                        EvidenceNeed.SOURCE_PROVENANCE,
                    }
                )
            )
        ),
    )

    contract = TaskEvidenceContractCompiler().compile(
        task=task,
    )

    assert contract.allowed_domains == frozenset(
        {
            expected,
        }
    )

    assert contract.required_domains == frozenset(
        {
            expected,
        }
    )
