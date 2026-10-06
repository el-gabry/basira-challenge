from __future__ import annotations

import pytest

from basira.competition.dorar_history import (
    DorarHistoryParseError,
    DorarHistoryRouteFamily,
    parse_dorar_history_event,
)
from basira.competition.history_policy import (
    HistoricalReportStatus,
    HistorySourceUseMode,
)


DIRECT = (
    "https://dorar.net/history/7"
)

EVENT = (
    "https://dorar.net/history/event/7"
)


def wrap(
    *,
    url: str = DIRECT,
    event_id: int = 7,
    details: str = "وقع حدث تاريخي.",
    month: str | None = "رمضان",
    outside: str = "",
    inside_extra: str = "",
) -> str:

    month_html = (
        (
            '<strong class="px-3">'
            f"الشهر القمري : {month}"
            "</strong>"
        )
        if month is not None
        else ""
    )

    return f"""
<!doctype html>
<html>
<head>
<link rel="canonical" href="{url}">
</head>
<body>

{outside}

<form id="hist-form">
<label class="form-check-label">
تفاصيل الحدث
</label>
<a href="/history/refs">
المراجع المعتمدة
</a>
</form>

<div id="cntnt" class="card-body">

<div class="row">
تصفح الكل
</div>

<hr class="my-0">

<div
 id="accordionEx"
 class="accordion md-accordion dorar_custom_accordion amiri_custom_content"
>
<div class="event-container">

<div class="card scroll-pos z-depth-0 mb-0">

<div
 id="headingTwo{event_id}"
 class="card-header p-0"
>
<a>
<h6
 class="h6-responsive mb-0 d-flex align-items-center justify-content-between b-0"
>
عنوان الحدث
</h6>
</a>
</div>

<div
 id="collapseTwo{event_id}"
 class="show"
>
<div class="card-body px-0 py-3 pt-0">

<strong>
العام الهجري : 10
</strong>

{month_html}

<strong class="px-3">
العام الميلادي : 631
</strong>

<h6 class="mt-3 font-weight-bold">
تفاصيل الحدث:
</h6>

<p>
{details}
</p>

{inside_extra}

</div>
</div>

</div>
</div>
</div>
</div>
</body>
</html>
"""


def parse(
    html: str,
    url: str = DIRECT,
):

    return parse_dorar_history_event(
        html=html,
        canonical_url=url,
    )


def test_direct_route_is_supported() -> None:
    event = parse(
        wrap()
    )

    assert (
        event.route_family
        is DorarHistoryRouteFamily
        .DIRECT_HISTORY_ID
    )

    assert event.event_id == 7


def test_event_route_is_supported() -> None:
    event = parse(
        wrap(
            url=EVENT,
        ),
        EVENT,
    )

    assert (
        event.route_family
        is DorarHistoryRouteFamily
        .HISTORY_EVENT_ID
    )


def test_canonical_link_must_match_requested_url() -> None:
    with pytest.raises(
        DorarHistoryParseError,
        match="canonical_link_mismatch",
    ):
        parse_dorar_history_event(
            html=wrap(
                url=EVENT,
            ),
            canonical_url=DIRECT,
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://dorar.net/history/7",
        "https://evil.example/history/7",
        "https://dorar.net/history",
        "https://dorar.net/history/",
        "https://dorar.net/history/0",
        "https://dorar.net/history/-1",
        "https://dorar.net/history/7/",
        "https://dorar.net/history/event",
        "https://dorar.net/history/event/0",
        "https://dorar.net/history/event/7/",
        "https://dorar.net/history/7?q=x",
        "https://dorar.net/history/7#x",
        "https://dorar.net/history/search",
        "https://dorar.net/history/refs",
    ],
)
def test_noncanonical_routes_fail_closed(
    url: str,
) -> None:

    html = wrap(
        url=url,
    )

    with pytest.raises(
        DorarHistoryParseError
    ):
        parse_dorar_history_event(
            html=html,
            canonical_url=url,
        )


def test_route_id_must_match_dom_event_id() -> None:
    html = wrap(
        event_id=8,
    )

    with pytest.raises(
        DorarHistoryParseError,
        match="headingTwo7",
    ):
        parse(
            html
        )


def test_required_event_structure_is_scoped_to_cntnt() -> None:
    outside = """
<div id="accordionEx"
 class="accordion md-accordion dorar_custom_accordion amiri_custom_content">
 <div class="event-container">
   fake outside event
 </div>
</div>
"""

    event = parse(
        wrap(
            outside=outside,
        )
    )

    assert event.title == "عنوان الحدث"

    assert (
        event.structural_audit
        .provenance_violation_count
        == 0
    )


def test_search_form_details_label_is_not_event_details() -> None:
    event = parse(
        wrap(
            details=(
                "النص التاريخي الحقيقي."
            )
        )
    )

    assert (
        event.details_text
        == "النص التاريخي الحقيقي."
    )

    assert (
        "المراجع المعتمدة"
        not in event.details_text
    )


def test_hijri_and_gregorian_are_required() -> None:
    html = wrap().replace(
        "<strong>\nالعام الهجري : 10\n</strong>",
        "",
    )

    with pytest.raises(
        DorarHistoryParseError,
        match="العام الهجري",
    ):
        parse(
            html
        )


def test_lunar_month_is_optional() -> None:
    event = parse(
        wrap(
            month=None,
        )
    )

    assert (
        event.lunar_month_text
        is None
    )

    assert (
        event.structural_audit
        .lunar_month_field_count
        == 0
    )


def test_lunar_month_is_preserved_when_present() -> None:
    event = parse(
        wrap(
            month="شوال",
        )
    )

    assert (
        event.lunar_month_text
        == "شوال"
    )


def test_adapter_does_not_promote_dorar_event_to_established_fact() -> None:
    event = parse(
        wrap()
    )

    assert (
        event.historical_report_status
        is HistoricalReportStatus
        .UNASSESSED
    )

    assert (
        event.per_event_machine_truth_grade_count
        == 0
    )


def test_dorar_is_curated_source_use_not_truth_grade() -> None:
    event = parse(
        wrap()
    )

    assert (
        event.source_use_mode
        is HistorySourceUseMode
        .CURATED_HISTORY_REFERENCE
    )

    assert (
        event.historical_report_status
        is HistoricalReportStatus
        .UNASSESSED
    )


def test_disagreement_language_is_signal_only() -> None:
    event = parse(
        wrap(
            details=(
                "اختلف أهل السير في ذلك، "
                "واتفقوا على أصل آخر."
            )
        )
    )

    assert (
        event.disagreement_lexical_signal
        is True
    )

    assert (
        event.lexical_signal_is_truth_grade
        is False
    )

    assert (
        event.historical_report_status
        is HistoricalReportStatus
        .UNASSESSED
    )


def test_prophetic_language_does_not_authenticate_hadith() -> None:
    event = parse(
        wrap(
            details=(
                "وجاء في السرد أن رسول الله "
                "قال كذا."
            )
        )
    )

    assert (
        event.prophetic_lexical_signal
        is True
    )

    assert (
        event.lexical_signal_is_hadith_authentication
        is False
    )

    assert (
        event.independent_hadith_authentication_count
        == 0
    )

    assert (
        event.hadith_matn_structurally_extractable
        is False
    )


def test_global_reference_link_is_not_event_citation() -> None:
    event = parse(
        wrap()
    )

    assert (
        event.event_reference_channel_established
        is False
    )

    assert (
        event.promoted_event_reference_count
        == 0
    )


def test_structural_reference_candidate_is_not_promoted() -> None:
    event = parse(
        wrap(
            inside_extra=(
                '<a href="/history/refs">'
                "مرجع"
                "</a>"
            )
        )
    )

    assert (
        event.structural_audit
        .structural_reference_candidate_count
        == 1
    )

    assert (
        event.promoted_event_reference_count
        == 0
    )

    assert (
        event.event_reference_channel_established
        is False
    )


def test_quran_like_node_is_not_canonical_quran_witness() -> None:
    event = parse(
        wrap(
            inside_extra=(
                '<span class="aaya">'
                "نص داخل السرد"
                "</span>"
            )
        )
    )

    assert (
        event.structural_audit
        .quran_structural_candidate_count
        == 1
    )

    assert (
        event.quran_typed_channel_established
        is False
    )

    assert (
        event.promoted_quran_witness_count
        == 0
    )


def test_hadith_like_node_does_not_create_authentication() -> None:
    event = parse(
        wrap(
            inside_extra=(
                '<span class="hadith">'
                "نص منقول"
                "</span>"
            )
        )
    )

    assert (
        event.structural_audit
        .hadith_structural_candidate_count
        == 1
    )

    assert (
        event.hadith_typed_channel_established
        is False
    )

    assert (
        event.independent_hadith_authentication_count
        == 0
    )


def test_duplicate_canonical_root_fails_closed() -> None:
    html = wrap()

    extra = """
<div id="cntnt" class="card-body">
duplicate
</div>
"""

    html = html.replace(
        "</body>",
        extra + "</body>",
    )

    with pytest.raises(
        DorarHistoryParseError,
        match="#cntnt",
    ):
        parse(
            html
        )


def test_duplicate_event_container_fails_closed() -> None:
    html = wrap()

    html = html.replace(
        '<div class="event-container">',
        (
            '<div class="event-container">'
            '<div class="event-container">'
            "duplicate"
            "</div>"
        ),
        1,
    )

    with pytest.raises(
        DorarHistoryParseError,
        match="event-container",
    ):
        parse(
            html
        )
