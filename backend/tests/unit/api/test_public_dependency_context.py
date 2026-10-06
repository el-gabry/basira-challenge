from basira.api.governed_runtime import (
    PublicGovernedQueryRuntime,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
)
from tests.unit.api.test_governed_public_runtime import (
    HostileUnifiedRetriever,
)


def _runtime() -> PublicGovernedQueryRuntime:
    return PublicGovernedQueryRuntime(
        retriever=(
            HostileUnifiedRetriever()
        ),  # type: ignore[arg-type]
    )


def test_explicit_dependent_general_claim_inherits_hadith_context():
    runtime = _runtime()

    plan, prepared = (
        runtime._plan_public_claim_graph(
            question=(
                "هل حديث إنما الأعمال بالنيات صحيح؟ "
                "وإذا ثبت، فماذا يدل على أهمية النية؟"
            )
        )
    )

    assert len(plan.tasks) == 2
    assert len(plan.dependencies) == 1

    prerequisite = plan.tasks[0]
    dependent = plan.tasks[1]

    assert (
        prerequisite.frame.reasoning_mode
        is ReasoningMode.AUTHENTICITY
    )

    assert (
        dependent.frame.primary_discipline
        is ReligiousDiscipline.HADITH
    )

    assert (
        dependent.frame.reasoning_mode
        is ReasoningMode.INTERPRETATION
    )

    understanding, resolution, domains = (
        prepared[dependent.task_id]
    )

    assert (
        understanding.primary_intent
        is BasiraIntent.HADITH_EXPLANATION
    )

    assert resolution is None

    assert domains == frozenset(
        {
            EvidenceDomain.HADITH,
        }
    )

    assert (
        EvidenceNeed.HADITH_TEXT
        in dependent.context_requirement.required
    )

    assert (
        EvidenceNeed.SOURCE_PROVENANCE
        in dependent.context_requirement.required
    )


def test_no_dependency_means_no_context_inheritance():
    runtime = _runtime()

    plan, prepared = (
        runtime._plan_public_claim_graph(
            question=(
                "هل حديث إنما الأعمال بالنيات صحيح؟ "
                "ما أهمية النية؟"
            )
        )
    )

    assert len(plan.tasks) == 2
    assert plan.dependencies == ()

    dependent = plan.tasks[1]

    understanding, _resolution, domains = (
        prepared[dependent.task_id]
    )

    assert (
        understanding.primary_intent
        is BasiraIntent.GENERAL_ISLAMIC_QUESTION
    )

    assert (
        dependent.frame.primary_discipline
        is ReligiousDiscipline.CROSS_DISCIPLINARY
    )

    assert domains == frozenset(
        {
            EvidenceDomain.GENERAL,
        }
    )
