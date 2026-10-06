from types import SimpleNamespace

from basira.competition.aqeedah_policy import (
    AqeedahSourceFamily,
    AqeedahUseContext,
    OfficialAqeedahPolicy,
)
from basira.competition.dorar_aqeedah_adapter import (
    runtime_to_aqeedah_record,
)
from basira.competition.dorar_general_retrieval import (
    _canonical_candidate,
)
from basira.competition.dorar_history_adapter import (
    runtime_to_history_record,
)
from basira.competition.history_policy import (
    HistoricalReportStatus,
    HistorySourceFamily,
    HistorySourceUseMode,
    HistoryUseContext,
    OfficialHistoryPolicy,
)


def _hash() -> str:
    return "a" * 64


def test_aqeedah_route_is_bounded() -> None:
    assert (
        _canonical_candidate(
            "/aqeeda/420/anything",
            family="aqeedah",
        )
        == "https://dorar.net/aqeeda/420"
    )

    assert (
        _canonical_candidate(
            "/feqhia/420",
            family="aqeedah",
        )
        is None
    )


def test_history_routes_are_bounded() -> None:
    assert _canonical_candidate(
        "/history/event/282",
        family="history",
    ) == ("https://dorar.net/history/event/282")

    assert (
        _canonical_candidate(
            "/aqeeda/282",
            family="history",
        )
        is None
    )


def test_aqeedah_runtime_becomes_policy_record_only_after_governance() -> None:
    runtime = SimpleNamespace(
        source_id="dorar-aqeeda-v1",
        source_family="dorar_aqeeda",
        provider="Dorar al-Sunniyyah",
        runtime_eligibility="eligible",
        passport_id="dorar-aqeeda-v1",
        canonical_url=("https://dorar.net/aqeeda/420"),
        adapter_contract="test-governed-contract",
        response_sha256=_hash(),
        quran_context_is_canonical_witness=False,
        independent_hadith_authentication=False,
        bibliographic_authority_promotion=False,
        generic_shamela_fallback_allowed=False,
        passage=SimpleNamespace(
            title="التوحيد",
            explanation_text=("شرح عقدي من النص المقبول."),
        ),
    )

    record = runtime_to_aqeedah_record(runtime)

    assert record is not None

    assert record.source_family is AqeedahSourceFamily.DORAR_AQEEDA

    result = OfficialAqeedahPolicy().assess(
        (record,),
        use_context=(AqeedahUseContext.BASIC_INTRODUCTION),
    )

    assert record in (result.usable_records)


def test_aqeedah_unsafe_boundary_never_promotes() -> None:
    runtime = SimpleNamespace(
        source_id="dorar-aqeeda-v1",
        source_family="dorar_aqeeda",
        provider="Dorar al-Sunniyyah",
        runtime_eligibility="eligible",
        passport_id="dorar-aqeeda-v1",
        canonical_url=("https://dorar.net/aqeeda/420"),
        adapter_contract="x",
        response_sha256=_hash(),
        quran_context_is_canonical_witness=True,
        independent_hadith_authentication=False,
        bibliographic_authority_promotion=False,
        generic_shamela_fallback_allowed=False,
        passage=SimpleNamespace(
            title="x",
            explanation_text="x",
        ),
    )

    assert runtime_to_aqeedah_record(runtime) is None


def test_history_runtime_preserves_unassessed_status() -> None:
    runtime = SimpleNamespace(
        source_id="dorar-history-v1",
        source_family="dorar_history",
        provider="Dorar al-Sunniyyah",
        runtime_eligibility="eligible",
        passport_id="dorar-history-v1",
        canonical_url=("https://dorar.net/history/event/282"),
        adapter_contract="test-governed-contract",
        response_sha256=_hash(),
        may_state_as_established_fact=False,
        categorical_claim_requires_governed_report_assessment=True,
        independent_hadith_authentication=False,
        canonical_quran_witness=False,
        generic_shamela_fallback_allowed=False,
        historical_report_status=(HistoricalReportStatus.UNASSESSED),
        event=SimpleNamespace(
            title="حدث تاريخي",
            details_text=("نص التقرير التاريخي."),
            source_use_mode=(HistorySourceUseMode.CURATED_HISTORY_REFERENCE),
        ),
    )

    record = runtime_to_history_record(runtime)

    assert record is not None

    assert record.source_family is HistorySourceFamily.DORAR_HISTORY

    assert record.report_assessment.status is HistoricalReportStatus.UNASSESSED

    assessment = OfficialHistoryPolicy().assess(
        (record,),
        use_context=(HistoryUseContext.CATEGORICAL_EVENT_CLAIM),
    )

    assert assessment.may_state_as_established_fact is False


def test_history_runtime_cannot_self_promote_to_fact() -> None:
    runtime = SimpleNamespace(
        source_id="dorar-history-v1",
        source_family="dorar_history",
        provider="Dorar al-Sunniyyah",
        runtime_eligibility="eligible",
        passport_id="dorar-history-v1",
        canonical_url=("https://dorar.net/history/10"),
        adapter_contract="x",
        response_sha256=_hash(),
        may_state_as_established_fact=True,
        categorical_claim_requires_governed_report_assessment=True,
        independent_hadith_authentication=False,
        canonical_quran_witness=False,
        generic_shamela_fallback_allowed=False,
        historical_report_status=(HistoricalReportStatus.UNASSESSED),
        event=SimpleNamespace(
            title="x",
            details_text="x",
            source_use_mode=(HistorySourceUseMode.CURATED_HISTORY_REFERENCE),
        ),
    )

    assert runtime_to_history_record(runtime) is None
