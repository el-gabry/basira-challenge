from __future__ import annotations

from dataclasses import (
    dataclass,
    replace,
)

from basira.evidence.models import (
    ContextRequirement,
)
from basira.reasoning.route_proposal import (
    RouteProposal,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
    context_requirement_for,
)


@dataclass(
    frozen=True,
    slots=True,
)
class RouteGovernanceResult:
    """
    Result of governing a non-authoritative semantic
    route proposal.

    effective_understanding is the only understanding
    that may continue to the authoritative deterministic
    ReligiousReasoningRouter.
    """

    effective_understanding: BasiraQueryUnderstanding

    proposal: RouteProposal

    accepted_intent_specialization: bool

    governance_reasons: tuple[
        str,
        ...,
    ]


class RouteGovernor:
    """
    Deterministic authority over semantic route
    proposals.

    Core invariants:

    - an LLM may specialize a generic baseline intent;
    - an LLM may not replace a specific deterministic
      intent with a conflicting guess;
    - proposal risks are additive only;
    - existing baseline requirements are never removed;
    - evidence requirements are derived through Basira's
      existing deterministic context policy;
    - canonical identity, sources and publication
      authority are outside this component.
    """

    def __init__(
        self,
        *,
        minimum_specialization_confidence: float = 0.80,
    ) -> None:
        if not (0.0 <= minimum_specialization_confidence <= 1.0):
            raise ValueError(
                "minimum_specialization_confidence must be between 0.0 and 1.0"
            )

        self.minimum_specialization_confidence = minimum_specialization_confidence

    def govern(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
        proposal: RouteProposal,
    ) -> RouteGovernanceResult:
        if proposal == RouteProposal():
            return RouteGovernanceResult(
                effective_understanding=understanding,
                proposal=proposal,
                accepted_intent_specialization=False,
                governance_reasons=("proposal:no_op",),
            )

        baseline_intent = understanding.primary_intent

        effective_intent = baseline_intent

        accepted_specialization = False

        reasons: list[str] = []

        proposed_intent = proposal.proposed_intent

        if proposed_intent is None:
            reasons.append("proposal:no_intent")

        elif proposed_intent is baseline_intent:
            reasons.append("proposal:intent_agrees")

        elif baseline_intent is not BasiraIntent.GENERAL_ISLAMIC_QUESTION:
            reasons.append("proposal:intent_conflict_baseline_preserved")

        elif proposal.ambiguity:
            reasons.append("proposal:ambiguous_specialization_rejected")

        elif proposal.confidence < self.minimum_specialization_confidence:
            reasons.append("proposal:low_confidence_specialization_rejected")

        else:
            effective_intent = proposed_intent

            accepted_specialization = True

            reasons.append("proposal:intent_specialization_accepted")

        effective_risks = frozenset(
            set(understanding.risk_tags) | set(proposal.additional_risk_tags)
        )

        if effective_risks != understanding.risk_tags:
            reasons.append("proposal:additional_risk_hints_applied")

        policy_requirement = context_requirement_for(
            effective_intent,
            effective_risks,
        )

        required = frozenset(
            set(understanding.context_requirement.required)
            | set(policy_requirement.required)
        )

        optional = frozenset(
            (
                set(understanding.context_requirement.optional)
                | set(policy_requirement.optional)
            )
            - set(required)
        )

        effective_understanding = replace(
            understanding,
            primary_intent=effective_intent,
            risk_tags=effective_risks,
            context_requirement=(
                ContextRequirement(
                    required=required,
                    optional=optional,
                )
            ),
        )

        return RouteGovernanceResult(
            effective_understanding=(effective_understanding),
            proposal=proposal,
            accepted_intent_specialization=(accepted_specialization),
            governance_reasons=tuple(reasons),
        )
