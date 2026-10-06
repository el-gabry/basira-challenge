from types import SimpleNamespace

import basira.competition.retrieval_adapters as adapters
from basira.evidence.scholarly_adapter import (
    ScholarlyEvidenceAdapter,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.retrieval.shamela_scout import (
    ShamelaScoutStopReason,
)


class FakeBackend:
    is_available = True


class FakeScout:
    result = None

    def __init__(
        self,
        *,
        backend,
        planner,
        advisor,
    ):
        del backend
        del planner
        del advisor

        self.adapter = (
            ScholarlyEvidenceAdapter()
        )

    def scout(
        self,
        route,
        *,
        limit_per_task,
    ):
        del route
        del limit_per_task

        assert self.result is not None
        return self.result


def _passage(
    *,
    passage_id: str,
    work_id: str,
    text: str,
) -> ScholarlyPassage:
    return ScholarlyPassage(
        passage_id=passage_id,
        source_id="shamela-test",
        domain=ScholarlyDomain.FIQH,
        work_id=work_id,
        work_title="كتاب فقهي",
        text=text,
        page="10",
        metadata={
            "madhhab": "shafii",
        },
    )


def _request(
    *,
    allowed_work_ids,
):
    return SimpleNamespace(
        query="ما حكم البيتكوين؟",
        limit=5,
        fiqh_policy=SimpleNamespace(
            allowed_work_ids=(
                allowed_work_ids
            ),
        ),
    )


def test_adapter_uses_adaptive_query_to_return_only_target_fragment(
    monkeypatch,
):
    parent = _passage(
        passage_id="book-1:10",
        work_id="book-1",
        text=(
            "باب الطهارة. "
            "ويشترط التقابض في المجلس في الصرف. "
            "ثم ذكر المصنف باب الصلاة."
        ),
    )

    FakeScout.result = SimpleNamespace(
        stop_reason=(
            ShamelaScoutStopReason
            .RETRIEVAL_COVERAGE_MET
        ),
        hits=(
            SimpleNamespace(
                passage=parent
            ),
        ),
        executed_query_hints=(
            "الثمنية الصرف التقابض",
        ),
    )

    monkeypatch.setattr(
        adapters,
        "ShamelaHybridEvidenceScout",
        FakeScout,
    )

    adapter = (
        adapters.FiqhHybridEvidenceAdapter(
            backend=FakeBackend(),
        )
    )

    result = adapter.retrieve(
        _request(
            allowed_work_ids=(
                "book-1",
            ),
        )
    )

    assert len(result) == 1

    node = result[0]

    assert node.text == (
        "ويشترط التقابض في المجلس في الصرف."
    )

    assert node.text in parent.text

    assert node.text != parent.text

    assert node.work_id == "book-1"

    # Public answer-bearing identity now belongs to the
    # structural Fiqh unit, not the intermediate projection.
    assert (
        node.evidence_id.startswith(
            "fiqh-unit:"
        )
    )

    assert (
        node.evidence_id.endswith(
            ":position"
        )
    )

    assert (
        node.claim_type
        == "fiqh_position"
    )

    # Parent source provenance is preserved structurally.
    assert (
        node.related_fiqh
        == (
            parent.passage_id,
        )
    )


def test_better_matching_unauthorized_book_is_never_projected(
    monkeypatch,
):
    allowed = _passage(
        passage_id="allowed:10",
        work_id="allowed-book",
        text=(
            "باب في أحكام الطهارة. "
            "ثم باب في أحكام الصلاة."
        ),
    )

    unauthorized = _passage(
        passage_id="forbidden:99",
        work_id="forbidden-book",
        text=(
            "ويشترط التقابض في المجلس "
            "في مسائل الصرف."
        ),
    )

    FakeScout.result = SimpleNamespace(
        stop_reason=(
            ShamelaScoutStopReason
            .RETRIEVAL_COVERAGE_MET
        ),
        hits=(
            SimpleNamespace(
                passage=allowed
            ),
            SimpleNamespace(
                passage=unauthorized
            ),
        ),
        executed_query_hints=(
            "الصرف التقابض",
        ),
    )

    monkeypatch.setattr(
        adapters,
        "ShamelaHybridEvidenceScout",
        FakeScout,
    )

    adapter = (
        adapters.FiqhHybridEvidenceAdapter(
            backend=FakeBackend(),
        )
    )

    result = adapter.retrieve(
        _request(
            allowed_work_ids=(
                "allowed-book",
            ),
        )
    )

    # The authorized book has no relevant fragment.
    # The relevant unauthorized book cannot be used.
    # Therefore we fail narrow.
    assert result == ()
