from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from basira.competition.dorar_fiqh import (
    parse_dorar_fiqh_article,
)
from basira.competition.dorar_fiqh_adapter import (
    DorarFiqhEvidenceAdapter,
    _article_relevance_score,
)
from basira.competition.dorar_fiqh_admission import (
    DorarFiqhAdmissionError,
    DorarFiqhRuntimeGate,
)
from basira.competition.dorar_fiqh_source import (
    DorarFiqhSourceDocument,
)
from basira.competition.fiqh_policy import (
    FiqhSourceEligibility,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
)
from basira.evidence.models import (
    EvidenceDomain,
)

ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)


def _document(
    *,
    canonical_url: str = (
        "https://dorar.net/feqhia/424"
    ),
) -> DorarFiqhSourceDocument:
    body = (
        ROOT
        / "data/competition/discovery/"
        "dorar-fiqh/articles/"
        "comparative.html"
    ).read_bytes()

    return DorarFiqhSourceDocument(
        discovery_url=canonical_url,
        canonical_url=canonical_url,
        response_sha256=(
            sha256(body).hexdigest()
        ),
        content_type="text/html",
        body=body,
    )


def test_runtime_gate_completes_source_passport_admission() -> None:
    gate = (
        DorarFiqhRuntimeGate
        .from_repo(ROOT)
    )

    admitted = gate.admit(
        _document()
    )

    assert (
        admitted.runtime_eligibility
        is FiqhSourceEligibility.ELIGIBLE
    )

    assert (
        admitted.source_id
        == "dorar:fiqh"
    )


def test_runtime_gate_rejects_non_dorar_article() -> None:
    gate = (
        DorarFiqhRuntimeGate
        .from_repo(ROOT)
    )

    with pytest.raises(
        DorarFiqhAdmissionError
    ):
        gate.admit(
            _document(
                canonical_url=(
                    "https://example.com/"
                    "feqhia/424"
                )
            )
        )


def test_adapter_emits_only_literal_attributed_fiqh_positions() -> None:
    document = _document()

    class Client:
        def search(
            self,
            query: str,
            *,
            limit: int = 10,
        ):
            del query
            del limit

            return SimpleNamespace(
                documents=(document,)
            )

    adapter = DorarFiqhEvidenceAdapter(
        client=Client(),
        gate=(
            DorarFiqhRuntimeGate
            .from_repo(ROOT)
        ),
    )

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(
                OfficialDomain.GENERAL_FIQH
            ),
            query=(
                "مس المرأة فرجها "
                "هل ينقض الوضوء"
            ),
            limit=3,
        )
    )

    assert nodes

    position_nodes = tuple(
        node
        for node in nodes
        if node.claim_type
        == "fiqh_position"
    )

    assert position_nodes

    article = parse_dorar_fiqh_article(
        html=document.body.decode(
            "utf-8"
        ),
        canonical_url=(
            document.canonical_url
        ),
    )

    source_text = article.full_text

    for node in position_nodes:
        assert (
            node.domain
            is EvidenceDomain.FIQH
        )

        assert node.text in source_text

        assert (
            node.source_url
            == document.canonical_url
        )

        assert (
            node.work_id
            == "dorar-fiqh"
        )

    assert all(
        node.claim_type
        != "fiqh_ruling"
        for node in nodes
    )


def test_malformed_candidate_does_not_poison_valid_fiqh_evidence() -> None:
    good = _document()

    bad_body = (
        b"<html><head><title>"
        b"Malformed Dorar Fiqh"
        b"</title></head><body>"
        b"no governed structural heading"
        b"</body></html>"
    )

    bad = DorarFiqhSourceDocument(
        discovery_url=(
            "https://dorar.net/feqhia/999999"
        ),
        canonical_url=(
            "https://dorar.net/feqhia/999999"
        ),
        response_sha256=(
            sha256(bad_body).hexdigest()
        ),
        content_type="text/html",
        body=bad_body,
    )

    class Client:
        def search(
            self,
            query: str,
            *,
            limit: int = 10,
        ):
            del query
            del limit

            return SimpleNamespace(
                documents=(
                    bad,
                    good,
                )
            )

    adapter = DorarFiqhEvidenceAdapter(
        client=Client(),
        gate=(
            DorarFiqhRuntimeGate
            .from_repo(ROOT)
        ),
    )

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(
                OfficialDomain.GENERAL_FIQH
            ),
            query=(
                "مس المرأة فرجها "
                "هل ينقض الوضوء"
            ),
            limit=10,
        )
    )

    assert nodes

    assert all(
        node.source_id
        == "dorar:fiqh:424"
        for node in nodes
    )

    assert any(
        node.claim_type
        == "fiqh_position"
        for node in nodes
    )


def test_all_malformed_candidates_fail_narrow_to_empty_evidence() -> None:
    bad_body = (
        b"<html><body>"
        b"not a structural Fiqh article"
        b"</body></html>"
    )

    bad = DorarFiqhSourceDocument(
        discovery_url=(
            "https://dorar.net/feqhia/999998"
        ),
        canonical_url=(
            "https://dorar.net/feqhia/999998"
        ),
        response_sha256=(
            sha256(bad_body).hexdigest()
        ),
        content_type="text/html",
        body=bad_body,
    )

    class Client:
        def search(
            self,
            query: str,
            *,
            limit: int = 10,
        ):
            del query
            del limit

            return SimpleNamespace(
                documents=(bad,)
            )

    adapter = DorarFiqhEvidenceAdapter(
        client=Client(),
        gate=(
            DorarFiqhRuntimeGate
            .from_repo(ROOT)
        ),
    )

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(
                OfficialDomain.GENERAL_FIQH
            ),
            query="سؤال فقهي",
            limit=10,
        )
    )

    assert nodes == ()



def test_fiqh_relevance_prefers_exact_issue_title() -> None:
    from basira.competition.dorar_fiqh import (
        DorarFiqhArticle,
    )

    query = (
        "ما حكم مس المرأة فرجها "
        "وهل ينقض الوضوء؟"
    )

    def article(
        source_id: str,
        title: str,
    ) -> DorarFiqhArticle:
        return DorarFiqhArticle(
            source_id=source_id,
            canonical_url=(
                "https://dorar.net/feqhia/"
                + source_id.rsplit(
                    ":",
                    1,
                )[-1]
            ),
            article_title=title,
            full_text="نص",
            explicit_disagreement=False,
            explicit_consensus_language=False,
            positions=(),
        )

    target = article(
        "dorar:fiqh:424",
        (
            "المطلب الثاني: "
            "مس المرأة فرجها"
        ),
    )

    other_person = article(
        "dorar:fiqh:426",
        (
            "المطلب الثالث: "
            "مس فرج الغير "
            "(الكبير والصغير)"
        ),
    )

    anus = article(
        "dorar:fiqh:428",
        (
            "المطلب الرابع: "
            "مس الدبر"
        ),
    )

    male = article(
        "dorar:fiqh:422",
        (
            "المطلب الأول: "
            "مس الرجل ذكره "
            "(بدون حائل)"
        ),
    )

    target_score = (
        _article_relevance_score(
            query=query,
            article=target,
        )
    )

    assert target_score > (
        _article_relevance_score(
            query=query,
            article=other_person,
        )
    )

    assert target_score > (
        _article_relevance_score(
            query=query,
            article=anus,
        )
    )

    assert target_score > (
        _article_relevance_score(
            query=query,
            article=male,
        )
    )



def test_runtime_gate_rejects_tampered_body_with_stale_hash() -> None:
    document = _document()

    body = document.body

    assert isinstance(
        body,
        bytes,
    )

    tampered = DorarFiqhSourceDocument(
        discovery_url=(
            document.discovery_url
        ),
        canonical_url=(
            document.canonical_url
        ),
        response_sha256=(
            document.response_sha256
        ),
        content_type=(
            document.content_type
        ),
        body=(
            body
            + b"\n<!-- BASIRA-TAMPER-PROBE -->"
        ),
    )

    gate = (
        DorarFiqhRuntimeGate
        .from_repo(ROOT)
    )

    with pytest.raises(
        DorarFiqhAdmissionError,
        match=(
            "dorar_fiqh_response_"
            "hash_mismatch"
        ),
    ):
        gate.admit(
            tampered
        )
