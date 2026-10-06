from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from hashlib import sha256

from basira.competition.fiqh_policy import (
    Madhhab,
)
from basira.competition.madhhab_authority import (
    HybridBookDecision,
    MadhhabBookAuthorityGate,
    MadhhabBookPassport,
    MadhhabBookRetrievalMode,
)
from basira.retrieval.shamela_scout import (
    ShamelaScoutPlan,
)

_FORBIDDEN_FALLBACKS = (
    "generic_shamela_fallback",
    "ungoverned_web_fallback",
)


def _normalize_nonblank(
    value: str,
) -> str:
    normalized = " ".join(
        str(value).split()
    )

    if not normalized:
        raise ValueError(
            "Policy values must be nonblank."
        )

    return normalized


def _normalize_madhhabs(
    values: Iterable[str],
) -> tuple[str, ...]:
    normalized = tuple(
        sorted(
            {
                _normalize_nonblank(value)
                for value in values
            }
        )
    )

    valid = {
        madhhab.value
        for madhhab in Madhhab
        if madhhab is not Madhhab.UNSPECIFIED
    }

    invalid = tuple(
        value
        for value in normalized
        if value not in valid
    )

    if invalid:
        raise ValueError(
            "Unknown madhhab policy value(s): "
            + ", ".join(invalid)
        )

    return normalized


@dataclass(
    frozen=True,
    slots=True,
)
class FiqhRetrievalPolicyEnvelope:
    """
    Immutable execution constraints for a Fiqh search.

    The agent may reformulate the query underneath this
    envelope, but may not widen source authority,
    madhhab scope, work scope, or fallback permissions.

    `primary_work_ids` is the only work allowlist used
    for answer-bearing retrieval in Agent V1.

    Supporting references are preserved separately so
    they cannot be silently promoted to primary evidence.
    """

    requested_madhhabs: tuple[
        str,
        ...,
    ]

    retrieval_mode: (
        MadhhabBookRetrievalMode
    )

    primary_work_ids: tuple[
        str,
        ...,
    ]

    supporting_work_ids: tuple[
        str,
        ...,
    ]

    forbidden_fallbacks: tuple[
        str,
        ...,
    ]

    policy_fingerprint: str

    @property
    def allowed_work_ids(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Primary answer-bearing work scope.

        Supporting references deliberately remain outside
        this lane in V1.
        """

        return self.primary_work_ids


class FiqhRetrievalPolicyCompiler:
    """
    Compile governed book passports into an immutable
    retrieval envelope.

    This class does not retrieve passages and does not
    make a Fiqh ruling. It only decides which governed
    works may enter the primary retrieval lane.
    """

    def __init__(
        self,
        *,
        authority_gate: (
            MadhhabBookAuthorityGate | None
        ) = None,
    ) -> None:
        self.authority_gate = (
            authority_gate
            or MadhhabBookAuthorityGate()
        )

    def compile(
        self,
        *,
        books: Iterable[
            MadhhabBookPassport
        ],
        requested_madhhabs: Iterable[
            str
        ] = (),
        mode: MadhhabBookRetrievalMode = (
            MadhhabBookRetrievalMode
            .MUTAMAD_ONLY
        ),
    ) -> FiqhRetrievalPolicyEnvelope:
        requested = _normalize_madhhabs(
            requested_madhhabs
        )

        seen_books: dict[
            str,
            MadhhabBookPassport,
        ] = {}

        primary: set[str] = set()
        supporting: set[str] = set()

        for book in books:
            work_id = _normalize_nonblank(
                book.work_id
            )

            previous = seen_books.get(
                work_id
            )

            if (
                previous is not None
                and previous != book
            ):
                raise ValueError(
                    "Conflicting passports for "
                    f"work_id={work_id!r}."
                )

            if previous is not None:
                continue

            seen_books[
                work_id
            ] = book

            if (
                requested
                and book.madhhab.value
                not in requested
            ):
                continue

            assessment = (
                self.authority_gate.assess(
                    book,
                    mode=mode,
                )
            )

            if (
                assessment.decision
                is not HybridBookDecision.ALLOW
            ):
                continue

            if (
                assessment
                .may_use_as_primary_book_evidence
            ):
                primary.add(
                    work_id
                )
                continue

            # Preserve a governed supporting source as
            # supporting only. Do not authority-launder it
            # into the primary answer-bearing search lane.
            supporting.add(
                work_id
            )

        primary_work_ids = tuple(
            sorted(primary)
        )

        supporting_work_ids = tuple(
            sorted(
                supporting
                - primary
            )
        )

        payload = {
            "requested_madhhabs": (
                requested
            ),
            "retrieval_mode": (
                mode.value
            ),
            "primary_work_ids": (
                primary_work_ids
            ),
            "supporting_work_ids": (
                supporting_work_ids
            ),
            "forbidden_fallbacks": (
                _FORBIDDEN_FALLBACKS
            ),
        }

        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        fingerprint = sha256(
            canonical.encode(
                "utf-8"
            )
        ).hexdigest()

        return FiqhRetrievalPolicyEnvelope(
            requested_madhhabs=(
                requested
            ),
            retrieval_mode=mode,
            primary_work_ids=(
                primary_work_ids
            ),
            supporting_work_ids=(
                supporting_work_ids
            ),
            forbidden_fallbacks=(
                _FORBIDDEN_FALLBACKS
            ),
            policy_fingerprint=(
                fingerprint
            ),
        )


def bind_fiqh_policy(
    plan: ShamelaScoutPlan,
    envelope: FiqhRetrievalPolicyEnvelope,
) -> ShamelaScoutPlan:
    """
    Bind an immutable Fiqh policy to an existing Scout
    plan without changing the semantic question.

    The plan's declared madhhab request must exactly
    match the compiled envelope. This prevents a later
    agent step from silently widening or narrowing the
    epistemic request.
    """

    planned_madhhabs = (
        _normalize_madhhabs(
            plan.requested_madhhabs
        )
    )

    if (
        planned_madhhabs
        != envelope.requested_madhhabs
    ):
        raise ValueError(
            "Scout plan madhhab scope does not "
            "match the compiled Fiqh policy."
        )

    initial_tasks = tuple(
        replace(
            task,
            allowed_work_ids=(
                envelope.allowed_work_ids
            ),
            policy_fingerprint=(
                envelope.policy_fingerprint
            ),
        )
        for task in plan.initial_tasks
    )

    return replace(
        plan,
        initial_tasks=initial_tasks,
        allowed_work_ids=(
            envelope.allowed_work_ids
        ),
        policy_fingerprint=(
            envelope.policy_fingerprint
        ),
    )
