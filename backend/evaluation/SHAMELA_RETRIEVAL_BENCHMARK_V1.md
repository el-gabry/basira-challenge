# Shamela Retrieval Benchmark v1

This benchmark evaluates retrieval over the frozen
two-book governed Shamela corpus.

It evaluates retrieval relevance and structural
coverage only. It does not evaluate religious truth,
preferred legal positions, or semantic claim
entailment.

## Frozen corpus

- Corpus fingerprint:
  `00edc4a799087fcc7fa0b83e2582604ffbc11f75dc4cfe2b90a424589a4a5a8f`
- Baseline FTS index fingerprint:
  `08db016154199e022fad28101fda5ed51f242d1fa6828521b6386bad3cabf94b`
- Canonical passages: 1561
- Retrieval windows: 1745
- FTS child window: 192 tokens
- Overlap: 32 tokens

The corpus fingerprint is the benchmark compatibility
invariant.

The FTS index fingerprint identifies the frozen
baseline retrieval artifact only. Future Dense,
Hybrid, RRF, and reranker candidates may use different
retrieval/index fingerprints while reading the same
frozen governed corpus.

## Splits

### DEV

`evaluation/shamela_retrieval_dev_v1.json`

SHA-256:

`e199b37de6983c8cdad713a7382e96bda522f4a81a830c138a7cd3c3748f2791`

DEV may be used for retrieval experiments, query
analysis, ablations, model selection, and fusion
decisions.

### HOLDOUT

`evaluation/shamela_retrieval_holdout_v1.json`

SHA-256:

`3675d10602e315d39438d0c8f2837bbe8c30ebe510fabe285ad89871d8fa6acd`

The HOLDOUT split is frozen before dense retrieval,
fusion, reranker, or query-expansion experiments.

Do not tune models, aliases, expansion rules, fusion
weights, rerankers, prompts, or retrieval logic
against HOLDOUT failures.

Schema/gold identity validation against the governed
corpus is allowed and does not execute retrieval.

HOLDOUT retrieval must remain unevaluated until a
final candidate is selected using DEV.

## Gold identity

Every gold unit is pinned by:

`book_id + structural_parent_id + madhhab`

`parent_text` is retained as a human-readable label,
but is not the authoritative structural identity.

This is important because structural titles may repeat
inside a book.

Some DEV exact-phrase cases additionally include an
exact passage ID.

## Metrics

- MRR
- Hit@K
- Parent / issue recall@K
- Book recall@K
- Madhhab coverage@K
- Passage recall@K for exact-passage gold
- Diversity-aware nDCG@K
- Governed context recovery@K
- mean retrieval latency
- p95 retrieval latency

Book recall and madhhab coverage are coarse structural
metrics and must not be interpreted as topical or
semantic support.

Parent recall is the primary structural issue metric.

Semantic claim verification remains outside this
benchmark.
