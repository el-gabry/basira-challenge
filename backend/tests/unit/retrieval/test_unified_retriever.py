from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
)


class DummyHadithRetriever:
    def retrieve(
        self,
        *,
        understanding,
        target,
        limit: int = 10,
    ):
        del understanding
        del target
        del limit

        return (
            EvidenceNode(
                evidence_id=(
                    "hadith:test:1"
                ),
                domain=(
                    EvidenceDomain.HADITH
                ),
                text="نص الحديث",
                source_id="test-source",
                reference="test:1",
                claim_type="hadith_text",
            ),
        )


def build_plan(
    query: str,
):
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(query)
    )

    return (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )


def test_hadith_plan_returns_hadith_evidence() -> None:
    retriever = (
        BasiraUnifiedRetriever(
            {
                EvidenceDomain.HADITH:
                    DummyHadithRetriever(),
            }
        )
    )

    result = retriever.retrieve(
        build_plan(
            "ما صحة هذا الحديث؟"
        )
    )

    assert result.has_evidence

    assert (
        len(result.evidence)
        == 1
    )

    assert (
        result.evidence[0].domain
        is EvidenceDomain.HADITH
    )

    assert not (
        result.unavailable_domains
    )


def test_missing_tafsir_retriever_is_explicit() -> None:
    retriever = (
        BasiraUnifiedRetriever(
            {}
        )
    )

    result = retriever.retrieve(
        build_plan(
            "ما معنى آية الكرسي؟"
        )
    )

    assert (
        EvidenceDomain.QURAN
        in result.unavailable_domains
    )

    assert (
        EvidenceDomain.TAFSIR
        in result.unavailable_domains
    )

    assert not result.has_evidence
