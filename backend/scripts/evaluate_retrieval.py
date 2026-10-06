from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from basira.api.service import build_default_query_service
from basira.evaluation.retrieval import (
    CaseRetrievalMetrics,
    RetrievalEvaluationCase,
    evaluate_case,
    evaluate_suite,
    load_evaluation_cases,
)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Basira retrieval evaluation against the configured production corpora."
        )
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("evaluation/retrieval_baseline_v1.json"),
        help="Path to the evaluation case JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path for the JSON evaluation report.",
    )
    parser.add_argument(
        "--candidate-k",
        type=_positive_int,
        default=10,
        help=(
            "Diagnostic candidate depth per retrieval domain. "
            "Production behavior remains unchanged; values above 10 "
            "re-run the already-built retrieval plan for evaluation only."
        ),
    )
    return parser.parse_args()


def _domain_value(node: object) -> str | None:
    domain = getattr(node, "domain", None)
    if domain is None:
        return None

    value = getattr(domain, "value", domain)
    return str(value)


def _query_type(tags: tuple[str, ...]) -> str:
    tag_set = set(tags)

    if "exact_anchor" in tag_set:
        return "exact_anchor"

    if "arabic_paraphrase" in tag_set:
        return "arabic_paraphrase"

    if "english" in tag_set or "cross_lingual" in tag_set:
        return "english_cross_lingual"

    if "conceptual" in tag_set and "arabic" in tag_set:
        return "arabic_direct"

    return "other"


def _role_filtered_evidence(
    case: RetrievalEvaluationCase,
    nodes: Iterable[object],
) -> tuple[object, ...]:
    expected_domains = {
        expectation.domain
        for expectation in case.expectations
        if expectation.domain is not None
    }

    ranked_nodes = tuple(nodes)

    if not expected_domains:
        return ranked_nodes

    return tuple(
        node for node in ranked_nodes if _domain_value(node) in expected_domains
    )


def _summaries_by_query_type(
    results: Iterable[CaseRetrievalMetrics],
) -> dict[str, object]:
    metrics = tuple(results)

    query_types = sorted({_query_type(result.tags) for result in metrics})

    return {
        query_type: asdict(
            evaluate_suite(
                result for result in metrics if _query_type(result.tags) == query_type
            )
        )
        for query_type in query_types
    }


def main() -> int:
    args = _parse_args()
    cases = load_evaluation_cases(args.cases)

    largest_requested_k = max(max(case.k_values) for case in cases)

    if args.candidate_k < largest_requested_k:
        raise SystemExit(
            "--candidate-k must be at least the largest "
            f"evaluation k ({largest_requested_k})."
        )

    print(
        (f"Loading Basira query service for {len(cases)} evaluation cases..."),
        flush=True,
    )
    print(
        f"Diagnostic candidate depth per domain: {args.candidate_k}",
        flush=True,
    )

    service = build_default_query_service()

    results: list[CaseRetrievalMetrics] = []
    role_results: list[CaseRetrievalMetrics] = []
    case_reports: list[dict[str, object]] = []

    for index, case in enumerate(cases, start=1):
        print(
            f"[{index}/{len(cases)}] {case.case_id}: {case.question}",
            flush=True,
        )

        execution = service.execute(question=case.question)

        retrieval = execution.retrieval

        if args.candidate_k != 10:
            retrieval = service.retriever.retrieve(
                plan=execution.retrieval.plan,
                limit_per_domain=args.candidate_k,
            )

        result = evaluate_case(
            case,
            retrieval.evidence,
        )

        role_result = evaluate_case(
            case,
            _role_filtered_evidence(
                case,
                retrieval.evidence,
            ),
        )

        results.append(result)
        role_results.append(role_result)

        query_type = _query_type(case.tags)

        largest_k = max(case.k_values)

        print(
            "  "
            f"type={query_type} "
            f"global_rank={result.first_relevant_rank} "
            f"role_rank={role_result.first_relevant_rank} "
            f"mrr={role_result.reciprocal_rank:.3f} "
            f"recall@{largest_k}="
            f"{role_result.recall_at_k[largest_k]:.3f}",
            flush=True,
        )

        case_report = asdict(result)
        case_report["query_type"] = query_type
        case_report["role_filtered"] = asdict(role_result)
        case_reports.append(case_report)

    summary = evaluate_suite(results)
    role_summary = evaluate_suite(role_results)

    report = {
        "cases_file": str(args.cases),
        "candidate_k_per_domain": args.candidate_k,
        "summary": asdict(summary),
        "role_filtered_summary": asdict(role_summary),
        "query_type_summaries": (_summaries_by_query_type(results)),
        "role_filtered_query_type_summaries": (_summaries_by_query_type(role_results)),
        "cases": case_reports,
    }

    rendered = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    )

    print()
    print(rendered)

    if args.output is not None:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            rendered + "\n",
            encoding="utf-8",
        )
        print(
            f"\nReport written to {args.output}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
