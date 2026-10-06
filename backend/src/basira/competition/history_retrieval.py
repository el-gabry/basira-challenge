from __future__ import annotations

from pydantic import BaseModel

from basira.competition.history_policy import (
    HistoricalAssessmentBasis,
    HistoricalReportStatus,
    HistoryEvidenceRecord,
    HistoryMaterialType,
    HistorySourceFamily,
    HistorySourceUseMode,
)


class HistoricalChunkingError(
    ValueError
):
    pass


class HistoricalEvidenceChunk(BaseModel):
    chunk_text: str

    source_family: HistorySourceFamily

    source_title: str

    source_reference: str | None

    source_use_mode: HistorySourceUseMode

    material_type: HistoryMaterialType

    attributed_to: str | None

    report_status: HistoricalReportStatus

    report_assessment_basis: HistoricalAssessmentBasis

    source_identity_verified: bool

    exact_artifact_governed: bool

    # Chunk construction never decides historical truth.
    #
    # Truth/fact promotion remains a later evidence-policy
    # decision.
    chunk_itself_may_establish_historical_fact: bool = False

    provenance_preserved: bool = True

    attribution_inferred_by_chunker: bool = False


def build_historical_evidence_chunk(
    *,
    record: HistoryEvidenceRecord,
    chunk_text: str,
) -> HistoricalEvidenceChunk:

    text = chunk_text.strip()

    if not text:
        raise HistoricalChunkingError(
            "empty_history_chunk"
        )

    if not record.source_title.strip():
        raise HistoricalChunkingError(
            "source_title_required"
        )

    if (
        record.source_use_mode
        is HistorySourceUseMode.UNKNOWN
    ):
        raise HistoricalChunkingError(
            "source_use_mode_required"
        )

    if (
        record.source_use_mode
        is HistorySourceUseMode
        .RAW_REPORT_COLLECTION
        and not record.source_reference
    ):
        raise HistoricalChunkingError(
            "raw_report_source_reference_required"
        )

    return HistoricalEvidenceChunk(
        chunk_text=text,
        source_family=(
            record.source_family
        ),
        source_title=(
            record.source_title
        ),
        source_reference=(
            record.source_reference
        ),
        source_use_mode=(
            record.source_use_mode
        ),
        material_type=(
            record.material_type
        ),
        attributed_to=(
            record.attributed_to
        ),
        report_status=(
            record.report_assessment.status
        ),
        report_assessment_basis=(
            record.report_assessment.basis
        ),
        source_identity_verified=(
            record.source_identity_verified
        ),
        exact_artifact_governed=(
            record.exact_artifact_governed
        ),
    )
