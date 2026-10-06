from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from basira.evaluation.retrieval import (
    EvidenceExpectation,
    RetrievalEvaluationCase,
    evaluate_case,
    evaluate_suite,
    load_evaluation_cases,
)


@dataclass(frozen=True)
class FakeNode:
    domain: str
    reference: str
    source_id: str
    evidence_id: str


def _node(
    *,
    domain: str = "tafsir",
    reference: str,
    source_id: str = "source-a",
) -> FakeNode:
    return FakeNode(
        domain=domain,
        reference=reference,
        source_id=source_id,
        evidence_id=f"{source_id}:{reference}",
    )


def test_expectation_matches_only_constrained_fields() -> None:
    expectation = EvidenceExpectation(
        domain="tafsir",
        reference="2:255",
        source_id="source-a",
    )

    assert expectation.matches(
        _node(
            reference="2:255",
            source_id="source-a",
        )
    )
    assert not expectation.matches(
        _node(
            reference="2:255",
            source_id="source-b",
        )
    )


def test_evaluate_case_reports_rank_recall_and_source_coverage() -> None:
    case = RetrievalEvaluationCase(
        case_id="anchor",
        question="question",
        expectations=(
            EvidenceExpectation(
                domain="tafsir",
                reference="2:255",
                source_id="source-a",
            ),
            EvidenceExpectation(
                domain="tafsir",
                reference="2:255",
                source_id="source-b",
            ),
        ),
        k_values=(1, 2, 3),
        tags=("exact_anchor",),
    )

    result = evaluate_case(
        case,
        (
            _node(
                reference="1:1",
                source_id="source-z",
            ),
            _node(
                reference="2:255",
                source_id="source-a",
            ),
            _node(
                reference="2:255",
                source_id="source-b",
            ),
        ),
    )

    assert result.first_relevant_rank == 2
    assert result.reciprocal_rank == pytest.approx(0.5)
    assert result.hit_at_k == {
        1: False,
        2: True,
        3: True,
    }
    assert result.recall_at_k == {
        1: 0.0,
        2: 0.5,
        3: 1.0,
    }
    assert result.source_coverage_at_k == {
        1: 0.0,
        2: 0.5,
        3: 1.0,
    }
    assert result.unique_sources_at_k == {
        1: 1,
        2: 2,
        3: 3,
    }


def test_source_coverage_is_not_applicable_without_expected_sources() -> None:
    case = RetrievalEvaluationCase(
        case_id="no-source-gold",
        question="question",
        expectations=(
            EvidenceExpectation(
                domain="tafsir",
                reference="2:153",
            ),
        ),
        k_values=(1, 3),
    )

    result = evaluate_case(
        case,
        (
            _node(reference="1:1"),
            _node(reference="2:153"),
        ),
    )

    assert result.source_coverage_at_k == {
        1: None,
        3: None,
    }


def test_any_relevance_mode_accepts_one_of_multiple_gold_references() -> None:
    case = RetrievalEvaluationCase(
        case_id="concept-any",
        question="question",
        expectations=(
            EvidenceExpectation(reference="2:153"),
            EvidenceExpectation(reference="3:200"),
        ),
        k_values=(1, 3),
        relevance_mode="any",
    )

    result = evaluate_case(
        case,
        (
            _node(reference="1:1"),
            _node(reference="3:200"),
        ),
    )

    assert result.expected_count == 1
    assert result.matched_count == 1
    assert result.first_relevant_rank == 2
    assert result.reciprocal_rank == pytest.approx(0.5)
    assert result.recall_at_k == {
        1: 0.0,
        3: 1.0,
    }


def test_evaluate_case_returns_zero_metrics_when_gold_is_missing() -> None:
    case = RetrievalEvaluationCase(
        case_id="missing",
        question="question",
        expectations=(
            EvidenceExpectation(
                domain="tafsir",
                reference="2:153",
            ),
        ),
        k_values=(1, 3),
    )

    result = evaluate_case(
        case,
        (
            _node(reference="1:1"),
            _node(reference="1:2"),
        ),
    )

    assert result.first_relevant_rank is None
    assert result.reciprocal_rank == 0.0
    assert result.hit_at_k == {
        1: False,
        3: False,
    }
    assert result.recall_at_k == {
        1: 0.0,
        3: 0.0,
    }
    assert result.source_coverage_at_k == {
        1: None,
        3: None,
    }


def test_evaluate_suite_aggregates_metrics_and_exact_anchor_accuracy() -> None:
    exact_case = RetrievalEvaluationCase(
        case_id="exact",
        question="question",
        expectations=(
            EvidenceExpectation(
                reference="2:255",
            ),
        ),
        k_values=(1, 3),
        tags=("exact_anchor",),
    )
    conceptual_case = RetrievalEvaluationCase(
        case_id="concept",
        question="question",
        expectations=(
            EvidenceExpectation(
                reference="2:153",
            ),
        ),
        k_values=(1, 3),
    )

    exact_result = evaluate_case(
        exact_case,
        (_node(reference="2:255"),),
    )
    conceptual_result = evaluate_case(
        conceptual_case,
        (
            _node(reference="1:1"),
            _node(reference="2:153"),
        ),
    )

    summary = evaluate_suite(
        (
            exact_result,
            conceptual_result,
        )
    )

    assert summary.case_count == 2
    assert summary.mean_reciprocal_rank == pytest.approx(0.75)
    assert summary.hit_rate_at_k[1] == pytest.approx(0.5)
    assert summary.hit_rate_at_k[3] == pytest.approx(1.0)
    assert summary.mean_recall_at_k[3] == pytest.approx(1.0)
    assert summary.mean_source_coverage_at_k[1] is None
    assert summary.mean_source_coverage_at_k[3] is None
    assert summary.exact_anchor_top1_accuracy == pytest.approx(1.0)


def test_evaluate_suite_ignores_not_applicable_source_coverage() -> None:
    source_case = RetrievalEvaluationCase(
        case_id="with-source",
        question="question",
        expectations=(
            EvidenceExpectation(
                reference="2:255",
                source_id="source-a",
            ),
        ),
        k_values=(1,),
    )
    no_source_case = RetrievalEvaluationCase(
        case_id="without-source",
        question="question",
        expectations=(
            EvidenceExpectation(reference="2:153"),
        ),
        k_values=(1,),
    )

    source_result = evaluate_case(
        source_case,
        (_node(reference="2:255", source_id="source-a"),),
    )
    no_source_result = evaluate_case(
        no_source_case,
        (_node(reference="2:153", source_id="source-b"),),
    )

    summary = evaluate_suite(
        (
            source_result,
            no_source_result,
        )
    )

    assert summary.mean_source_coverage_at_k[1] == pytest.approx(1.0)


def test_load_evaluation_cases_parses_json_and_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "one",
                        "question": "q",
                        "k_values": [1, 3],
                        "relevance_mode": "any",
                        "expectations": [
                            {
                                "domain": "quran",
                                "reference": "2:255",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    cases = load_evaluation_cases(path)

    assert len(cases) == 1
    assert cases[0].case_id == "one"
    assert cases[0].k_values == (1, 3)
    assert cases[0].relevance_mode == "any"

    path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "dup",
                        "question": "q1",
                        "expectations": [
                            {"reference": "1:1"}
                        ],
                    },
                    {
                        "id": "dup",
                        "question": "q2",
                        "expectations": [
                            {"reference": "1:2"}
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate evaluation case id",
    ):
        load_evaluation_cases(path)


def test_relevance_mode_must_be_supported() -> None:
    with pytest.raises(
        ValueError,
        match="relevance_mode must be all or any",
    ):
        RetrievalEvaluationCase(
            case_id="bad-mode",
            question="question",
            expectations=(
                EvidenceExpectation(reference="2:153"),
            ),
            relevance_mode="unsupported",
        )
