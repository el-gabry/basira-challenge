from __future__ import annotations

from types import SimpleNamespace

from basira.competition.dorar_hadith import (
    DorarHadithRecord,
)
from basira.competition.dorar_hadith_adapter import (
    DorarHadithEvidenceAdapter,
    record_to_candidate,
)
from basira.competition.hadith_policy import (
    HadithEvidenceDecision,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalBridge,
    CompetitionRetrievalRequest,
)
from basira.evidence.models import (
    EvidenceDomain,
)


class Retriever:
    def __init__(
        self,
        records,
    ):
        self.records = records

    def search(
        self,
        query,
        *,
        limit,
    ):
        return SimpleNamespace(records=tuple(self.records[:limit]))


class Policy:
    def __init__(
        self,
        decision,
    ):
        self.decision = decision
        self.candidates = []

    def assess(
        self,
        candidate,
    ):
        self.candidates.append(candidate)

        return SimpleNamespace(decision=self.decision)


def usable_decision():
    return HadithEvidenceDecision("usable_with_attributed_gradings")


def nonusable_decision():
    usable = HadithEvidenceDecision("usable_with_attributed_gradings")

    for item in HadithEvidenceDecision:
        if item is not usable:
            return item

    raise AssertionError("No non-usable policy decision")


def record(
    *,
    verdict="صحيح",
):
    return DorarHadithRecord(
        rank=1,
        hadith_text=("إنما الأعمال بالنيات"),
        narrator="عمر بن الخطاب",
        muhaddith="النووي",
        source="شرح مسلم",
        page_or_number="1/10",
        verdict=verdict,
    )


def test_record_maps_reported_grading_without_recomputing():
    candidate = record_to_candidate(record(verdict=("صحيح غريب")))

    assert candidate.hadith_text == ("إنما الأعمال بالنيات")

    assert candidate.narrator == ("عمر بن الخطاب")

    assert len(candidate.attestations) == 1

    rendered = str(candidate.attestations[0].model_dump())

    assert "صحيح غريب" in rendered

    assert "النووي" in rendered


def test_policy_usable_record_emits_text_and_grade():
    policy = Policy(usable_decision())

    adapter = DorarHadithEvidenceAdapter(
        retriever=Retriever(
            [
                record(),
            ]
        ),
        policy=policy,
    )

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.HADITH),
            query=("إنما الأعمال بالنيات"),
        )
    )

    assert {node.claim_type for node in nodes} == {
        "hadith_text",
        "hadith_grade",
    }

    assert all(node.domain is EvidenceDomain.HADITH for node in nodes)

    grade = next(node for node in nodes if (node.claim_type == "hadith_grade"))

    assert grade.text == "صحيح"

    assert grade.author_name == ("النووي")


def test_nonusable_policy_result_emits_no_evidence():
    adapter = DorarHadithEvidenceAdapter(
        retriever=Retriever(
            [
                record(),
            ]
        ),
        policy=Policy(nonusable_decision()),
    )

    result = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.HADITH),
            query="حديث",
        )
    )

    assert result == ()


def test_no_reported_verdict_does_not_invent_grade():
    adapter = DorarHadithEvidenceAdapter(
        retriever=Retriever(
            [
                record(verdict=None),
            ]
        ),
        policy=Policy(usable_decision()),
    )

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.HADITH),
            query="حديث",
        )
    )

    assert {node.claim_type for node in nodes} == {
        "hadith_text",
    }


def test_bridge_receives_policy_approved_hadith_only():
    adapter = DorarHadithEvidenceAdapter(
        retriever=Retriever(
            [
                record(),
            ]
        ),
        policy=Policy(usable_decision()),
    )

    bridge = CompetitionRetrievalBridge(
        evidence_adapters={
            OfficialDomain.HADITH: adapter,
        }
    )

    result = bridge.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.HADITH),
            query="حديث",
        )
    )

    assert result.unavailable is False
    assert result.materials == ()
    assert result.evidence

    assert all(node.domain is EvidenceDomain.HADITH for node in result.evidence)


def test_two_source_gradings_are_not_majority_collapsed():
    records = [
        record(verdict="صحيح"),
        DorarHadithRecord(
            rank=2,
            hadith_text=("إنما الأعمال بالنيات"),
            narrator=("عمر بن الخطاب"),
            muhaddith=("ناقد آخر"),
            source=("مصدر آخر"),
            page_or_number="2/20",
            verdict="ضعيف",
        ),
    ]

    adapter = DorarHadithEvidenceAdapter(
        retriever=Retriever(records),
        policy=Policy(usable_decision()),
    )

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.HADITH),
            query="حديث",
        )
    )

    grades = [node.text for node in nodes if (node.claim_type == "hadith_grade")]

    assert grades == [
        "صحيح",
        "ضعيف",
    ]


def test_real_dorar_policy_decision_is_evidence_eligible():
    adapter = DorarHadithEvidenceAdapter(
        retriever=Retriever(
            [
                record(verdict="صحيح غريب"),
            ]
        ),
        policy=Policy(HadithEvidenceDecision("usable_with_attributed_gradings")),
    )

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.HADITH),
            query="حديث",
        )
    )

    assert {node.claim_type for node in nodes} == {
        "hadith_text",
        "hadith_grade",
    }


def test_every_non_dorar_usable_decision_is_rejected():
    accepted = HadithEvidenceDecision("usable_with_attributed_gradings")

    for decision in HadithEvidenceDecision:
        if decision is accepted:
            continue

        adapter = DorarHadithEvidenceAdapter(
            retriever=Retriever(
                [
                    record(),
                ]
            ),
            policy=Policy(decision),
        )

        nodes = adapter.retrieve(
            CompetitionRetrievalRequest(
                official_domain=(OfficialDomain.HADITH),
                query="حديث",
            )
        )

        assert nodes == (), f"Unexpected Dorar evidence for decision={decision.value}"
