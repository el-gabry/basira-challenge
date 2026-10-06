from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
)
from basira.retrieval.shamela_scout import (
    InMemoryShamelaBackend,
    ShamelaHybridEvidenceScout,
)
from tests.unit.retrieval.test_shamela_scout import (
    StubAdvisor,
    manifest,
    passage,
    route,
)


def test_hybrid_scout_exposes_queries_it_actually_executed():
    item = passage(
        source_id="fiqh",
        book_id="1",
        page_id="1",
        text="أحكام الصرف والتقابض",
        domain=ScholarlyDomain.FIQH,
    )

    advisor = StubAdvisor()

    result = (
        ShamelaHybridEvidenceScout(
            backend=InMemoryShamelaBackend(
                (item,),
                manifest=manifest(
                    "fiqh"
                ),
            ),
            advisor=advisor,
        )
        .scout(
            route(
                (
                    "ما حكم معاملة "
                    "غير مذكورة بهذه الألفاظ؟"
                ),
                BasiraIntent.FIQH_QUESTION,
            )
        )
    )

    assert result.executed_query_hints

    assert (
        len(result.executed_query_hints)
        == result.subqueries_used
    )

    # This is the advisor's classical reformulation.
    assert "الصرف" in result.executed_query_hints

    assert advisor.calls >= 1
