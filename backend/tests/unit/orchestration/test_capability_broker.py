from __future__ import annotations

from dataclasses import fields

import pytest

from basira.evidence.models import (
    ContextRequirement,
    EvidenceNeed,
)
from basira.orchestration.capability_broker import (
    AmbiguousCapabilitySelection,
    CapabilityBroker,
    CapabilityDemand,
    NoMatchingCapability,
)
from basira.orchestration.contracts import (
    AgentCapability,
    ClaimTask,
    ContextKind,
    DelegationRequest,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)


def capability(
    *,
    capability_id: str,
    agent_id: str,
    disciplines: tuple[
        ReligiousDiscipline,
        ...,
    ] = (),
    evidence_needs: tuple[
        EvidenceNeed,
        ...,
    ] = (),
    context_kinds: tuple[
        ContextKind,
        ...,
    ] = (),
) -> AgentCapability:
    return AgentCapability(
        capability_id=capability_id,
        agent_id=agent_id,
        disciplines=disciplines,
        evidence_needs=evidence_needs,
        context_kinds=context_kinds,
        may_delegate=False,
    )


def task(
    *,
    primary: ReligiousDiscipline,
    secondary: tuple[
        ReligiousDiscipline,
        ...,
    ] = (),
) -> ClaimTask:
    question = "Test claim"

    return ClaimTask(
        task_id="claim:1",
        claim_text=question,
        frame=ReligiousReasoningFrame(
            frame_id="frame:1",
            question=question,
            primary_discipline=primary,
            secondary_disciplines=secondary,
            reasoning_mode=(
                ReasoningMode
                .DIRECT_GROUNDING
            ),
        ),
        context_requirement=(
            ContextRequirement()
        ),
        risk_tags=(),
        context_ids=(),
    )


def test_task_dispatch_uses_primary_discipline_only() -> None:
    fiqh = capability(
        capability_id="cap:fiqh",
        agent_id="agent:fiqh",
        disciplines=(
            ReligiousDiscipline.FIQH,
        ),
    )

    hadith = capability(
        capability_id="cap:hadith",
        agent_id="agent:hadith",
        disciplines=(
            ReligiousDiscipline.HADITH,
        ),
    )

    broker = CapabilityBroker(
        (
            hadith,
            fiqh,
        )
    )

    selected = broker.select_for_task(
        task(
            primary=(
                ReligiousDiscipline.FIQH
            ),
            secondary=(
                ReligiousDiscipline.HADITH,
            ),
        )
    )

    assert (
        selected.capability_id
        == "cap:fiqh"
    )

    assert (
        selected.agent_id
        == "agent:fiqh"
    )


def test_delegation_routes_by_evidence_need() -> None:
    hadith = capability(
        capability_id="cap:hadith-grade",
        agent_id="agent:hadith",
        evidence_needs=(
            EvidenceNeed.HADITH_GRADE,
        ),
    )

    broker = CapabilityBroker(
        (hadith,)
    )

    request = DelegationRequest(
        delegation_id="delegation:1",
        task_id="claim:1",
        reason="Need authentication",
        requested_evidence_needs=(
            EvidenceNeed.HADITH_GRADE,
        ),
    )

    selected = (
        broker
        .select_for_delegation(
            request
        )
    )

    assert (
        selected.capability_id
        == "cap:hadith-grade"
    )


def test_delegation_requires_full_dimension_coverage() -> None:
    partial = capability(
        capability_id="cap:partial",
        agent_id="agent:partial",
        disciplines=(
            ReligiousDiscipline.HADITH,
        ),
        evidence_needs=(
            EvidenceNeed.HADITH_TEXT,
        ),
    )

    broker = CapabilityBroker(
        (partial,)
    )

    demand = CapabilityDemand(
        task_id="claim:1",
        disciplines=(
            ReligiousDiscipline.HADITH,
        ),
        evidence_needs=(
            EvidenceNeed.HADITH_TEXT,
            EvidenceNeed.HADITH_GRADE,
        ),
    )

    with pytest.raises(
        NoMatchingCapability
    ):
        broker.select(
            demand
        )


def test_context_capability_can_be_selected() -> None:
    dawah_context = capability(
        capability_id="cap:dawah-context",
        agent_id="agent:dawah",
        context_kinds=(
            ContextKind.AUDIENCE,
            ContextKind.LANGUAGE,
        ),
    )

    broker = CapabilityBroker(
        (dawah_context,)
    )

    demand = CapabilityDemand(
        task_id="claim:1",
        context_kinds=(
            ContextKind.AUDIENCE,
        ),
    )

    assert (
        broker.select(
            demand
        ).capability_id
        == "cap:dawah-context"
    )


def test_no_match_fails_closed() -> None:
    broker = CapabilityBroker(
        (
            capability(
                capability_id="cap:hadith",
                agent_id="agent:hadith",
                disciplines=(
                    ReligiousDiscipline.HADITH,
                ),
            ),
        )
    )

    with pytest.raises(
        NoMatchingCapability
    ):
        broker.select_for_task(
            task(
                primary=(
                    ReligiousDiscipline.FIQH
                ),
            )
        )


def test_ambiguous_match_fails_closed() -> None:
    broker = CapabilityBroker(
        (
            capability(
                capability_id="cap:fiqh:b",
                agent_id="agent:b",
                disciplines=(
                    ReligiousDiscipline.FIQH,
                ),
            ),
            capability(
                capability_id="cap:fiqh:a",
                agent_id="agent:a",
                disciplines=(
                    ReligiousDiscipline.FIQH,
                ),
            ),
        )
    )

    with pytest.raises(
        AmbiguousCapabilitySelection,
        match=(
            "cap:fiqh:a, cap:fiqh:b"
        ),
    ):
        broker.select_for_task(
            task(
                primary=(
                    ReligiousDiscipline.FIQH
                ),
            )
        )


def test_registration_order_does_not_change_candidates() -> None:
    first = capability(
        capability_id="cap:a",
        agent_id="agent:a",
        disciplines=(
            ReligiousDiscipline.FIQH,
        ),
    )

    second = capability(
        capability_id="cap:b",
        agent_id="agent:b",
        disciplines=(
            ReligiousDiscipline.FIQH,
        ),
    )

    demand = CapabilityDemand(
        task_id="claim:1",
        disciplines=(
            ReligiousDiscipline.FIQH,
        ),
    )

    left = CapabilityBroker(
        (
            second,
            first,
        )
    ).candidates(
        demand
    )

    right = CapabilityBroker(
        (
            first,
            second,
        )
    ).candidates(
        demand
    )

    assert tuple(
        item.capability_id
        for item in left
    ) == (
        "cap:a",
        "cap:b",
    )

    assert tuple(
        item.capability_id
        for item in right
    ) == (
        "cap:a",
        "cap:b",
    )


def test_duplicate_capability_id_is_rejected() -> None:
    one = capability(
        capability_id="cap:duplicate",
        agent_id="agent:one",
        disciplines=(
            ReligiousDiscipline.FIQH,
        ),
    )

    two = capability(
        capability_id="cap:duplicate",
        agent_id="agent:two",
        disciplines=(
            ReligiousDiscipline.HADITH,
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate capability_id",
    ):
        CapabilityBroker(
            (
                one,
                two,
            )
        )


def test_capability_demand_contains_no_source_authority_fields() -> None:
    names = {
        field.name
        for field in fields(
            CapabilityDemand
        )
    }

    forbidden_fragments = (
        "source",
        "authority",
        "book",
        "work",
        "url",
        "runtime",
        "policy",
    )

    assert not any(
        fragment in name
        for name in names
        for fragment in forbidden_fragments
    )


def test_broker_cannot_turn_capability_into_source_permission() -> None:
    fiqh = capability(
        capability_id="cap:fiqh",
        agent_id="agent:fiqh",
        disciplines=(
            ReligiousDiscipline.FIQH,
        ),
    )

    broker = CapabilityBroker(
        (fiqh,)
    )

    selected = broker.select_for_task(
        task(
            primary=(
                ReligiousDiscipline.FIQH
            ),
        )
    )

    assert not hasattr(
        selected,
        "source_id",
    )

    assert not hasattr(
        selected,
        "work_id",
    )

    assert not hasattr(
        selected,
        "authority_level",
    )
