from __future__ import annotations

from collections import Counter
from pathlib import Path

from basira.answer.composer import (
    GroundedAnswerComposer,
)
from basira.evidence.models import (
    EvidenceDomain,
)
from basira.evidence.service import (
    EvidenceDecisionService,
)
from basira.models.source_manifest import (
    SourceManifest,
)
from basira.retrieval.governed_scholarly_retriever import (
    GovernedScholarlyRetriever,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.quran_retriever import (
    QuranDomainRetriever,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
)
from basira.retrieval.revelation_context_retriever import (
    RevelationContextRetriever,
)
from basira.retrieval.tafsir_retriever import (
    TafsirDomainRetriever,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
)
from basira.sources.policy_catalog import (
    get_source_usage_policy,
)
from basira.sources.quran.repository import (
    QuranRepository,
)
from basira.sources.quran.tanzil.parser import (
    TanzilQuranParser,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)
from basira.sources.scholarly.repository import (
    ScholarlyRepository,
)
from basira.sources.scholarly.surahapp_parser import (
    SurahAppScholarlyParser,
)
from basira.sources.scholarly.surahapp_runtime import (
    SURAHAPP_REVELATION_CONTEXT_SOURCE_IDS,
    SURAHAPP_TAFSIR_SOURCE_IDS,
    build_surahapp_scholarly_runtime,
)

ROOT = Path("/mnt/c/Users/_/Downloads")

TANZIL_ROOT = ROOT / "tanzil"

SCHOLARLY_ROOT = ROOT / "basira-tafsir" / "surahapp" / "snapshot-v1"

MANIFEST_PATH = Path("data/manifests/quran/tanzil-quran-v1.1-uthmani.json")


def build_quran_runtime() -> FailClosedSourceRuntime:
    manifest = SourceManifest.model_validate_json(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )

    policy = get_source_usage_policy(manifest.source_id)

    manifest = manifest.model_copy(
        update={
            "usage_policy": policy,
        }
    )

    registry = TrustedSourceRegistry([manifest])

    return FailClosedSourceRuntime(registry)


def build_retriever() -> BasiraUnifiedRetriever:
    quran_verses = TanzilQuranParser().parse_files(
        uthmani_path=(TANZIL_ROOT / "quran-uthmani.txt"),
        simple_plain_path=(TANZIL_ROOT / "quran-simple-plain.txt"),
    )

    quran_repository = QuranRepository(quran_verses)

    scholarly_passages = SurahAppScholarlyParser().parse_snapshot(SCHOLARLY_ROOT)

    scholarly_repository = ScholarlyRepository(scholarly_passages)

    scholarly_runtime = build_surahapp_scholarly_runtime()

    print(
        "Quran verses:",
        len(quran_repository),
    )

    print(
        "Scholarly passages:",
        len(scholarly_repository),
    )

    return BasiraUnifiedRetriever(
        {
            EvidenceDomain.QURAN: (
                QuranDomainRetriever(
                    repository=(quran_repository),
                    runtime=(build_quran_runtime()),
                )
            ),
            EvidenceDomain.TAFSIR: (
                GovernedScholarlyRetriever(
                    delegate=(TafsirDomainRetriever(repository=(scholarly_repository))),
                    runtime=scholarly_runtime,
                    source_ids=(SURAHAPP_TAFSIR_SOURCE_IDS),
                )
            ),
            EvidenceDomain.REVELATION_CONTEXT: (
                GovernedScholarlyRetriever(
                    delegate=(
                        RevelationContextRetriever(repository=(scholarly_repository))
                    ),
                    runtime=scholarly_runtime,
                    source_ids=(SURAHAPP_REVELATION_CONTEXT_SOURCE_IDS),
                )
            ),
        }
    )


def run_query(
    *,
    retriever: BasiraUnifiedRetriever,
    query: str,
) -> None:
    understanding = BasiraQueryUnderstandingService().understand(query)

    plan = BasiraRetrievalPlanner().build(understanding)

    result = retriever.retrieve(plan)

    outcome = EvidenceDecisionService().evaluate(retrieval_result=result)

    composed = GroundedAnswerComposer().compose(
        question=query,
        outcome=outcome,
    )

    counts = Counter(node.domain.value for node in result.evidence)

    print()
    print("=" * 88)
    print("QUERY:", query)
    print("=" * 88)

    print(
        "INTENT:",
        understanding.primary_intent.value,
    )

    print(
        "TARGETS:",
        [target.domain.value for target in plan.targets],
    )

    print(
        "EVIDENCE:",
        dict(sorted(counts.items())),
    )

    print(
        "TOTAL EVIDENCE:",
        len(result.evidence),
    )

    print(
        "UNAVAILABLE:",
        sorted(domain.value for domain in result.unavailable_domains),
    )

    print("REQUIRED STATES:")

    for assessment in outcome.bundle.required_assessments:
        print(
            " -",
            assessment.need.value,
            "→",
            assessment.state.value,
        )

    print(
        "EVIDENCE COVERAGE:",
        outcome.bundle.evidence_coverage,
    )

    print(
        "RESOLUTION COVERAGE:",
        outcome.bundle.resolution_coverage,
    )

    print(
        "DECISION:",
        outcome.decision.action.value,
    )

    print(
        "COMPOSED:",
        composed.has_answer,
    )

    print(
        "USED EVIDENCE:",
        list(composed.used_evidence_ids),
    )

    print("LIMITATIONS:")

    if composed.limitations:
        for limitation in composed.limitations:
            print(
                " -",
                limitation,
            )
    else:
        print(" - none")

    print("CITATIONS:")

    if composed.citations:
        for citation in composed.citations:
            print(
                " -",
                citation.marker,
                citation.source_id,
                citation.reference,
                citation.evidence_id,
            )
    else:
        print(" - none")

    if composed.answer:
        print(
            "ANSWER PREVIEW:",
            composed.answer[:1200],
        )
    else:
        print(
            "ANSWER PREVIEW:",
            None,
        )

    # --------------------------------------------------------
    # Real user-facing regression assertions
    # --------------------------------------------------------

    assert all(
        citation.source_id != "tanzil-quran-v1.1-uthmani"
        for citation in composed.citations
    )

    if "58:1" in query:
        assert composed.has_answer

        assert outcome.decision.action.value == "answer"

        assert len(composed.citations) == 1

        assert any(
            citation.source_id == "surahapp-ayat-nozool"
            for citation in composed.citations
        )

    if "2:255" in query:
        assert composed.has_answer

        assert outcome.decision.action.value == "answer_with_limitation"

        assert composed.citations == ()

        assert any(
            "لا يوجد مدخل مُثبت" in limitation for limitation in composed.limitations
        )

        assert all(
            citation.source_id != "surahapp-ayat-nozool"
            for citation in composed.citations
        )

        assert "لا يوجد سبب نزول لهذه الآية" not in (composed.answer or "")


def main() -> None:
    retriever = build_retriever()

    run_query(
        retriever=retriever,
        query=("ما سبب نزول الآية 58:1؟"),
    )

    run_query(
        retriever=retriever,
        query=("ما سبب نزول الآية 2:255؟"),
    )


if __name__ == "__main__":
    main()
