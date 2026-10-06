from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

import basira.api.app as app_module
from basira.api.presenter import (
    _localized_quran_representation,
)
from basira.api.schemas import (
    QueryRequest,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)


def _canonical_node() -> EvidenceNode:
    return EvidenceNode(
        evidence_id=(
            "quranpedia:mushaf:1:2:255"
        ),
        domain=EvidenceDomain.QURAN,
        text="canonical-arabic-placeholder",
        source_id="quranpedia:mushaf:1",
        reference="2:255",
        claim_type="quran_text",
        related_quran=("2:255",),
    )


def test_query_language_contract() -> None:
    assert QueryRequest(
        question="ما معنى آية الكرسي؟"
    ).language == "ar"

    assert QueryRequest(
        question="What is Ayat al-Kursi?",
        language="en",
    ).language == "en"

    with pytest.raises(
        ValidationError
    ):
        QueryRequest(
            question="test",
            language="fr",
        )


def test_english_quran_representation_is_source_native() -> None:
    localized = (
        _localized_quran_representation(
            _canonical_node(),
            language="en",
            may_expose_text=True,
        )
    )

    assert localized is not None

    assert localized.language == "en"

    assert (
        localized.evidence_id
        == (
            "quranpedia:translation:"
            "en:13638:2:255"
        )
    )

    assert (
        localized.source_id
        == (
            "quranpedia:translation:"
            "en:13638"
        )
    )

    assert (
        localized.claim_type
        == "quran_translation"
    )

    assert localized.reference == "2:255"

    assert (
        localized.work_title
        == (
            "Sahih International "
            "- English translation"
        )
    )

    assert (
        "His Kursi extends over "
        "the heavens and the earth"
        in localized.text
    )

    assert (
        localized.source_verification
        is not None
    )

    assert (
        "snapshot_sha256"
        in localized.source_verification.methods
    )


def test_localization_never_bypasses_text_gate() -> None:
    node = _canonical_node()

    assert (
        _localized_quran_representation(
            node,
            language="ar",
            may_expose_text=True,
        )
        is None
    )

    assert (
        _localized_quran_representation(
            node,
            language="en",
            may_expose_text=False,
        )
        is None
    )


def test_language_never_enters_reasoning_service() -> None:
    source = inspect.getsource(
        app_module.query
    )

    assert (
        "language=payload.language"
        in source
    )

    service_call = source.split(
        "execution = service.execute(",
        1,
    )[1].split(
        "except ValueError",
        1,
    )[0]

    assert (
        "language="
        not in service_call
    )


def test_presenter_serializes_language_in_query_response() -> None:
    import basira.api.presenter as presenter_module

    source = inspect.getsource(
        presenter_module.present_query
    )

    constructor = source.split(
        "return QueryResponse(",
        1,
    )[1]

    constructor_head = "\n".join(
        constructor.splitlines()[:12]
    )

    assert (
        "language=language,"
        in constructor_head
    )
