from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from basira.competition.dorar_history_admission import (
    DorarHistoryAdmissionError,
    admit_dorar_history_response,
)
from basira.competition.history_policy import (
    HistoricalReportStatus,
)


ROOT = Path(
    __file__
).resolve().parents[3]


RUNTIME = (
    ROOT
    / "data/competition/manifests/"
    "history/"
    "dorar-history-runtime-v1.json"
)


PASSPORT = (
    ROOT
    / "data/competition/passports/"
    "dorar-history.json"
)


URL = (
    "https://dorar.net/"
    "history/event/999999"
)


def fixture_html(
    *,
    url: str = URL,
    event_id: int = 999999,
    details: str = (
        "ورد في السرد التاريخي "
        "تفصيل للحدث."
    ),
) -> bytes:

    html = f"""
<!doctype html>
<html>
<head>
<link rel="canonical" href="{url}">
</head>
<body>

<form>
<label>
تفاصيل الحدث
</label>
<a href="/history/refs">
المراجع
</a>
</form>

<div id="cntnt" class="card-body">

<div class="row">
تصفح
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
<h6>
حدث اختباري
</h6>
</a>
</div>

<div
 id="collapseTwo{event_id}"
 class="show"
>
<div class="card-body">

<strong>
العام الهجري : 10
</strong>

<strong>
العام الميلادي : 631
</strong>

<h6>
تفاصيل الحدث:
</h6>

<p>
{details}
</p>

</div>
</div>

</div>
</div>
</div>
</div>
</body>
</html>
"""

    return html.encode(
        "utf-8"
    )


def admit(
    *,
    url: str = URL,
    raw: bytes | None = None,
    runtime_path: Path = RUNTIME,
):

    return admit_dorar_history_response(
        canonical_url=url,
        response_bytes=(
            fixture_html(
                url=url,
                event_id=int(
                    url.rstrip(
                        "/"
                    ).split(
                        "/"
                    )[-1]
                ),
            )
            if raw is None
            else raw
        ),
        runtime_manifest_path=(
            runtime_path
        ),
        passport_path=(
            PASSPORT
        ),
    )


def test_nonbaseline_canonical_event_is_runtime_admitted() -> None:
    envelope = admit()

    assert (
        envelope.source_id
        == "dorar-history-v1"
    )

    assert (
        envelope.runtime_eligibility
        == "eligible"
    )

    assert (
        envelope.passport_id
        == "dorar-history-source-trust-v1"
    )

    assert (
        envelope.event.event_id
        == 999999
    )


def test_runtime_admission_does_not_establish_historical_fact() -> None:
    envelope = admit()

    assert (
        envelope.historical_report_status
        is HistoricalReportStatus
        .UNASSESSED
    )

    assert (
        envelope.event.historical_report_status
        is HistoricalReportStatus
        .UNASSESSED
    )

    assert (
        envelope.may_state_as_established_fact
        is False
    )

    assert (
        envelope
        .categorical_claim_requires_governed_report_assessment
        is True
    )


def test_response_hash_is_carried() -> None:
    raw = fixture_html()

    envelope = admit(
        raw=raw
    )

    assert (
        envelope.response_sha256
        == hashlib.sha256(
            raw
        ).hexdigest()
    )

    assert (
        envelope.response_bytes
        == len(raw)
    )


def test_search_form_does_not_enter_event_details() -> None:
    envelope = admit()

    assert (
        "المراجع"
        not in envelope.event.details_text
    )


def test_prophetic_wording_does_not_authenticate_hadith() -> None:
    raw = fixture_html(
        details=(
            "ذكر السرد رسول الله "
            "صلى الله عليه وسلم."
        )
    )

    envelope = admit(
        raw=raw
    )

    assert (
        envelope.event
        .prophetic_lexical_signal
        is True
    )

    assert (
        envelope
        .independent_hadith_authentication
        is False
    )

    assert (
        envelope.event
        .independent_hadith_authentication_count
        == 0
    )

    assert (
        envelope.event
        .hadith_matn_structurally_extractable
        is False
    )


def test_disagreement_wording_does_not_create_truth_grade() -> None:
    raw = fixture_html(
        details=(
            "اختلف أهل السير "
            "في بعض تفاصيل الخبر."
        )
    )

    envelope = admit(
        raw=raw
    )

    assert (
        envelope.event
        .disagreement_lexical_signal
        is True
    )

    assert (
        envelope.event
        .lexical_signal_is_truth_grade
        is False
    )

    assert (
        envelope.event
        .per_event_machine_truth_grade_count
        == 0
    )


def test_event_reference_channel_remains_unestablished() -> None:
    envelope = admit()

    assert (
        envelope
        .event_reference_channel_established
        is False
    )

    assert (
        envelope.event
        .promoted_event_reference_count
        == 0
    )


def test_quran_witness_is_never_promoted() -> None:
    envelope = admit()

    assert (
        envelope.canonical_quran_witness
        is False
    )

    assert (
        envelope.event
        .promoted_quran_witness_count
        == 0
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://dorar.net/history/1",
        "https://evil.example/history/1",
        "https://dorar.net/history",
        "https://dorar.net/history/",
        "https://dorar.net/history/search",
        "https://dorar.net/history/refs",
        "https://dorar.net/history/0",
        "https://dorar.net/history/-1",
        "https://dorar.net/history/1/",
        "https://dorar.net/history/event",
        "https://dorar.net/history/event/0",
        "https://dorar.net/history/event/1/",
        "https://dorar.net/history/1?q=x",
        "https://dorar.net/history/1#x",
    ],
)
def test_noncanonical_runtime_urls_fail_closed(
    url: str,
) -> None:

    with pytest.raises(
        DorarHistoryAdmissionError
    ):
        admit_dorar_history_response(
            canonical_url=url,
            response_bytes=b"<html></html>",
            runtime_manifest_path=RUNTIME,
            passport_path=PASSPORT,
        )


def test_audited_baseline_drift_is_blocked(
    tmp_path: Path,
) -> None:

    raw = fixture_html()

    manifest = json.loads(
        RUNTIME.read_text(
            encoding="utf-8"
        )
    )

    manifest[
        "audited_baselines"
    ] = [
        {
            "case":
                "synthetic",

            "canonical_url":
                URL,

            "sha256":
                hashlib.sha256(
                    raw
                ).hexdigest(),

            "purpose":
                "unit-test sentinel"
        }
    ]

    runtime_path = (
        tmp_path
        / "runtime.json"
    )

    runtime_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    mutated = (
        raw
        + b"\n<!-- drift -->\n"
    )

    with pytest.raises(
        DorarHistoryAdmissionError,
        match=(
            "audited_baseline_artifact_drift"
        ),
    ):

        admit(
            raw=mutated,
            runtime_path=(
                runtime_path
            ),
        )


def test_policy_coverage_and_registry_are_promoted() -> None:
    official = json.loads(
        (
            ROOT
            / "data/competition/manifests/"
            "history/"
            "official-history-policy-v1.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        official[
            "runtime_state"
        ][
            "dorar_history"
        ]
        == "ELIGIBLE"
    )

    assert (
        official[
            "runtime_state"
        ][
            "first_three_centuries_registry"
        ]
        == "EMPTY_PENDING_SOURCE_AUDIT"
    )


    coverage = json.loads(
        (
            ROOT
            / "data/competition/coverage/"
            "official-domain-coverage-v1.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    history = next(
        item
        for item in coverage[
            "domains"
        ]
        if (
            item["domain"]
            == "seerah_history"
        )
    )

    assert (
        history["status"]
        == "governed_runtime"
    )

    assert (
        history[
            "runtime_source_ids"
        ]
        == [
            "dorar-history-v1"
        ]
    )


    registry = json.loads(
        (
            ROOT
            / "data/competition/sources/"
            "history/"
            "history_source_registry.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    dorar = [
        item
        for item in registry[
            "sources"
        ]
        if (
            item.get(
                "source_id"
            )
            == "dorar-history-v1"
        )
    ]

    assert len(dorar) == 1

    assert (
        dorar[0][
            "independently_establishes_event"
        ]
        is False
    )

    assert not any(
        item.get(
            "source_family"
        )
        == "first_three_centuries_islamic_source"
        for item
        in registry[
            "sources"
        ]
    )


def test_entity_registry_remains_empty() -> None:
    entities = json.loads(
        (
            ROOT
            / "data/competition/sources/"
            "history/"
            "historical_entity_registry.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        entities["entities"]
        == []
    )


def test_passport_freezes_semantic_boundaries() -> None:
    passport = json.loads(
        PASSPORT.read_text(
            encoding="utf-8"
        )
    )

    assert (
        passport[
            "runtime_eligibility"
        ]
        == "eligible"
    )

    assert (
        passport[
            "admission_scope"
        ]
        == "canonical_event_only"
    )

    semantic = passport[
        "semantic_guarantees"
    ]

    assert (
        semantic[
            "runtime_admission_equals_established_fact"
        ]
        is False
    )

    assert (
        semantic[
            "default_historical_report_status"
        ]
        == "unassessed"
    )

    assert (
        semantic[
            "may_state_as_established_fact"
        ]
        is False
    )

    assert (
        semantic[
            "categorical_claim_requires_governed_report_assessment"
        ]
        is True
    )

    assert (
        semantic[
            "independent_hadith_authentication"
        ]
        is False
    )

    assert (
        semantic[
            "generic_shamela_fallback"
        ]
        is False
    )
