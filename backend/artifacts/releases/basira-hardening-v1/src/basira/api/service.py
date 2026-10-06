from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from basira.answer.models import (
    GroundedAnswer,
)
from basira.answer.semantic_verification import (
    GeneratedClaimSemanticVerifier,
)
from basira.api.governed_runtime import (
    PublicGovernedQueryRuntime,
    _quran_repository,
)
from basira.competition.dorar_fiqh_adapter import (
    DorarFiqhEvidenceAdapter,
)
from basira.competition.dorar_fiqh_admission import (
    DorarFiqhRuntimeGate,
)
from basira.competition.dorar_fiqh_source import (
    DorarFiqhSourceClient,
)
from basira.competition.dorar_hadith_adapter import (
    DorarHadithEvidenceAdapter,
)
from basira.competition.dorar_hadith_retrieval import (
    DorarHadithRetriever,
)
from basira.competition.dorar_transport import (
    DorarHttpTransport,
)
from basira.competition.quranpedia_adapter import (
    QuranpediaEvidenceAdapter,
)
from basira.competition.retrieval_adapters import (
    build_live_dorar_tafsir_adapter,
)
from basira.evidence.models import (
    EvidenceDomain,
)
from basira.evidence.publication import (
    EvidencePublicationAuthorizer,
    GovernedPublicationLedger,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.models.source_manifest import (
    SourceManifest,
)
from basira.models.source_snapshot import (
    SnapshotIntegrityStatus,
    SourceSnapshot,
)
from basira.models.source_usage import (
    RuntimeUse,
)
from basira.reasoning.route_governor import (
    RouteGovernor,
)
from basira.reasoning.route_proposal import (
    RouteProposer,
)
from basira.retrieval.governed_scholarly_retriever import (
    GovernedScholarlyRetriever,
)
from basira.retrieval.hadith_index import (
    HadithLocalIndex,
)
from basira.retrieval.hadith_retriever import (
    HadithDomainRetriever,
)
from basira.retrieval.official_fiqh_retriever import (
    OfficialFiqhDomainRetriever,
)
from basira.retrieval.official_hadith_retriever import (
    OfficialHadithDomainRetriever,
)
from basira.retrieval.official_quran_retriever import (
    OfficialQuranDomainRetriever,
)
from basira.retrieval.official_tafsir_retriever import (
    OfficialTafsirDomainRetriever,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.quran_retriever import (
    QuranDomainRetriever,
)
from basira.retrieval.revelation_context_retriever import (
    RevelationContextRetriever,
)
from basira.retrieval.tafsir_retriever import (
    TafsirDomainRetriever,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
    UnifiedRetrievalResult,
)
from basira.sources.hadith.hadeethenc.parser import (
    HadeethEncOfficialParser,
)
from basira.sources.hadith.hadeethenc.workbook import (
    load_hadeethenc_arabic_workbook,
    load_hadeethenc_english_workbook,
)
from basira.sources.policy_catalog import (
    SourceUsagePolicyNotFoundError,
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
from basira.sources.snapshot_validation import (
    validate_source_snapshot,
)
from basira.verification.quran_verifier import (
    QuranQuoteResult,
    QuranQuoteStatus,
    QuranQuoteVerifier,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


DEFAULT_QURAN_MANIFEST = (
    PROJECT_ROOT / "data" / "manifests" / "quran" / "tanzil-quran-v1.1-uthmani.json"
)

DEFAULT_HADEETHENC_MANIFEST = (
    PROJECT_ROOT / "data" / "manifests" / "hadith" / "hadeethenc-official.json"
)

DEFAULT_HADEETHENC_SNAPSHOT = (
    PROJECT_ROOT / "data" / "manifests" / "hadith" / "hadeethenc-official-snapshot.json"
)


@dataclass(
    frozen=True,
    slots=True,
)
class QueryExecution:
    question: str

    understanding: BasiraQueryUnderstanding

    retrieval: UnifiedRetrievalResult

    outcome: EvidenceDecisionOutcome

    answer: GroundedAnswer

    quran_verification: QuranQuoteResult | None = None


class BasiraQueryService:
    """
    Thin application orchestration layer.

    It deliberately reuses the same understanding,
    retrieval, evidence-decision, and answer-composition
    pipeline used by the real scholarly smoke test.
    """

    def __init__(
        self,
        *,
        retriever: BasiraUnifiedRetriever,
        publication_authorizer: EvidencePublicationAuthorizer | None = None,
        scholarly_repository: ScholarlyRepository | None = None,
        scholarly_runtime: FailClosedSourceRuntime | None = None,
        semantic_verifier: (GeneratedClaimSemanticVerifier | None) = None,
        route_proposer: RouteProposer | None = None,
        route_governor: RouteGovernor | None = None,
    ) -> None:
        self.retriever = retriever
        self.scholarly_repository = scholarly_repository
        self.scholarly_runtime = scholarly_runtime

        # Publication authority is an independent capability.
        # Never infer trust from the retriever supplying evidence.
        self.publication_ledger = publication_authorizer

        quran_repository = _quran_repository(
            retriever
        )

        self.quran_quote_verifier = (
            QuranQuoteVerifier(
                quran_repository
            )
            if quran_repository is not None
            else None
        )

        self.governed_runtime = PublicGovernedQueryRuntime(
            retriever=retriever,
            publication_authorizer=publication_authorizer,
            semantic_verifier=semantic_verifier,
            route_proposer=route_proposer,
            route_governor=route_governor,
        )

        self.composer = self.governed_runtime.composer

        # Evidence detail MUST read from the exact same
        # publication capability used by the governed composer.
        # Do not construct or infer a second authority.
        self.publication_ledger = getattr(
            self.composer,
            "publication_authorizer",
            None,
        )

    def get_publishable_tafsir(
        self,
        evidence_id: str,
    ) -> ScholarlyPassage | None:
        """
        Resolve one Tafsir passage for explicit
        user-requested full-text display.

        This remains fail-closed:
        - passage must exist in the active repository
        - domain must be Tafsir
        - policy must permit SUPPORT_ANSWER
        - policy must permit CITE_TO_USER
        - human review must not be required
        - active runtime governance must also allow
          both publication uses
        """

        cleaned_id = evidence_id.strip()

        if not cleaned_id:
            return None

        # Current official-source lane:
        #
        # Return the ORIGINAL admitted Tafsir node stored before
        # FocusAwareRetriever projects a shorter public excerpt.
        # This gives the drawer the complete governed passage while
        # remaining fail-closed.
        ledger = self.publication_ledger

        if (
            ledger is not None
            and hasattr(ledger, "get_admitted")
        ):
            admitted = ledger.get_admitted(
                cleaned_id
            )

            if (
                admitted is not None
                and getattr(
                    admitted.domain,
                    "value",
                    None,
                )
                == "tafsir"
                and ledger.may_publish(
                    admitted
                )
            ):
                return admitted

        # Legacy scholarly lane remains available when configured.
        if (
            self.scholarly_repository is None
            or self.scholarly_runtime is None
        ):
            return None

        passage = self.scholarly_repository.get(cleaned_id)

        if passage is None or passage.domain is not ScholarlyDomain.TAFSIR:
            return None

        try:
            policy = get_source_usage_policy(passage.source_id)
        except SourceUsagePolicyNotFoundError:
            return None

        if policy.requires_human_review:
            return None

        for runtime_use in (
            RuntimeUse.SUPPORT_ANSWER,
            RuntimeUse.CITE_TO_USER,
        ):
            if not policy.allows(runtime_use):
                return None

            if not self.scholarly_runtime.allows(
                source_id=passage.source_id,
                runtime_use=runtime_use,
            ):
                return None

        return passage

    def execute(
        self,
        *,
        question: str,
        quran_reference: str | None = None,
    ) -> QueryExecution:
        result = self.governed_runtime.execute(
            question=question,
            quran_reference=quran_reference,
        )

        quran_verification = None

        if self.quran_quote_verifier is not None:
            quote_result = (
                self.quran_quote_verifier.verify(
                    question
                )
            )

            # Do not attach meaningless NOT_FOUND metadata
            # to ordinary non-Quran questions.
            #
            # Exact, normalized, partial, altered and
            # ambiguous Quran candidates remain visible.
            if (
                quote_result.status
                is not QuranQuoteStatus.NOT_FOUND
                and quote_result.candidates
            ):
                quran_verification = quote_result

        return QueryExecution(
            question=result.question,
            understanding=result.understanding,
            retrieval=result.retrieval,
            outcome=result.outcome,
            answer=result.answer,
            quran_verification=quran_verification,
        )


def _optional_directory(
    env_name: str,
) -> Path | None:
    raw = os.getenv(env_name)

    if not raw:
        return None

    path = Path(raw).expanduser().resolve()

    if not path.is_dir():
        raise RuntimeError(f"{env_name} does not point to a directory.")

    return path


def _required_directory(
    env_name: str,
) -> Path:
    raw = os.getenv(env_name)

    if not raw:
        raise RuntimeError(f"{env_name} is required.")

    path = Path(raw).expanduser().resolve()

    if not path.is_dir():
        raise RuntimeError(f"{env_name} does not point to a directory.")

    return path


def _quran_manifest_path() -> Path:
    raw = os.getenv("BASIRA_QURAN_MANIFEST")

    path = Path(raw) if raw else DEFAULT_QURAN_MANIFEST

    path = path.expanduser().resolve()

    if not path.is_file():
        raise RuntimeError("Configured Quran manifest does not exist.")

    return path


def build_quran_runtime() -> FailClosedSourceRuntime:
    manifest = SourceManifest.model_validate_json(
        _quran_manifest_path().read_text(encoding="utf-8")
    )

    policy = get_source_usage_policy(manifest.source_id)

    manifest = manifest.model_copy(
        update={
            "usage_policy": policy,
        }
    )

    registry = TrustedSourceRegistry([manifest])

    return FailClosedSourceRuntime(registry)


def build_default_scholarly_repository() -> ScholarlyRepository:
    scholarly_root = _required_directory("BASIRA_SCHOLARLY_ROOT")

    scholarly_passages = SurahAppScholarlyParser().parse_snapshot(scholarly_root)

    return ScholarlyRepository(scholarly_passages)


def build_hadeethenc_runtime() -> FailClosedSourceRuntime:
    manifest = SourceManifest.model_validate_json(
        DEFAULT_HADEETHENC_MANIFEST.read_text(encoding="utf-8")
    )

    policy = get_source_usage_policy(manifest.source_id)

    manifest = manifest.model_copy(
        update={
            "usage_policy": policy,
        }
    )

    return FailClosedSourceRuntime(TrustedSourceRegistry([manifest]))


def build_default_hadith_retriever(
    snapshot_root: Path,
) -> HadithDomainRetriever:
    manifest = SourceManifest.model_validate_json(
        DEFAULT_HADEETHENC_MANIFEST.read_text(encoding="utf-8")
    )

    snapshot = SourceSnapshot.model_validate_json(
        DEFAULT_HADEETHENC_SNAPSHOT.read_text(encoding="utf-8")
    )

    if snapshot.source_id != manifest.source_id:
        raise RuntimeError("HadeethEnc manifest and snapshot source IDs do not match.")

    if manifest.version != snapshot.revision:
        raise RuntimeError(
            "HadeethEnc manifest version and snapshot revision do not match."
        )

    if snapshot.integrity_status is not SnapshotIntegrityStatus.VERIFIED_LOCAL_COPY:
        raise RuntimeError(
            "HadeethEnc snapshot is not marked as a verified local copy."
        )

    report = validate_source_snapshot(
        snapshot,
        snapshot_root=snapshot_root,
    )

    if not report.valid:
        failed = ", ".join(result.artifact.path for result in report.failed_artifacts)

        raise RuntimeError(
            "HadeethEnc snapshot validation failed" + (f": {failed}" if failed else ".")
        )

    arabic_artifacts = [
        artifact for artifact in snapshot.artifacts if artifact.config.startswith("ar-")
    ]

    english_artifacts = [
        artifact for artifact in snapshot.artifacts if artifact.config.startswith("en-")
    ]

    if len(arabic_artifacts) != 1 or len(english_artifacts) != 1:
        raise RuntimeError(
            "HadeethEnc snapshot must contain "
            "exactly one Arabic and one English "
            "release artifact."
        )

    arabic = load_hadeethenc_arabic_workbook(snapshot_root / arabic_artifacts[0].path)

    english = load_hadeethenc_english_workbook(
        snapshot_root / english_artifacts[0].path
    )

    parsed_revision = f"ar-{arabic.release.version}+en-{english.release.version}"

    if parsed_revision != snapshot.revision:
        raise RuntimeError(
            "HadeethEnc parsed release revision does not match the pinned snapshot."
        )

    index = HadithLocalIndex(runtime=build_hadeethenc_runtime())

    english_by_id = {row.id: row for row in english.rows}

    parser = HadeethEncOfficialParser()

    for row in arabic.rows:
        translated = english_by_id.get(row.id)

        record = parser.parse(
            row.model_dump(),
            arabic_release=(arabic.release),
            english_payload=(
                translated.model_dump() if translated is not None else None
            ),
            english_release=(english.release if translated is not None else None),
        )

        index.add(record)

    return HadithDomainRetriever(
        index=index,
        default_collection_id=("hadeethenc"),
    )


def _configured_hadith_retriever() -> HadithDomainRetriever | None:
    root = _optional_directory("BASIRA_HADEETHENC_ROOT")

    if root is None:
        return None

    return build_default_hadith_retriever(root)


def build_default_retriever(
    *,
    scholarly_repository: (ScholarlyRepository | None) = None,
    scholarly_runtime: (FailClosedSourceRuntime | None) = None,
) -> BasiraUnifiedRetriever:
    tanzil_root = _required_directory("BASIRA_TANZIL_ROOT")

    if scholarly_repository is None:
        scholarly_repository = build_default_scholarly_repository()

    if scholarly_runtime is None:
        scholarly_runtime = build_surahapp_scholarly_runtime()

    quran_verses = TanzilQuranParser().parse_files(
        uthmani_path=(tanzil_root / "quran-uthmani.txt"),
        simple_plain_path=(tanzil_root / "quran-simple-plain.txt"),
    )

    quran_repository = QuranRepository(quran_verses)

    retrievers = {
        EvidenceDomain.QURAN: (
            QuranDomainRetriever(
                repository=(quran_repository),
                runtime=(build_quran_runtime()),
            )
        ),
        EvidenceDomain.TAFSIR: (
            GovernedScholarlyRetriever(
                delegate=(
                    TafsirDomainRetriever(
                        repository=scholarly_repository,
                        source_ids=(SURAHAPP_TAFSIR_SOURCE_IDS),
                    )
                ),
                runtime=(scholarly_runtime),
                source_ids=(SURAHAPP_TAFSIR_SOURCE_IDS),
            )
        ),
        EvidenceDomain.REVELATION_CONTEXT: (
            GovernedScholarlyRetriever(
                delegate=(
                    RevelationContextRetriever(repository=(scholarly_repository))
                ),
                runtime=(scholarly_runtime),
                source_ids=(SURAHAPP_REVELATION_CONTEXT_SOURCE_IDS),
            )
        ),
    }

    hadith_retriever = _configured_hadith_retriever()

    if hadith_retriever is not None:
        retrievers[EvidenceDomain.HADITH] = hadith_retriever

    return BasiraUnifiedRetriever(retrievers)


def build_public_official_retriever(
    *,
    repo_root: Path | str = PROJECT_ROOT,
    publication_ledger: GovernedPublicationLedger | None = None,
) -> BasiraUnifiedRetriever:
    """
    Public governed retrieval composition.

    Only admitted official source lanes may issue
    publication capability.
    """

    root = Path(repo_root).resolve()

    if publication_ledger is None:
        publication_ledger = GovernedPublicationLedger()

    quran_adapter = QuranpediaEvidenceAdapter(
        repo_root=root,
    )

    quran = OfficialQuranDomainRetriever(
        adapter=quran_adapter,
        publication_ledger=(publication_ledger),
    )

    hadith_adapter = DorarHadithEvidenceAdapter(
        retriever=DorarHadithRetriever(
            transport=DorarHttpTransport(),
        ),
    )

    hadith = OfficialHadithDomainRetriever(
        adapter=hadith_adapter,
        publication_ledger=publication_ledger,
    )

    tafsir_adapter = build_live_dorar_tafsir_adapter(
        repo_root=root,
    )

    tafsir = OfficialTafsirDomainRetriever(
        adapter=tafsir_adapter,
        quran_repository=(quran.repository),
        publication_ledger=(publication_ledger),
    )



    fiqh_adapter = DorarFiqhEvidenceAdapter(
        client=DorarFiqhSourceClient(
            transport=DorarHttpTransport(),
        ),
        gate=(
            DorarFiqhRuntimeGate
            .from_repo(root)
        ),
    )

    fiqh = OfficialFiqhDomainRetriever(
        adapter=fiqh_adapter,
        publication_ledger=(
            publication_ledger
        ),
    )
    return BasiraUnifiedRetriever(
        {
            EvidenceDomain.QURAN: quran,
            EvidenceDomain.HADITH: hadith,
            EvidenceDomain.TAFSIR: tafsir,
            EvidenceDomain.FIQH: fiqh,
        },
        publication_authorizer=(publication_ledger),
    )


def build_default_query_service() -> BasiraQueryService:
    """
    Default public HTTP/API service.

    Unsupported official domains remain unavailable.
    No legacy-source fallback is permitted.
    """

    publication_ledger = GovernedPublicationLedger()

    retriever = build_public_official_retriever(
        publication_ledger=publication_ledger,
    )

    return BasiraQueryService(
        retriever=retriever,
        publication_authorizer=publication_ledger,
    )
