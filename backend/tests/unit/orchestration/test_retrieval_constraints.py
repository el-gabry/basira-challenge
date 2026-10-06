from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.orchestration.evidence_acceptance import (
    AnchorKind,
    AnchorOrigin,
    EvidenceAnchor,
    RetrievalShape,
    TaskEvidenceAcceptanceContract,
)
from basira.orchestration.retrieval_constraints import (
    project_contract_onto_plan,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlan,
    BasiraRetrievalPlanner,
    RetrievalStrategy,
    RetrievalTarget,
)


def test_retrieval_target_references_default_empty() -> None:
    target = RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(RetrievalStrategy.LEXICAL_FALLBACK,),
    )

    assert target.references == ()


def test_quran_anchor_projects_to_every_bound_domain() -> None:
    understanding = BasiraQueryUnderstandingService().understand(
        "ما سبب نزول الآية 2:255؟"
    )

    plan = BasiraRetrievalPlanner().build(understanding)

    domains = frozenset(
        {
            EvidenceDomain.QURAN,
            EvidenceDomain.TAFSIR,
            EvidenceDomain.REVELATION_CONTEXT,
        }
    )

    contract = TaskEvidenceAcceptanceContract(
        task_id="claim:2:255",
        retrieval_shape=(RetrievalShape.HYBRID),
        allowed_domains=domains,
        required_domains=domains,
        anchors=(
            EvidenceAnchor(
                reference="2:255",
                domains=domains,
                kind=(AnchorKind.QURAN_AYAH),
                origin=(AnchorOrigin.CANONICAL_TEXT_MATCH),
            ),
        ),
    )

    projected = project_contract_onto_plan(
        plan=plan,
        contract=contract,
    )

    by_domain = {target.domain: target for target in projected.targets}

    for domain in domains:
        assert by_domain[domain].references == ("2:255",)


def test_projection_does_not_invent_reference_for_conceptual_contract() -> None:
    understanding = BasiraQueryUnderstandingService().understand(
        "ماذا يقول الإسلام عن الصبر؟"
    )

    plan = BasiraRetrievalPlan(
        understanding=understanding,
        targets=(
            RetrievalTarget(
                domain=(EvidenceDomain.TAFSIR),
                strategies=(RetrievalStrategy.LEXICAL_FALLBACK,),
            ),
        ),
        context_requirement=(understanding.context_requirement),
    )

    contract = TaskEvidenceAcceptanceContract(
        task_id="claim:patience",
        retrieval_shape=(RetrievalShape.CONCEPTUAL),
        allowed_domains=frozenset(
            {
                EvidenceDomain.TAFSIR,
            }
        ),
        required_domains=frozenset(
            {
                EvidenceDomain.TAFSIR,
            }
        ),
    )

    projected = project_contract_onto_plan(
        plan=plan,
        contract=contract,
    )

    assert projected.targets[0].references == ()
