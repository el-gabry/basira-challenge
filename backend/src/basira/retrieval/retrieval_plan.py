from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
)


class RetrievalStrategy(StrEnum):
    EXACT_REFERENCE = "exact_reference"
    EXACT_TEXT = "exact_text"
    NORMALIZED_TEXT = "normalized_text"
    PHRASE = "phrase"
    LEXICAL_FALLBACK = "lexical_fallback"
    SEMANTIC_FALLBACK = "semantic_fallback"


@dataclass(
    frozen=True,
    slots=True,
)
class RetrievalTarget:
    domain: EvidenceDomain

    strategies: tuple[
        RetrievalStrategy,
        ...,
    ]

    # Verified execution references projected
    # from the claim evidence contract.
    # This is NOT source authority and is NOT
    # independently planner-generated truth.
    references: tuple[str, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class BasiraRetrievalPlan:
    understanding: BasiraQueryUnderstanding

    targets: tuple[
        RetrievalTarget,
        ...,
    ]

    context_requirement: ContextRequirement


class BasiraRetrievalPlanner:
    """
    Deterministic baseline retrieval planning.

    This planner describes what should be retrieved.

    Future protection layers may strengthen the
    ContextRequirement but should not bypass it.
    """

    def build(
        self,
        understanding: (BasiraQueryUnderstanding),
    ) -> BasiraRetrievalPlan:
        intent = understanding.primary_intent

        targets: list[RetrievalTarget] = []

        if intent in {
            BasiraIntent.HADITH_LOOKUP,
            BasiraIntent.HADITH_AUTHENTICITY,
            BasiraIntent.HADITH_EXPLANATION,
        }:
            targets.append(
                RetrievalTarget(
                    domain=(EvidenceDomain.HADITH),
                    strategies=(
                        RetrievalStrategy.EXACT_REFERENCE,
                        RetrievalStrategy.EXACT_TEXT,
                        RetrievalStrategy.NORMALIZED_TEXT,
                        RetrievalStrategy.PHRASE,
                    ),
                )
            )

        elif intent in {
            BasiraIntent.QURAN_LOOKUP,
            BasiraIntent.QURAN_MEANING,
            BasiraIntent.TAFSIR_CONTEXT,
        }:
            targets.append(
                RetrievalTarget(
                    domain=(EvidenceDomain.QURAN),
                    strategies=(
                        RetrievalStrategy.EXACT_REFERENCE,
                        RetrievalStrategy.EXACT_TEXT,
                        RetrievalStrategy.NORMALIZED_TEXT,
                        RetrievalStrategy.PHRASE,
                    ),
                )
            )

            if intent in {
                BasiraIntent.QURAN_MEANING,
                BasiraIntent.TAFSIR_CONTEXT,
            }:
                targets.append(
                    RetrievalTarget(
                        domain=(EvidenceDomain.TAFSIR),
                        strategies=(
                            RetrievalStrategy.EXACT_REFERENCE,
                            RetrievalStrategy.LEXICAL_FALLBACK,
                            RetrievalStrategy.SEMANTIC_FALLBACK,
                        ),
                    )
                )

            if intent is BasiraIntent.TAFSIR_CONTEXT:
                targets.append(
                    RetrievalTarget(
                        domain=(EvidenceDomain.REVELATION_CONTEXT),
                        strategies=(RetrievalStrategy.EXACT_REFERENCE,),
                    )
                )

        elif intent is BasiraIntent.FIQH_QUESTION:
            targets.extend(
                [
                    RetrievalTarget(
                        domain=(EvidenceDomain.FIQH),
                        strategies=(
                            RetrievalStrategy.NORMALIZED_TEXT,
                            RetrievalStrategy.SEMANTIC_FALLBACK,
                        ),
                    ),
                    RetrievalTarget(
                        domain=(EvidenceDomain.HADITH),
                        strategies=(
                            RetrievalStrategy.PHRASE,
                            RetrievalStrategy.SEMANTIC_FALLBACK,
                        ),
                    ),
                ]
            )

        elif intent in {
            BasiraIntent.GENERAL_ISLAMIC_QUESTION,
            BasiraIntent.THEOLOGY,
            BasiraIntent.HISTORICAL_CONTEXT,
        }:
            targets.extend(
                [
                    RetrievalTarget(
                        domain=(EvidenceDomain.QURAN),
                        strategies=(
                            RetrievalStrategy.NORMALIZED_TEXT,
                            RetrievalStrategy.PHRASE,
                        ),
                    ),
                    RetrievalTarget(
                        domain=(EvidenceDomain.HADITH),
                        strategies=(
                            RetrievalStrategy.NORMALIZED_TEXT,
                            RetrievalStrategy.PHRASE,
                        ),
                    ),
                    RetrievalTarget(
                        domain=(EvidenceDomain.TAFSIR),
                        strategies=(RetrievalStrategy.LEXICAL_FALLBACK,),
                    ),
                ]
            )

        else:
            targets.extend(
                [
                    RetrievalTarget(
                        domain=(EvidenceDomain.QURAN),
                        strategies=(
                            RetrievalStrategy.NORMALIZED_TEXT,
                            RetrievalStrategy.PHRASE,
                        ),
                    ),
                    RetrievalTarget(
                        domain=(EvidenceDomain.HADITH),
                        strategies=(
                            RetrievalStrategy.NORMALIZED_TEXT,
                            RetrievalStrategy.PHRASE,
                        ),
                    ),
                ]
            )

        return BasiraRetrievalPlan(
            understanding=understanding,
            targets=tuple(targets),
            context_requirement=(understanding.context_requirement),
        )
