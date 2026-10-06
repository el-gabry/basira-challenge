from __future__ import annotations

from basira.retrieval.atomic_query import (
    plan_atomic_queries,
)


def test_exact_quran_reference_is_not_expanded() -> None:
    plan = plan_atomic_queries("ما معنى الآية 2:255؟")

    assert plan.route == "exact_reference"
    assert plan.atomic_queries == ()


def test_arabic_paraphrase_maps_to_search_concept() -> None:
    plan = plan_atomic_queries("كيف يتحدث القرآن والتفسير عن الثبات عند الشدائد؟")

    assert plan.route == "conceptual"
    assert 1 <= len(plan.atomic_queries) <= 3

    assert any("الصبر" in query.search_text for query in plan.atomic_queries)


def test_english_query_gets_arabic_search_representation() -> None:
    plan = plan_atomic_queries("What does Islam teach about patience during hardship?")

    assert plan.route == "cross_lingual"
    assert 1 <= len(plan.atomic_queries) <= 3

    assert any("الصبر" in query.search_text for query in plan.atomic_queries)


def test_planner_never_emits_reference_or_evidence_ids() -> None:
    plan = plan_atomic_queries(
        "Can someone with many sins return to God and be forgiven?"
    )

    rendered = " ".join(query.search_text for query in plan.atomic_queries)

    assert ":" not in rendered
    assert "evidence" not in rendered.casefold()
    assert "hadith" not in rendered.casefold()


def test_planner_is_bounded() -> None:
    plan = plan_atomic_queries(
        "I want patience, gratitude, justice, mercy, "
        "knowledge, prayer and trust in God."
    )

    assert len(plan.atomic_queries) <= 3


def test_unmatched_query_does_not_invent_concept() -> None:
    plan = plan_atomic_queries("موضوع غير معروف تماما")

    assert plan.route == "conceptual"
    assert plan.atomic_queries == ()


def test_english_token_matching_avoids_sin_inside_blessings() -> None:
    plan = plan_atomic_queries(
        "What does the Quran teach about being grateful for blessings?"
    )

    concepts = {query.concept for query in plan.atomic_queries}

    assert "gratitude" in concepts
    assert "repentance_forgiveness" not in concepts
