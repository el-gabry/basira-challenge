from __future__ import annotations

from dataclasses import (
    dataclass,
    fields,
)

import pytest

from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
    EvidenceNeed,
)
from basira.orchestration.capability_executor import (
    CapabilityRetrievalBinding,
    CapabilityRetrievalMismatch,
    GovernedCapabilityExecutor,
    UnregisteredCapabilityExecution,
)
from basira.orchestration.contracts import (
    AgentCapability,
    ClaimTask,
    DelegationRequest,
)
from basira.reasoning.contracts import (
    EvidenceObligation,
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class FakeEvidence:
    evidence_id: str


class RecordingRetriever:
    def __init__(
        self,
        *,
        emit_evidence: bool = False,
    ) -> None:
        self.calls = []
        self.emit_evidence = (
            emit_evidence
        )

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

        evidence = ()

        if self.emit_evidence:
            evidence = tuple(
                FakeEvidence(
                    evidence_id=(
                        f"{target.domain.value}:"
                        f"{len(self.calls)}"
                    )
                )
                for target in plan.targets
            )

        return UnifiedRetrievalResult(
            plan=plan,
            evidence=evidence,  # type: ignore[arg-type]
            unavailable_domains=frozenset(),
        )


def quran_task() -> ClaimTask:
    text = (
        "ما معنى الآية 2:255؟"
    )

    return ClaimTask(
        task_id="claim:quran",
        claim_text=text,
        frame=ReligiousReasoningFrame(
            frame_id="frame:quran",
            question=text,
            primary_discipline=(
                ReligiousDiscipline.QURAN
            ),
            reasoning_mode=(
                ReasoningMode.INTERPRETATION
            ),
            obligations=(
                EvidenceObligation
                .EXACT_CANONICAL_TEXT,
            ),
        ),
        context_requirement=(
            ContextRequirement(
                required=frozenset(
                    {
                        EvidenceNeed
                        .SOURCE_PROVENANCE,
                    }
                )
            )
        ),
    )


def fiqh_task() -> ClaimTask:
    text = (
        "ما حكم البيع في هذه المسألة؟"
    )

    return ClaimTask(
        task_id="claim:fiqh",
        claim_text=text,
        frame=ReligiousReasoningFrame(
            frame_id="frame:fiqh",
            question=text,
            primary_discipline=(
                ReligiousDiscipline.FIQH
            ),
            reasoning_mode=(
                ReasoningMode.LEGAL_RULING
            ),
        ),
        context_requirement=(
            ContextRequirement()
        ),
    )


def capability(
    *,
    capability_id: str,
    agent_id: str,
    discipline: ReligiousDiscipline,
) -> AgentCapability:
    return AgentCapability(
        capability_id=capability_id,
        agent_id=agent_id,
        disciplines=frozenset(
            {
                discipline,
            }
        ),
    )


def test_executor_only_narrows_existing_plan_targets() -> None:
    retriever = RecordingRetriever()

    executor = GovernedCapabilityExecutor(
        retriever=retriever,  # type: ignore[arg-type]
        bindings=(
            CapabilityRetrievalBinding(
                capability_id="cap:quran",
                domains=frozenset(
                    {
                        EvidenceDomain.QURAN,
                    }
                ),
            ),
        ),
    )

    executor.execute(
        task=quran_task(),
        capability=capability(
            capability_id="cap:quran",
            agent_id="agent:quran",
            discipline=(
                ReligiousDiscipline.QURAN
            ),
        ),
        delegation=None,
    )

    assert len(
        retriever.calls
    ) == 1

    plan = retriever.calls[
        0
    ][0]

    assert tuple(
        target.domain
        for target in plan.targets
    ) == (
        EvidenceDomain.QURAN,
    )


def test_executor_cannot_add_domain_missing_from_plan() -> None:
    retriever = RecordingRetriever()

    executor = GovernedCapabilityExecutor(
        retriever=retriever,  # type: ignore[arg-type]
        bindings=(
            CapabilityRetrievalBinding(
                capability_id="cap:fiqh",
                domains=frozenset(
                    {
                        EvidenceDomain.FIQH,
                    }
                ),
            ),
        ),
    )

    with pytest.raises(
        CapabilityRetrievalMismatch
    ):
        executor.execute(
            task=quran_task(),
            capability=capability(
                capability_id="cap:fiqh",
                agent_id="agent:fiqh",
                discipline=(
                    ReligiousDiscipline.FIQH
                ),
            ),
            delegation=None,
        )

    assert retriever.calls == []


def test_unregistered_capability_fails_before_retrieval() -> None:
    retriever = RecordingRetriever()

    executor = GovernedCapabilityExecutor(
        retriever=retriever,  # type: ignore[arg-type]
        bindings=(
            CapabilityRetrievalBinding(
                capability_id="cap:quran",
                domains=frozenset(
                    {
                        EvidenceDomain.QURAN,
                    }
                ),
            ),
        ),
    )

    with pytest.raises(
        UnregisteredCapabilityExecution
    ):
        executor.execute(
            task=quran_task(),
            capability=capability(
                capability_id="cap:other",
                agent_id="agent:other",
                discipline=(
                    ReligiousDiscipline.QURAN
                ),
            ),
            delegation=None,
        )

    assert retriever.calls == []


def test_agent_result_does_not_copy_trusted_evidence() -> None:
    retriever = RecordingRetriever(
        emit_evidence=True
    )

    executor = GovernedCapabilityExecutor(
        retriever=retriever,  # type: ignore[arg-type]
        bindings=(
            CapabilityRetrievalBinding(
                capability_id="cap:quran",
                domains=frozenset(
                    {
                        EvidenceDomain.QURAN,
                    }
                ),
            ),
        ),
    )

    product = executor.execute(
        task=quran_task(),
        capability=capability(
            capability_id="cap:quran",
            agent_id="agent:quran",
            discipline=(
                ReligiousDiscipline.QURAN
            ),
        ),
        delegation=None,
    )

    assert (
        product.result.evidence
        == ()
    )

    assert len(
        product.retrieval_result.evidence
    ) == 1


def test_task_requirement_is_not_weakened() -> None:
    retriever = RecordingRetriever()

    executor = GovernedCapabilityExecutor(
        retriever=retriever,  # type: ignore[arg-type]
        bindings=(
            CapabilityRetrievalBinding(
                capability_id="cap:quran",
                domains=frozenset(
                    {
                        EvidenceDomain.QURAN,
                    }
                ),
            ),
        ),
    )

    executor.execute(
        task=quran_task(),
        capability=capability(
            capability_id="cap:quran",
            agent_id="agent:quran",
            discipline=(
                ReligiousDiscipline.QURAN
            ),
        ),
        delegation=None,
    )

    plan = retriever.calls[
        0
    ][0]

    assert (
        EvidenceNeed.SOURCE_PROVENANCE
        in plan
        .context_requirement
        .required
    )

    assert (
        EvidenceNeed.CANONICAL_TEXT
        in plan
        .context_requirement
        .required
    )


def test_governed_results_accumulate_across_delegated_runs() -> None:
    retriever = RecordingRetriever(
        emit_evidence=True
    )

    executor = GovernedCapabilityExecutor(
        retriever=retriever,  # type: ignore[arg-type]
        bindings=(
            CapabilityRetrievalBinding(
                capability_id="cap:fiqh",
                domains=frozenset(
                    {
                        EvidenceDomain.FIQH,
                    }
                ),
            ),
            CapabilityRetrievalBinding(
                capability_id="cap:hadith",
                domains=frozenset(
                    {
                        EvidenceDomain.HADITH,
                    }
                ),
            ),
        ),
    )

    task = fiqh_task()

    executor.execute(
        task=task,
        capability=capability(
            capability_id="cap:fiqh",
            agent_id="agent:fiqh",
            discipline=(
                ReligiousDiscipline.FIQH
            ),
        ),
        delegation=None,
    )

    delegation = DelegationRequest(
        delegation_id="delegation:hadith",
        task_id=task.task_id,
        reason="Need hadith support",
        requested_disciplines=frozenset(
            {
                ReligiousDiscipline.HADITH,
            }
        ),
    )

    product = executor.execute(
        task=task,
        capability=capability(
            capability_id="cap:hadith",
            agent_id="agent:hadith",
            discipline=(
                ReligiousDiscipline.HADITH
            ),
        ),
        delegation=delegation,
    )

    assert tuple(
        target.domain
        for target
        in product
        .retrieval_result
        .plan
        .targets
    ) == (
        EvidenceDomain.FIQH,
        EvidenceDomain.HADITH,
    )

    assert len(
        product
        .retrieval_result
        .evidence
    ) == 2

    assert (
        product.result.evidence
        == ()
    )


def test_duplicate_binding_is_rejected() -> None:
    binding = (
        CapabilityRetrievalBinding(
            capability_id="cap:quran",
            domains=frozenset(
                {
                    EvidenceDomain.QURAN,
                }
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="duplicate capability retrieval binding",
    ):
        GovernedCapabilityExecutor(
            retriever=RecordingRetriever(),  # type: ignore[arg-type]
            bindings=(
                binding,
                binding,
            ),
        )


def test_binding_contains_no_source_authority_controls() -> None:
    names = {
        field.name
        for field in fields(
            CapabilityRetrievalBinding
        )
    }

    forbidden = (
        "source",
        "authority",
        "book",
        "work",
        "url",
        "runtime",
        "policy",
    )

    assert not any(
        token in name
        for name in names
        for token in forbidden
    )
