# Basira Competition Evaluator Contract V1

## Result states

Every benchmark requirement must resolve to one of:

- PASS
- FAIL
- NOT_IMPLEMENTED
- NOT_EXECUTED

`NOT_IMPLEMENTED` is not silently counted as PASS.

`NOT_EXECUTED` is used when a capability exists but cannot be
responsibly exercised in the current runtime.

## Competition extension contracts

The evaluator may dynamically discover the following optional
competition modules as they are implemented:

### Content sensitivity

`basira.competition.sensitivity`

Expected public symbols:

- `ContentSensitivityLevel`
- `ContentSensitivityClassifier`
- `ContentSensitivityClassifier.classify(question: str)`

### Quran witness attestation

`basira.trust.quran_witness`

Expected public symbols:

- `QuranWitness`
- `QuranWitnessAttestor`
- `QuranWitnessAttestor.compare_identity(a, b)`

### Semantic claim/evidence verification

`basira.trust.claim_evidence`

Expected public symbols:

- `ClaimEvidenceRelation`
- `ClaimEvidenceVerifier`
- `ClaimEvidenceVerifier.verify(claim: str, evidence: str)`

### Failure certification

`basira.trust.failure`

Expected public symbols:

- `FailureClass`
- `FailureCertifier`

### Safe memory admission

`basira.learning.memory`

Expected public symbols:

- `MemoryDestination`
- `MemoryAdmissionPolicy`

## Scientific rule

The evaluator must not use lexical similarity as proof of semantic
entailment.

Missing competition capabilities are reported explicitly rather than
simulated.
