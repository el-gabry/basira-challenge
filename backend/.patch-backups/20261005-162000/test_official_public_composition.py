from __future__ import annotations

from basira.api.service import (
    build_default_query_service,
    build_public_official_retriever,
)
from basira.evidence.models import (
    EvidenceDomain,
)
from basira.retrieval.official_quran_retriever import (
    OfficialQuranDomainRetriever,
)
from basira.retrieval.official_tafsir_retriever import (
    OfficialTafsirDomainRetriever,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
)


def test_public_retriever_uses_official_domain_lanes():
    retriever = build_public_official_retriever()

    assert isinstance(
        retriever,
        BasiraUnifiedRetriever,
    )

    assert isinstance(
        retriever.retrievers[EvidenceDomain.QURAN],
        OfficialQuranDomainRetriever,
    )

    assert isinstance(
        retriever.retrievers[EvidenceDomain.TAFSIR],
        OfficialTafsirDomainRetriever,
    )


def test_public_retriever_has_no_legacy_fallback_domains():
    retriever = build_public_official_retriever()

    assert set(retriever.retrievers) == {
        EvidenceDomain.QURAN,
        EvidenceDomain.TAFSIR,
    }

    assert EvidenceDomain.HADITH not in retriever.retrievers

    assert EvidenceDomain.REVELATION_CONTEXT not in retriever.retrievers


def test_default_query_service_uses_public_official_retriever():
    service = build_default_query_service()

    assert isinstance(
        service.retriever.retrievers[EvidenceDomain.QURAN],
        OfficialQuranDomainRetriever,
    )

    assert isinstance(
        service.retriever.retrievers[EvidenceDomain.TAFSIR],
        OfficialTafsirDomainRetriever,
    )

    assert service.scholarly_repository is None

    assert service.scholarly_runtime is None
