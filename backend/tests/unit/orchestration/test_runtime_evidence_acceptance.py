from __future__ import annotations

import pytest

from basira.evidence.bundle import (
    EvidenceBundleBuilder,
)
from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.orchestration.capability_executor import (
    CapabilityExecutionError,
    CapabilityRetrievalBinding,
    GovernedCapabilityExecutor,
)
from basira.orchestration.contracts import (
    AgentCapability,
    ClaimTask,
)
from basira.orchestration.evidence_acceptance import (
    AnchorKind,
    AnchorOrigin,
    ClaimEvidencePolicySet,
    EvidenceAcceptanceReason,
)
from basira.orchestration.evidence_contract_compiler import (
    TaskEvidenceContractCompiler,
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
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)


class RuntimeRetriever:
    def __init__(
        self,
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> None:
        self.evidence = evidence
        self.calls = []

    def retrieve(
        self,
        plan,
        *,
        limit_per_domain: int = 10,
    ) -> UnifiedRetrievalResult:
        self.calls.append(
            (
                plan,
                limit_per_domain,
            )
        )

        domains = {target.domain for target in plan.targets}

        evidence = tuple(node for node in self.evidence if node.domain in domains)

        return UnifiedRetrievalResult(
            plan=plan,
            evidence=evidence,
            unavailable_domains=(frozenset()),
        )


def task() -> ClaimTask:
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


def resolution() -> QuranAnchorResolution:
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


def policies() -> ClaimEvidencePolicySet:
    contract = TaskEvidenceContractCompiler().compile(
        task=task(),
        quran_resolution=resolution(),
    )

    return ClaimEvidencePolicySet(contracts=(contract,))


def evidence() -> tuple[
    EvidenceNode,
    ...,
]:
    return (
        EvidenceNode(
            evidence_id="quran:2:255",
            domain=EvidenceDomain.QURAN,
            text=("وسع كرسيه السماوات والأرض"),
            source_id="quran:canonical",
            reference="2:255",
        ),
        EvidenceNode(
            evidence_id="tafsir:2:43",
            domain=EvidenceDomain.TAFSIR,
            text=("authoritative but wrong verse"),
            source_id="dorar:tafsir",
            reference="2:43",
        ),
        EvidenceNode(
            evidence_id="tafsir:2:255",
            domain=EvidenceDomain.TAFSIR,
            text=("tafsir attached to the correct ayah"),
            source_id="dorar:tafsir",
            reference="2:255",
        ),
    )


def capability() -> AgentCapability:
    return AgentCapability(
        capability_id=("cap:quran-tafsir"),
        agent_id=("agent:quran-tafsir"),
        disciplines=frozenset(
            {
                ReligiousDiscipline.QURAN,
                ReligiousDiscipline.TAFSIR,
            }
        ),
    )


def binding() -> CapabilityRetrievalBinding:
    return CapabilityRetrievalBinding(
        capability_id=("cap:quran-tafsir"),
        domains=frozenset(
            {
                EvidenceDomain.QURAN,
                EvidenceDomain.TAFSIR,
            }
        ),
    )


def test_runtime_never_returns_wrong_anchor_as_trusted_evidence():
    retriever = RuntimeRetriever(evidence())

    executor = GovernedCapabilityExecutor(
        retriever=retriever,
        bindings=(binding(),),
        evidence_policies=(policies()),
    )

    product = executor.execute(
        task=task(),
        capability=capability(),
        delegation=None,
    )

    ids = tuple(node.evidence_id for node in product.retrieval_result.evidence)

    assert ids == (
        "quran:2:255",
        "tafsir:2:255",
    )

    # Agent-owned evidence channel remains empty.
    assert product.result.evidence == ()

    audit = executor.acceptance_for_task("claim:chair")

    assert audit is not None

    rejected = next(
        record for record in audit.records if (record.evidence_id == "tafsir:2:43")
    )

    assert rejected.reason is EvidenceAcceptanceReason.HARD_ANCHOR_MISMATCH

    assert audit.structural_contract_satisfied


def test_evidence_bundle_only_receives_structurally_accepted_evidence():
    executor = GovernedCapabilityExecutor(
        retriever=(RuntimeRetriever(evidence())),
        bindings=(binding(),),
        evidence_policies=(policies()),
    )

    product = executor.execute(
        task=task(),
        capability=capability(),
        delegation=None,
    )

    bundle = EvidenceBundleBuilder().build(product.retrieval_result)

    ids = {node.evidence_id for node in bundle.evidence}

    assert "tafsir:2:43" not in ids

    assert ids == {
        "quran:2:255",
        "tafsir:2:255",
    }


def test_strict_runtime_missing_contract_fails_before_retrieval():
    retriever = RuntimeRetriever(evidence())

    executor = GovernedCapabilityExecutor(
        retriever=retriever,
        bindings=(binding(),),
        evidence_policies=(ClaimEvidencePolicySet(contracts=())),
    )

    with pytest.raises(
        CapabilityExecutionError,
        match=("missing structural evidence contract"),
    ):
        executor.execute(
            task=task(),
            capability=capability(),
            delegation=None,
        )

    assert retriever.calls == []
