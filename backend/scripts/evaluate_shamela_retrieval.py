from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path

from basira.evaluation.shamela_retrieval import (
    ShamelaRetrievalBenchmark,
    evaluate_shamela_case,
    evaluate_shamela_suite,
    load_shamela_benchmark,
)
from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.retrieval.shamela_fts import (
    ShamelaFtsIndex,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Shamela retrieval against the frozen structural benchmark."
        )
    )

    parser.add_argument(
        "--cases",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--index",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--summary-only",
        action="store_true",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Validate benchmark gold against "
            "the governed corpus without "
            "executing retrieval queries."
        ),
    )

    return parser.parse_args()


def _file_sha256(
    path: Path,
) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tag_summaries(
    results,
):
    tags = sorted({tag for result in results for tag in result.tags})

    return {
        tag: asdict(
            evaluate_shamela_suite(
                tuple(result for result in results if tag in result.tags)
            )
        )
        for tag in tags
    }


def _validate_gold_against_index(
    benchmark: ShamelaRetrievalBenchmark,
    index: ShamelaFtsIndex,
) -> dict[str, int]:
    """
    Validate benchmark identity only.

    This does not execute retrieval and therefore
    may safely validate the frozen HOLDOUT schema
    and gold references without observing HOLDOUT
    retrieval performance.
    """

    stats = index.stats

    if stats.corpus_fingerprint != benchmark.corpus_fingerprint:
        raise ValueError("Benchmark corpus fingerprint does not match governed corpus")

    with sqlite3.connect(index.path) as connection:
        rows = connection.execute(
            """
            SELECT
                passage_id,
                work_id,
                madhhab,
                metadata_json
            FROM passages
            ORDER BY rowid
            """
        ).fetchall()

    catalog = []

    by_passage_id = {}

    for (
        passage_id,
        work_id,
        madhhab,
        metadata_json,
    ) in rows:
        metadata = json.loads(metadata_json)

        record = {
            "passage_id": str(passage_id),
            "book_id": str(work_id),
            "madhhab": (None if madhhab is None else str(madhhab)),
            "parent_text": (metadata.get("parent_text")),
            "parent_id": (metadata.get("structural_parent_id")),
        }

        catalog.append(record)

        by_passage_id[record["passage_id"]] = record

    gold_units = 0
    exact_passages = 0

    for case in benchmark.cases:
        for unit in case.gold_units:
            gold_units += 1

            if unit.structural_parent_id is None:
                raise ValueError(
                    f"{case.case_id}: gold unit is not pinned to structural_parent_id"
                )

            matches = [
                row
                for row in catalog
                if (
                    row["book_id"] == unit.book_id
                    and row["parent_id"] == unit.structural_parent_id
                    and (unit.madhhab is None or row["madhhab"] == unit.madhhab)
                )
            ]

            if not matches:
                raise ValueError(
                    f"{case.case_id}: structural gold parent does not exist"
                )

            parent_labels = {row["parent_text"] for row in matches}

            if unit.parent_text not in parent_labels:
                raise ValueError(
                    f"{case.case_id}: "
                    "parent_text label does not "
                    "match structural_parent_id"
                )

            for passage_id in unit.passage_ids:
                exact_passages += 1

                record = by_passage_id.get(passage_id)

                if record is None:
                    raise ValueError(
                        f"{case.case_id}: unknown exact passage {passage_id}"
                    )

                if (
                    record["book_id"] != unit.book_id
                    or record["parent_id"] != unit.structural_parent_id
                    or (unit.madhhab is not None and record["madhhab"] != unit.madhhab)
                ):
                    raise ValueError(
                        f"{case.case_id}: "
                        "exact passage does not "
                        "belong to its gold unit"
                    )

    return {
        "case_count": len(benchmark.cases),
        "gold_unit_count": (gold_units),
        "exact_passage_count": (exact_passages),
    }


def main() -> int:
    args = _parse_args()

    benchmark = load_shamela_benchmark(args.cases)

    index = ShamelaFtsIndex(args.index)

    validation = _validate_gold_against_index(
        benchmark,
        index,
    )

    if args.validate_only:
        print(
            json.dumps(
                {
                    "benchmark_id": (benchmark.benchmark_id),
                    "split": (benchmark.split),
                    "benchmark_sha256": (_file_sha256(args.cases)),
                    "corpus_fingerprint": (benchmark.corpus_fingerprint),
                    "gold_validation": (validation),
                    "retrieval_executed": (False),
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    stats = index.stats

    results = []

    for position, case in enumerate(
        benchmark.cases,
        start=1,
    ):
        limit = max(case.k_values)

        started = time.perf_counter_ns()

        hits = index.search(
            case.question,
            limit=limit,
            domains=(ScholarlyDomain.FIQH,),
        )

        ended = time.perf_counter_ns()

        latency_ms = (ended - started) / 1_000_000

        result = evaluate_shamela_case(
            case,
            hits,
            latency_ms=latency_ms,
        )

        results.append(result)

        if not args.summary_only:
            print(
                f"[{position}/"
                f"{len(benchmark.cases)}] "
                f"{case.case_id}: "
                f"rank="
                f"{result.first_relevant_rank} "
                f"rr="
                f"{result.reciprocal_rank:.3f} "
                f"parent@10="
                f"{result.parent_recall_at_k.get(10, 0.0):.3f} "
                f"latency="
                f"{latency_ms:.2f}ms"
            )

    summary = evaluate_shamela_suite(results)

    report = {
        "schema_version": 1,
        "benchmark_id": (benchmark.benchmark_id),
        "split": benchmark.split,
        "benchmark_sha256": (_file_sha256(args.cases)),
        "corpus_fingerprint": (stats.corpus_fingerprint),
        # This is the baseline FTS artifact recorded
        # when the benchmark was frozen. It is NOT a
        # compatibility constraint for future dense
        # or hybrid retrieval candidates.
        "baseline_index_fingerprint": (benchmark.index_fingerprint),
        # Fingerprint of the retriever artifact used
        # for this concrete run.
        "retriever_index_fingerprint": (stats.index_fingerprint),
        "index_stats": (asdict(stats)),
        "gold_validation": (validation),
        "summary": (asdict(summary)),
        "tag_summaries": (_tag_summaries(results)),
        "cases": [asdict(result) for result in results],
    }

    rendered = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    )

    if args.summary_only:
        print(
            json.dumps(
                {
                    "benchmark_id": (benchmark.benchmark_id),
                    "split": (benchmark.split),
                    "benchmark_sha256": (report["benchmark_sha256"]),
                    "summary": (report["summary"]),
                    "tag_summaries": (report["tag_summaries"]),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
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

        print()
        print(
            "Report written to",
            args.output,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
