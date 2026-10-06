from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from basira.models.scholarly import ScholarlyPassage

_ARABIC_TOKEN_RE = re.compile(
    r"[\u0621-\u063A\u0641-\u064A]+"
)

_SEGMENT_BREAK_RE = re.compile(
    r"""
    (?:
        (?<=[.!؟؛])
        [ \t\r\n]+
    )
    |
    (?:
        \n[ \t]*\n+
    )
    """,
    re.VERBOSE,
)

_CONTEXT_DEPENDENCY_MARKERS = (
    "ما تقدم",
    "كما تقدم",
    "كما سبق",
    "المذكور",
    "المتقدم",
    "السابق",
    "على ما سبق",
    "على ما تقدم",
    "على ذلك",
    "بناء على ذلك",
    "بناءً على ذلك",
)

_STOPWORDS = frozenset(
    {
        "ما",
        "ماذا",
        "هل",
        "هو",
        "هي",
        "في",
        "من",
        "إلى",
        "الى",
        "على",
        "عن",
        "مع",
        "هذا",
        "هذه",
        "ذلك",
        "تلك",
        "الذي",
        "التي",
        "و",
        "أو",
        "او",
        "ثم",
        "عند",
        "حكم",
        "ماحكم",
    }
)


def _normalize_arabic(
    value: str,
) -> str:
    chars: list[str] = []

    for char in value:
        if char == "\u0640":
            continue

        if unicodedata.category(char) == "Mn":
            continue

        if char in "أإآ":
            chars.append("ا")
            continue

        if char == "ى":
            chars.append("ي")
            continue

        chars.append(char)

    return "".join(chars)


def _tokens(
    value: str,
) -> tuple[str, ...]:
    normalized = _normalize_arabic(
        value.lower()
    )

    return tuple(
        token
        for token in _ARABIC_TOKEN_RE.findall(
            normalized
        )
        if (
            len(token) > 1
            and token not in _STOPWORDS
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class FiqhTextSegment:
    start: int
    end: int
    text: str


@dataclass(
    frozen=True,
    slots=True,
)
class FiqhEvidenceProjection:
    """
    Exact source-faithful projection from one larger
    scholarly passage.

    `text` is always a contiguous substring of the
    original passage. The projector never paraphrases,
    summarizes, or manufactures religious content.
    """

    parent_passage_id: str
    start: int
    end: int
    text: str
    matched_terms: tuple[str, ...]
    context_expanded: bool

    def __post_init__(
        self,
    ) -> None:
        if self.start < 0:
            raise ValueError(
                "Projection start must be non-negative."
            )

        if self.end <= self.start:
            raise ValueError(
                "Projection end must be after start."
            )

        if not self.text:
            raise ValueError(
                "Projection text must not be empty."
            )


def _segments(
    text: str,
) -> tuple[
    FiqhTextSegment,
    ...,
]:
    """
    Split for selection only.

    Every returned segment is represented by offsets into
    the ORIGINAL text, so publication can preserve exact
    source characters.
    """

    if not text:
        return ()

    boundaries = [
        0,
    ]

    for match in _SEGMENT_BREAK_RE.finditer(
        text
    ):
        boundaries.extend(
            (
                match.start(),
                match.end(),
            )
        )

    boundaries.append(
        len(text)
    )

    candidates: list[
        FiqhTextSegment
    ] = []

    index = 0

    while index < len(boundaries) - 1:
        start = boundaries[index]
        end = boundaries[index + 1]

        raw = text[start:end]

        leading = len(raw) - len(
            raw.lstrip()
        )
        trailing = len(raw) - len(
            raw.rstrip()
        )

        exact_start = start + leading
        exact_end = (
            end - trailing
            if trailing
            else end
        )

        if exact_end > exact_start:
            segment_text = text[
                exact_start:exact_end
            ]

            if _tokens(segment_text):
                candidates.append(
                    FiqhTextSegment(
                        start=exact_start,
                        end=exact_end,
                        text=segment_text,
                    )
                )

        index += 1

    if candidates:
        return tuple(
            candidates
        )

    stripped = text.strip()

    if not stripped:
        return ()

    start = text.index(
        stripped
    )

    return (
        FiqhTextSegment(
            start=start,
            end=start + len(stripped),
            text=stripped,
        ),
    )


def _query_terms(
    query_hints: Iterable[str],
) -> frozenset[str]:
    values: set[str] = set()

    for query in query_hints:
        values.update(
            _tokens(query)
        )

    return frozenset(
        values
    )


def _segment_score(
    segment: FiqhTextSegment,
    *,
    query_terms: frozenset[str],
) -> tuple[
    int,
    float,
    int,
]:
    segment_terms = set(
        _tokens(segment.text)
    )

    overlap = (
        segment_terms
        & query_terms
    )

    overlap_count = len(
        overlap
    )

    density = (
        overlap_count
        / max(
            len(segment_terms),
            1,
        )
    )

    # Higher overlap/density wins.
    # For equal support, shorter text is preferred.
    return (
        overlap_count,
        density,
        -len(segment.text),
    )


def _needs_previous_context(
    text: str,
) -> bool:
    normalized = _normalize_arabic(
        text
    )

    return any(
        _normalize_arabic(marker)
        in normalized
        for marker
        in _CONTEXT_DEPENDENCY_MARKERS
    )


class FiqhEvidenceProjector:
    """
    Narrow a retrieved Fiqh passage to the smallest
    source-faithful unit that matches the search intent.

    Rules:
    - search/reasoning may use many query hints;
    - returned evidence remains an exact source slice;
    - no paraphrase;
    - no ruling generation;
    - no authority changes;
    - local context expands only when the selected text
      explicitly depends on previous context.
    """

    def project(
        self,
        passage: ScholarlyPassage,
        *,
        query_hints: Iterable[str],
    ) -> FiqhEvidenceProjection | None:
        text = passage.text

        segments = _segments(
            text
        )

        if not segments:
            return None

        terms = _query_terms(
            query_hints
        )

        if not terms:
            return None

        ranked = sorted(
            enumerate(segments),
            key=lambda item: (
                _segment_score(
                    item[1],
                    query_terms=terms,
                ),
                -item[0],
            ),
            reverse=True,
        )

        best_index, best = ranked[
            0
        ]

        matched = tuple(
            sorted(
                set(
                    _tokens(best.text)
                )
                & terms
            )
        )

        # Fail narrow:
        # no lexical support means we do NOT pretend that
        # the whole passage is the requested evidence.
        if not matched:
            return None

        selected_start = best.start
        selected_end = best.end
        context_expanded = False

        if (
            best_index > 0
            and _needs_previous_context(
                best.text
            )
        ):
            previous = segments[
                best_index - 1
            ]

            selected_start = (
                previous.start
            )
            context_expanded = True

        exact_text = text[
            selected_start:selected_end
        ]

        if (
            exact_text
            not in text
        ):
            raise AssertionError(
                "Projected Fiqh evidence must be an "
                "exact substring of its parent source."
            )

        return FiqhEvidenceProjection(
            parent_passage_id=(
                passage.passage_id
            ),
            start=selected_start,
            end=selected_end,
            text=exact_text,
            matched_terms=matched,
            context_expanded=(
                context_expanded
            ),
        )

    def project_passage(
        self,
        passage: ScholarlyPassage,
        *,
        query_hints: Iterable[str],
    ) -> ScholarlyPassage | None:
        projection = self.project(
            passage,
            query_hints=query_hints,
        )

        if projection is None:
            return None

        metadata = dict(
            passage.metadata
        )

        metadata.update(
            {
                "projection_kind":
                    "fiqh_targeted_exact_slice",
                "parent_passage_id":
                    projection.parent_passage_id,
                "projection_char_start":
                    str(projection.start),
                "projection_char_end":
                    str(projection.end),
                "projection_context_expanded":
                    (
                        "true"
                        if projection.context_expanded
                        else "false"
                    ),
                "projection_matched_terms":
                    "|".join(
                        projection.matched_terms
                    ),
            }
        )

        return passage.model_copy(
            update={
                "passage_id": (
                    f"{passage.passage_id}"
                    f":fiqh-projection:"
                    f"{projection.start}:"
                    f"{projection.end}"
                ),
                "text": projection.text,
                "metadata": metadata,
            }
        )
