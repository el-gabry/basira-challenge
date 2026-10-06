# Basira Competition Benchmark V1

## Purpose

This benchmark was frozen before competition-period trust
innovations were implemented.

It is intended to measure deltas over the imported Basira baseline.

## Benchmark families

The benchmark deliberately separates:

- sacred-text integrity;
- source attestation;
- hadith attribution;
- false consensus;
- valid scholarly disagreement;
- comparative evidence coverage;
- Level-D personal cases;
- insufficient evidence;
- semantic claim/evidence support;
- safe failure learning.

## Important interpretation

Retrieval success is not equivalent to semantic support.

Literal integrity is not equivalent to religious truth.

Cross-source agreement is not equivalent to consensus.

A valid scholarly alternative is not automatically a system error.

## Evaluation layers

### Layer 1 — deterministic / structural

Examples:

- routing;
- evidence requirements;
- source eligibility;
- verse integrity;
- policy action;
- missing evidence;
- citation linkage.

### Layer 2 — semantic support

Claim/evidence relation:

- ENTAILED
- PARTIALLY_SUPPORTED
- CONTRADICTED
- TOPICALLY_RELATED_ONLY
- CONTEXT_MISSING
- SOURCE_SCOPE_MISMATCH
- INSUFFICIENT_EVIDENCE
- VALID_ALTERNATIVE_POSITION

This layer must not be represented as implemented until it actually is.

### Layer 3 — safe learning

Only verified system errors may enter repair memory.

Legitimate scholarly disagreement must remain protected from
automatic correction.

## Freeze rule

The benchmark cases must not be edited after the frozen Git tag.

If a benchmark defect is discovered, create V2 and document the reason.
