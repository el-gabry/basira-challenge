from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import (
    snapshot_download,
)
from sentence_transformers import (
    SentenceTransformer,
)

from basira.evaluation.shamela_dense import (
    DenseHit,
    DensePassage,
    reciprocal_rank_fusion,
)
from basira.evaluation.shamela_retrieval import (
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

MODEL_ID = "intfloat/multilingual-e5-small"

RANK_CONSTANT = 60

RESULT_LIMIT = 50

BODY_WINDOW_TOKENS = 320
BODY_WINDOW_OVERLAP = 64


def _sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def _benchmark_sha(
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


def _report(
    *,
    benchmark,
    benchmark_path,
    results,
    retriever_name,
    metadata,
):
    summary = evaluate_shamela_suite(results)

    return {
        "schema_version": 1,
        "benchmark_id": (benchmark.benchmark_id),
        "split": benchmark.split,
        "benchmark_sha256": (_benchmark_sha(benchmark_path)),
        "corpus_fingerprint": (benchmark.corpus_fingerprint),
        "retriever": (retriever_name),
        "retriever_metadata": (metadata),
        "summary": (asdict(summary)),
        "tag_summaries": (_tag_summaries(results)),
        "cases": [asdict(result) for result in results],
    }


def _write_json(
    path: Path,
    value,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _parent_text(
    metadata: dict,
) -> str:
    return str(metadata.get("parent_text") or "").strip()


def _structural_prefix(
    row,
    metadata,
) -> str:
    values = (
        row["work_title"],
        _parent_text(metadata),
        row["section_title"],
        row["chapter_title"],
        row["volume"],
        row["madhhab"],
        row["author_name"],
    )

    return " | ".join(
        str(value).strip()
        for value in values
        if (value is not None and str(value).strip())
    )


def _load_passages(
    db_path: Path,
):
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT
                rowid,
                passage_id,
                work_id,
                work_title,
                author_name,
                section_title,
                chapter_title,
                volume,
                page,
                madhhab,
                raw_text,
                metadata_json
            FROM passages
            ORDER BY rowid
            """
        ).fetchall()

    result = []

    for row in rows:
        metadata = json.loads(row["metadata_json"])

        result.append(
            (
                row,
                DensePassage(
                    passage_id=str(row["passage_id"]),
                    work_id=(None if row["work_id"] is None else str(row["work_id"])),
                    metadata=metadata,
                ),
            )
        )

    return tuple(result)


def _build_dense_windows(
    passages,
    *,
    tokenizer,
):
    windows = []

    stride = BODY_WINDOW_TOKENS - BODY_WINDOW_OVERLAP

    if stride <= 0:
        raise ValueError("Invalid dense window stride")

    for row, passage in passages:
        raw_text = str(row["raw_text"])

        metadata = dict(passage.metadata)

        prefix = _structural_prefix(
            row,
            metadata,
        )

        body_ids = tokenizer.encode(
            raw_text,
            add_special_tokens=False,
        )

        if not body_ids:
            text = "passage: " + prefix

            windows.append(
                {
                    "window_id": (passage.passage_id + ":dense:0:0"),
                    "passage": passage,
                    "text": text,
                    "token_start": 0,
                    "token_end": 0,
                }
            )

            continue

        start = 0

        while start < len(body_ids):
            end = min(
                start + BODY_WINDOW_TOKENS,
                len(body_ids),
            )

            chunk = tokenizer.decode(
                body_ids[start:end],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )

            if prefix:
                representation = "passage: " + prefix + "\n" + chunk
            else:
                representation = "passage: " + chunk

            windows.append(
                {
                    "window_id": (
                        passage.passage_id + ":dense:" + str(start) + ":" + str(end)
                    ),
                    "passage": passage,
                    "text": representation,
                    "token_start": (start),
                    "token_end": (end),
                }
            )

            if end >= len(body_ids):
                break

            start += stride

    return tuple(windows)


def _dense_search(
    *,
    model,
    embeddings,
    windows,
    question,
    limit,
):
    started = time.perf_counter_ns()

    query_vector = model.encode(
        ["query: " + question],
        batch_size=1,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]

    scores = embeddings @ query_vector

    order = np.argsort(
        -scores,
        kind="stable",
    )

    best_by_passage = {}

    for index in order:
        window = windows[int(index)]

        passage_id = window["passage"].passage_id

        if passage_id in best_by_passage:
            continue

        best_by_passage[passage_id] = DenseHit(
            passage=window["passage"],
            score=float(scores[int(index)]),
            matched_window_id=(window["window_id"]),
        )

        if len(best_by_passage) >= limit:
            break

    hits = tuple(best_by_passage.values())

    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000

    return (
        hits,
        elapsed_ms,
    )


def _evaluate_dense(
    *,
    benchmark,
    model,
    embeddings,
    windows,
):
    results = []

    for case in benchmark.cases:
        hits, latency_ms = _dense_search(
            model=model,
            embeddings=embeddings,
            windows=windows,
            question=case.question,
            limit=RESULT_LIMIT,
        )

        results.append(
            evaluate_shamela_case(
                case,
                hits,
                latency_ms=latency_ms,
            )
        )

    return tuple(results)


def _evaluate_rrf(
    *,
    benchmark,
    model,
    embeddings,
    windows,
    fts,
):
    results = []

    for case in benchmark.cases:
        started = time.perf_counter_ns()

        fts_hits = fts.search(
            case.question,
            limit=RESULT_LIMIT,
            domains=(ScholarlyDomain.FIQH,),
        )

        dense_hits, _ = _dense_search(
            model=model,
            embeddings=embeddings,
            windows=windows,
            question=case.question,
            limit=RESULT_LIMIT,
        )

        fused = reciprocal_rank_fusion(
            (
                fts_hits,
                dense_hits,
            ),
            limit=RESULT_LIMIT,
            rank_constant=(RANK_CONSTANT),
        )

        latency_ms = (time.perf_counter_ns() - started) / 1_000_000

        results.append(
            evaluate_shamela_case(
                case,
                fused,
                latency_ms=latency_ms,
            )
        )

    return tuple(results)


def _metric(
    report,
    field,
    *,
    k=None,
    tag=None,
):
    container = report["summary"] if tag is None else report["tag_summaries"][tag]

    value = container[field]

    if k is not None:
        value = value[
            str(k)
            if isinstance(
                next(iter(value.keys())),
                str,
            )
            else k
        ]

    return float(value)


def main() -> int:
    repo = Path.cwd()

    benchmark_path = repo / "evaluation" / "shamela_retrieval_dev_v1.json"

    baseline_path = repo / "evaluation" / "results" / "shamela_fts_dev_v1_baseline.json"

    root = Path(os.environ["BASIRA_SHAMELA_ROOT"])

    db_path = root / "indexes" / "r3b3-shamela-fts.sqlite3"

    artifact_dir = root / "indexes" / "r3b6-e5-small-v1"

    artifact_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    benchmark = load_shamela_benchmark(benchmark_path)

    if benchmark.split != "dev":
        raise SystemExit("Dense experiment is DEV-only")

    fts = ShamelaFtsIndex(db_path)

    if fts.stats.corpus_fingerprint != benchmark.corpus_fingerprint:
        raise SystemExit("Corpus fingerprint mismatch")

    print(
        "Downloading/resolving model:",
        MODEL_ID,
    )

    snapshot = Path(
        snapshot_download(
            repo_id=MODEL_ID,
        )
    )

    model_revision = snapshot.name

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(
        "model snapshot =",
        model_revision,
    )

    print(
        "device =",
        device,
    )

    model = SentenceTransformer(
        str(snapshot),
        device=device,
    )

    print(
        "max sequence length =",
        model.max_seq_length,
    )

    passages = _load_passages(db_path)

    windows = _build_dense_windows(
        passages,
        tokenizer=model.tokenizer,
    )

    print(
        "canonical passages =",
        len(passages),
    )

    print(
        "dense windows =",
        len(windows),
    )

    representations = [window["text"] for window in windows]

    started = time.perf_counter()

    embeddings = model.encode(
        representations,
        batch_size=16,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype(
        np.float32,
        copy=False,
    )

    build_seconds = time.perf_counter() - started

    artifact_path = artifact_dir / "dense_embeddings.npz"

    np.savez_compressed(
        artifact_path,
        embeddings=embeddings,
        window_ids=np.asarray([window["window_id"] for window in windows]),
        passage_ids=np.asarray([window["passage"].passage_id for window in windows]),
        token_start=np.asarray(
            [window["token_start"] for window in windows],
            dtype=np.int32,
        ),
        token_end=np.asarray(
            [window["token_end"] for window in windows],
            dtype=np.int32,
        ),
    )

    artifact_sha = _sha256_file(artifact_path)

    environment = {
        "model_id": MODEL_ID,
        "model_revision": (model_revision),
        "device": device,
        "gpu_name": (
            torch.cuda.get_device_name(0) if (torch.cuda.is_available()) else None
        ),
        "sentence_transformers": (version("sentence-transformers")),
        "transformers": (version("transformers")),
        "torch": version("torch"),
        "numpy": version("numpy"),
        "max_sequence_length": (model.max_seq_length),
        "body_window_tokens": (BODY_WINDOW_TOKENS),
        "body_window_overlap": (BODY_WINDOW_OVERLAP),
        "canonical_passages": len(passages),
        "dense_windows": len(windows),
        "embedding_dimension": int(embeddings.shape[1]),
        "embedding_build_seconds": (build_seconds),
        "artifact_sha256": (artifact_sha),
        "corpus_fingerprint": (benchmark.corpus_fingerprint),
        "representation": (
            "E5 passage prefix + governed "
            "structural title context + "
            "model-token window over canonical "
            "raw_text; retrieval artifact only"
        ),
    }

    _write_json(
        artifact_dir / "metadata.json",
        environment,
    )

    print()
    print(
        "Dense artifact:",
        artifact_path,
    )

    print(
        "artifact SHA256 =",
        artifact_sha,
    )

    # Warm GPU/model path before timed DEV queries.
    model.encode(
        ["query: اختبار"],
        batch_size=1,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    dense_results = _evaluate_dense(
        benchmark=benchmark,
        model=model,
        embeddings=embeddings,
        windows=windows,
    )

    rrf_results = _evaluate_rrf(
        benchmark=benchmark,
        model=model,
        embeddings=embeddings,
        windows=windows,
        fts=fts,
    )

    dense_report = _report(
        benchmark=benchmark,
        benchmark_path=(benchmark_path),
        results=dense_results,
        retriever_name=("multilingual-e5-small"),
        metadata=environment,
    )

    rrf_metadata = {
        **environment,
        "fusion": ("passage-level reciprocal rank fusion"),
        "rank_constant": (RANK_CONSTANT),
        "fts_candidate_limit": (RESULT_LIMIT),
        "dense_candidate_limit": (RESULT_LIMIT),
    }

    rrf_report = _report(
        benchmark=benchmark,
        benchmark_path=(benchmark_path),
        results=rrf_results,
        retriever_name=("fts5+multilingual-e5-small+rrf"),
        metadata=rrf_metadata,
    )

    results_dir = repo / "evaluation" / "results"

    dense_result_path = results_dir / "shamela_dense_e5small_dev_v1.json"

    rrf_result_path = results_dir / "shamela_rrf_e5small_dev_v1.json"

    _write_json(
        dense_result_path,
        dense_report,
    )

    _write_json(
        rrf_result_path,
        rrf_report,
    )

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    def show(
        name,
        report,
    ):
        print()
        print("=" * 68)
        print(name)
        print("=" * 68)

        print(
            "MRR =",
            round(
                _metric(
                    report,
                    "mean_reciprocal_rank",
                ),
                4,
            ),
        )

        print(
            "parent@10 =",
            round(
                _metric(
                    report,
                    "mean_parent_recall_at_k",
                    k=10,
                ),
                4,
            ),
        )

        print(
            "nDCG@10 =",
            round(
                _metric(
                    report,
                    "mean_ndcg_at_k",
                    k=10,
                ),
                4,
            ),
        )

        print(
            "comparative parent@10 =",
            round(
                _metric(
                    report,
                    "mean_parent_recall_at_k",
                    k=10,
                    tag="comparative",
                ),
                4,
            ),
        )

        print(
            "paraphrase parent@10 =",
            round(
                _metric(
                    report,
                    "mean_parent_recall_at_k",
                    k=10,
                    tag="paraphrase",
                ),
                4,
            ),
        )

        print(
            "exact parent@10 =",
            round(
                _metric(
                    report,
                    "mean_parent_recall_at_k",
                    k=10,
                    tag="exact_phrase",
                ),
                4,
            ),
        )

        print(
            "single parent@10 =",
            round(
                _metric(
                    report,
                    "mean_parent_recall_at_k",
                    k=10,
                    tag="single_madhhab",
                ),
                4,
            ),
        )

        print(
            "mean latency ms =",
            round(
                _metric(
                    report,
                    "mean_latency_ms",
                ),
                3,
            ),
        )

    show(
        "FTS BASELINE",
        baseline,
    )

    show(
        "DENSE ONLY",
        dense_report,
    )

    show(
        "FTS + DENSE RRF",
        rrf_report,
    )

    baseline_parent = _metric(
        baseline,
        "mean_parent_recall_at_k",
        k=10,
    )

    baseline_comp = _metric(
        baseline,
        "mean_parent_recall_at_k",
        k=10,
        tag="comparative",
    )

    baseline_para = _metric(
        baseline,
        "mean_parent_recall_at_k",
        k=10,
        tag="paraphrase",
    )

    baseline_ndcg = _metric(
        baseline,
        "mean_ndcg_at_k",
        k=10,
    )

    baseline_mrr = _metric(
        baseline,
        "mean_reciprocal_rank",
    )

    rrf_parent = _metric(
        rrf_report,
        "mean_parent_recall_at_k",
        k=10,
    )

    rrf_comp = _metric(
        rrf_report,
        "mean_parent_recall_at_k",
        k=10,
        tag="comparative",
    )

    rrf_para = _metric(
        rrf_report,
        "mean_parent_recall_at_k",
        k=10,
        tag="paraphrase",
    )

    rrf_ndcg = _metric(
        rrf_report,
        "mean_ndcg_at_k",
        k=10,
    )

    rrf_mrr = _metric(
        rrf_report,
        "mean_reciprocal_rank",
    )

    exact_guard = _metric(
        rrf_report,
        "mean_parent_recall_at_k",
        k=10,
        tag="exact_phrase",
    )

    single_guard = _metric(
        rrf_report,
        "mean_parent_recall_at_k",
        k=10,
        tag="single_madhhab",
    )

    criteria = {
        "overall_parent_gain_ge_0.03": (rrf_parent >= baseline_parent + 0.03),
        "comparative_parent_gain_ge_0.04": (rrf_comp >= baseline_comp + 0.04),
        "paraphrase_parent_gain_ge_0.10": (rrf_para >= baseline_para + 0.10),
        "ndcg_not_materially_worse": (rrf_ndcg >= baseline_ndcg - 0.01),
        "mrr_not_materially_worse": (rrf_mrr >= baseline_mrr - 0.03),
        "exact_phrase_guard": (exact_guard == 1.0),
        "single_madhhab_guard": (single_guard == 1.0),
    }

    promote = all(criteria.values())

    decision = {
        "schema_version": 1,
        "benchmark_id": (benchmark.benchmark_id),
        "benchmark_sha256": (_benchmark_sha(benchmark_path)),
        "holdout_used": False,
        "candidate": ("fts5+multilingual-e5-small+rrf"),
        "criteria": criteria,
        "decision": ("PROMOTE_RRF_FOR_INTEGRATION" if promote else "KEEP_FTS_BASELINE"),
        "important_deltas": {
            "overall_parent_at_10": (rrf_parent - baseline_parent),
            "comparative_parent_at_10": (rrf_comp - baseline_comp),
            "paraphrase_parent_at_10": (rrf_para - baseline_para),
            "ndcg_at_10": (rrf_ndcg - baseline_ndcg),
            "mrr": (rrf_mrr - baseline_mrr),
        },
        "note": (
            "Dense similarity is a retrieval "
            "signal only. These metrics do not "
            "establish claim entailment, religious "
            "truth, or source authority."
        ),
    }

    decision_path = results_dir / "shamela_e5small_dev_decision_v1.json"

    _write_json(
        decision_path,
        decision,
    )

    print()
    print("=" * 68)

    print("DEV DECISION")

    print("=" * 68)

    for name, passed in criteria.items():
        print(
            f"{name:42}",
            "PASS" if passed else "FAIL",
        )

    print()
    print(
        "DECISION =",
        decision["decision"],
    )

    print()
    print(
        "Dense result:",
        dense_result_path,
    )

    print(
        "RRF result:",
        rrf_result_path,
    )

    print(
        "Decision:",
        decision_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
