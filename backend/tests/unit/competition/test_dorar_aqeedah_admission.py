from __future__ import annotations

import json
from pathlib import Path

import pytest

from basira.competition.dorar_aqeedah_admission import (
    DorarAqeedahAdmissionError,
    admit_dorar_aqeedah_response,
)


ROOT = Path(
    __file__
).resolve().parents[3]


RUNTIME = (
    ROOT
    / "data/competition/manifests/"
    "aqeedah/"
    "dorar-aqeedah-runtime-v1.json"
)


PASSPORT = (
    ROOT
    / "data/competition/passports/"
    "dorar-aqeeda.json"
)


BASELINE = (
    ROOT
    / "data/competition/discovery/"
    "dorar-aqeedah/raw/"
    "detailed_evidence.html"
)


def baseline_bytes() -> bytes:
    return BASELINE.read_bytes()


def admit(
    *,
    url: str = (
        "https://dorar.net/aqeeda/420"
    ),
    raw: bytes | None = None,
):
    return admit_dorar_aqeedah_response(
        canonical_url=url,
        response_bytes=(
            baseline_bytes()
            if raw is None
            else raw
        ),
        runtime_manifest_path=RUNTIME,
        passport_path=PASSPORT,
    )


def test_audited_baseline_is_admitted() -> None:
    envelope = admit()

    assert (
        envelope.source_id
        == "dorar-aqeeda-v1"
    )

    assert (
        envelope.runtime_eligibility
        == "eligible"
    )

    assert envelope.article_id == 420

    assert (
        envelope.passport_id
        == "dorar-aqeeda-source-trust-v1"
    )

    assert (
        envelope.passage.routing
        .provenance_violation_count
        == 0
    )


def test_response_hash_is_carried_into_evidence_envelope() -> None:
    envelope = admit()

    assert len(
        envelope.response_sha256
    ) == 64

    assert (
        envelope.response_bytes
        == len(
            baseline_bytes()
        )
    )


def test_baseline_artifact_drift_is_blocked() -> None:
    mutated = (
        baseline_bytes()
        + b"\n<!-- drift -->\n"
    )

    with pytest.raises(
        DorarAqeedahAdmissionError,
        match="baseline_artifact_drift",
    ):
        admit(
            raw=mutated
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://dorar.net/aqeeda/420",
        "https://evil.example/aqeeda/420",
        "https://dorar.net/aqeeda",
        "https://dorar.net/aqeeda/",
        "https://dorar.net/aqeeda/search",
        "https://dorar.net/aqeeda/420/",
        "https://dorar.net/aqeeda/420/title-slug",
        "https://dorar.net/aqeeda/0",
        "https://dorar.net/aqeeda/-1",
        "https://dorar.net/aqeeda/420?q=x",
        "https://dorar.net/aqeeda/420#x",
        "https://dorar.net/refs/aqeeda",
        "https://dorar.net/article/1987",
    ],
)
def test_noncanonical_surfaces_fail_closed(
    url: str,
) -> None:

    with pytest.raises(
        DorarAqeedahAdmissionError
    ):
        admit(
            url=url
        )


def test_quran_boundary_survives_runtime_admission() -> None:
    envelope = admit()

    assert (
        envelope
        .quran_context_is_canonical_witness
        is False
    )

    assert all(
        item.canonical_quran_witness
        is False
        for item
        in envelope.passage.quran_contexts
    )


def test_hadith_boundary_survives_runtime_admission() -> None:
    envelope = admit()

    assert (
        envelope
        .independent_hadith_authentication
        is False
    )

    assert (
        envelope.passage
        .hadith_matn_structurally_extractable
        is False
    )

    assert all(
        note.independent_authenticity_judgment
        is False
        for note
        in envelope.passage.source_notes
    )


def test_bibliography_never_promotes_authority() -> None:
    envelope = admit()

    assert (
        envelope
        .bibliographic_authority_promotion
        is False
    )

    assert all(
        note.aqeedah_authority_promotion
        is False
        for note
        in envelope.passage.source_notes
    )


def test_generic_shamela_fallback_remains_false() -> None:
    envelope = admit()

    assert (
        envelope
        .generic_shamela_fallback_allowed
        is False
    )


def test_policy_and_coverage_are_runtime_promoted() -> None:
    official = json.loads(
        (
            ROOT
            / "data/competition/manifests/"
            "aqeedah/"
            "official-aqeedah-policy-v1.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        official[
            "runtime_state"
        ][
            "dorar_aqeeda"
        ]
        == "ELIGIBLE"
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

    aqeedah = next(
        item
        for item in coverage[
            "domains"
        ]
        if (
            item["domain"]
            == "aqeedah_intro_to_islam"
        )
    )

    assert (
        aqeedah["status"]
        == "governed_runtime"
    )

    assert (
        aqeedah[
            "runtime_source_ids"
        ]
        == [
            "dorar-aqeeda-v1"
        ]
    )


def test_early_source_authority_registry_remains_empty() -> None:
    registry = json.loads(
        (
            ROOT
            / "data/competition/sources/"
            "aqeedah/"
            "aqeedah_authority_registry.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert registry[
        "sources"
    ] == []


def test_passport_freezes_expected_boundaries() -> None:
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
        == "canonical_article_only"
    )

    boundaries = passport[
        "hard_boundaries"
    ]

    assert (
        boundaries[
            "quran_context_is_canonical_quran_witness"
        ]
        is False
    )

    assert (
        boundaries[
            "independent_hadith_authentication"
        ]
        is False
    )

    assert (
        boundaries[
            "bibliographic_citation_promotes_aqeedah_authority"
        ]
        is False
    )

    assert (
        boundaries[
            "generic_shamela_fallback"
        ]
        is False
    )
