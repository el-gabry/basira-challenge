# Basira Public API Surface Snapshot

---

## basira.reasoning.routing.ReligiousReasoningRouter
constructor: (*, evidence_adapter: 'ReasoningEvidenceAdapter | None' = None) -> 'None'

- route(self, understanding: 'BasiraQueryUnderstanding') -> 'ReligiousReasoningRoute'

---

## basira.evidence.decision.EvidenceDecisionPolicy
constructor: ()

- decide(self, *, understanding: 'BasiraQueryUnderstanding', bundle: 'EvidenceBundle', sufficiency: 'RetrievalSufficiencyAssessment | None' = None) -> 'EvidenceDecision'

---

## basira.evidence.sufficiency.RetrievalSufficiencyGate
constructor: ()

- assess(self, bundle: 'EvidenceBundle') -> 'RetrievalSufficiencyAssessment'

---

## basira.verification.quran_verifier.QuranQuoteVerifier
constructor: (repository: 'QuranRepository') -> 'None'

- verify(self, text: 'str') -> 'QuranQuoteResult'

---

## basira.verification.quran_integrity.QuranCrossSourceIntegrityVerifier
constructor: (*, orthography_comparator: 'QuranOrthographySegmentComparator | None' = None, expected_reference_count: 'int' = 6236) -> 'None'

- compare(self, source_a: 'QuranRepository', source_b: 'QuranRepository') -> 'QuranIntegrityReport'

---

## basira.answer.integrity.ClaimSourceIntegrityVerifier
constructor: ()

- require_valid(self, *, claims: 'tuple[StructuredClaim, ...]', evidence: 'tuple[EvidenceNode, ...]') -> 'ClaimIntegrityReport'
- verify(self, *, claims: 'tuple[StructuredClaim, ...]', evidence: 'tuple[EvidenceNode, ...]') -> 'ClaimIntegrityReport'

---

## basira.api.service.BasiraQueryService
constructor: (*, retriever: 'BasiraUnifiedRetriever', scholarly_repository: 'ScholarlyRepository | None' = None, scholarly_runtime: 'FailClosedSourceRuntime | None' = None) -> 'None'

- execute(self, *, question: 'str', quran_reference: 'str | None' = None) -> 'QueryExecution'
- get_publishable_tafsir(self, evidence_id: 'str') -> 'ScholarlyPassage | None'
