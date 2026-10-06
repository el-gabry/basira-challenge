from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean


def _domain_value(node: object) -> str | None:
    domain = getattr(node, "domain", None)
    if domain is None:
        return None

    value = getattr(domain, "value", domain)
    return str(value)


def _optional_text(node: object, attribute: str) -> str | None:
    value = getattr(node, attribute, None)
    if value is None:
        return None
    return str(value)


@dataclass(frozen=True, slots=True)
class EvidenceExpectation:
    """Gold relevance criterion for one expected evidence item."""

    domain: str | None = None
    reference: str | None = None
    source_id: str | None = None
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        if not any(
            (
                self.domain,
                self.reference,
                self.source_id,
                self.evidence_id,
            )
        ):
            raise ValueError(
                "EvidenceExpectation must constrain at least one evidence field."
            )

    def matches(self, node: object) -> bool:
        checks = (
            (self.domain, _domain_value(node)),
            (self.reference, _optional_text(node, "reference")),
            (self.source_id, _optional_text(node, "source_id")),
            (self.evidence_id, _optional_text(node, "evidence_id")),
        )

        return all(
            expected is None or actual == expected
            for expected, actual in checks
        )


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    case_id: str
    question: str
    expectations: tuple[EvidenceExpectation, ...]
    k_values: tuple[int, ...] = (1, 3, 5, 10)
    relevance_mode: str = "all"
    tags: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id must not be empty.")

        if not self.question.strip():
            raise ValueError("question must not be empty.")

        if not self.expectations:
            raise ValueError(
                f"{self.case_id}: at least one expectation is required."
            )

        if self.relevance_mode not in {"all", "any"}:
            raise ValueError(
                f"{self.case_id}: relevance_mode must be all or any."
            )

        if not self.k_values:
            raise ValueError(
                f"{self.case_id}: at least one k value is required."
            )

        if any(value <= 0 for value in self.k_values):
            raise ValueError(
                f"{self.case_id}: k values must be positive."
            )

        if tuple(sorted(set(self.k_values))) != self.k_values:
            raise ValueError(
                f"{self.case_id}: k values must be unique and sorted."
            )


@dataclass(frozen=True, slots=True)
class CaseRetrievalMetrics:
    case_id: str
    question: str
    tags: tuple[str, ...]
    retrieved_count: int
    expected_count: int
    matched_count: int
    first_relevant_rank: int | None
    reciprocal_rank: float
    hit_at_k: dict[int, bool]
    recall_at_k: dict[int, float]
    source_coverage_at_k: dict[int, float | None]
    unique_sources_at_k: dict[int, int]


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationSummary:
    case_count: int
    mean_reciprocal_rank: float
    hit_rate_at_k: dict[int, float]
    mean_recall_at_k: dict[int, float]
    mean_source_coverage_at_k: dict[int, float | None]
    mean_unique_sources_at_k: dict[int, float]
    exact_anchor_top1_accuracy: float | None


def _first_relevant_rank(
    expectations: Sequence[EvidenceExpectation],
    nodes: Sequence[object],
) -> int | None:
    for index, node in enumerate(nodes, start=1):
        if any(expectation.matches(node) for expectation in expectations):
            return index
    return None


def _matched_expectation_count(
    expectations: Sequence[EvidenceExpectation],
    nodes: Sequence[object],
    *,
    relevance_mode: str,
) -> int:
    if relevance_mode == "any":
        return int(
            any(
                expectation.matches(node)
                for expectation in expectations
                for node in nodes
            )
        )

    return sum(
        1
        for expectation in expectations
        if any(expectation.matches(node) for node in nodes)
    )


def _expected_sources(
    expectations: Sequence[EvidenceExpectation],
) -> set[str]:
    return {
        expectation.source_id
        for expectation in expectations
        if expectation.source_id is not None
    }


def _source_coverage(
    expectations: Sequence[EvidenceExpectation],
    nodes: Sequence[object],
) -> float | None:
    expected_sources = _expected_sources(expectations)

    if not expected_sources:
        return None

    retrieved_sources = {
        source_id
        for node in nodes
        if (source_id := _optional_text(node, "source_id")) is not None
    }

    return len(expected_sources & retrieved_sources) / len(expected_sources)


def _unique_source_count(nodes: Sequence[object]) -> int:
    return len(
        {
            source_id
            for node in nodes
            if (source_id := _optional_text(node, "source_id")) is not None
        }
    )


def _mean_optional(values: Iterable[float | None]) -> float | None:
    applicable = tuple(value for value in values if value is not None)
    if not applicable:
        return None
    return fmean(applicable)


def evaluate_case(
    case: RetrievalEvaluationCase,
    nodes: Iterable[object],
) -> CaseRetrievalMetrics:
    ranked_nodes = tuple(nodes)
    expected_count = (
        1
        if case.relevance_mode == "any"
        else len(case.expectations)
    )

    first_rank = _first_relevant_rank(
        case.expectations,
        ranked_nodes,
    )

    hit_at_k: dict[int, bool] = {}
    recall_at_k: dict[int, float] = {}
    source_coverage_at_k: dict[int, float | None] = {}
    unique_sources_at_k: dict[int, int] = {}

    for k_value in case.k_values:
        top_k = ranked_nodes[:k_value]
        matched = _matched_expectation_count(
            case.expectations,
            top_k,
            relevance_mode=case.relevance_mode,
        )

        hit_at_k[k_value] = matched > 0
        recall_at_k[k_value] = matched / expected_count
        source_coverage_at_k[k_value] = _source_coverage(
            case.expectations,
            top_k,
        )
        unique_sources_at_k[k_value] = _unique_source_count(top_k)

    return CaseRetrievalMetrics(
        case_id=case.case_id,
        question=case.question,
        tags=case.tags,
        retrieved_count=len(ranked_nodes),
        expected_count=expected_count,
        matched_count=_matched_expectation_count(
            case.expectations,
            ranked_nodes,
            relevance_mode=case.relevance_mode,
        ),
        first_relevant_rank=first_rank,
        reciprocal_rank=(
            0.0
            if first_rank is None
            else 1.0 / first_rank
        ),
        hit_at_k=hit_at_k,
        recall_at_k=recall_at_k,
        source_coverage_at_k=source_coverage_at_k,
        unique_sources_at_k=unique_sources_at_k,
    )


def evaluate_suite(
    metrics: Iterable[CaseRetrievalMetrics],
) -> RetrievalEvaluationSummary:
    results = tuple(metrics)

    if not results:
        raise ValueError("At least one evaluation result is required.")

    k_values = tuple(results[0].hit_at_k)

    if any(tuple(result.hit_at_k) != k_values for result in results):
        raise ValueError(
            "All evaluation cases must use the same k values for aggregation."
        )

    exact_anchor_results = tuple(
        result
        for result in results
        if "exact_anchor" in result.tags
    )

    exact_anchor_top1_accuracy: float | None = None
    if exact_anchor_results and all(
        1 in result.hit_at_k
        for result in exact_anchor_results
    ):
        exact_anchor_top1_accuracy = fmean(
            1.0 if result.hit_at_k[1] else 0.0
            for result in exact_anchor_results
        )

    return RetrievalEvaluationSummary(
        case_count=len(results),
        mean_reciprocal_rank=fmean(
            result.reciprocal_rank
            for result in results
        ),
        hit_rate_at_k={
            k_value: fmean(
                1.0 if result.hit_at_k[k_value] else 0.0
                for result in results
            )
            for k_value in k_values
        },
        mean_recall_at_k={
            k_value: fmean(
                result.recall_at_k[k_value]
                for result in results
            )
            for k_value in k_values
        },
        mean_source_coverage_at_k={
            k_value: _mean_optional(
                result.source_coverage_at_k[k_value]
                for result in results
            )
            for k_value in k_values
        },
        mean_unique_sources_at_k={
            k_value: fmean(
                result.unique_sources_at_k[k_value]
                for result in results
            )
            for k_value in k_values
        },
        exact_anchor_top1_accuracy=exact_anchor_top1_accuracy,
    )


def load_evaluation_cases(
    path: str | Path,
) -> tuple[RetrievalEvaluationCase, ...]:
    document = json.loads(
        Path(path).read_text(encoding="utf-8")
    )

    raw_cases = document.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError(
            "Evaluation document must contain a cases list."
        )

    cases: list[RetrievalEvaluationCase] = []
    seen_ids: set[str] = set()

    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise ValueError(
                "Each evaluation case must be an object."
            )

        case_id = str(raw_case["id"])

        if case_id in seen_ids:
            raise ValueError(
                f"Duplicate evaluation case id: {case_id}"
            )
        seen_ids.add(case_id)

        raw_expectations = raw_case.get("expectations", [])
        expectations = tuple(
            EvidenceExpectation(
                domain=expectation.get("domain"),
                reference=expectation.get("reference"),
                source_id=expectation.get("source_id"),
                evidence_id=expectation.get("evidence_id"),
            )
            for expectation in raw_expectations
        )

        k_values = tuple(
            int(value)
            for value in raw_case.get(
                "k_values",
                (1, 3, 5, 10),
            )
        )

        cases.append(
            RetrievalEvaluationCase(
                case_id=case_id,
                question=str(raw_case["question"]),
                expectations=expectations,
                k_values=k_values,
                relevance_mode=str(
                    raw_case.get("relevance_mode", "all")
                ),
                tags=tuple(
                    str(tag)
                    for tag in raw_case.get("tags", ())
                ),
                notes=(
                    None
                    if raw_case.get("notes") is None
                    else str(raw_case["notes"])
                ),
            )
        )

    if not cases:
        raise ValueError(
            "Evaluation document contains no cases."
        )

    return tuple(cases)
