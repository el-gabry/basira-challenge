from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi.testclient import (
    TestClient,
)

from basira.api.app import (
    app,
)


def _enum(
    value: str,
) -> Any:
    return SimpleNamespace(value=value)


class FakeQueryService:
    def execute(
        self,
        *,
        question: str,
        quran_reference: str | None = None,
    ) -> Any:
        del quran_reference

        answer = SimpleNamespace(
            action=_enum("answer"),
            has_answer=True,
            answer="إجابة موثقة.",
            limitations=(),
            citations=(),
            evidence_coverage=1.0,
            resolution_coverage=1.0,
            used_evidence_ids=(),
            claims=(),
            expert_review=None,
        )

        bundle = SimpleNamespace(
            required_assessments=(),
            conflicts=(),
        )

        outcome = SimpleNamespace(bundle=bundle)

        understanding = SimpleNamespace(
            primary_intent=(_enum("tafsir_context")),
            risk_tags=frozenset(),
            entities=(),
            context_requirement=SimpleNamespace(
                required=frozenset(),
                optional=frozenset(),
            ),
            confidence=1.0,
        )

        retrieval = SimpleNamespace(
            evidence=(),
            unavailable_domains=(frozenset()),
        )

        return SimpleNamespace(
            question=question,
            understanding=(understanding),
            retrieval=retrieval,
            outcome=outcome,
            answer=answer,
        )


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": "basira-verify",
    }


def test_query_contract(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "basira.api.app.get_query_service",
        lambda: FakeQueryService(),
    )

    client = TestClient(app)

    response = client.post(
        "/api/v1/query",
        json={
            "question": ("ما سبب نزول سورة المجادلة؟"),
            "quran_reference": "58:1",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["action"] == "answer"
    assert body["has_answer"] is True

    assert body["answer"] == ("إجابة موثقة.")

    assert body["understanding"]["intent"] == "tafsir_context"

    assert body["conflicts"] == []


class FakeConflictQueryService(FakeQueryService):
    def execute(
        self,
        *,
        question: str,
        quran_reference: str | None = None,
    ) -> Any:
        execution = super().execute(
            question=question,
            quran_reference=quran_reference,
        )

        conflict = SimpleNamespace(
            conflict_type=(_enum("hadith_grade")),
            group_id=("hadeethenc:5457"),
            evidence_ids=(
                "source-a:5457:grade",
                "source-b:5457:grade",
            ),
        )

        execution.outcome.bundle.conflicts = (conflict,)

        execution.answer.action = _enum("escalate_to_expert")

        execution.answer.has_answer = False
        execution.answer.answer = None

        execution.answer.expert_review = {
            "case_id": ("hadith-conflict-5457"),
            "conflicts": [
                {
                    "conflict_type": ("hadith_grade"),
                    "group_id": ("hadeethenc:5457"),
                    "evidence_ids": [
                        "source-a:5457:grade",
                        "source-b:5457:grade",
                    ],
                }
            ],
        }

        return execution


def test_query_exposes_evidence_conflicts(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "basira.api.app.get_query_service",
        lambda: FakeConflictQueryService(),
    )

    client = TestClient(app)

    response = client.post(
        "/api/v1/query",
        json={
            "question": ("ما صحة حديث رقم 5457؟"),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["action"] == "escalate_to_expert"

    assert body["has_answer"] is False

    assert body["conflicts"] == [
        {
            "type": "hadith_grade",
            "group_id": ("hadeethenc:5457"),
            "evidence_ids": [
                "source-a:5457:grade",
                "source-b:5457:grade",
            ],
        }
    ]

    assert body["expert_review"]["conflicts"][0]["conflict_type"] == "hadith_grade"


def test_blank_question_is_rejected() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/query",
        json={
            "question": "   ",
        },
    )

    assert response.status_code == 422


def test_invalid_quran_reference_is_rejected() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/query",
        json={
            "question": "سؤال",
            "quran_reference": ("المجادلة:1"),
        },
    )

    assert response.status_code == 422


def _tafsir_passage() -> Any:
    from basira.models.scholarly import (
        ScholarlyDomain,
        ScholarlyPassage,
    )

    return ScholarlyPassage(
        passage_id="test-tafsir:58:1",
        source_id="test-tafsir-source",
        domain=ScholarlyDomain.TAFSIR,
        work_id="test-work",
        work_title="Test Tafsir",
        text="نص التفسير الكامل.",
    )


class FakeEvidenceDetailService:
    def __init__(
        self,
        passage: Any | None,
    ) -> None:
        self.passage = passage

    def get_publishable_tafsir(
        self,
        evidence_id: str,
    ) -> Any | None:
        if self.passage is not None and evidence_id == self.passage.passage_id:
            return self.passage

        return None


def test_evidence_detail_returns_full_publishable_tafsir(
    monkeypatch,
) -> None:
    passage = _tafsir_passage()

    monkeypatch.setattr(
        "basira.api.app.get_query_service",
        lambda: FakeEvidenceDetailService(passage),
    )

    client = TestClient(app)

    response = client.get("/api/v1/evidence/test-tafsir:58:1")

    assert response.status_code == 200

    body = response.json()

    assert body["evidence_id"] == "test-tafsir:58:1"
    assert body["domain"] == "tafsir"
    assert body["text"] == "نص التفسير الكامل."


def test_evidence_detail_hides_missing_or_unpublishable_evidence(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "basira.api.app.get_query_service",
        lambda: FakeEvidenceDetailService(None),
    )

    client = TestClient(app)

    response = client.get("/api/v1/evidence/not-visible")

    assert response.status_code == 404
    assert response.json() == {"detail": "Evidence not found."}


def test_service_rejects_non_tafsir_full_text(
    monkeypatch,
) -> None:
    from basira.api.service import (
        BasiraQueryService,
    )
    from basira.models.scholarly import (
        ScholarlyDomain,
        ScholarlyPassage,
    )

    passage = ScholarlyPassage(
        passage_id="revelation:58:1",
        source_id="test-source",
        domain=(ScholarlyDomain.REVELATION_CONTEXT),
        work_id="test-work",
        work_title="Test Revelation Source",
        text="نص سبب النزول.",
    )

    repository = SimpleNamespace(
        get=lambda evidence_id: passage if evidence_id == passage.passage_id else None
    )

    runtime = SimpleNamespace(allows=lambda **kwargs: True)

    service = BasiraQueryService(
        retriever=SimpleNamespace(),
        scholarly_repository=repository,
        scholarly_runtime=runtime,
    )

    result = service.get_publishable_tafsir(passage.passage_id)

    assert result is None


def test_service_fails_closed_when_runtime_denies_publication(
    monkeypatch,
) -> None:
    from basira.api.service import (
        BasiraQueryService,
    )

    passage = _tafsir_passage()

    class Policy:
        requires_human_review = False

        def allows(
            self,
            runtime_use,
        ) -> bool:
            del runtime_use
            return True

    monkeypatch.setattr(
        "basira.api.service.get_source_usage_policy",
        lambda source_id: Policy(),
    )

    repository = SimpleNamespace(
        get=lambda evidence_id: passage if evidence_id == passage.passage_id else None
    )

    runtime = SimpleNamespace(allows=lambda **kwargs: False)

    service = BasiraQueryService(
        retriever=SimpleNamespace(),
        scholarly_repository=repository,
        scholarly_runtime=runtime,
    )

    result = service.get_publishable_tafsir(passage.passage_id)

    assert result is None
