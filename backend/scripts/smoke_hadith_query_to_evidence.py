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
from basira.retrieval.hadith_index import (
    HadithLocalIndex,
)
from basira.retrieval.hadith_retriever import (
    HadithDomainRetriever,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
)
from basira.sources.hadith.hadeethenc.parser import (
    HadeethEncOfficialParser,
)
from basira.sources.hadith.hadeethenc.workbook import (
    load_hadeethenc_arabic_workbook,
    load_hadeethenc_english_workbook,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)

TARGET_ID = 1751


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--arabic",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--english",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    arabic = (
        load_hadeethenc_arabic_workbook(
            args.arabic
        )
    )

    english = (
        load_hadeethenc_english_workbook(
            args.english
        )
    )

    source_manifest = SourceManifest(
        source_id="hadeethenc-official",
        source_name=(
            "HadeethEnc Official Hadith Releases"
        ),
        domain=SourceDomain.HADITH,
        role=(
            SourceRole.AUTHORITATIVE_REFERENCE
        ),
        status=SourceStatus.APPROVED,
        integrity_status=(
            IntegrityStatus.VERIFIED
        ),
    )

    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [source_manifest]
        )
    )

    index = HadithLocalIndex(
        runtime=runtime
    )

    english_by_id = {
        row.id: row
        for row in english.rows
    }

    parser = (
        HadeethEncOfficialParser()
    )

    for row in arabic.rows:
        translated = (
            english_by_id.get(
                row.id
            )
        )

        record = parser.parse(
            row.model_dump(),
            arabic_release=(
                arabic.release
            ),
            english_payload=(
                translated.model_dump()
                if translated
                is not None
                else None
            ),
            english_release=(
                english.release
                if translated
                is not None
                else None
            ),
        )

        index.add(record)

    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            f"ما صحة حديث رقم {TARGET_ID}؟"
        )
    )

    assert (
        understanding.primary_intent
        is BasiraIntent
        .HADITH_AUTHENTICITY
    )

    plan = (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )

    unified = (
        BasiraUnifiedRetriever(
            {
                EvidenceDomain.HADITH:
                    HadithDomainRetriever(
                        index=index,
                        default_collection_id=(
                            "hadeethenc"
                        ),
                    ),
            }
        )
    )

    result = unified.retrieve(
        plan
    )

    assert result.has_evidence
    assert not result.unavailable_domains

    text_nodes = [
        node
        for node in result.evidence
        if (
            node.claim_type
            == "hadith_text"
        )
    ]

    grade_nodes = [
        node
        for node in result.evidence
        if (
            node.claim_type
            == "hadith_grade"
        )
    ]

    assert text_nodes
    assert grade_nodes

    assert all(
        node.source_id
        == "hadeethenc-official"
        for node
        in result.evidence
    )

    print("=" * 88)
    print(
        "BASIRA — QUERY TO TRUSTED EVIDENCE"
    )
    print("=" * 88)

    print(
        "Query:",
        understanding.query.original_text,
    )

    print(
        "Intent:",
        understanding.primary_intent.value,
    )

    print(
        "Dialect:",
        understanding.query.dialect.value,
    )

    print(
        "Evidence nodes:",
        len(result.evidence),
    )

    print(
        "Hadith text nodes:",
        len(text_nodes),
    )

    print(
        "Grade nodes:",
        len(grade_nodes),
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
        "Reference:",
        text_nodes[0].reference,
    )

    print(
        "Grade:",
        grade_nodes[0].text,
    )

    print()
    print("=" * 88)
    print(
        "QUERY → TRUSTED EVIDENCE: PASS"
    )
    print("=" * 88)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
