# Competition Core Baseline Audit

Generated: 2026-10-03T23:24:31.273703-07:00

Purpose: determine what the imported pre-competition core already
implements before adding competition-period architecture.

---

## `src/basira/reasoning/contracts.py`

- class `ReligiousDiscipline(StrEnum)` — line 7
  - members: QURAN, HADITH, TAFSIR, ASBAB_AL_NUZUL, AQIDAH, FIQH, USUL_AL_FIQH, CONTEMPORARY_FIQH, SIRAH, MAWARITH, CROSS_DISCIPLINARY
- class `ReasoningMode(StrEnum)` — line 32
  - members: DIRECT_GROUNDING, INTERPRETATION, AUTHENTICITY, COMPARATIVE, LEGAL_RULING, CONTEMPORARY_APPLICATION, CONTESTED_CLAIM, DETERMINISTIC_CALCULATION
- class `EvidenceObligation(StrEnum)` — line 60
  - members: EXACT_CANONICAL_TEXT, SOURCE_ATTRIBUTION, HADITH_TEXT, HADITH_GRADING, TAFSIR_CONTEXT, REVELATION_CONTEXT, CLASSICAL_FIQH_POSITION, MADHHAB_SCOPE, USUL_PRINCIPLE, LEGAL_RATIONALE, CONDITIONS, EXCEPTIONS, CONTEMPORARY_GUIDANCE, CONTEMPORARY_FACTS, TEMPORAL_CONTEXT, JURISDICTION_CONTEXT, INSTITUTION_ATTRIBUTION, DOCUMENTED_DISAGREEMENT
- class `AnswerConstraint(StrEnum)` — line 108
  - members: PRESERVE_DISAGREEMENT, DO_NOT_CLAIM_CONSENSUS, DO_NOT_COLLAPSE_MADHHABS, ATTRIBUTE_OPINIONS, PRESERVE_CONDITIONS, PRESERVE_EXCEPTIONS, DO_NOT_ACCEPT_PREMISE_AS_FACT, REQUIRE_CONTEXT_BEFORE_CONCLUSION, REQUIRE_EXPERT_REVIEW
- class `ReligiousReasoningFrame` — line 138
- class `ClassicalFiqhIssue` — line 202
- class `ContemporaryFiqhContext` — line 235
- class `ContestedClaim` — line 274
- function `classical_fiqh_comparison_frame()` — line 302
- function `contemporary_fiqh_frame()` — line 330
- function `contested_claim_frame()` — line 364

**Capability keywords:** ANSWER, discipline, reasoning_mode, source, requirement, claim, evidence, semantic, quran

---

## `src/basira/reasoning/routing.py`

- class `UnmappedEvidenceObligationError(RuntimeError)` — line 25
- function `_contains_any()` — line 220
- class `ReasoningEvidenceAdapter` — line 227
- class `ReligiousReasoningRoute` — line 285
- class `ReligiousReasoningRouter` — line 301

**Capability keywords:** ANSWER, discipline, reasoning_mode, source, requirement, claim, evidence, semantic, quran

---

## `src/basira/evidence/decision.py`

- class `EvidenceDecisionAction(StrEnum)` — line 23
  - members: ANSWER, ANSWER_WITH_LIMITATION, RETRIEVE_MORE, ABSTAIN, ESCALATE_TO_EXPERT
- class `EvidenceDecisionReason(StrEnum)` — line 35
  - members: COMPLETE_EVIDENCE, RESOLVED_ABSENCE, MISSING_REQUIRED_EVIDENCE, UNAVAILABLE_REQUIRED_DOMAIN, HIGH_RISK_QUERY, EVIDENCE_CONFLICT, INVALID_REQUIRED_EVIDENCE_LINK
- class `EvidenceDecision` — line 55
- class `EvidenceDecisionPolicy` — line 93

**Capability keywords:** ANSWER, ABSTAIN, RETRIEVE_MORE, ESCALATE, requirement, conflict, evidence

---

## `src/basira/evidence/sufficiency.py`

- class `RetrievalSufficiencyState(StrEnum)` — line 15
  - members: SUFFICIENT, RESOLVED_ABSENCE, NEEDS_MORE_RETRIEVAL, UNAVAILABLE, INVALID_EVIDENCE_LINK
- class `RetrievalSufficiencyAssessment` — line 38
- class `RetrievalSufficiencyGate` — line 89

**Capability keywords:** ANSWER, requirement, claim, evidence, semantic

---

## `src/basira/sources/policy_catalog.py`

- class `SourceUsagePolicyNotFoundError(KeyError)` — line 11
- function `has_source_usage_policy()` — line 380
- function `get_source_usage_policy()` — line 397
- function `list_source_usage_policies()` — line 421

**Capability keywords:** ANSWER, source, conflict, evidence, quran

---

## `src/basira/api/service.py`

- class `QueryExecution` — line 130
- class `BasiraQueryService` — line 142
- function `_optional_directory()` — line 271
- function `_required_directory()` — line 289
- function `_quran_manifest_path()` — line 305
- function `build_quran_runtime()` — line 318
- function `build_default_scholarly_repository()` — line 336
- function `build_hadeethenc_runtime()` — line 344
- function `build_default_hadith_retriever()` — line 369
- function `_configured_hadith_retriever()` — line 516
- function `build_default_retriever()` — line 530
- function `build_default_query_service()` — line 596

**Capability keywords:** ANSWER, source, evidence, quran

---

## `src/basira/answer/models.py`

- class `AnswerCitation` — line 20
- class `StructuredClaim` — line 55
- class `GroundedAnswer` — line 86

**Capability keywords:** ANSWER, ABSTAIN, RETRIEVE_MORE, ESCALATE, source, coverage, claim, evidence, semantic

---

## `src/basira/answer/integrity.py`

- class `ClaimIntegrityIssueType(StrEnum)` — line 14
  - members: EMPTY_AXIS_ID, EMPTY_CLAIM_ID, DUPLICATE_CLAIM_ID, EMPTY_CLAIM_TEXT, MISSING_EVIDENCE_LINK, UNKNOWN_EVIDENCE_ID, NON_LITERAL_CLAIM_TEXT
- class `ClaimIntegrityIssue` — line 34
- class `ClaimIntegrityReport` — line 49
- class `ClaimIntegrityError(ValueError)` — line 76
- function `_normalize_literal()` — line 90
- function `_claim_literal_candidate()` — line 96
- class `ClaimSourceIntegrityVerifier` — line 116

**Capability keywords:** ANSWER, source, claim, evidence, semantic

---

## `src/basira/verification/quran_integrity.py`

- class `QuranIntegrityStatus(StrEnum)` — line 23
  - members: EXACT_MATCH, ORTHOGRAPHICALLY_EQUIVALENT, UNRESOLVED_MISMATCH, REFERENCE_MISSING
- class `QuranIntegrityComparison(BaseModel)` — line 65
- class `QuranIntegrityReport(BaseModel)` — line 136
- class `QuranCrossSourceIntegrityVerifier` — line 304

**Capability keywords:** source, coverage, claim, semantic, quran

---

## `src/basira/verification/quran_verifier.py`

- class `QuranQuoteStatus(StrEnum)` — line 13
  - members: EXACT_MATCH, NORMALIZED_MATCH, PARTIAL_MATCH, ALTERED_TEXT, AMBIGUOUS, NOT_FOUND
- class `QuranDifferenceKind(StrEnum)` — line 22
  - members: ORTHOGRAPHIC, SUBSTITUTION, INSERTION, DELETION
- class `QuranDifference(BaseModel)` — line 29
- class `QuranCandidate(BaseModel)` — line 40
- class `QuranQuoteResult(BaseModel)` — line 65
- class `QuranQuoteVerifier` — line 84
  - members: MIN_ALTERATION_TOKENS, ALTERATION_THRESHOLD, AMBIGUITY_MARGIN

**Capability keywords:** source, evidence, quran

