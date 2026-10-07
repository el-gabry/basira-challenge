from basira.retrieval.fiqh_discovery_query_planner import (
    FiqhDiscoveryQueryPlanner,
)


def test_preserves_original_question():
    question = (
        "ما حكم الإجارة "
        "المنتهية بالتمليك؟"
    )

    plan = (
        FiqhDiscoveryQueryPlanner()
        .plan(question)
    )

    assert (
        plan.queries[0]
        == question
    )


def test_primary_evidence_query_is_user_issue_without_wrapper():
    plan = (
        FiqhDiscoveryQueryPlanner()
        .plan(
            "ما حكم الإجارة "
            "المنتهية بالتمليك؟"
        )
    )

    assert (
        plan.evidence_query
        == "الإجارة المنتهية بالتمليك"
    )


def test_composite_followup_does_not_pollute_evidence_query():
    plan = (
        FiqhDiscoveryQueryPlanner()
        .plan(
            "ما حكم بيع الطعام بالأجل؟ "
            "وما الشروط المتعلقة بهذه الصورة؟"
        )
    )

    assert (
        plan.evidence_query
        == "بيع الطعام بالأجل"
    )

    assert (
        "بيع الطعام بالأجل"
        in plan.queries
    )

    assert not any(
        query.startswith(
            "وما الشروط"
        )
        for query in plan.queries
    )


def test_removes_generic_request_wrapper():
    plan = (
        FiqhDiscoveryQueryPlanner()
        .plan(
            "ما حكم الإجارة "
            "المنتهية بالتمليك؟"
        )
    )

    assert (
        "الإجارة المنتهية بالتمليك"
        in plan.queries
    )


def test_planner_does_not_add_religious_synonyms():
    plan = (
        FiqhDiscoveryQueryPlanner()
        .plan(
            "ما حكم بيع الطعام بالأجل؟"
        )
    )

    joined = " | ".join(
        plan.queries
    )

    assert "نسيئة" not in joined
    assert "ربا" not in joined
    assert "حرام" not in joined
    assert "جائز" not in joined
