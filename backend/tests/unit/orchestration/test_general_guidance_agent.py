from basira.orchestration.hybrid_agent import (
    HybridAgentHandoff,
    HybridResolverAgent,
)
from basira.retrieval.hybrid_query_resolver import (
    HybridTopic,
)


def test_bare_ayat_al_kursi_routes_to_existing_quran_core() -> None:
    plan = HybridResolverAgent().plan(
        question="آية الكرسي",
        language="ar",
    )

    assert any(
        hint.kind == "quran_reference_candidate"
        and hint.value == "2:255"
        and hint.verification_required
        for hint in plan.identity_hints
    )

    assert plan.resolution.topic is HybridTopic.QURAN

    assert plan.capability == "quran"

    assert plan.handoff is HybridAgentHandoff.GOVERNED_CORE


def test_ayat_al_kursi_meaning_stays_tafsir_core() -> None:
    plan = HybridResolverAgent().plan(
        question="ما معنى آية الكرسي؟",
        language="ar",
    )

    assert plan.resolution.topic is HybridTopic.TAFSIR

    assert plan.capability == "tafsir"

    assert plan.handoff is HybridAgentHandoff.GOVERNED_CORE

    assert any(
        hint.kind == "quran_reference_candidate"
        and hint.value == "2:255"
        and hint.verification_required
        for hint in plan.identity_hints
    )


def test_hadith_id_is_candidate_only() -> None:
    plan = HybridResolverAgent().plan(
        question="ما صحة حديث 65065؟",
        language="ar",
    )

    assert any(
        hint.kind == "hadith_identifier_candidate"
        and hint.value == "65065"
        and hint.verification_required
        for hint in plan.identity_hints
    )

    assert plan.handoff is HybridAgentHandoff.GOVERNED_CORE


def test_fiqh_is_only_handoff() -> None:
    plan = HybridResolverAgent().plan(
        question=("هل لمس المرأة فرجها ينقض الوضوء؟"),
        language="ar",
    )

    assert plan.resolution.topic is HybridTopic.FIQH

    assert plan.handoff is HybridAgentHandoff.GOVERNED_CORE

    assert not hasattr(plan, "ruling")
    assert not hasattr(plan, "madhhab")


def test_shubuhat_owned_by_general_agent() -> None:
    plan = HybridResolverAgent().plan(
        question=("لماذا يعبد المسلمون الكعبة؟"),
        language="ar",
    )

    assert plan.resolution.topic is HybridTopic.SHUBUHAT

    assert plan.handoff is HybridAgentHandoff.GENERAL_MATERIAL

    assert plan.capability == "shubuhat_faq"


def test_dawah_owned_by_general_agent() -> None:
    plan = HybridResolverAgent().plan(
        question=("كيف أدعو صديقي إلى الإسلام؟"),
        language="ar",
    )

    assert plan.resolution.topic is HybridTopic.DAWAH

    assert plan.handoff is HybridAgentHandoff.GENERAL_MATERIAL

    assert plan.capability == "dawah_general_content"


def test_terminology_owned_by_general_agent() -> None:
    plan = HybridResolverAgent().plan(
        question=("Translate tawhid into English"),
        language="en",
    )

    assert plan.resolution.topic is HybridTopic.TERMINOLOGY

    assert plan.handoff is HybridAgentHandoff.GENERAL_MATERIAL


def test_general_concept_is_material_only() -> None:
    plan = HybridResolverAgent().plan(
        question="ما هو الكرسي؟",
        language="ar",
    )

    assert plan.resolution.topic is HybridTopic.GENERAL

    assert plan.handoff is HybridAgentHandoff.GENERAL_MATERIAL
