# M29 — Bounded Conceptual Retrieval Rescue

## Status

**Implementation frozen with documented generalization limitation.**

The retrieval rescue improves bounded conceptual and cross-lingual
candidate generation while preserving deterministic exact-anchor
retrieval. It does not establish general semantic retrieval over
previously unseen concepts.

## Frozen evaluation protocol

The independent holdout was frozen before pre/post execution.

The comparison is:

- pre-rescue: `af6cad7`
- frozen retrieval rescue: `20e29cf`
- holdout definition freeze: `9ec7e06`
- recorded holdout results: `94067fc`

No retrieval tuning should be performed against the frozen holdout.

## One-shot holdout result

### In-vocabulary concepts, unseen wording

| Metric | Pre | Post |
|---|---:|---:|
| MRR | 0.030 | 0.273 |
| Recall@10 | 0.125 | 0.625 |
| Recall@50 | 0.375 | 0.625 |
| Recall@100 | 0.375 | 0.750 |

### Out-of-vocabulary concepts

| Metric | Pre | Post |
|---|---:|---:|
| MRR | 0.143 | 0.132 |
| Recall@10 | 0.250 | 0.125 |
| Recall@50 | 0.375 | 0.375 |
| Recall@100 | 0.375 | 0.375 |

### All conceptual holdout cases

| Metric | Pre | Post |
|---|---:|---:|
| MRR | 0.0863 | 0.2029 |
| Recall@10 | 0.1875 | 0.3750 |
| Recall@50 | 0.3750 | 0.5000 |
| Recall@100 | 0.3750 | 0.5625 |

Exact-anchor Top-1 remained `1.0`.

## Interpretation

The rescue successfully improves retrieval when a concept is
represented by the bounded atomic-query vocabulary but is expressed
with unseen wording.

The frozen holdout does not show improved generalization to concepts
outside that vocabulary. OOV retrieval therefore remains an explicit
limitation rather than being patched against the holdout.

This implementation should be described as bounded query-side
conceptual retrieval rescue, not as general semantic retrieval.

## Consequence for the Basira pipeline

Retrieval is now frozen for this milestone.

The next protection layer is the **Retrieval Sufficiency Gate**.

The gate must prevent downstream answer generation from interpreting
retrieval availability as semantic support. It should distinguish:

- sufficient retrieved evidence;
- incomplete role/source coverage;
- retrieval unavailable;
- no attested evidence;
- evidence present but insufficient for the requested claim;
- cases requiring abstention or additional retrieval.

The frozen holdout must not be reused for retrieval tuning.
