import pytest

from basira.competition.history_policy import (
    HistoricalReportAssessment,
    HistoryEvidenceRecord,
    HistoryMaterialType,
    HistorySourceEligibility,
    HistorySourceFamily,
    HistorySourceUseMode,
)
from basira.competition.history_retrieval import (
    HistoricalChunkingError,
    build_historical_evidence_chunk,
)


def raw_record():
    return HistoryEvidenceRecord(
        text="الرواية الأصلية",
        source_family=(
            HistorySourceFamily
            .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
        ),
        source_title="مصدر تاريخي خام",
        source_reference="1/25",
        source_eligibility=(
            HistorySourceEligibility.ELIGIBLE
        ),
        material_type=(
            HistoryMaterialType
            .HISTORICAL_EVENT_REPORT
        ),
        source_use_mode=(
            HistorySourceUseMode
            .RAW_REPORT_COLLECTION
        ),
        report_assessment=(
            HistoricalReportAssessment()
        ),
        source_identity_verified=True,
        exact_artifact_governed=True,
        attributed_to="راوٍ منقول عنه",
    )


def test_chunk_preserves_source_provenance() -> None:
    record = raw_record()

    chunk = (
        build_historical_evidence_chunk(
            record=record,
            chunk_text="جزء من الرواية",
        )
    )

    assert (
        chunk.source_title
        == record.source_title
    )

    assert (
        chunk.source_reference
        == record.source_reference
    )

    assert (
        chunk.source_use_mode
        is HistorySourceUseMode
        .RAW_REPORT_COLLECTION
    )

    assert (
        chunk.attributed_to
        == record.attributed_to
    )

    assert chunk.provenance_preserved is True


def test_chunk_never_promotes_itself_to_historical_fact() -> None:
    chunk = (
        build_historical_evidence_chunk(
            record=raw_record(),
            chunk_text="جزء من الرواية",
        )
    )

    assert (
        chunk
        .chunk_itself_may_establish_historical_fact
        is False
    )


def test_chunker_does_not_infer_new_attribution() -> None:
    record = raw_record()

    record.attributed_to = None

    chunk = (
        build_historical_evidence_chunk(
            record=record,
            chunk_text=(
                "قال فلان في النص"
            ),
        )
    )

    assert chunk.attributed_to is None

    assert (
        chunk.attribution_inferred_by_chunker
        is False
    )


def test_raw_report_chunk_requires_source_reference() -> None:
    record = raw_record()

    record.source_reference = None

    with pytest.raises(
        HistoricalChunkingError,
        match=(
            "raw_report_source_reference_required"
        ),
    ):
        build_historical_evidence_chunk(
            record=record,
            chunk_text="نص",
        )


def test_unknown_source_use_mode_cannot_be_chunked() -> None:
    record = raw_record()

    record.source_use_mode = (
        HistorySourceUseMode.UNKNOWN
    )

    with pytest.raises(
        HistoricalChunkingError,
        match="source_use_mode_required",
    ):
        build_historical_evidence_chunk(
            record=record,
            chunk_text="نص",
        )
