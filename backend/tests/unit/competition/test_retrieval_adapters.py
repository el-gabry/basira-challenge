from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from basira.competition.madhhab_authority import (
    MadhhabBookRetrievalMode,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_adapters import (
    BayyinatMaterialAdapter,
    JamharaResolverConfig,
    JamharaTerminologyAdapter,
    PolicyBoundShamelaPlanner,
)
from basira.competition.retrieval_bridge import (
    CompetitionMaterialRole,
    CompetitionRetrievalRequest,
)
from basira.evidence.models import (
    ContextRequirement,
)
from basira.reasoning.routing import (
    ReligiousReasoningRouter,
)
from basira.retrieval.arabic_query import (
    build_arabic_query,
)
from basira.retrieval.fiqh_policy_compiler import (
    FiqhRetrievalPolicyEnvelope,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
)


def ready_bayyinat_state():
    return SimpleNamespace(
        eligibility=SimpleNamespace(value="eligible"),
        exact_artifact_governed=True,
        source_identity_verified=True,
    )


def test_bayyinat_is_material_not_primary_evidence():
    adapter = BayyinatMaterialAdapter(
        search=lambda query, limit: [
            {
                "unit_id": "u-1",
                "question": ("كيف نجيب عن الشبهة؟"),
                "answer": ("نص من المصدر نفسه"),
                "source_url": ("https://example.test/u-1"),
            }
        ],
        runtime_loader=(ready_bayyinat_state),
    )

    result = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.SHUBUHAT_FAQ),
            query="شبهة",
        )
    )

    assert len(result) == 1

    material = result[0]

    assert material.role is CompetitionMaterialRole.CONVERSATIONAL

    assert "نص من المصدر نفسه" in material.text

    assert material.source_id == "bayyinat-v1"


def test_bayyinat_fails_closed_when_runtime_not_ready():
    adapter = BayyinatMaterialAdapter(
        search=lambda query, limit: [
            {
                "text": "must not leak",
            }
        ],
        runtime_loader=lambda: SimpleNamespace(
            eligibility=(SimpleNamespace(value=("pending_audit"))),
            exact_artifact_governed=False,
            source_identity_verified=False,
        ),
    )

    result = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.SHUBUHAT_FAQ),
            query="test",
        )
    )

    assert result == ()


class FakeStore:
    def __init__(
        self,
        path: Path,
    ) -> None:
        self.path = path
        self.closed = False

    def close(
        self,
    ) -> None:
        self.closed = True


def ready_jamhara_state():
    return SimpleNamespace(
        source_id="jamhara-live-v1",
        eligible=True,
        source_identity_verified=True,
        implementation_governed=True,
        terminology_only=True,
        cross_domain_primary_evidence=False,
    )


def test_jamhara_is_terminology_material_only(
    tmp_path: Path,
):
    def resolver(**kwargs):
        return {
            "word_id": 17,
            "resolved_language": "ar",
            "title": "الربا",
            "terminological_meaning": ("معنى اصطلاحي من المصدر"),
            "source_url": ("https://islamic-content.com/dictionary/word/17/ar"),
        }

    adapter = JamharaTerminologyAdapter(
        config=JamharaResolverConfig(
            raw_cache_dir=(tmp_path / "raw"),
            warmer_state_db=(tmp_path / "warm.sqlite3"),
            semantic_store_db=(tmp_path / "semantic.sqlite3"),
            allow_network=False,
        ),
        resolver=resolver,
        runtime_loader=(ready_jamhara_state),
        store_factory=FakeStore,
    )

    result = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.TRANSLATION_TERMINOLOGY),
            query="الربا",
        )
    )

    assert len(result) == 1

    assert result[0].role is CompetitionMaterialRole.TERMINOLOGY

    assert result[0].source_id == "jamhara-live-v1"

    assert "معنى اصطلاحي من المصدر" in result[0].text


def test_jamhara_cross_domain_authority_is_rejected(
    tmp_path: Path,
):
    adapter = JamharaTerminologyAdapter(
        config=JamharaResolverConfig(
            raw_cache_dir=(tmp_path / "raw"),
            warmer_state_db=(tmp_path / "warm.sqlite3"),
            semantic_store_db=(tmp_path / "semantic.sqlite3"),
        ),
        resolver=lambda **kwargs: {
            "terminological_meaning": ("must not leak"),
        },
        runtime_loader=lambda: SimpleNamespace(
            source_id="bad",
            eligible=True,
            source_identity_verified=True,
            implementation_governed=True,
            terminology_only=True,
            cross_domain_primary_evidence=True,
        ),
        store_factory=FakeStore,
    )

    result = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.TRANSLATION_TERMINOLOGY),
            query="test",
        )
    )

    assert result == ()


def route(
    text: str,
):
    understanding = BasiraQueryUnderstanding(
        query=build_arabic_query(text),
        primary_intent=(BasiraIntent.FIQH_QUESTION),
        risk_tags=frozenset(),
        entities=(),
        context_requirement=(ContextRequirement()),
        confidence=1.0,
    )

    return ReligiousReasoningRouter().route(understanding)


def test_policy_bound_fiqh_planner_applies_work_allowlist():
    envelope = FiqhRetrievalPolicyEnvelope(
        requested_madhhabs=(),
        retrieval_mode=(MadhhabBookRetrievalMode.MUTAMAD_ONLY),
        primary_work_ids=(
            "book-1",
            "book-2",
        ),
        supporting_work_ids=("support-only",),
        forbidden_fallbacks=(
            "generic_shamela_fallback",
            "ungoverned_web_fallback",
        ),
        policy_fingerprint=("a" * 64),
    )

    plan = PolicyBoundShamelaPlanner(envelope).build(route("ما حكم الشفعة؟"))

    assert plan.allowed_work_ids == (
        "book-1",
        "book-2",
    )

    assert plan.policy_fingerprint == "a" * 64

    assert all(
        task.allowed_work_ids
        == (
            "book-1",
            "book-2",
        )
        for task in plan.initial_tasks
    )

    assert all(task.policy_fingerprint == "a" * 64 for task in plan.initial_tasks)

    assert "support-only" not in plan.allowed_work_ids
