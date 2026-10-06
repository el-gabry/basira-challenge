from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from basira.competition.dorar_tafsir_admission import (
    DorarTafsirAdmissionDecision,
    DorarTafsirPassport,
    DorarTafsirRuntimeGate,
    load_dorar_tafsir_passport,
    passport_artifact_mismatches,
)
from basira.competition.tafsir_policy import (
    TafsirSourceEligibility,
    TafsirSourceFamily,
)


ROOT = Path(
    __file__
).resolve().parents[3]


PASSPORT_PATH = (
    ROOT
    / "data/competition/passports/"
    "dorar-tafsir.json"
)


def gate() -> DorarTafsirRuntimeGate:
    return (
        DorarTafsirRuntimeGate
        .from_repo(
            ROOT
        )
    )


def test_passport_is_dorar_and_runtime_eligible() -> None:
    passport = (
        load_dorar_tafsir_passport(
            PASSPORT_PATH
        )
    )

    assert (
        passport.source_family
        is TafsirSourceFamily.DORAR_TAFSIR
    )

    assert (
        passport.runtime_eligibility
        is TafsirSourceEligibility.ELIGIBLE
    )

    assert (
        passport.runtime_scope
        == "canonical_passage_only"
    )


def test_passport_artifacts_are_exactly_verified() -> None:
    passport = (
        load_dorar_tafsir_passport(
            PASSPORT_PATH
        )
    )

    assert (
        passport_artifact_mismatches(
            passport,
            repo_root=ROOT,
        )
        == ()
    )


def test_canonical_passage_is_allowed() -> None:
    result = gate().assess(
        "https://dorar.net/tafseer/1/1"
    )

    assert (
        result.decision
        is DorarTafsirAdmissionDecision.ALLOW
    )

    assert result.surah_number == 1

    assert result.passage_id == 1


def test_surah_page_is_discovery_only() -> None:
    result = gate().assess(
        "https://dorar.net/tafseer/48"
    )

    assert (
        result.decision
        is DorarTafsirAdmissionDecision
        .DISCOVERY_ONLY
    )


def test_tafsir_home_is_discovery_only() -> None:
    result = gate().assess(
        "https://dorar.net/tafseer"
    )

    assert (
        result.decision
        is DorarTafsirAdmissionDecision
        .DISCOVERY_ONLY
    )


def test_non_dorar_host_is_blocked() -> None:
    result = gate().assess(
        "https://example.com/tafseer/1/1"
    )

    assert (
        result.decision
        is DorarTafsirAdmissionDecision.BLOCK
    )


def test_http_is_blocked() -> None:
    result = gate().assess(
        "http://dorar.net/tafseer/1/1"
    )

    assert (
        result.decision
        is DorarTafsirAdmissionDecision.BLOCK
    )


def test_query_is_blocked() -> None:
    result = gate().assess(
        "https://dorar.net/tafseer/1/1?x=1"
    )

    assert (
        result.decision
        is DorarTafsirAdmissionDecision.BLOCK
    )


def test_out_of_range_surah_is_blocked() -> None:
    result = gate().assess(
        "https://dorar.net/tafseer/115/1"
    )

    assert (
        result.decision
        is DorarTafsirAdmissionDecision.BLOCK
    )


def test_live_evidence_carries_exact_response_hash() -> None:
    html = """
<div id="cntnt">

<article id="tt4">

<h5>تفسير الآيات:</h5>

<p>
<span class="aaya">
الْحَمْدُ لِلَّهِ
</span>

شرح الآية.

<span class="tip">
[1] رواه البخاري.
</span>
</p>

</article>

</div>
"""

    evidence = gate().admit(
        html=html,
        canonical_url=(
            "https://dorar.net/tafseer/1/1"
        ),
    )

    assert evidence.passport_id == (
        "dorar-tafsir-v1"
    )

    assert evidence.response_sha256 == (
        hashlib.sha256(
            html.encode(
                "utf-8"
            )
        ).hexdigest()
    )

    assert evidence.response_bytes == len(
        html.encode(
            "utf-8"
        )
    )

    assert len(
        evidence.passage.sections
    ) == 1


def test_discovery_surface_cannot_be_admitted_as_evidence() -> None:
    with pytest.raises(
        ValueError,
        match="admission blocked",
    ):
        gate().admit(
            html="<html></html>",
            canonical_url=(
                "https://dorar.net/tafseer/1"
            ),
        )


def test_tampered_audit_result_blocks_runtime() -> None:
    raw = json.loads(
        PASSPORT_PATH.read_text(
            encoding="utf-8"
        )
    )

    raw[
        "adversarial_audit_result"
    ] = "FAIL"

    passport = DorarTafsirPassport(
        **raw
    )

    bad_gate = (
        DorarTafsirRuntimeGate(
            passport=passport
        )
    )

    result = bad_gate.assess(
        "https://dorar.net/tafseer/1/1"
    )

    assert (
        result.decision
        is DorarTafsirAdmissionDecision.BLOCK
    )

    assert (
        "adversarial_audit_not_pass"
        in result.reasons
    )


def test_guardrails_remain_fail_closed() -> None:
    passport = (
        load_dorar_tafsir_passport(
            PASSPORT_PATH
        )
    )

    assert passport.guardrails[
        "quran_text_as_canonical_quran_witness"
    ] is False

    assert passport.guardrails[
        "independent_isnad_grading"
    ] is False

    assert passport.guardrails[
        "authenticity_from_frequency"
    ] is False

    assert passport.guardrails[
        "direct_fiqh_ruling_from_tafsir"
    ] is False
