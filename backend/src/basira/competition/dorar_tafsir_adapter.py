from __future__ import annotations

from hashlib import sha256

from basira.competition.dorar_tafsir import (
    DorarTafsirSection,
    DorarTafsirSectionKind,
)
from basira.competition.dorar_tafsir_retrieval import (
    DorarTafsirPayloadError,
    DorarTafsirRetriever,
)
from basira.competition.dorar_transport import (
    DorarTransportError,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
    CompetitionSourceUnavailable,
)
from basira.competition.tafsir_policy import (
    OfficialTafsirPolicy,
    TafsirEvidenceRecord,
    TafsirMaterialType,
    TafsirSourceEligibility,
    TafsirSourceFamily,
    TafsirUseContext,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)

DORAR_TAFSIR_SOURCE_ID = "dorar-tafsir-v1"

DORAR_TAFSIR_PASSPORT_ID = "dorar-tafsir-v1"

DORAR_TAFSIR_ADAPTER_CONTRACT = "dorar-tafsir-canonical-passages-v1"


_SECTION_MATERIAL_MAP = {
    DorarTafsirSectionKind.GENERAL_MEANING: TafsirMaterialType.SCHOLARLY_REASONING,
    DorarTafsirSectionKind.WORD_MEANING: TafsirMaterialType.LINGUISTIC_EXPLANATION,
    DorarTafsirSectionKind.GRAMMAR: TafsirMaterialType.LINGUISTIC_EXPLANATION,
    DorarTafsirSectionKind.TAFSIR_AYAT: TafsirMaterialType.SCHOLARLY_REASONING,
    DorarTafsirSectionKind.EDUCATIONAL_BENEFITS: TafsirMaterialType.SCHOLARLY_REASONING,
    DorarTafsirSectionKind.SCHOLARLY_BENEFITS: TafsirMaterialType.SCHOLARLY_REASONING,
    DorarTafsirSectionKind.RHETORIC: TafsirMaterialType.LINGUISTIC_EXPLANATION,
}


def _clean(
    value: object,
) -> str | None:
    if value is None:
        return None

    result = " ".join(str(value).split())

    return result or None


def _valid_sha256(
    value: object,
) -> bool:
    text = _clean(value)

    if text is None or len(text) != 64:
        return False

    return all(char in "0123456789abcdef" for char in text.lower())


def _runtime_is_governed(
    runtime_evidence,
) -> bool:
    """
    Defense-in-depth after DorarTafsirRuntimeGate.

    The gate remains the source of admission authority;
    this prevents a caller from injecting a lookalike
    runtime object directly into policy conversion.
    """

    return (
        runtime_evidence.passport_id == DORAR_TAFSIR_PASSPORT_ID
        and runtime_evidence.source_family is TafsirSourceFamily.DORAR_TAFSIR
        and runtime_evidence.runtime_eligibility is TafsirSourceEligibility.ELIGIBLE
        and runtime_evidence.adapter_contract == DORAR_TAFSIR_ADAPTER_CONTRACT
        and _valid_sha256(runtime_evidence.response_sha256)
    )


def _material_type(
    kind: DorarTafsirSectionKind,
) -> TafsirMaterialType:
    """
    Explicit structural mapping only.

    No Quran text, prophetic report, athar, Asbab,
    or early-scholar attribution is inferred from a
    generic Dorar section.
    """

    return _SECTION_MATERIAL_MAP.get(
        kind,
        TafsirMaterialType.UNKNOWN,
    )


def section_to_policy_record(
    *,
    section: DorarTafsirSection,
    source_family: TafsirSourceFamily,
    source_eligibility: TafsirSourceEligibility,
    canonical_url: str,
) -> TafsirEvidenceRecord | None:
    """
    Only explanation_text enters this lane.

    Quran context is kept separate by the parser.
    If Quran-context nodes were routed into explanation,
    fail closed instead of treating them as Tafsir.
    """

    if section.quran_context_text_nodes_routed_to_explanation != 0:
        return None

    text = _clean(section.explanation_text)

    if text is None:
        return None

    article_id = _clean(section.article_id)

    reference = canonical_url

    if article_id is not None:
        reference += "#" + article_id

    return TafsirEvidenceRecord(
        text=text,
        source_family=source_family,
        source_title=(_clean(section.heading) or "Dorar Tafsir"),
        source_reference=reference,
        source_eligibility=(source_eligibility),
        material_type=(_material_type(section.section_kind)),
        edition_or_provider=("Dorar Tafsir"),
        exact_artifact_governed=True,
    )


def runtime_to_policy_records(
    runtime_evidence,
) -> tuple[
    TafsirEvidenceRecord,
    ...,
]:
    if not _runtime_is_governed(runtime_evidence):
        return ()

    records = []

    for section in runtime_evidence.passage.sections:
        record = section_to_policy_record(
            section=section,
            source_family=(runtime_evidence.source_family),
            source_eligibility=(runtime_evidence.runtime_eligibility),
            canonical_url=(runtime_evidence.canonical_url),
        )

        if record is not None:
            records.append(record)

    return tuple(records)


def _record_id(
    record: TafsirEvidenceRecord,
) -> str:
    digest = sha256(
        (
            (record.source_reference or "")
            + "\n"
            + record.material_type.value
            + "\n"
            + record.text
        ).encode("utf-8")
    ).hexdigest()[:24]

    return "dorar-tafsir:" + digest


class DorarTafsirEvidenceAdapter:
    """
    Governed Competition Tafsir lane.

    question
      -> Dorar discovery
      -> canonical passage
      -> runtime admission
      -> policy records
      -> OfficialTafsirPolicy
      -> policy.usable_records
      -> EvidenceNode

    The adapter does not interpret the policy decision
    string and never promotes records omitted from
    assessment.usable_records.
    """

    def __init__(
        self,
        *,
        retriever: DorarTafsirRetriever,
        policy: (OfficialTafsirPolicy | None) = None,
        use_context: TafsirUseContext = (TafsirUseContext.EXPLAIN_AYAH),
    ) -> None:
        self._retriever = retriever
        self._policy = policy or OfficialTafsirPolicy()
        self._use_context = use_context

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        try:
            if request.references:
                result = self._retriever.search(
                    request.query,
                    limit=request.limit,
                    required_quran_references=(request.references),
                )
            else:
                result = self._retriever.search(
                    request.query,
                    limit=request.limit,
                )

        except (
            DorarTransportError,
            DorarTafsirPayloadError,
        ) as exc:
            raise (CompetitionSourceUnavailable("dorar_tafsir")) from exc

        coverage_by_url: dict[
            str,
            tuple[
                str,
                ...,
            ],
        ] = {}

        records = []

        for retrieved in result.passages:
            runtime = retrieved.admitted

            raw_coverage = (
                getattr(
                    retrieved,
                    "quran_references",
                    (),
                )
                or ()
            )

            quran_references = tuple(
                str(value).strip() for value in raw_coverage if str(value).strip()
            )

            canonical_url = getattr(
                retrieved,
                "canonical_url",
                None,
            ) or getattr(
                runtime,
                "canonical_url",
                None,
            )

            if canonical_url and quran_references:
                coverage_by_url[str(canonical_url).rstrip("/")] = quran_references

            records.extend(runtime_to_policy_records(runtime))

        assessment = self._policy.assess(
            tuple(records),
            use_context=(self._use_context),
        )

        nodes = []
        seen = set()

        for record in assessment.usable_records:
            evidence_id = _record_id(record)

            if evidence_id in seen:
                continue

            seen.add(evidence_id)

            source_reference = record.source_reference

            source_base = (
                source_reference.split(
                    "#",
                    maxsplit=1,
                )[0].rstrip("/")
                if source_reference
                else ""
            )

            nodes.append(
                EvidenceNode(
                    evidence_id=(evidence_id),
                    domain=(EvidenceDomain.TAFSIR),
                    text=record.text,
                    source_id=(DORAR_TAFSIR_SOURCE_ID),
                    reference=(source_reference),
                    related_quran=(
                        coverage_by_url.get(
                            source_base,
                            (),
                        )
                    ),
                    source_url=(source_reference),
                    work_title=(
                        record.edition_or_provider
                        or record.source_title
                    ),
                    author_name=(record.attributed_to),
                    claim_type=("tafsir_" + record.material_type.value),
                )
            )

        return tuple(nodes)
