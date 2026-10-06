from __future__ import annotations

from dataclasses import replace

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.orchestration.evidence_acceptance import (
    AnchorStrength,
    TaskEvidenceAcceptanceContract,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlan,
    RetrievalTarget,
)


class RetrievalConstraintProjectionError(RuntimeError):
    pass


def _hard_references_for_domain(
    contract: TaskEvidenceAcceptanceContract,
    domain: EvidenceDomain,
) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []

    for anchor in contract.anchors:
        if anchor.strength is not AnchorStrength.HARD or domain not in anchor.domains:
            continue

        reference = anchor.reference.strip()

        if not reference or reference in seen:
            continue

        seen.add(reference)
        result.append(reference)

    return tuple(result)


def project_contract_onto_plan(
    *,
    plan: BasiraRetrievalPlan,
    contract: TaskEvidenceAcceptanceContract,
) -> BasiraRetrievalPlan:
    planned_domains = {target.domain for target in plan.targets}

    missing_required = contract.required_domains - planned_domains

    if missing_required:
        raise (
            RetrievalConstraintProjectionError(
                "retrieval plan is missing "
                "required claim domains: "
                + ", ".join(sorted(domain.value for domain in missing_required))
            )
        )

    constrained: list[RetrievalTarget] = []

    for target in plan.targets:
        if target.domain not in contract.allowed_domains:
            continue

        constrained.append(
            replace(
                target,
                references=(
                    _hard_references_for_domain(
                        contract,
                        target.domain,
                    )
                ),
            )
        )

    if not constrained:
        raise (
            RetrievalConstraintProjectionError(
                "claim contract removed all retrieval targets"
            )
        )

    return replace(
        plan,
        targets=tuple(constrained),
    )
