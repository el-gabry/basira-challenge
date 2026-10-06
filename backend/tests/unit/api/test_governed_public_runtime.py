from __future__ import annotations

import inspect

from basira.answer.models import StructuredClaim
from basira.api.governed_runtime import (
    LiteralGeneratedClaimEvaluator,
    PublicGovernedQueryRuntime,
    PublicTaskEvidenceEvaluator,
    normalize_semantic_text,
)
from basira.api.service import BasiraQueryService
from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.evidence.publication import (
    GovernedPublicationLedger,
)
from basira.models.quran import QuranVerse
from basira.orchestration.claim_sufficiency import (
    ClaimResolutionState,
    ClaimSufficiencyState,
)
from basira.orchestration.contracts import ClaimTask
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)
from basira.sources.quran.repository import QuranRepository


class QuranRepoCarrier:
    def __init__(
        self,
        repository: QuranRepository,
    ) -> None:
        self.repository = repository


class HostileUnifiedRetriever:
    def __init__(self) -> None:
        self.repository = QuranRepository(
            (
                QuranVerse(
                    source_id="quran:canonical",
                    surah_number=2,
                    ayah_number=255,
                    text_uthmani=("اللَّهُ لَا إِلَهَ إِلَّا هُوَ وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالْأَرْضَ"),
                    text_search=("الله لا اله الا هو وسع كرسيه السماوات والارض"),
                ),
                QuranVerse(
                    source_id="quran:canonical",
                    surah_number=2,
                    ayah_number=43,
                    text_uthmani="وَأَقِيمُوا الصَّلَاةَ",
                    text_search="واقيموا الصلاة",
                ),
            )
        )

        self.retrievers = {
            EvidenceDomain.QURAN: (QuranRepoCarrier(self.repository)),
        }

        self.publication_authorizer = GovernedPublicationLedger()

    def retrieve(
        self,
        plan,
        *,
        limit_per_domain: int = 10,
    ) -> UnifiedRetrievalResult:
        del limit_per_domain

        domains = {target.domain for target in plan.targets}

        candidates = (
            EvidenceNode(
                evidence_id="quran:2:255",
                domain=EvidenceDomain.QURAN,
                text=("وسع كرسيه السماوات والأرض"),
                source_id="quran:canonical",
                reference="2:255",
            ),
            EvidenceNode(
                evidence_id="tafsir:wrong:2:43",
                domain=EvidenceDomain.TAFSIR,
                text=("مصدر معتبر لكنه يتعلق بآية أخرى."),
                source_id="tafsir:trusted",
                reference="2:43",
            ),
            EvidenceNode(
                evidence_id="tafsir:right:2:255",
                domain=EvidenceDomain.TAFSIR,
                text=(
                    "مقدمة في الآية ثم قوله "
                    "وسع كرسيه السماوات والأرض. "
                    "ثم قال المفسر في معنى كرسيه: "
                    "هذا هو الموضع التفسيري "
                    "المتعلق بالسؤال."
                ),
                source_id="tafsir:trusted",
                reference="2:255",
            ),
        )

        for node in candidates:
            if node.domain in domains:
                self.publication_authorizer.admit(node)

        return UnifiedRetrievalResult(
            plan=plan,
            evidence=tuple(node for node in candidates if node.domain in domains),
            unavailable_domains=frozenset(),
        )


_TrustedRuntime = PublicGovernedQueryRuntime


def _runtime_with_explicit_test_authority(
    *,
    retriever,
    **kwargs,
):
    return _TrustedRuntime(
        retriever=retriever,
        publication_authorizer=getattr(
            retriever,
            "publication_authorizer",
            None,
        ),
        **kwargs,
    )


def _task(text: str) -> ClaimTask:
    return ClaimTask(
        task_id="claim:test",
        claim_text=text,
        frame=ReligiousReasoningFrame(
            frame_id="frame:test",
            question=text,
            primary_discipline=(ReligiousDiscipline.TAFSIR),
            reasoning_mode=(ReasoningMode.INTERPRETATION),
        ),
        context_requirement=ContextRequirement(),
    )


def test_public_execute_has_no_direct_legacy_bypass() -> None:
    source = inspect.getsource(BasiraQueryService.execute)

    assert "self.planner.build" not in source
    assert "self.retriever.retrieve" not in source
    assert "governed_runtime.execute" in source


def test_kursi_runs_e1_e2_e3_e4_end_to_end() -> None:
    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    result = runtime.execute(
        question=("ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟")
    )

    references = {
        node.reference for node in result.retrieval.evidence if node.reference
    }

    assert references == {"2:255"}

    assert result.relation is not None
    assert "tafsir:right:2:255" in result.relation.supporting_evidence_ids
    assert "quran:2:255" in result.relation.context_only_evidence_ids

    assert result.sufficiency is not None
    assert result.sufficiency.state is ClaimSufficiencyState.SUFFICIENT

    assert result.dependency is not None
    assert result.dependency.state is ClaimResolutionState.READY

    assert result.answer.has_answer
    assert result.answer.semantic_claim_verification == "pass"
    assert "كرسي" in normalize_semantic_text(result.answer.answer or "")


def test_canonical_quote_beats_wrong_manual_2_43_hint() -> None:
    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    result = runtime.execute(
        question=("ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟"),
        quran_reference="2:43",
    )

    refs = {node.reference for node in result.retrieval.evidence if node.reference}

    assert refs == {"2:255"}
    assert result.answer.has_answer


def test_taqwa_irrelevant_tafsir_cannot_support_definition() -> None:
    evaluator = PublicTaskEvidenceEvaluator()
    task = _task("ما معنى التقوى؟")

    irrelevant = EvidenceNode(
        evidence_id="tafsir:riba",
        domain=EvidenceDomain.TAFSIR,
        text=("العبد ينبغي له مراعاة الأوامر والنواهي."),
        source_id="tafsir:trusted",
        reference="3:130",
    )

    relevant = EvidenceNode(
        evidence_id="tafsir:taqwa",
        domain=EvidenceDomain.TAFSIR,
        text=("التقوى لفظ يشرح هذا المعنى في النص التفسيري."),
        source_id="tafsir:trusted",
        reference="2:2",
    )

    assert (
        evaluator.evaluate(
            task=task,
            evidence=irrelevant,
        ).relation
        is ClaimEvidenceRelation.IRRELEVANT
    )

    assert (
        evaluator.evaluate(
            task=task,
            evidence=relevant,
        ).relation
        is ClaimEvidenceRelation.SUPPORTS
    )


def test_direct_quran_canonical_text_supports_by_verified_identity() -> None:
    evaluator = PublicTaskEvidenceEvaluator()

    task = ClaimTask(
        task_id="claim:quran-direct",
        claim_text="هات نص الآية 2:255",
        frame=ReligiousReasoningFrame(
            frame_id="reasoning:quran_lookup",
            question="هات نص الآية 2:255",
            primary_discipline=ReligiousDiscipline.QURAN,
            reasoning_mode=ReasoningMode.DIRECT_GROUNDING,
        ),
        context_requirement=ContextRequirement(
            required=frozenset(
                {
                    EvidenceNeed.CANONICAL_TEXT,
                    EvidenceNeed.SOURCE_PROVENANCE,
                }
            ),
        ),
    )

    canonical = EvidenceNode(
        evidence_id="quran:2:255",
        domain=EvidenceDomain.QURAN,
        text=(
            "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ "
            "الْحَيُّ الْقَيُّومُ"
        ),
        source_id="quran:canonical",
        reference="2:255",
        claim_type="quran_text",
        related_quran=("2:255",),
    )

    assert (
        evaluator.evaluate(
            task=task,
            evidence=canonical,
        ).relation
        is ClaimEvidenceRelation.SUPPORTS
    )

    # Do not create a blanket Quran bypass. Only canonical
    # Quran-text evidence receives identity-based support.
    noncanonical = EvidenceNode(
        evidence_id="quran:context",
        domain=EvidenceDomain.QURAN,
        text="نص لا يطابق ألفاظ الطلب.",
        source_id="quran:canonical",
        reference="2:255",
        claim_type="context",
        related_quran=("2:255",),
    )

    assert (
        evaluator.evaluate(
            task=task,
            evidence=noncanonical,
        ).relation
        is ClaimEvidenceRelation.IRRELEVANT
    )


def test_e4_is_literal_fail_closed_not_always_supports() -> None:
    evaluator = LiteralGeneratedClaimEvaluator()

    evidence = EvidenceNode(
        evidence_id="evidence:1",
        domain=EvidenceDomain.TAFSIR,
        text="هذا نص تفسيري أصلي من المصدر.",
        source_id="tafsir:trusted",
        reference="2:255",
    )

    supported = StructuredClaim(
        axis_id="tafsir",
        claim_id="claim:1",
        text="هذا نص تفسيري أصلي",
        evidence_ids=("evidence:1",),
    )

    invented = StructuredClaim(
        axis_id="tafsir",
        claim_id="claim:2",
        text="دعوى جديدة غير موجودة في المصدر",
        evidence_ids=("evidence:1",),
    )

    assert (
        evaluator.evaluate(
            claim=supported,
            evidence=evidence,
        ).relation
        is ClaimEvidenceRelation.SUPPORTS
    )

    assert (
        evaluator.evaluate(
            claim=invented,
            evidence=evidence,
        ).relation
        is not ClaimEvidenceRelation.SUPPORTS
    )


def test_public_semantic_verifier_is_on_by_default() -> None:
    service = BasiraQueryService(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    assert service.composer.semantic_verifier is not None


class NoPublicationAuthorizerRetriever:
    """
    Same hostile retrieval behavior, but the runtime
    cannot see a publication capability.

    Even if the delegate internally admits its nodes,
    publication must fail closed.
    """

    def __init__(
        self,
    ) -> None:
        self.delegate = HostileUnifiedRetriever()

        self.retrievers = self.delegate.retrievers

    def retrieve(
        self,
        plan,
        *,
        limit_per_domain: int = 10,
    ):
        return self.delegate.retrieve(
            plan,
            limit_per_domain=(limit_per_domain),
        )


def test_missing_publication_authorizer_fails_closed() -> None:
    runtime = _TrustedRuntime(
        retriever=(NoPublicationAuthorizerRetriever()),  # type: ignore[arg-type]
    )

    result = runtime.execute(
        question=("ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟")
    )

    assert not result.answer.has_answer

    assert result.answer.used_evidence_ids == ()

    assert result.answer.semantic_claim_verification == "not_enabled"


def test_public_runtime_uses_final_output_firewall() -> None:
    from basira.answer.final_output import (
        FinalOutputVerifier,
    )
    from basira.answer.governed_composer import (
        GovernedGroundedAnswerComposer,
    )

    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    assert isinstance(
        runtime.composer,
        GovernedGroundedAnswerComposer,
    )

    assert isinstance(
        runtime.composer.final_output_verifier,
        FinalOutputVerifier,
    )


def test_public_runtime_defaults_to_noop_route_governance():
    from basira.reasoning.route_governor import (
        RouteGovernor,
    )
    from basira.reasoning.route_proposal import (
        NoOpRouteProposer,
    )

    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    assert isinstance(
        runtime.route_proposer,
        NoOpRouteProposer,
    )

    assert isinstance(
        runtime.route_governor,
        RouteGovernor,
    )


def test_hostile_route_proposal_cannot_override_specific_quran_intent():
    from basira.reasoning.route_proposal import (
        RouteProposal,
    )
    from basira.retrieval.query_understanding import (
        BasiraIntent,
    )

    class HostileRouteProposer:
        def propose(
            self,
            *,
            understanding,
        ) -> RouteProposal:
            del understanding

            return RouteProposal(
                proposed_intent=(BasiraIntent.HADITH_AUTHENTICITY),
                confidence=1.0,
                reason_codes=("hostile:wrong_intent",),
            )

    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
        route_proposer=(HostileRouteProposer()),
    )

    result = runtime.execute(
        question=("ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟")
    )

    assert result.understanding.primary_intent is BasiraIntent.QURAN_MEANING

    references = {
        node.reference for node in result.retrieval.evidence if node.reference
    }

    assert references == {
        "2:255",
    }

    assert result.answer.has_answer


def test_structured_llm_cannot_override_canonical_quran_public_path():
    from collections.abc import Mapping

    from basira.reasoning.llm_route_proposer import (
        LLMRouteProposer,
    )
    from basira.retrieval.query_understanding import (
        BasiraIntent,
    )

    class HostileStructuredClient:
        def complete_structured(
            self,
            *,
            instruction: str,
            input_data: Mapping[str, object],
            schema: Mapping[str, object],
        ) -> Mapping[str, object]:
            del instruction
            del input_data
            del schema

            return {
                "proposed_intent": ("hadith_authenticity"),
                "confidence": 1.0,
                "canonical_reference": ("2:43"),
                "publish": True,
            }

    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
        route_proposer=LLMRouteProposer(client=(HostileStructuredClient())),
    )

    result = runtime.execute(
        question=("ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟")
    )

    assert result.understanding.primary_intent is BasiraIntent.QURAN_MEANING

    references = {
        node.reference for node in result.retrieval.evidence if node.reference
    }

    assert references == {"2:255"}

    assert result.answer.has_answer


def test_named_ayat_al_kursi_lookup_resolves_canonical_2_255() -> None:
    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    result = runtime.execute(
        question="آية الكرسي",
    )

    references = {
        node.reference
        for node in result.retrieval.evidence
        if node.domain is EvidenceDomain.QURAN
    }

    assert references == {"2:255"}
    assert result.answer.has_answer


def test_natural_ayat_al_kursi_question_resolves_canonical_2_255() -> None:
    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    result = runtime.execute(
        question="ما هي آية الكرسي؟",
    )

    references = {
        node.reference
        for node in result.retrieval.evidence
        if node.domain is EvidenceDomain.QURAN
    }

    assert references == {"2:255"}
    assert result.answer.has_answer


def test_named_ayat_al_kursi_tafsir_resolves_and_answers() -> None:
    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    result = runtime.execute(
        question="تفسير آية الكرسي",
    )

    quran_references = {
        node.reference
        for node in result.retrieval.evidence
        if node.domain is EvidenceDomain.QURAN
    }

    assert quran_references == {"2:255"}

    assert any(
        node.domain is EvidenceDomain.TAFSIR for node in result.retrieval.evidence
    )

    assert result.answer.has_answer


def test_kursi_spelling_variants_are_resolved_without_frontend_anchor() -> None:
    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    lookup_cases = (
        "آية الكرسي",
        "اية الكرسي",
        "آيه الكرسي",
        "ايه الكرسي",
    )

    for question in lookup_cases:
        result = runtime.execute(
            question=question,
        )

        assert result.understanding.primary_intent is BasiraIntent.QURAN_LOOKUP

        quran = [
            node
            for node in result.retrieval.evidence
            if node.domain is EvidenceDomain.QURAN
        ]

        assert quran
        assert all(node.reference == "2:255" for node in quran)
        assert result.answer.has_answer


def test_kursi_tafsir_spelling_variants_are_resolved_without_frontend_anchor() -> None:
    runtime = _runtime_with_explicit_test_authority(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    meaning_cases = (
        "تفسير آية الكرسي",
        "تفسير اية الكرسي",
        "تفسير آيه الكرسي",
        "تفسير ايه الكرسي",
    )

    for question in meaning_cases:
        result = runtime.execute(
            question=question,
        )

        assert result.understanding.primary_intent is BasiraIntent.QURAN_MEANING

        quran = [
            node
            for node in result.retrieval.evidence
            if node.domain is EvidenceDomain.QURAN
        ]

        tafsir = [
            node
            for node in result.retrieval.evidence
            if node.domain is EvidenceDomain.TAFSIR
        ]

        assert quran
        assert tafsir

        assert all(node.reference == "2:255" for node in quran)

        assert result.answer.has_answer


def test_egyptian_interrogative_eih_is_not_globally_rewritten_as_ayah() -> None:
    service = BasiraQueryUnderstandingService()

    result = service.understand("الحديث ده صح ولا ايه؟")

    assert result.primary_intent is BasiraIntent.HADITH_AUTHENTICITY
