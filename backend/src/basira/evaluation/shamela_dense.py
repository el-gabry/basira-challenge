from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class DensePassage:
    """
    Minimal canonical passage identity required by
    the frozen Shamela retrieval evaluator.

    Dense representations are retrieval artifacts
    only. This object points back to canonical
    governed passage identity.
    """

    passage_id: str
    work_id: str | None
    metadata: Mapping[
        str,
        object,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class DenseHit:
    passage: DensePassage
    score: float
    matched_window_id: str


@dataclass(
    frozen=True,
    slots=True,
)
class FusedHit:
    passage: object
    score: float

    source_ranks: tuple[
        int | None,
        ...,
    ]


def _passage_id(
    hit: object,
) -> str:
    passage = hit.passage

    passage_id = passage.passage_id

    return str(passage_id)


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[object]],
    *,
    limit: int,
    rank_constant: int = 60,
) -> tuple[
    FusedHit,
    ...,
]:
    """
    Deterministic passage-level RRF.

    Ranking scores are not confidence scores and
    do not represent semantic support.
    """

    if limit <= 0:
        raise ValueError("limit must be positive")

    if rank_constant <= 0:
        raise ValueError("rank_constant must be positive")

    source_count = len(rankings)

    if source_count == 0:
        return ()

    passages: dict[
        str,
        object,
    ] = {}

    scores: dict[
        str,
        float,
    ] = {}

    ranks: dict[
        str,
        list[int | None],
    ] = {}

    for source_index, ranking in enumerate(rankings):
        seen_in_source = set()

        for rank, hit in enumerate(
            ranking,
            start=1,
        ):
            passage_id = _passage_id(hit)

            if passage_id in seen_in_source:
                continue

            seen_in_source.add(passage_id)

            passages.setdefault(
                passage_id,
                hit.passage,
            )

            scores[passage_id] = scores.get(
                passage_id,
                0.0,
            ) + (1.0 / (rank_constant + rank))

            source_ranks = ranks.setdefault(
                passage_id,
                [None] * source_count,
            )

            source_ranks[source_index] = rank

    ordered_ids = sorted(
        scores,
        key=lambda passage_id: (
            -scores[passage_id],
            passage_id,
        ),
    )

    return tuple(
        FusedHit(
            passage=passages[passage_id],
            score=scores[passage_id],
            source_ranks=tuple(ranks[passage_id]),
        )
        for passage_id in ordered_ids[:limit]
    )
