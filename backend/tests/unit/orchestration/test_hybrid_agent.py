from basira.orchestration.hybrid_agent import (
    HybridAgentHandoff,
    HybridPublicationObligation,
    HybridResolverAgent,
    govern_hybrid_resolution,
)
from basira.retrieval.hybrid_query_resolver import (
    HybridLookupMode,
    HybridQueryResolution,
    HybridTopic,
    ResponseGovernanceLevel,
)


def resolution(
    *,
    topic: HybridTopic,
    capability: str,
    level: ResponseGovernanceLevel = (ResponseGovernanceLevel.B),
    personalized: bool = False,
    cross_language: bool = False,
) -> HybridQueryResolution:
    return HybridQueryResolution(
        topic=topic,
        language="ar",
        lookup_mode=(HybridLookupMode.CONCEPT),
        response_level=level,
        personalized=personalized,
        capability=capability,
        allow_cross_language_fallback=(cross_language),
        reasons=("test",),
    )


def test_quran_handoffs_to_existing_governed_core() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.QURAN,
            capability="quran",
            level=ResponseGovernanceLevel.A,
        )
    )

    assert plan.handoff is HybridAgentHandoff.GOVERNED_CORE

    assert plan.publication_obligation is HybridPublicationObligation.GOVERNED_ANSWER

    assert plan.capability == "quran"
    assert plan.direct_public_answer_allowed


def test_hadith_handoffs_without_selecting_source() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.HADITH,
            capability="hadith",
            level=ResponseGovernanceLevel.A,
        )
    )

    assert plan.handoff is HybridAgentHandoff.GOVERNED_CORE

    assert plan.capability == "hadith"

    assert not hasattr(
        plan,
        "source_id",
    )

    assert not hasattr(
        plan,
        "authority",
    )


def test_tafsir_handoffs_to_governed_core() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.TAFSIR,
            capability="tafsir",
        )
    )

    assert plan.handoff is HybridAgentHandoff.GOVERNED_CORE

    assert plan.capability == "tafsir"


def test_general_fiqh_preserves_disagreement() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.FIQH,
            capability="general_fiqh",
            level=ResponseGovernanceLevel.C,
        )
    )

    assert plan.publication_obligation is (
        HybridPublicationObligation.PRESERVE_DISAGREEMENT
    )

    assert not plan.requires_expert_referral
    assert plan.direct_public_answer_allowed


def test_personal_fiqh_cannot_be_directly_published() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.FIQH,
            capability="general_fiqh",
            level=ResponseGovernanceLevel.D,
            personalized=True,
        )
    )

    assert plan.handoff is HybridAgentHandoff.GOVERNED_CORE

    assert plan.publication_obligation is (
        HybridPublicationObligation.GENERAL_INFORMATION_AND_REFER
    )

    assert plan.requires_expert_referral
    assert not plan.direct_public_answer_allowed


def test_shubuhat_is_material_only() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.SHUBUHAT,
            capability="shubuhat_faq",
        )
    )

    assert plan.handoff is HybridAgentHandoff.GENERAL_MATERIAL

    assert plan.material_only
    assert not plan.direct_public_answer_allowed


def test_terminology_is_material_only() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.TERMINOLOGY,
            capability="translation_terminology",
        )
    )

    assert plan.material_only

    assert plan.publication_obligation is HybridPublicationObligation.DISPLAY_ONLY


def test_general_concept_is_material_only() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.GENERAL,
            capability="general_islamic",
        )
    )

    assert plan.handoff is HybridAgentHandoff.GENERAL_MATERIAL

    assert not plan.direct_public_answer_allowed


def test_phase_two_domains_fail_closed() -> None:
    for topic, capability in (
        (
            HybridTopic.AQEEDAH,
            "aqeedah",
        ),
        (
            HybridTopic.HISTORY,
            "seerah_history",
        ),
    ):
        plan = govern_hybrid_resolution(
            resolution(
                topic=topic,
                capability=capability,
            )
        )

        assert plan.handoff is HybridAgentHandoff.FAIL_CLOSED

        assert plan.unavailable_reason == "phase_2_capability_not_admitted"


def test_cross_language_fallback_fails_closed() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.TAFSIR,
            capability="tafsir",
            cross_language=True,
        )
    )

    assert plan.handoff is HybridAgentHandoff.FAIL_CLOSED

    assert plan.unavailable_reason == "cross_language_fallback_not_permitted"


def test_capability_laundering_fails_closed() -> None:
    plan = govern_hybrid_resolution(
        resolution(
            topic=HybridTopic.SHUBUHAT,
            capability="tafsir",
        )
    )

    assert plan.handoff is HybridAgentHandoff.FAIL_CLOSED

    assert plan.unavailable_reason == "resolver_capability_mismatch"


def test_agent_uses_existing_resolver() -> None:
    agent = HybridResolverAgent()

    plan = agent.plan(
        question=("لماذا يعبد المسلمون الكعبة؟"),
        language="ar",
    )

    assert plan.resolution.topic is HybridTopic.SHUBUHAT

    assert plan.handoff is HybridAgentHandoff.GENERAL_MATERIAL

    assert plan.capability == "shubuhat_faq"


def test_agent_preserves_real_fiqh_obligation() -> None:
    agent = HybridResolverAgent()

    plan = agent.plan(
        question=("هل لمس المرأة فرجها ينقض الوضوء؟"),
        language="ar",
    )

    assert plan.resolution.topic is HybridTopic.FIQH

    assert plan.publication_obligation is (
        HybridPublicationObligation.PRESERVE_DISAGREEMENT
    )

    assert plan.direct_public_answer_allowed
