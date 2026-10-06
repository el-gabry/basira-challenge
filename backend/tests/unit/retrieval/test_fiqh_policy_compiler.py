from __future__ import annotations

from dataclasses import (
    FrozenInstanceError,
)

import pytest

from basira.competition.fiqh_policy import (
    FiqhSourceEligibility,
    Madhhab,
)
from basira.competition.madhhab_authority import (
    MadhhabBookAuthorityClass,
    MadhhabBookPassport,
    MadhhabBookRetrievalMode,
)
from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.retrieval.fiqh_policy_compiler import (
    FiqhRetrievalPolicyCompiler,
    bind_fiqh_policy,
)
from basira.retrieval.shamela_fts_backend import (
    ShamelaFtsBackend,
)
from basira.retrieval.shamela_scout import (
    ShamelaPlanningAdvisor,
    ShamelaScoutPlan,
    ShamelaScoutPlanner,
    ShamelaSearchTask,
)


def passport(
    *,
    work_id: str,
    madhhab: Madhhab = Madhhab.MALIKI,
    authority_class: MadhhabBookAuthorityClass = (
        MadhhabBookAuthorityClass
        .VERIFIED_MUTAMAD
    ),
    governed: bool = True,
    eligible: bool = True,
) -> MadhhabBookPassport:
    return MadhhabBookPassport(
        work_id=work_id,
        canonical_title=f"Book {work_id}",
        author="Test Author",
        madhhab=madhhab,
        authority_class=authority_class,
        authority_evidence_ids=(
            f"authority:{work_id}",
        ),
        edition_or_provider="test",
        exact_edition_governed=(
            governed
        ),
        source_eligibility=(
            FiqhSourceEligibility.ELIGIBLE
            if eligible
            else FiqhSourceEligibility
            .PENDING_AUDIT
        ),
    )


def test_compiler_allows_only_verified_mutamad_primary_work() -> None:
    envelope = (
        FiqhRetrievalPolicyCompiler()
        .compile(
            books=(
                passport(
                    work_id="work:mutamad"
                ),
                passport(
                    work_id="work:ungoverned",
                    governed=False,
                ),
            ),
            requested_madhhabs=(
                Madhhab.MALIKI.value,
            ),
        )
    )

    assert envelope.primary_work_ids == (
        "work:mutamad",
    )

    assert envelope.allowed_work_ids == (
        "work:mutamad",
    )

    assert (
        "work:ungoverned"
        not in envelope.allowed_work_ids
    )


def test_supporting_reference_is_never_promoted_to_primary_lane() -> None:
    envelope = (
        FiqhRetrievalPolicyCompiler()
        .compile(
            books=(
                passport(
                    work_id="work:mutamad",
                ),
                passport(
                    work_id="work:recognized",
                    authority_class=(
                        MadhhabBookAuthorityClass
                        .VERIFIED_RECOGNIZED_REFERENCE
                    ),
                ),
            ),
            requested_madhhabs=(
                Madhhab.MALIKI.value,
            ),
            mode=(
                MadhhabBookRetrievalMode
                .SUPPORTING_REFERENCE_ALLOWED
            ),
        )
    )

    assert envelope.primary_work_ids == (
        "work:mutamad",
    )

    assert envelope.supporting_work_ids == (
        "work:recognized",
    )

    assert envelope.allowed_work_ids == (
        "work:mutamad",
    )


def test_compiler_filters_books_by_requested_madhhab() -> None:
    envelope = (
        FiqhRetrievalPolicyCompiler()
        .compile(
            books=(
                passport(
                    work_id="work:maliki",
                    madhhab=Madhhab.MALIKI,
                ),
                passport(
                    work_id="work:hanafi",
                    madhhab=Madhhab.HANAFI,
                ),
            ),
            requested_madhhabs=(
                Madhhab.MALIKI.value,
            ),
        )
    )

    assert envelope.allowed_work_ids == (
        "work:maliki",
    )


def test_policy_fingerprint_is_order_independent() -> None:
    compiler = (
        FiqhRetrievalPolicyCompiler()
    )

    one = compiler.compile(
        books=(
            passport(
                work_id="work:b"
            ),
            passport(
                work_id="work:a"
            ),
        ),
        requested_madhhabs=(
            Madhhab.MALIKI.value,
        ),
    )

    two = compiler.compile(
        books=(
            passport(
                work_id="work:a"
            ),
            passport(
                work_id="work:b"
            ),
        ),
        requested_madhhabs=(
            Madhhab.MALIKI.value,
        ),
    )

    assert (
        one.policy_fingerprint
        == two.policy_fingerprint
    )


def test_policy_envelope_is_frozen() -> None:
    envelope = (
        FiqhRetrievalPolicyCompiler()
        .compile(
            books=(
                passport(
                    work_id="work:mutamad"
                ),
            ),
            requested_madhhabs=(
                Madhhab.MALIKI.value,
            ),
        )
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        envelope.primary_work_ids = (  # type: ignore[misc]
            "work:evil",
        )


def test_binding_places_same_policy_on_plan_and_initial_tasks() -> None:
    task = ShamelaSearchTask(
        task_id="task:1",
        query="بيع العينة",
        domains=(
            ScholarlyDomain.FIQH,
        ),
        requested_madhhabs=(
            Madhhab.MALIKI.value,
        ),
    )

    plan = ShamelaScoutPlan(
        plan_id="plan:1",
        question="بيع العينة عند المالكية",
        required_domains=(
            ScholarlyDomain.FIQH,
        ),
        requested_madhhabs=(
            Madhhab.MALIKI.value,
        ),
        comparative=False,
        preserve_disagreement=True,
        book_family_hints=(),
        initial_tasks=(task,),
    )

    envelope = (
        FiqhRetrievalPolicyCompiler()
        .compile(
            books=(
                passport(
                    work_id="work:mutamad"
                ),
            ),
            requested_madhhabs=(
                Madhhab.MALIKI.value,
            ),
        )
    )

    bound = bind_fiqh_policy(
        plan,
        envelope,
    )

    assert bound.allowed_work_ids == (
        "work:mutamad",
    )

    assert (
        bound.policy_fingerprint
        == envelope.policy_fingerprint
    )

    assert (
        bound.initial_tasks[
            0
        ].allowed_work_ids
        == bound.allowed_work_ids
    )

    assert (
        bound.initial_tasks[
            0
        ].policy_fingerprint
        == bound.policy_fingerprint
    )


def test_binding_rejects_madhhab_scope_mutation() -> None:
    plan = ShamelaScoutPlan(
        plan_id="plan:1",
        question="comparative question",
        required_domains=(
            ScholarlyDomain.FIQH,
        ),
        requested_madhhabs=(
            Madhhab.HANAFI.value,
        ),
        comparative=False,
        preserve_disagreement=True,
        book_family_hints=(),
        initial_tasks=(),
    )

    envelope = (
        FiqhRetrievalPolicyCompiler()
        .compile(
            books=(
                passport(
                    work_id="work:maliki"
                ),
            ),
            requested_madhhabs=(
                Madhhab.MALIKI.value,
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="madhhab scope",
    ):
        bind_fiqh_policy(
            plan,
            envelope,
        )


class Advisor(
    ShamelaPlanningAdvisor
):
    def propose_queries(
        self,
        *,
        plan: ShamelaScoutPlan,
        observations: tuple,
        max_queries: int,
    ) -> tuple[str, ...]:
        del plan
        del observations
        del max_queries

        return (
            "adaptive reformulated query",
        )


def test_advisor_can_mutate_query_but_not_policy() -> None:
    plan = ShamelaScoutPlan(
        plan_id="plan:adaptive",
        question="original query",
        required_domains=(),
        requested_madhhabs=(),
        comparative=False,
        preserve_disagreement=True,
        book_family_hints=(),
        initial_tasks=(),
        allowed_work_ids=(
            "work:1",
        ),
        policy_fingerprint=(
            "policy:frozen"
        ),
    )

    tasks = (
        ShamelaScoutPlanner()
        .next_tasks(
            plan=plan,
            hits=(),
            observations=(),
            remaining_subqueries=1,
            advisor=Advisor(),
        )
    )

    assert len(tasks) == 1

    assert (
        tasks[0].query
        == "adaptive reformulated query"
    )

    assert (
        tasks[0].allowed_work_ids
        == plan.allowed_work_ids
    )

    assert (
        tasks[0].policy_fingerprint
        == plan.policy_fingerprint
    )


class RecordingIndex:
    def __init__(
        self,
    ) -> None:
        self.calls = 0
        self.kwargs: dict[
            str,
            object,
        ] = {}

    def search(
        self,
        query: str,
        **kwargs: object,
    ) -> tuple:
        self.calls += 1
        self.kwargs = {
            "query": query,
            **kwargs,
        }

        return ()


def test_fts_backend_forwards_policy_work_allowlist() -> None:
    index = RecordingIndex()

    backend = object.__new__(
        ShamelaFtsBackend
    )

    backend.index = index

    task = ShamelaSearchTask(
        task_id="task:fts",
        query="مسألة",
        domains=(
            ScholarlyDomain.FIQH,
        ),
        allowed_work_ids=(
            "work:1",
            "work:2",
        ),
        policy_fingerprint=(
            "policy:1"
        ),
    )

    assert (
        backend.search(
            task,
            limit=5,
        )
        == ()
    )

    assert index.calls == 1

    assert (
        index.kwargs[
            "book_ids"
        ]
        == (
            "work:1",
            "work:2",
        )
    )


def test_fts_backend_bound_empty_allowlist_fails_closed() -> None:
    index = RecordingIndex()

    backend = object.__new__(
        ShamelaFtsBackend
    )

    backend.index = index

    task = ShamelaSearchTask(
        task_id="task:none",
        query="مسألة",
        domains=(
            ScholarlyDomain.FIQH,
        ),
        allowed_work_ids=(),
        policy_fingerprint=(
            "policy:empty"
        ),
    )

    assert (
        backend.search(
            task
        )
        == ()
    )

    assert index.calls == 0
