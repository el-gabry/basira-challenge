from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from basira.evaluation.shamela_retrieval import (
    ShamelaGoldUnit,
    ShamelaRetrievalCase,
    evaluate_shamela_case,
    evaluate_shamela_suite,
    load_shamela_benchmark,
)


@dataclass
class FakePassage:
    passage_id: str
    work_id: str
    metadata: dict


@dataclass
class FakeHit:
    passage: FakePassage


def hit(
    *,
    passage_id: str,
    book_id: str,
    parent: str,
    madhhab: str,
    governed: bool = True,
) -> FakeHit:
    metadata = {
        "parent_text": parent,
        "madhhab": madhhab,
    }

    if governed:
        metadata.update(
            {
                "structural_parent_id": ("parent-1"),
                "source_locator": ("page:1"),
                "raw_text_sha256": ("a" * 64),
            }
        )

    return FakeHit(
        passage=FakePassage(
            passage_id=passage_id,
            work_id=book_id,
            metadata=metadata,
        )
    )


def comparative_case():
    return ShamelaRetrievalCase(
        case_id="case",
        question="أحكام المسألة",
        gold_units=(
            ShamelaGoldUnit(
                book_id="1",
                parent_text="باب المسألة",
                madhhab="hanafi",
            ),
            ShamelaGoldUnit(
                book_id="2",
                parent_text="فصل المسألة",
                madhhab="maliki",
            ),
        ),
        k_values=(
            1,
            5,
            10,
        ),
        tags=("comparative",),
    )


def test_parent_recall_does_not_reward_wrong_chapter():
    case = comparative_case()

    hits = (
        hit(
            passage_id="wrong",
            book_id="1",
            parent="المقدمة",
            madhhab="hanafi",
        ),
        hit(
            passage_id="right",
            book_id="2",
            parent="فصل المسألة",
            madhhab="maliki",
        ),
    )

    result = evaluate_shamela_case(
        case,
        hits,
        latency_ms=1.0,
    )

    assert result.book_recall_at_k[5] == 1.0

    assert result.madhhab_coverage_at_k[5] == 1.0

    assert result.parent_recall_at_k[5] == 0.5


def test_duplicate_passages_from_one_parent_do_not_fake_diversity():
    case = comparative_case()

    hits = (
        hit(
            passage_id="h1",
            book_id="1",
            parent="باب المسألة",
            madhhab="hanafi",
        ),
        hit(
            passage_id="h2",
            book_id="1",
            parent="باب المسألة",
            madhhab="hanafi",
        ),
    )

    result = evaluate_shamela_case(
        case,
        hits,
        latency_ms=1.0,
    )

    assert result.parent_recall_at_k[5] == 0.5

    assert result.madhhab_coverage_at_k[5] == 0.5

    assert result.ndcg_at_k[5] < 1.0


def test_exact_passage_recall_is_separate_from_parent_relevance():
    case = ShamelaRetrievalCase(
        case_id="exact",
        question="عبارة",
        gold_units=(
            ShamelaGoldUnit(
                book_id="1",
                parent_text="باب",
                madhhab="hanafi",
                passage_ids=("gold",),
            ),
        ),
        k_values=(
            1,
            5,
        ),
    )

    result = evaluate_shamela_case(
        case,
        (
            hit(
                passage_id="other",
                book_id="1",
                parent="باب",
                madhhab="hanafi",
            ),
            hit(
                passage_id="gold",
                book_id="1",
                parent="باب",
                madhhab="hanafi",
            ),
        ),
        latency_ms=2.0,
    )

    assert result.reciprocal_rank == 1.0

    assert result.parent_recall_at_k[1] == 1.0

    assert result.passage_recall_at_k[1] == 0.0

    assert result.passage_recall_at_k[5] == 1.0


def test_context_recovery_requires_governed_metadata():
    case = ShamelaRetrievalCase(
        case_id="context",
        question="مسألة",
        gold_units=(
            ShamelaGoldUnit(
                book_id="1",
                parent_text="باب",
                madhhab="hanafi",
            ),
        ),
        k_values=(1,),
    )

    result = evaluate_shamela_case(
        case,
        (
            hit(
                passage_id="x",
                book_id="1",
                parent="باب",
                madhhab="hanafi",
                governed=False,
            ),
        ),
        latency_ms=1.0,
    )

    assert result.parent_recall_at_k[1] == 1.0

    assert result.context_recovery_at_k[1] == 0.0


def test_suite_aggregates_latency_and_metrics():
    case = comparative_case()

    first = evaluate_shamela_case(
        case,
        (
            hit(
                passage_id="a",
                book_id="1",
                parent="باب المسألة",
                madhhab="hanafi",
            ),
        ),
        latency_ms=10.0,
    )

    second = evaluate_shamela_case(
        case,
        (
            hit(
                passage_id="b",
                book_id="2",
                parent="فصل المسألة",
                madhhab="maliki",
            ),
        ),
        latency_ms=20.0,
    )

    summary = evaluate_shamela_suite(
        (
            first,
            second,
        )
    )

    assert summary.case_count == 2

    assert summary.mean_latency_ms == pytest.approx(15.0)

    assert summary.p95_latency_ms == pytest.approx(20.0)


def test_loader_validates_fingerprints(
    tmp_path: Path,
):
    path = tmp_path / "benchmark.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "benchmark_id": "b",
                "split": "dev",
                "description": "test",
                "corpus_fingerprint": ("a" * 64),
                "index_fingerprint": ("b" * 64),
                "k_values": [
                    1,
                    5,
                ],
                "cases": [
                    {
                        "id": "c",
                        "question": "q",
                        "gold": [
                            {
                                "book_id": "1",
                                "parent_text": ("باب"),
                                "madhhab": ("hanafi"),
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    benchmark = load_shamela_benchmark(path)

    assert benchmark.corpus_fingerprint == "a" * 64

    assert benchmark.index_fingerprint == "b" * 64


def test_structural_parent_id_disambiguates_same_title():
    case = ShamelaRetrievalCase(
        case_id="structural-id",
        question="مسألة",
        gold_units=(
            ShamelaGoldUnit(
                book_id="1",
                parent_text="مدخل",
                structural_parent_id=("gold-parent"),
                madhhab="hanafi",
            ),
        ),
        k_values=(
            1,
            5,
        ),
    )

    wrong = FakeHit(
        passage=FakePassage(
            passage_id="wrong",
            work_id="1",
            metadata={
                "parent_text": "مدخل",
                "structural_parent_id": ("other-parent"),
                "madhhab": "hanafi",
                "source_locator": "page:1",
                "raw_text_sha256": ("a" * 64),
            },
        )
    )

    right = FakeHit(
        passage=FakePassage(
            passage_id="right",
            work_id="1",
            metadata={
                "parent_text": "مدخل",
                "structural_parent_id": ("gold-parent"),
                "madhhab": "hanafi",
                "source_locator": "page:2",
                "raw_text_sha256": ("b" * 64),
            },
        )
    )

    result = evaluate_shamela_case(
        case,
        (
            wrong,
            right,
        ),
        latency_ms=1.0,
    )

    assert result.first_relevant_rank == 2

    assert result.parent_recall_at_k[1] == 0.0

    assert result.parent_recall_at_k[5] == 1.0
