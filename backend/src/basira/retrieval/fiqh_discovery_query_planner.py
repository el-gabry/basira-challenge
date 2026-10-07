from __future__ import annotations

import re
from dataclasses import dataclass

_BOUNDARY_RE = re.compile(
    r"[؟?!؛;\n]+"
)

_ARABIC_REQUEST_PREFIX_RE = re.compile(
    r"""
    ^
    (?:
        ما\s+(?:هو\s+)?حكم
        |
        هل\s+يجوز
        |
        ما\s+هي\s+أحكام
        |
        ما\s+الأحكام
    )
    \s+
    """,
    re.VERBOSE,
)

_DEPENDENT_REFERENCE_MARKERS = (
    "هذه الصورة",
    "هذه المسألة",
    "هذا الحكم",
    "هذه الحالة",
    "ذلك الحكم",
    "تلك المسألة",
)

_EDGE_PUNCTUATION = (
    " \t\r\n"
    "؟?!؛;:،,."
    "\"'«»"
)


def _clean(
    value: str,
) -> str:
    return " ".join(
        value.strip(
            _EDGE_PUNCTUATION
        ).split()
    )


def _strip_request_wrapper(
    value: str,
) -> str:
    cleaned = _clean(
        value
    )

    stripped = (
        _ARABIC_REQUEST_PREFIX_RE.sub(
            "",
            cleaned,
            count=1,
        )
    )

    return _clean(
        stripped
    )


def _is_dependent_followup(
    value: str,
) -> bool:
    return any(
        marker in value
        for marker
        in _DEPENDENT_REFERENCE_MARKERS
    )


def _substantive_token_count(
    value: str,
) -> int:
    return len(
        [
            token
            for token in value.split()
            if len(token) > 1
        ]
    )


@dataclass(
    frozen=True,
    slots=True,
)
class FiqhDiscoveryQueryPlan:
    """
    Search-only Fiqh query variants.

    `evidence_query` is derived ONLY by removing
    generic request wording from the user's own
    primary issue clause.

    Discovery variants are never evidence.
    """

    original_query: str

    # User-authored primary issue used for evidence
    # relevance/projection. This is NOT a semantic
    # reformulation or legal inference.
    evidence_query: str

    queries: tuple[
        str,
        ...,
    ]


class FiqhDiscoveryQueryPlanner:
    """
    Conservative deterministic Fiqh search planner.

    Allowed:
    - preserve the original question;
    - split explicit punctuation boundaries;
    - remove generic request wrappers.

    Forbidden:
    - legal synonyms;
    - generated rulings;
    - inferred legal concepts;
    - madhhab expansion;
    - authority expansion.
    """

    def plan(
        self,
        question: str,
        *,
        max_queries: int = 4,
    ) -> FiqhDiscoveryQueryPlan:
        original = " ".join(
            question.split()
        ).strip()

        if not original:
            raise ValueError(
                "Fiqh discovery question "
                "must not be blank."
            )

        if max_queries <= 0:
            raise ValueError(
                "max_queries must be positive."
            )

        clauses = tuple(
            _clean(part)
            for part in _BOUNDARY_RE.split(
                original
            )
            if _clean(part)
        )

        primary_clause = (
            clauses[0]
            if clauses
            else _clean(original)
        )

        evidence_query = (
            _strip_request_wrapper(
                primary_clause
            )
            or primary_clause
        )

        queries: list[str] = []
        seen: set[str] = set()

        def add(
            value: str,
            *,
            preserve_surface: bool = False,
        ) -> None:
            surface = (
                " ".join(
                    value.split()
                ).strip()
                if preserve_surface
                else _clean(
                    value
                )
            )

            if not surface:
                return

            semantic_form = _clean(
                surface
            )

            if (
                _substantive_token_count(
                    semantic_form
                )
                < 2
            ):
                return

            key = (
                semantic_form.casefold()
            )

            if key in seen:
                return

            seen.add(key)

            queries.append(
                surface
            )

        # 1. Exact user surface.
        add(
            original,
            preserve_surface=True,
        )

        # 2. Explicit independent clauses.
        for index, clause in enumerate(
            clauses
        ):
            if len(queries) >= max_queries:
                break

            if (
                index > 0
                and _is_dependent_followup(
                    clause
                )
            ):
                continue

            add(
                clause
            )

            if len(queries) >= max_queries:
                break

            # 3. Same user clause minus generic
            # question wrapper.
            add(
                _strip_request_wrapper(
                    clause
                )
            )

        return FiqhDiscoveryQueryPlan(
            original_query=original,
            evidence_query=(
                evidence_query
            ),
            queries=tuple(
                queries[:max_queries]
            ),
        )
