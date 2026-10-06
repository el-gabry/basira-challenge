from __future__ import annotations

import hashlib
import json
import os
import runpy
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from basira.evaluation.shamela_retrieval import (
    evaluate_shamela_case,
    evaluate_shamela_suite,
    load_shamela_benchmark,
)
from basira.models.scholarly import ScholarlyDomain
from basira.retrieval.shamela_fts import ShamelaFtsIndex

EXPECTED_HOLDOUT_SHA = (
    "3675d10602e315d39438d0c8f2837bbe8c30ebe510fabe285ad89871d8fa6acd"
)

EXPECTED_ARTIFACT_SHA = (
    "b2cd375e2e8f21022118348a0a066f16083e163b66e0a9f501a3383e5574f7fd"
)

RESULT_LIMIT = 50


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def tag_summaries(results):
    tags = sorted({tag for result in results for tag in result.tags})

    return {
        tag: asdict(
            evaluate_shamela_suite(
                tuple(result for result in results if tag in result.tags)
            )
        )
        for tag in tags
    }


def make_report(
    *,
    benchmark,
    benchmark_path,
    results,
    retriever,
    metadata,
):
    return {
        "schema_version": 1,
        "benchmark_id": (benchmark.benchmark_id),
        "split": benchmark.split,
        "benchmark_sha256": (sha256_file(benchmark_path)),
        "corpus_fingerprint": (benchmark.corpus_fingerprint),
        "retriever": retriever,
        "retriever_metadata": metadata,
        "summary": asdict(evaluate_shamela_suite(results)),
        "tag_summaries": (tag_summaries(results)),
        "cases": [asdict(result) for result in results],
    }


def metric(
    report,
    field,
    *,
    k=None,
    tag=None,
):
    data = report["summary"] if tag is None else report["tag_summaries"][tag]

    value = data[field]

    if k is not None:
        if k in value:
            value = value[k]
        elif str(k) in value:
            value = value[str(k)]
        else:
            raise KeyError(f"Metric k={k} not present; available={tuple(value.keys())}")

    return float(value)


def evaluate_fts(
    benchmark,
    index,
):
    results = []

    for case in benchmark.cases:
        started = time.perf_counter_ns()

        hits = index.search(
            case.question,
            limit=max(case.k_values),
            domains=(ScholarlyDomain.FIQH,),
        )

        latency_ms = (time.perf_counter_ns() - started) / 1_000_000

        results.append(
            evaluate_shamela_case(
                case,
                hits,
                latency_ms=latency_ms,
            )
        )

    return tuple(results)


def main():
    repo = Path.cwd()

    root = Path(os.environ["BASIRA_SHAMELA_ROOT"])

    holdout_path = repo / "evaluation" / "shamela_retrieval_holdout_v1.json"

    if sha256_file(holdout_path) != EXPECTED_HOLDOUT_SHA:
        raise SystemExit("Frozen HOLDOUT hash mismatch")

    selection = load_json(
        repo / "evaluation" / "results" / "shamela_dense_candidate_selection_v1.json"
    )

    if selection["selected_candidate"] != "DENSE_ONLY":
        raise SystemExit("Frozen candidate is not DENSE_ONLY")

    if selection["holdout_used"] is not False:
        raise SystemExit("Candidate selection was not DEV-only")

    dense_dev = load_json(
        repo / "evaluation" / "results" / "shamela_dense_e5small_dev_v1.json"
    )

    dense_metadata = dense_dev["retriever_metadata"]

    artifact_path = root / "indexes" / "r3b6-e5-small-v1" / "dense_embeddings.npz"

    artifact_sha = sha256_file(artifact_path)

    if artifact_sha != EXPECTED_ARTIFACT_SHA:
        raise SystemExit("Frozen dense artifact hash mismatch")

    db_path = root / "indexes" / "r3b3-shamela-fts.sqlite3"

    benchmark = load_shamela_benchmark(holdout_path)

    if benchmark.split != "holdout":
        raise SystemExit("Expected frozen HOLDOUT split")

    fts = ShamelaFtsIndex(db_path)

    if fts.stats.corpus_fingerprint != benchmark.corpus_fingerprint:
        raise SystemExit("Corpus fingerprint mismatch")

    # Reuse the exact frozen DEV dense representation
    # and search implementation. Do not alter candidate
    # logic for HOLDOUT.
    frozen = runpy.run_path(str(repo / "scripts" / "evaluate_shamela_dense_dev.py"))

    load_passages = frozen["_load_passages"]

    build_dense_windows = frozen["_build_dense_windows"]

    dense_search = frozen["_dense_search"]

    revision = dense_metadata["model_revision"]

    snapshot = (
        Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / "models--intfloat--multilingual-e5-small"
        / "snapshots"
        / revision
    )

    if not snapshot.is_dir():
        raise SystemExit("Frozen model snapshot not found")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = SentenceTransformer(
        str(snapshot),
        device=device,
    )

    passages = load_passages(db_path)

    windows = build_dense_windows(
        passages,
        tokenizer=model.tokenizer,
    )

    artifact = np.load(artifact_path)

    embeddings = artifact["embeddings"]

    stored_window_ids = [str(value) for value in artifact["window_ids"]]

    rebuilt_window_ids = [window["window_id"] for window in windows]

    if stored_window_ids != rebuilt_window_ids:
        raise SystemExit("Frozen dense window identity mismatch")

    stored_passage_ids = [str(value) for value in artifact["passage_ids"]]

    rebuilt_passage_ids = [window["passage"].passage_id for window in windows]

    if stored_passage_ids != rebuilt_passage_ids:
        raise SystemExit("Frozen dense passage identity mismatch")

    if embeddings.shape[0] != len(windows):
        raise SystemExit("Dense embedding/window count mismatch")

    # Everything above is preflight.
    # HOLDOUT retrieval starts below this line.

    print()
    print("============================================")
    print("HOLDOUT RETRIEVAL STARTS NOW — ONE SHOT")
    print("============================================")

    fts_results = evaluate_fts(
        benchmark,
        fts,
    )

    dense_results = []

    for case in benchmark.cases:
        hits, latency_ms = dense_search(
            model=model,
            embeddings=embeddings,
            windows=windows,
            question=case.question,
            limit=max(case.k_values),
        )

        dense_results.append(
            evaluate_shamela_case(
                case,
                hits,
                latency_ms=latency_ms,
            )
        )

    dense_results = tuple(dense_results)

    fts_report = make_report(
        benchmark=benchmark,
        benchmark_path=holdout_path,
        results=fts_results,
        retriever=("fts5-frozen-baseline"),
        metadata={
            "index_fingerprint": (fts.stats.index_fingerprint),
            "corpus_fingerprint": (fts.stats.corpus_fingerprint),
            "pre_holdout_tag": ("shamela-dense-v1-pre-holdout"),
        },
    )

    dense_report = make_report(
        benchmark=benchmark,
        benchmark_path=holdout_path,
        results=dense_results,
        retriever=("multilingual-e5-small"),
        metadata={
            **dense_metadata,
            "artifact_sha256": (artifact_sha),
            "pre_holdout_tag": ("shamela-dense-v1-pre-holdout"),
            "candidate_frozen_before_holdout": (True),
        },
    )

    result_dir = repo / "evaluation" / "results"

    fts_path = result_dir / "shamela_fts_holdout_v1_baseline.json"

    dense_path = result_dir / "shamela_dense_e5small_holdout_v1.json"

    # Predeclared before seeing HOLDOUT results.
    fields = {
        "overall_parent_at_10": (
            "mean_parent_recall_at_k",
            10,
            None,
        ),
        "ndcg_at_10": (
            "mean_ndcg_at_k",
            10,
            None,
        ),
        "mrr": (
            "mean_reciprocal_rank",
            None,
            None,
        ),
    }

    comparison = {}

    for name, (
        field,
        k,
        tag,
    ) in fields.items():
        baseline_value = metric(
            fts_report,
            field,
            k=k,
            tag=tag,
        )

        dense_value = metric(
            dense_report,
            field,
            k=k,
            tag=tag,
        )

        comparison[name] = {
            "fts": baseline_value,
            "dense": dense_value,
            "delta": (dense_value - baseline_value),
        }

    # Add tag metrics only when the frozen HOLDOUT
    # actually contains that tag.
    for tag in (
        "comparative",
        "paraphrase",
        "direct",
        "exact_phrase",
        "single_madhhab",
    ):
        if (
            tag not in fts_report["tag_summaries"]
            or tag not in dense_report["tag_summaries"]
        ):
            continue

        key = f"{tag}_parent_at_10"

        baseline_value = metric(
            fts_report,
            "mean_parent_recall_at_k",
            k=10,
            tag=tag,
        )

        dense_value = metric(
            dense_report,
            "mean_parent_recall_at_k",
            k=10,
            tag=tag,
        )

        comparison[key] = {
            "fts": baseline_value,
            "dense": dense_value,
            "delta": (dense_value - baseline_value),
        }

    # Final validation criteria were fixed before
    # reading the HOLDOUT results:
    #
    # 1. primary structural Parent@10 cannot regress;
    # 2. nDCG@10 may not regress by >0.05;
    # 3. MRR may not regress by >0.10;
    # 4. comparative Parent@10 cannot regress if the
    #    HOLDOUT contains comparative cases.
    criteria = {
        "overall_parent_not_worse": (
            comparison["overall_parent_at_10"]["delta"] >= 0.0
        ),
        "ndcg_regression_within_0_05": (comparison["ndcg_at_10"]["delta"] >= -0.05),
        "mrr_regression_within_0_10": (comparison["mrr"]["delta"] >= -0.10),
    }

    if "comparative_parent_at_10" in comparison:
        criteria["comparative_parent_not_worse"] = (
            comparison["comparative_parent_at_10"]["delta"] >= 0.0
        )

    validation_passed = all(criteria.values())

    decision = {
        "schema_version": 1,
        "holdout_opened": True,
        "holdout_sha256": (EXPECTED_HOLDOUT_SHA),
        "pre_holdout_tag": ("shamela-dense-v1-pre-holdout"),
        "pre_holdout_commit": ("ffb7ae0"),
        "selected_candidate_before_holdout": ("DENSE_ONLY"),
        "artifact_sha256": (artifact_sha),
        "criteria_predeclared": (True),
        "comparison": (comparison),
        "criteria": criteria,
        "validation": ("PASS" if validation_passed else "FAIL"),
        "post_holdout_tuning_allowed": (False),
        "note": (
            "This is frozen retrieval evaluation. "
            "Metrics measure structural retrieval "
            "relevance/coverage, not semantic "
            "entailment, religious truth, or source "
            "authority."
        ),
    }

    decision_path = result_dir / "shamela_dense_holdout_validation_v1.json"

    # Write all outputs only after both frozen
    # retrievers finish.
    write_json(
        fts_path,
        fts_report,
    )

    write_json(
        dense_path,
        dense_report,
    )

    write_json(
        decision_path,
        decision,
    )

    print()
    print("============================================")
    print("FROZEN HOLDOUT RESULTS")
    print("============================================")

    for name, values in comparison.items():
        print()
        print(name)
        print(
            "  FTS   =",
            round(
                values["fts"],
                4,
            ),
        )
        print(
            "  Dense =",
            round(
                values["dense"],
                4,
            ),
        )
        print(
            "  delta =",
            round(
                values["delta"],
                4,
            ),
        )

    print()
    print("Criteria:")

    for name, passed in criteria.items():
        print(
            f"  {name:38}",
            "PASS" if passed else "FAIL",
        )

    print()
    print(
        "FINAL HOLDOUT VALIDATION =",
        decision["validation"],
    )

    print()
    print("POST-HOLDOUT TUNING = FORBIDDEN")


if __name__ == "__main__":
    main()
