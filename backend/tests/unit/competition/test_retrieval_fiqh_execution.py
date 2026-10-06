from __future__ import annotations

from basira.competition.madhhab_authority import (
    MadhhabBookRetrievalMode,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_adapters import (
    FiqhHybridEvidenceAdapter,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
)
from basira.evidence.models import (
    EvidenceDomain,
)
from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.retrieval.fiqh_policy_compiler import (
    FiqhRetrievalPolicyEnvelope,
)
from basira.retrieval.shamela_scout import (
    InMemoryShamelaBackend,
)
from basira.sources.shamela.contracts import (
    ShamelaCorpusManifest,
    ShamelaPassageRecord,
)

HASH = "d" * 64


def passage(
    *,
    source_id: str,
    book_id: str,
    text: str,
):
    return ShamelaPassageRecord(
        source_id=source_id,
        source_version="v1",
        snapshot_id="competition-fixture-v1",
        snapshot_sha256=HASH,
        book_id=book_id,
        page_id="1",
        domain=ScholarlyDomain.FIQH,
        work_title=(f"كتاب فقهي {book_id}"),
        text=text,
        author_name="مؤلف",
        madhhab="hanafi",
        parent_text="باب الشفعة",
    ).to_scholarly_passage()


def test_hybrid_scout_executes_inside_policy_allowlist():
    allowed = passage(
        source_id="allowed-source",
        book_id="book-allowed",
        text=("الشفعة حق ثابت للشريك بشروطها المذكورة في باب الشفعة"),
    )

    blocked = passage(
        source_id="blocked-source",
        book_id="book-blocked",
        text=("الشفعة حق ثابت للشريك بشروطها المذكورة في باب الشفعة"),
    )

    manifest = ShamelaCorpusManifest(
        corpus_id="competition-fixture",
        snapshot_id=("competition-fixture-v1"),
        snapshot_sha256=HASH,
        source_ids=(
            "allowed-source",
            "blocked-source",
        ),
    )

    backend = InMemoryShamelaBackend(
        (
            allowed,
            blocked,
        ),
        manifest=manifest,
    )

    policy = FiqhRetrievalPolicyEnvelope(
        requested_madhhabs=(),
        retrieval_mode=(MadhhabBookRetrievalMode.MUTAMAD_ONLY),
        primary_work_ids=("book-allowed",),
        supporting_work_ids=("book-blocked",),
        forbidden_fallbacks=(
            "generic_shamela_fallback",
            "ungoverned_web_fallback",
        ),
        policy_fingerprint=("a" * 64),
    )

    adapter = FiqhHybridEvidenceAdapter(backend=backend)

    evidence = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.GENERAL_FIQH),
            query="ما حكم الشفعة؟",
            limit=5,
            fiqh_policy=policy,
        )
    )

    assert evidence

    assert all(node.domain is EvidenceDomain.FIQH for node in evidence)

    assert {node.work_id for node in evidence} == {
        "book-allowed",
    }

    assert all(node.work_id != "book-blocked" for node in evidence)


def test_supporting_work_cannot_enter_primary_lane():
    passage_only_supporting = passage(
        source_id="support-source",
        book_id="support-only",
        text="الشفعة من أبواب المعاملات",
    )

    manifest = ShamelaCorpusManifest(
        corpus_id="competition-fixture",
        snapshot_id=("competition-fixture-v1"),
        snapshot_sha256=HASH,
        source_ids=("support-source",),
    )

    backend = InMemoryShamelaBackend(
        (passage_only_supporting,),
        manifest=manifest,
    )

    policy = FiqhRetrievalPolicyEnvelope(
        requested_madhhabs=(),
        retrieval_mode=(MadhhabBookRetrievalMode.MUTAMAD_ONLY),
        primary_work_ids=(),
        supporting_work_ids=("support-only",),
        forbidden_fallbacks=(
            "generic_shamela_fallback",
            "ungoverned_web_fallback",
        ),
        policy_fingerprint=("b" * 64),
    )

    evidence = FiqhHybridEvidenceAdapter(backend=backend).retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.GENERAL_FIQH),
            query="ما حكم الشفعة؟",
            fiqh_policy=policy,
        )
    )

    assert evidence == ()
