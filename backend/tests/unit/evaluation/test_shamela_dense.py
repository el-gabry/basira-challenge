from __future__ import annotations

from dataclasses import dataclass

from basira.evaluation.shamela_dense import (
    reciprocal_rank_fusion,
)


@dataclass
class Passage:
    passage_id: str


@dataclass
class Hit:
    passage: Passage


def _hit(
    passage_id: str,
) -> Hit:
    return Hit(Passage(passage_id))


def test_rrf_rewards_cross_retriever_agreement():
    fused = reciprocal_rank_fusion(
        (
            (
                _hit("a"),
                _hit("b"),
            ),
            (
                _hit("b"),
                _hit("c"),
            ),
        ),
        limit=3,
        rank_constant=60,
    )

    assert fused[0].passage.passage_id == "b"

    assert fused[0].source_ranks == (
        2,
        1,
    )


def test_rrf_collapses_duplicate_passages_per_source():
    fused = reciprocal_rank_fusion(
        (
            (
                _hit("a"),
                _hit("a"),
                _hit("b"),
            ),
        ),
        limit=5,
    )

    assert [hit.passage.passage_id for hit in fused] == [
        "a",
        "b",
    ]


def test_rrf_is_deterministic_on_score_tie():
    fused = reciprocal_rank_fusion(
        (
            (_hit("b"),),
            (_hit("a"),),
        ),
        limit=2,
    )

    assert [hit.passage.passage_id for hit in fused] == [
        "a",
        "b",
    ]
