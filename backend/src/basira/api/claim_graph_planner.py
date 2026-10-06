from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from basira.orchestration.claim_graph import (
    ClaimDependency,
    ClaimGraphPlan,
)
from basira.orchestration.contracts import (
    ClaimTask,
)


class ClaimTaskFactory(Protocol):
    """
    Build one already-routed ClaimTask from one atomic
    public claim.

    The graph planner owns decomposition/topology only.
    It does not choose sources, authority, or evidence.
    """

    def __call__(
        self,
        claim_text: str,
    ) -> ClaimTask: ...


# Split only at strong, explicit claim boundaries.
#
# We deliberately do NOT split ordinary Arabic commas
# or every conjunction. Ambiguous prose remains one claim
# rather than being over-decomposed.
_CLAIM_BOUNDARY_RE = re.compile(
    r"""
    [؟?]+\s*
    |
    [؛;]+\s*
    |
    ،\s*(?=(?:فهل|وهل|هل)\b)
    """,
    re.VERBOSE,
)


# These cues express an actual epistemic dependency on
# the immediately preceding claim.
#
# "فهل ..." alone is intentionally NOT included:
# a follow-up question can be an independent authority
# claim rather than a prerequisite relation.
_DEPENDENCY_CUES = (
    "بناء على ذلك",
    "بناءً على ذلك",
    "إذا ثبت",
    "اذا ثبت",
    "إن ثبت",
    "ان ثبت",
    "فما حكم",
    "وما حكم",
    "ما أثره في الحكم",
    "وما أثره في الحكم",
)


def _clean(
    value: str,
) -> str:
    return " ".join(value.split()).strip(" ،؛?؟")


def _depends_on_previous(
    claim_text: str,
) -> bool:
    normalized = _clean(claim_text)

    return any(
        cue in normalized
        for cue in _DEPENDENCY_CUES
    )


@dataclass(
    frozen=True,
    slots=True,
)
class PublicClaimGraphPlanner:
    """
    Conservative deterministic public claim planner.

    Responsibilities:
    - preserve simple questions as one ClaimTask;
    - split only explicit multi-claim constructions;
    - create dependencies only for explicit dependency
      language;
    - return the existing ClaimGraphPlan.

    Non-responsibilities:
    - routing;
    - source selection;
    - authority decisions;
    - evidence retrieval;
    - sufficiency;
    - publication decisions.
    """

    def decompose(
        self,
        question: str,
    ) -> tuple[str, ...]:
        normalized = " ".join(
            question.split()
        )

        if not normalized:
            raise ValueError(
                "Question must not be blank."
            )

        raw_parts = _CLAIM_BOUNDARY_RE.split(
            normalized
        )

        claims: list[str] = []
        seen: set[str] = set()

        for raw_part in raw_parts:
            claim = _clean(raw_part)

            if not claim:
                continue

            key = claim.casefold()

            if key in seen:
                continue

            seen.add(key)
            claims.append(claim)

        if not claims:
            return (normalized,)

        return tuple(claims)

    def plan(
        self,
        *,
        question: str,
        task_factory: ClaimTaskFactory,
    ) -> ClaimGraphPlan:
        claim_texts = self.decompose(
            question
        )

        tasks = tuple(
            task_factory(claim_text)
            for claim_text in claim_texts
        )

        dependencies: list[
            ClaimDependency
        ] = []

        for index in range(
            1,
            len(tasks),
        ):
            if not _depends_on_previous(
                claim_texts[index]
            ):
                continue

            dependencies.append(
                ClaimDependency(
                    prerequisite_task_id=(
                        tasks[index - 1].task_id
                    ),
                    dependent_task_id=(
                        tasks[index].task_id
                    ),
                    reason=(
                        "explicit linguistic dependency "
                        "on previous claim"
                    ),
                )
            )

        return ClaimGraphPlan(
            tasks=tasks,
            dependencies=tuple(
                dependencies
            ),
        )
