from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from basira.competition.dorar_general_retrieval import (
    DorarGovernedPageClient,
)
from basira.competition.dorar_history_admission import (
    DorarHistoryAdmissionError,
    DorarHistoryEvidenceEnvelope,
    admit_dorar_history_response,
)
from basira.competition.dorar_transport import (
    DorarTransportError,
)
from basira.competition.history_policy import (
    HistoricalReportAssessment,
    HistoryEvidenceRecord,
    HistoryMaterialType,
    HistorySourceEligibility,
    HistorySourceFamily,
    HistoryUseContext,
    OfficialHistoryPolicy,
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

HISTORY_MANIFEST = Path(
    "data/competition/manifests/history/dorar-history-runtime-v1.json"
)

HISTORY_PASSPORT = Path("data/competition/passports/dorar-history.json")


def _valid_hash(
    value: str,
) -> bool:
    return len(value) == 64 and all(
        char in "0123456789abcdef" for char in value.casefold()
    )


def _runtime_is_governed(
    runtime: DorarHistoryEvidenceEnvelope,
) -> bool:
    return (
        runtime.source_id == "dorar-history-v1"
        and runtime.source_family == "dorar_history"
        and runtime.runtime_eligibility == "eligible"
        and _valid_hash(runtime.response_sha256)
        and not (runtime.may_state_as_established_fact)
        and (runtime.categorical_claim_requires_governed_report_assessment)
        and not (runtime.independent_hadith_authentication)
        and not (runtime.canonical_quran_witness)
        and not (runtime.generic_shamela_fallback_allowed)
    )


def runtime_to_history_record(
    runtime: DorarHistoryEvidenceEnvelope,
) -> HistoryEvidenceRecord | None:
    """
    Preserve Dorar as a governed historical report.

    Runtime admission NEVER upgrades the report into
    an established historical fact.
    """

    if not _runtime_is_governed(runtime):
        return None

    event = runtime.event

    text = event.details_text.strip()

    if not text:
        return None

    return HistoryEvidenceRecord(
        text=text,
        source_family=(HistorySourceFamily.DORAR_HISTORY),
        source_title=event.title,
        source_reference=(runtime.canonical_url),
        source_eligibility=(HistorySourceEligibility.ELIGIBLE),
        material_type=(HistoryMaterialType.HISTORICAL_EVENT_REPORT),
        source_use_mode=(event.source_use_mode),
        report_assessment=(
            HistoricalReportAssessment(
                status=(runtime.historical_report_status),
                notes=("runtime_admission_does_not_establish_historical_truth",),
            )
        ),
        source_identity_verified=True,
        exact_artifact_governed=True,
    )


def _use_context(
    query: str,
) -> HistoryUseContext:
    lowered = query.casefold()

    disputed = (
        "بالسيف",
        "انتشر بالسيف",
        "خلاف تاريخي",
        "disputed",
        "controvers",
        "spread by the sword",
    )

    categorical = (
        "هل حدث",
        "هل وقعت",
        "متى",
        "من الذي",
        "did ",
        "when ",
        "who ",
    )

    if any(marker in lowered for marker in disputed):
        return HistoryUseContext.DISPUTED_HISTORICAL_QUESTION

    if any(marker in lowered for marker in categorical):
        return HistoryUseContext.CATEGORICAL_EVENT_CLAIM

    return HistoryUseContext.NARRATIVE_CONTEXT


def _record_id(
    record: HistoryEvidenceRecord,
) -> str:
    digest = sha256(
        ((record.source_reference or "") + "\n" + record.text).encode("utf-8")
    ).hexdigest()[:24]

    return "dorar-history:" + digest


class DorarHistoryEvidenceAdapter:
    def __init__(
        self,
        *,
        client: DorarGovernedPageClient,
        repo_root: Path,
        policy: (OfficialHistoryPolicy | None) = None,
    ) -> None:
        self.client = client
        self.repo_root = repo_root.resolve()
        self.policy = policy or OfficialHistoryPolicy()

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if request.official_domain is not OfficialDomain.SEERAH_HISTORY:
            raise (
                CompetitionAuthorityBoundaryError(
                    "Dorar History adapter requires SEERAH_HISTORY"
                )
            )

        try:
            pages = self.client.search(
                query=request.query,
                family="history",
                limit=request.limit,
            )
        except DorarTransportError as exc:
            raise CompetitionSourceUnavailable("dorar_history") from exc

        records: list[HistoryEvidenceRecord] = []

        version_by_reference: dict[
            str,
            str,
        ] = {}

        for page in pages:
            try:
                runtime = admit_dorar_history_response(
                    canonical_url=(page.canonical_url),
                    response_bytes=(page.body),
                    runtime_manifest_path=(self.repo_root / HISTORY_MANIFEST),
                    passport_path=(self.repo_root / HISTORY_PASSPORT),
                )
            except DorarHistoryAdmissionError:
                continue

            record = runtime_to_history_record(runtime)

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
                    domain=(EvidenceDomain.HISTORY),
                    text=record.text,
                    source_id=("dorar-history-v1"),
                    source_version=(
                        version_by_reference.get(record.source_reference or "")
                    ),
                    reference=(record.source_reference),
                    source_url=(record.source_reference),
                    work_title=(record.source_title),
                    topic=(record.source_title),
                    claim_type=("history_" + record.material_type.value),
                    historical_context=(
                        "governed_historical_report_not_automatically_established_fact"
                    ),
                )
            )

        return tuple(nodes[: request.limit])
