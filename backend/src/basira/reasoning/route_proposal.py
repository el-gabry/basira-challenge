from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
    RiskTag,
)


@dataclass(
    frozen=True,
    slots=True,
)
class RouteProposal:
    """
    Non-authoritative semantic routing proposal.

    This object may be produced by an LLM or another
    semantic classifier.

    It may propose interpretation of the user's
    question, but it grants no retrieval, evidence,
    source, identity, safety, or publication authority.

    In particular, this contract deliberately contains
    no:
    - canonical Quran/Hadith identity
    - required evidence needs
    - allowed evidence domains
    - allowed sources
    - publication decision
    """

    proposed_intent: BasiraIntent | None = None

    proposed_primary_discipline: ReligiousDiscipline | None = None

    proposed_secondary_disciplines: tuple[
        ReligiousDiscipline,
        ...,
    ] = ()

    proposed_reasoning_mode: ReasoningMode | None = None

    additional_risk_tags: frozenset[RiskTag] = frozenset()

    ambiguity: bool = False

    confidence: float = 0.0

    reason_codes: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

        if self.proposed_primary_discipline in self.proposed_secondary_disciplines:
            raise ValueError("primary discipline must not also be secondary")

        if len(set(self.proposed_secondary_disciplines)) != len(
            self.proposed_secondary_disciplines
        ):
            raise ValueError("secondary disciplines must be unique")

        cleaned_codes = tuple(code.strip() for code in self.reason_codes)

        if any(not code for code in cleaned_codes):
            raise ValueError("reason codes must not be blank")

        if len(set(cleaned_codes)) != len(cleaned_codes):
            raise ValueError("reason codes must be unique")


class RouteProposer(Protocol):
    """
    Semantic interpretation boundary.

    A proposer may suggest a route.
    It may not authorize that route.
    """

    def propose(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
    ) -> RouteProposal: ...


class NoOpRouteProposer:
    """
    Default semantic-routing implementation.

    It proposes nothing and therefore must produce
    no change to Basira's deterministic understanding.
    """

    def propose(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
    ) -> RouteProposal:
        del understanding

        return RouteProposal()
