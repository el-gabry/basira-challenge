from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from basira.competition.aqeedah_authority import (
    AqeedahAuthorityBasis,
    AqeedahAuthorityEvidence,
    AqeedahAuthorityStatus,
)
from basira.competition.aqeedah_policy import (
    AqeedahEvidenceRecord,
    AqeedahMaterialType,
    AqeedahSourceEligibility,
    AqeedahSourceFamily,
    AqeedahUseContext,
    OfficialAqeedahPolicy,
)
from basira.competition.dorar_aqeedah_admission import (
    DorarAqeedahAdmissionError,
    DorarAqeedahEvidenceEnvelope,
    admit_dorar_aqeedah_response,
)
from basira.competition.dorar_general_retrieval import (
    DorarGovernedPageClient,
)
from basira.competition.dorar_transport import (
    DorarTransportError,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionAuthorityBoundaryError,
    CompetitionRetrievalRequest,
    CompetitionSourceUnavailable,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)

AQEEDAH_MANIFEST = Path(
    "data/competition/manifests/aqeedah/dorar-aqeedah-runtime-v1.json"
)

AQEEDAH_PASSPORT = Path("data/competition/passports/dorar-aqeeda.json")


def _valid_hash(
    value: str,
) -> bool:
    return len(value) == 64 and all(
        char in "0123456789abcdef" for char in value.casefold()
    )


def _runtime_is_governed(
    runtime: DorarAqeedahEvidenceEnvelope,
) -> bool:
    return (
        runtime.source_id == "dorar-aqeeda-v1"
        and runtime.source_family == "dorar_aqeeda"
        and runtime.runtime_eligibility == "eligible"
        and _valid_hash(runtime.response_sha256)
        and not (runtime.quran_context_is_canonical_witness)
        and not (runtime.independent_hadith_authentication)
        and not (runtime.bibliographic_authority_promotion)
        and not (runtime.generic_shamela_fallback_allowed)
    )


def runtime_to_aqeedah_record(
    runtime: DorarAqeedahEvidenceEnvelope,
) -> AqeedahEvidenceRecord | None:
    """
    Admit only Dorar's own explanation_text.

    Quran snippets, hadith-like material, and source
    notes remain outside this answer-bearing record.
    """

    if not _runtime_is_governed(runtime):
        return None

    text = runtime.passage.explanation_text.strip()

    if not text:
        return None

    return AqeedahEvidenceRecord(
        text=text,
        source_family=(AqeedahSourceFamily.DORAR_AQEEDA),
        source_title=(runtime.passage.title),
        source_reference=(runtime.canonical_url),
        source_eligibility=(AqeedahSourceEligibility.ELIGIBLE),
        material_type=(AqeedahMaterialType.SCHOLARLY_EXPLANATION),
        authority=(
            AqeedahAuthorityEvidence(
                status=(AqeedahAuthorityStatus.VERIFIED_PRIMARY),
                basis=(AqeedahAuthorityBasis.OFFICIAL_COMPETITION_RULE),
                evidence_ids=(
                    runtime.source_id,
                    runtime.passport_id,
                    runtime.adapter_contract,
                ),
                notes=(
                    "authority_is_for_the_"
                    "governed_dorar_aqeeda_"
                    "source_family_not_for_"
                    "bibliographic_references",
                ),
            )
        ),
        edition_or_provider=(runtime.provider),
        exact_artifact_governed=True,
        source_identity_verified=True,
    )


def _use_context(
    query: str,
) -> AqeedahUseContext:
    lowered = query.casefold()

    comparative = (
        "فرقة",
        "مذهب عقدي",
        "مقارنة",
        "comparative",
        "sect",
    )

    detailed = (
        "تفصيل",
        "اختلف",
        "الخلاف",
        "detailed",
        "difference",
    )

    if any(marker in lowered for marker in comparative):
        return AqeedahUseContext.COMPARATIVE_RELIGION_OR_SECT

    if any(marker in lowered for marker in detailed):
        return AqeedahUseContext.DETAILED_AQEEDAH_ISSUE

    return AqeedahUseContext.BASIC_INTRODUCTION


def _record_id(
    record: AqeedahEvidenceRecord,
) -> str:
    digest = sha256(
        ((record.source_reference or "") + "\n" + record.text).encode("utf-8")
    ).hexdigest()[:24]

    return "dorar-aqeedah:" + digest


class DorarAqeedahEvidenceAdapter:
    def __init__(
        self,
        *,
        client: DorarGovernedPageClient,
        repo_root: Path,
        policy: (OfficialAqeedahPolicy | None) = None,
    ) -> None:
        self.client = client
        self.repo_root = repo_root.resolve()
        self.policy = policy or OfficialAqeedahPolicy()

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if request.official_domain is not OfficialDomain.AQEEDAH_INTRO_TO_ISLAM:
            raise (
                CompetitionAuthorityBoundaryError(
                    "Dorar Aqeedah adapter requires AQEEDAH_INTRO_TO_ISLAM"
                )
            )

        try:
            pages = self.client.search(
                query=request.query,
                family="aqeedah",
                limit=request.limit,
            )
        except DorarTransportError as exc:
            raise CompetitionSourceUnavailable("dorar_aqeedah") from exc

        records: list[AqeedahEvidenceRecord] = []

        version_by_reference: dict[
            str,
            str,
        ] = {}

        for page in pages:
            try:
                runtime = admit_dorar_aqeedah_response(
                    canonical_url=(page.canonical_url),
                    response_bytes=(page.body),
                    runtime_manifest_path=(self.repo_root / AQEEDAH_MANIFEST),
                    passport_path=(self.repo_root / AQEEDAH_PASSPORT),
                )
            except DorarAqeedahAdmissionError:
                continue

            record = runtime_to_aqeedah_record(runtime)

            if record is None:
                continue

            records.append(record)

            if record.source_reference:
                version_by_reference[record.source_reference] = runtime.response_sha256

        assessment = self.policy.assess(
            tuple(records),
            use_context=(_use_context(request.query)),
        )

        nodes: list[EvidenceNode] = []

        for record in assessment.usable_records:
            evidence_id = _record_id(record)

            nodes.append(
                EvidenceNode(
                    evidence_id=evidence_id,
                    domain=(EvidenceDomain.AQIDAH),
                    text=record.text,
                    source_id=("dorar-aqeeda-v1"),
                    source_version=(
                        version_by_reference.get(record.source_reference or "")
                    ),
                    reference=(record.source_reference),
                    source_url=(record.source_reference),
                    work_title=(record.source_title),
                    topic=(record.source_title),
                    claim_type=("aqeedah_" + record.material_type.value),
                )
            )

        return tuple(nodes[: request.limit])
