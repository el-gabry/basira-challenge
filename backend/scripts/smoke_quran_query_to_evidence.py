from __future__ import annotations

import argparse
from pathlib import Path

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.models.source_manifest import (
    IntegrityStatus,
    SourceDomain,
    SourceManifest,
    SourceRole,
    SourceStatus,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)
from basira.retrieval.quran_retriever import (
    QuranDomainRetriever,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
)
from basira.sources.quran.repository import (
    QuranRepository,
)
from basira.sources.quran.tanzil.parser import (
    TANZIL_SOURCE_ID,
    TanzilQuranParser,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--uthmani",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--simple-plain",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    verses = (
        TanzilQuranParser()
        .parse_files(
            args.uthmani,
            args.simple_plain,
        )
    )

    assert len(verses) == 6_236

    repository = QuranRepository(
        verses
    )

    manifest = SourceManifest(
        source_id=TANZIL_SOURCE_ID,
        source_name="Tanzil Quran",
        domain=SourceDomain.QURAN,
        role=(
            SourceRole
            .INDEPENDENT_VERIFIER
        ),
        status=SourceStatus.APPROVED,
        integrity_status=(
            IntegrityStatus.VERIFIED
        ),
    )

    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )

    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما معنى الآية 2:255؟"
        )
    )

    assert (
        understanding.primary_intent
        is BasiraIntent.QURAN_MEANING
    )

    plan = (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )

    result = (
        BasiraUnifiedRetriever(
            {
                EvidenceDomain.QURAN:
                    QuranDomainRetriever(
                        repository=repository,
                        runtime=runtime,
                    ),
            }
        )
        .retrieve(plan)
    )

    quran_nodes = [
        node
        for node in result.evidence
        if (
            node.domain
            is EvidenceDomain.QURAN
        )
    ]

    assert len(quran_nodes) == 1

    assert (
        quran_nodes[0].reference
        == "2:255"
    )

    # Tafsir is requested by the retrieval plan but
    # intentionally not implemented yet.
    assert (
        EvidenceDomain.TAFSIR
        in result.unavailable_domains
    )

    print("=" * 88)
    print(
        "BASIRA — QURAN QUERY TO TRUSTED EVIDENCE"
    )
    print("=" * 88)

    print(
        "Loaded verses:",
        len(repository),
    )

    print(
        "Query:",
        understanding.query.original_text,
    )

    print(
        "Intent:",
        understanding.primary_intent.value,
    )

    print(
        "Quran evidence nodes:",
        len(quran_nodes),
    )

    print(
        "Reference:",
        quran_nodes[0].reference,
    )

    print(
        "Text:",
        quran_nodes[0].text,
    )

    print(
        "Unavailable domains:",
        sorted(
            domain.value
            for domain
            in result.unavailable_domains
        ),
    )

    print()
    print(
        "Quran retrieval: PASS"
    )

    print(
        "Context complete: NO "
        "(Tafsir retriever not implemented yet)"
    )

    print("=" * 88)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
