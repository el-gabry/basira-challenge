from __future__ import annotations

from dataclasses import dataclass

from basira.evidence.models import (
    ContextRequirement,
)
from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.reasoning.routing import (
    ReligiousReasoningRouter,
)
from basira.retrieval.arabic_query import (
    build_arabic_query,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
)
from basira.retrieval.shamela_scout import (
    InMemoryShamelaBackend,
    ShamelaHybridEvidenceScout,
    ShamelaPlanningAdvisor,
    ShamelaScoutPlan,
    ShamelaScoutStopReason,
)
from basira.sources.shamela.contracts import (
    ShamelaCorpusManifest,
    ShamelaPassageRecord,
)

HASH = "b" * 64


def understanding(
    text: str,
    intent: BasiraIntent,
) -> BasiraQueryUnderstanding:
    return BasiraQueryUnderstanding(
        query=build_arabic_query(text),
        primary_intent=intent,
        risk_tags=frozenset(),
        entities=(),
        context_requirement=(ContextRequirement()),
        confidence=1.0,
    )


def route(
    text: str,
    intent: BasiraIntent,
):
    return ReligiousReasoningRouter().route(
        understanding(
            text,
            intent,
        )
    )


def passage(
    *,
    source_id: str,
    book_id: str,
    page_id: str,
    text: str,
    domain: ScholarlyDomain,
    madhhab: str | None = None,
    parent_text: str | None = None,
):
    return ShamelaPassageRecord(
        source_id=source_id,
        source_version="v1",
        snapshot_id="fixture-v1",
        snapshot_sha256=HASH,
        book_id=book_id,
        page_id=page_id,
        domain=domain,
        work_title=(f"book-{book_id}"),
        text=text,
        author_name=(f"author-{book_id}"),
        madhhab=madhhab,
        discipline=domain.value,
        book_family=(
            "classical_fiqh"
            if domain is ScholarlyDomain.FIQH
            else (
                "contemporary_fatwa"
                if domain is ScholarlyDomain.FATWA
                else domain.value
            )
        ),
        parent_text=(parent_text),
    ).to_scholarly_passage()


def manifest(
    *source_ids: str,
    complete: bool = False,
) -> ShamelaCorpusManifest:
    return ShamelaCorpusManifest(
        corpus_id="fixture",
        snapshot_id="fixture-v1",
        snapshot_sha256=HASH,
        source_ids=source_ids,
        attested_complete=complete,
    )


def test_pure_hadith_authenticity_does_not_use_shamela() -> None:
    backend = InMemoryShamelaBackend(
        (),
        manifest=manifest("dummy"),
    )

    result = ShamelaHybridEvidenceScout(backend=backend).scout(
        route(
            "هل هذا الحديث صحيح؟",
            BasiraIntent.HADITH_AUTHENTICITY,
        )
    )

    assert result.stop_reason is ShamelaScoutStopReason.NOT_APPLICABLE

    assert result.evidence == ()


def test_classical_fiqh_returns_attributed_evidence() -> None:
    item = passage(
        source_id="fiqh-source",
        book_id="44",
        page_id="9",
        text=("البيع الصحيح له شروط معتبرة"),
        domain=ScholarlyDomain.FIQH,
        madhhab="hanafi",
        parent_text=("باب شروط البيع"),
    )

    backend = InMemoryShamelaBackend(
        (item,),
        manifest=manifest("fiqh-source"),
    )

    result = ShamelaHybridEvidenceScout(backend=backend).scout(
        route(
            "ما شروط البيع الصحيح؟",
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert result.stop_reason is ShamelaScoutStopReason.RETRIEVAL_COVERAGE_MET

    assert len(result.evidence) == 1

    assert result.evidence[0].work_id == "44"

    assert result.evidence[0].author_name == "author-44"

    assert result.hits[0].parent_context == "باب شروط البيع"


def test_comparative_fiqh_requires_source_diversity() -> None:
    hanafi = passage(
        source_id="hanafi",
        book_id="h1",
        page_id="1",
        text=("البيع في المذهب الحنفي له شروط"),
        domain=ScholarlyDomain.FIQH,
        madhhab="hanafi",
    )

    maliki = passage(
        source_id="maliki",
        book_id="m1",
        page_id="1",
        text=("البيع في المذهب المالكي له شروط"),
        domain=ScholarlyDomain.FIQH,
        madhhab="maliki",
    )

    backend = InMemoryShamelaBackend(
        (
            hanafi,
            maliki,
        ),
        manifest=manifest(
            "hanafi",
            "maliki",
        ),
    )

    result = ShamelaHybridEvidenceScout(backend=backend).scout(
        route(
            ("ما أقوال المذاهب في البيع؟"),
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert result.stop_reason is ShamelaScoutStopReason.RETRIEVAL_COVERAGE_MET

    assert {hit.identity.madhhab for hit in result.hits} == {
        "hanafi",
        "maliki",
    }


def test_comparative_single_madhhab_does_not_fake_coverage() -> None:
    hanafi = passage(
        source_id="hanafi",
        book_id="h1",
        page_id="1",
        text=("البيع في المذهب الحنفي له شروط"),
        domain=ScholarlyDomain.FIQH,
        madhhab="hanafi",
    )

    backend = InMemoryShamelaBackend(
        (hanafi,),
        manifest=manifest("hanafi"),
    )

    result = ShamelaHybridEvidenceScout(backend=backend).scout(
        route(
            ("ما أقوال المذاهب في البيع؟"),
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert result.stop_reason is ShamelaScoutStopReason.BUDGET_EXHAUSTED

    assert result.has_evidence

    assert result.subqueries_used <= 3

    assert result.passes_used <= 3


def test_contemporary_fiqh_requires_fatwa_and_classical_fiqh() -> None:
    classical = passage(
        source_id="fiqh",
        book_id="f1",
        page_id="1",
        text=("المال والبيع والصرف له أحكام"),
        domain=ScholarlyDomain.FIQH,
    )

    modern = passage(
        source_id="fatwa",
        book_id="c1",
        page_id="1",
        text=("حكم البيتكوين والعملات الرقمية"),
        domain=ScholarlyDomain.FATWA,
    )

    backend = InMemoryShamelaBackend(
        (
            classical,
            modern,
        ),
        manifest=manifest(
            "fiqh",
            "fatwa",
        ),
    )

    result = ShamelaHybridEvidenceScout(backend=backend).scout(
        route(
            "ما حكم البيتكوين؟",
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert result.stop_reason is ShamelaScoutStopReason.RETRIEVAL_COVERAGE_MET

    assert {item.domain for item in result.evidence} == {
        ScholarlyDomain.FIQH.value,
        ScholarlyDomain.FATWA.value,
    }


def test_snapshot_hash_mismatch_fails_closed() -> None:
    item = passage(
        source_id="source",
        book_id="1",
        page_id="1",
        text="البيع له شروط",
        domain=ScholarlyDomain.FIQH,
    )

    bad_manifest = ShamelaCorpusManifest(
        corpus_id="fixture",
        snapshot_id="fixture-v1",
        snapshot_sha256=("c" * 64),
        source_ids=("source",),
    )

    try:
        InMemoryShamelaBackend(
            (item,),
            manifest=bad_manifest,
        )
    except ValueError as exc:
        assert "snapshot hash" in str(exc)
    else:
        raise AssertionError("hash mismatch must fail closed")


def test_absence_requires_attested_complete_snapshot() -> None:
    question = "ما حكم مسألة لا توجد في هذا corpus؟"

    incomplete_backend = InMemoryShamelaBackend(
        (),
        manifest=manifest(
            "source",
            complete=False,
        ),
    )

    incomplete_result = ShamelaHybridEvidenceScout(backend=(incomplete_backend)).scout(
        route(
            question,
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert incomplete_result.stop_reason is ShamelaScoutStopReason.BUDGET_EXHAUSTED

    complete_backend = InMemoryShamelaBackend(
        (),
        manifest=manifest(
            "source",
            complete=True,
        ),
    )

    complete_result = ShamelaHybridEvidenceScout(backend=complete_backend).scout(
        route(
            question,
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert complete_result.stop_reason is ShamelaScoutStopReason.RESOLVED_ABSENCE


@dataclass
class StubAdvisor:
    calls: int = 0

    def propose_queries(
        self,
        *,
        plan: ShamelaScoutPlan,
        observations,
        max_queries: int,
    ) -> tuple[
        str,
        ...,
    ]:
        del plan
        del observations

        self.calls += 1

        return ("الصرف",) if max_queries > 0 else ()


def test_planning_advisor_can_reformulate_but_not_create_evidence() -> None:
    item = passage(
        source_id="fiqh",
        book_id="1",
        page_id="1",
        text=("أحكام الصرف والتقابض"),
        domain=ScholarlyDomain.FIQH,
    )

    backend = InMemoryShamelaBackend(
        (item,),
        manifest=manifest("fiqh"),
    )

    advisor: ShamelaPlanningAdvisor = StubAdvisor()

    result = ShamelaHybridEvidenceScout(
        backend=backend,
        advisor=advisor,
    ).scout(
        route(
            ("ما حكم معاملة غير مذكورة بهذه الألفاظ؟"),
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert result.stop_reason is ShamelaScoutStopReason.RETRIEVAL_COVERAGE_MET

    assert result.evidence[0].text == "أحكام الصرف والتقابض"

    assert advisor.calls >= 1

    # The advisor only proposed a query.
    # The returned text still comes from the
    # governed source passage.
    assert result.evidence[0].source_id == "fiqh"


def test_agent_budget_is_hard_bounded() -> None:
    backend = InMemoryShamelaBackend(
        (),
        manifest=manifest("source"),
    )

    result = ShamelaHybridEvidenceScout(
        backend=backend,
        advisor=StubAdvisor(),
    ).scout(
        route(
            ("ما أقوال المذاهب في مسألة غير موجودة؟"),
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert result.subqueries_used <= 3

    assert result.passes_used <= 3
