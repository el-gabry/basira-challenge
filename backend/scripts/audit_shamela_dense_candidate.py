from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from transformers import AutoTokenizer

MODEL_ID = "intfloat/multilingual-e5-small"

DENSE_BODY_WINDOW = 320
DENSE_OVERLAP = 64

MODEL_LIMIT = 512


def _load_json(
    path: Path,
):
    return json.loads(path.read_text(encoding="utf-8"))


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
        value = value[str(k)]

    return float(value)


def _metrics(
    report,
):
    return {
        "mrr": _metric(
            report,
            "mean_reciprocal_rank",
        ),
        "parent_at_10": _metric(
            report,
            "mean_parent_recall_at_k",
            k=10,
        ),
        "ndcg_at_10": _metric(
            report,
            "mean_ndcg_at_k",
            k=10,
        ),
        "comparative_parent_at_10": _metric(
            report,
            "mean_parent_recall_at_k",
            k=10,
            tag="comparative",
        ),
        "paraphrase_parent_at_10": _metric(
            report,
            "mean_parent_recall_at_k",
            k=10,
            tag="paraphrase",
        ),
        "direct_parent_at_10": _metric(
            report,
            "mean_parent_recall_at_k",
            k=10,
            tag="direct",
        ),
        "exact_parent_at_10": _metric(
            report,
            "mean_parent_recall_at_k",
            k=10,
            tag="exact_phrase",
        ),
        "single_madhhab_parent_at_10": _metric(
            report,
            "mean_parent_recall_at_k",
            k=10,
            tag="single_madhhab",
        ),
        "mean_latency_ms": _metric(
            report,
            "mean_latency_ms",
        ),
    }


def _structural_prefix(
    row,
    metadata,
):
    values = (
        row["work_title"],
        metadata.get("parent_text"),
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


def _token_audit(
    *,
    repo: Path,
    shamela_root: Path,
    metadata,
):
    revision = metadata["model_revision"]

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
        raise SystemExit("Cached model snapshot not found: " + str(snapshot))

    tokenizer = AutoTokenizer.from_pretrained(
        str(snapshot),
        local_files_only=True,
    )

    # Avoid the warning generated while tokenizing
    # full source passages before our own chunking.
    tokenizer.model_max_length = 10_000_000

    db_path = shamela_root / "indexes" / "r3b3-shamela-fts.sqlite3"

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT
                passage_id,
                work_title,
                author_name,
                section_title,
                chapter_title,
                volume,
                madhhab,
                raw_text,
                metadata_json
            FROM passages
            ORDER BY rowid
            """
        ).fetchall()

    stride = DENSE_BODY_WINDOW - DENSE_OVERLAP

    max_input_tokens = 0
    max_window_id = None

    over_limit = []

    window_count = 0

    for row in rows:
        metadata_json = json.loads(row["metadata_json"])

        prefix = _structural_prefix(
            row,
            metadata_json,
        )

        raw_text = str(row["raw_text"])

        body_ids = tokenizer.encode(
            raw_text,
            add_special_tokens=False,
        )

        if not body_ids:
            representation = "passage: " + prefix

            length = len(
                tokenizer.encode(
                    representation,
                    add_special_tokens=True,
                )
            )

            window_id = str(row["passage_id"]) + ":dense:0:0"

            window_count += 1

            if length > max_input_tokens:
                max_input_tokens = length
                max_window_id = window_id

            if length > MODEL_LIMIT:
                over_limit.append(
                    (
                        window_id,
                        length,
                    )
                )

            continue

        start = 0

        while start < len(body_ids):
            end = min(
                start + DENSE_BODY_WINDOW,
                len(body_ids),
            )

            chunk = tokenizer.decode(
                body_ids[start:end],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )

            representation = (
                ("passage: " + prefix + "\n" + chunk)
                if prefix
                else ("passage: " + chunk)
            )

            encoded = tokenizer.encode(
                representation,
                add_special_tokens=True,
            )

            length = len(encoded)

            window_id = str(row["passage_id"]) + ":dense:" + str(start) + ":" + str(end)

            window_count += 1

            if length > max_input_tokens:
                max_input_tokens = length
                max_window_id = window_id

            if length > MODEL_LIMIT:
                over_limit.append(
                    (
                        window_id,
                        length,
                    )
                )

            if end >= len(body_ids):
                break

            start += stride

    benchmark = _load_json(repo / "evaluation" / "shamela_retrieval_dev_v1.json")

    max_query_tokens = 0
    max_query_case = None

    query_over_limit = []

    for case in benchmark["cases"]:
        representation = "query: " + str(case["question"])

        length = len(
            tokenizer.encode(
                representation,
                add_special_tokens=True,
            )
        )

        if length > max_query_tokens:
            max_query_tokens = length
            max_query_case = case["id"]

        if length > MODEL_LIMIT:
            query_over_limit.append(
                (
                    case["id"],
                    length,
                )
            )

    return {
        "model_id": MODEL_ID,
        "model_revision": revision,
        "model_limit": MODEL_LIMIT,
        "dense_body_window_tokens": (DENSE_BODY_WINDOW),
        "dense_overlap": (DENSE_OVERLAP),
        "reconstructed_window_count": (window_count),
        "expected_window_count": (int(metadata["dense_windows"])),
        "max_final_passage_input_tokens": (max_input_tokens),
        "max_final_passage_window_id": (max_window_id),
        "passage_inputs_over_limit": (len(over_limit)),
        "passage_over_limit_examples": (over_limit[:10]),
        "max_query_input_tokens": (max_query_tokens),
        "max_query_case_id": (max_query_case),
        "query_inputs_over_limit": (len(query_over_limit)),
        "query_over_limit_examples": (query_over_limit[:10]),
        "safe": (
            len(over_limit) == 0
            and len(query_over_limit) == 0
            and window_count == int(metadata["dense_windows"])
        ),
    }


def _dominates(
    left,
    right,
):
    fields = (
        "mrr",
        "parent_at_10",
        "ndcg_at_10",
        "comparative_parent_at_10",
        "paraphrase_parent_at_10",
        "direct_parent_at_10",
    )

    no_worse = all(left[field] >= right[field] - 1e-12 for field in fields)

    strictly_better = any(left[field] > right[field] + 1e-12 for field in fields)

    return no_worse and strictly_better


def main():
    repo = Path.cwd()

    root = Path(os.environ["BASIRA_SHAMELA_ROOT"])

    result_dir = repo / "evaluation" / "results"

    reports = {
        "FTS_BASELINE": _load_json(result_dir / "shamela_fts_dev_v1_baseline.json"),
        "DENSE_ONLY": _load_json(result_dir / "shamela_dense_e5small_dev_v1.json"),
        "FTS_DENSE_RRF": _load_json(result_dir / "shamela_rrf_e5small_dev_v1.json"),
    }

    benchmark_hashes = {report["benchmark_sha256"] for report in reports.values()}

    corpus_fingerprints = {report["corpus_fingerprint"] for report in reports.values()}

    splits = {report["split"] for report in reports.values()}

    if len(benchmark_hashes) != 1:
        raise SystemExit("Benchmark hash mismatch")

    if len(corpus_fingerprints) != 1:
        raise SystemExit("Corpus fingerprint mismatch")

    if splits != {"dev"}:
        raise SystemExit("Candidate audit must be DEV-only")

    dense_metadata = reports["DENSE_ONLY"]["retriever_metadata"]

    token_audit = _token_audit(
        repo=repo,
        shamela_root=root,
        metadata=dense_metadata,
    )

    if not token_audit["safe"]:
        print(
            json.dumps(
                token_audit,
                ensure_ascii=False,
                indent=2,
            )
        )

        raise SystemExit("Dense token audit failed")

    metrics = {name: _metrics(report) for name, report in (reports.items())}

    baseline = metrics["FTS_BASELINE"]

    candidate_eligibility = {}

    for name, values in metrics.items():
        if name == "FTS_BASELINE":
            candidate_eligibility[name] = True
            continue

        candidate_eligibility[name] = all(
            (
                values["parent_at_10"] >= baseline["parent_at_10"],
                values["ndcg_at_10"] >= baseline["ndcg_at_10"],
                values["mrr"] >= baseline["mrr"],
                values["comparative_parent_at_10"]
                >= baseline["comparative_parent_at_10"],
                values["paraphrase_parent_at_10"]
                >= baseline["paraphrase_parent_at_10"],
                values["direct_parent_at_10"] >= baseline["direct_parent_at_10"],
                values["exact_parent_at_10"] >= baseline["exact_parent_at_10"],
                values["single_madhhab_parent_at_10"]
                >= baseline["single_madhhab_parent_at_10"],
                token_audit["safe"],
            )
        )

    eligible = [name for name, passed in (candidate_eligibility.items()) if passed]

    dominant = []

    for candidate in eligible:
        if all(
            (
                other == candidate
                or _dominates(
                    metrics[candidate],
                    metrics[other],
                )
            )
            for other in eligible
        ):
            dominant.append(candidate)

    if len(dominant) == 1:
        selected = dominant[0]
        decision = "SELECT_UNIQUE_DEV_DOMINANT"
    else:
        selected = None
        decision = "NO_UNIQUE_DEV_DOMINANT"

    output = {
        "schema_version": 1,
        "benchmark_sha256": (next(iter(benchmark_hashes))),
        "corpus_fingerprint": (next(iter(corpus_fingerprints))),
        "split": "dev",
        "holdout_used": False,
        "selection_method": (
            "Candidate must not regress "
            "against frozen FTS baseline "
            "on overall parent@10, nDCG@10, "
            "MRR, comparative, paraphrase, "
            "direct, exact phrase, or "
            "single-madhhab parent recall. "
            "Among eligible candidates, "
            "select only a unique candidate "
            "that Pareto-dominates every "
            "other eligible candidate on "
            "MRR, overall parent@10, "
            "nDCG@10, comparative, "
            "paraphrase, and direct "
            "parent@10."
        ),
        "token_audit": (token_audit),
        "metrics": metrics,
        "eligible": (candidate_eligibility),
        "dominant_candidates": (dominant),
        "selected_candidate": (selected),
        "decision": decision,
        "note": (
            "Dense similarity is a "
            "retrieval/ranking signal only. "
            "This evaluation does not "
            "establish semantic entailment, "
            "religious truth, or source "
            "authority."
        ),
    }

    output_path = result_dir / "shamela_dense_candidate_selection_v1.json"

    output_path.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("================================================")

    print("TOKEN AUDIT")

    print("================================================")

    print(
        "windows reconstructed =",
        token_audit["reconstructed_window_count"],
    )

    print(
        "max passage input tokens =",
        token_audit["max_final_passage_input_tokens"],
    )

    print(
        "passage inputs >512 =",
        token_audit["passage_inputs_over_limit"],
    )

    print(
        "max query tokens =",
        token_audit["max_query_input_tokens"],
    )

    print(
        "query inputs >512 =",
        token_audit["query_inputs_over_limit"],
    )

    print(
        "TOKEN_SAFE =",
        token_audit["safe"],
    )

    print()

    print("================================================")

    print("DEV CANDIDATE COMPARISON")

    print("================================================")

    fields = (
        "mrr",
        "parent_at_10",
        "ndcg_at_10",
        "comparative_parent_at_10",
        "paraphrase_parent_at_10",
        "direct_parent_at_10",
        "exact_parent_at_10",
        "single_madhhab_parent_at_10",
        "mean_latency_ms",
    )

    for name in (
        "FTS_BASELINE",
        "DENSE_ONLY",
        "FTS_DENSE_RRF",
    ):
        print()
        print(name)

        for field in fields:
            print(
                f"  {field:34}",
                round(
                    metrics[name][field],
                    4,
                ),
            )

        print(
            "  eligible".ljust(36),
            candidate_eligibility[name],
        )

    print()
    print(
        "dominant candidates =",
        dominant,
    )

    print(
        "SELECTED_CANDIDATE =",
        selected,
    )

    print(
        "DECISION =",
        decision,
    )

    print()
    print(
        "result =",
        output_path,
    )


if __name__ == "__main__":
    main()
