from __future__ import annotations

from types import SimpleNamespace

from basira.competition.dorar_tafsir import (
    DorarTafsirSection,
    DorarTafsirSectionKind,
)
from basira.competition.dorar_tafsir_adapter import (
    DorarTafsirEvidenceAdapter,
    runtime_to_policy_records,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_adapters import (
    build_ready_competition_adapters,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalBridge,
    CompetitionRetrievalRequest,
)
from basira.competition.tafsir_policy import (
    TafsirMaterialType,
    TafsirSourceEligibility,
    TafsirSourceFamily,
)


def section(
    kind,
    *,
    text="شرح الآية",
):
    return DorarTafsirSection(
        section_kind=kind,
        article_id="tt7",
        heading="عنوان",
        explanation_text=text,
        quran_contexts=(),
        quran_references=(),
        citations=(),
        narration_citations=(),
        reported_grade_citations=(),
        quran_context_text_node_count=0,
        quran_context_text_nodes_routed_to_explanation=0,
    )


def governed_runtime(
    *,
    sections,
):
    return SimpleNamespace(
        passport_id=("dorar-tafsir-v1"),
        source_family=(TafsirSourceFamily.DORAR_TAFSIR),
        runtime_eligibility=(TafsirSourceEligibility.ELIGIBLE),
        canonical_url=("https://dorar.net/tafseer/2/43"),
        response_sha256=("a" * 64),
        response_bytes=100,
        adapter_contract=("dorar-tafsir-canonical-passages-v1"),
        passage=SimpleNamespace(sections=tuple(sections)),
    )


class Retriever:
    def __init__(
        self,
        runtime,
    ):
        self.runtime = runtime

    def search(
        self,
        query,
        *,
        limit,
    ):
        del (
            query,
            limit,
        )

        return SimpleNamespace(passages=(SimpleNamespace(admitted=(self.runtime)),))


class Policy:
    def __init__(
        self,
        *,
        usable_count=None,
    ):
        self.usable_count = usable_count
        self.records = ()

    def assess(
        self,
        records,
        *,
        use_context,
    ):
        del use_context

        self.records = records

        if self.usable_count is None:
            usable = records
        else:
            usable = records[: self.usable_count]

        return SimpleNamespace(usable_records=usable)


def request():
    return CompetitionRetrievalRequest(
        official_domain=(OfficialDomain.TAFSIR),
        query="فسر الآية",
    )


def test_all_parser_sections_have_explicit_safe_mapping():
    expected = {
        DorarTafsirSectionKind.GENERAL_MEANING: TafsirMaterialType.SCHOLARLY_REASONING,
        DorarTafsirSectionKind.WORD_MEANING: TafsirMaterialType.LINGUISTIC_EXPLANATION,
        DorarTafsirSectionKind.GRAMMAR: TafsirMaterialType.LINGUISTIC_EXPLANATION,
        DorarTafsirSectionKind.TAFSIR_AYAT: TafsirMaterialType.SCHOLARLY_REASONING,
        DorarTafsirSectionKind.EDUCATIONAL_BENEFITS: (
            TafsirMaterialType.SCHOLARLY_REASONING
        ),
        DorarTafsirSectionKind.SCHOLARLY_BENEFITS: (
            TafsirMaterialType.SCHOLARLY_REASONING
        ),
        DorarTafsirSectionKind.RHETORIC: TafsirMaterialType.LINGUISTIC_EXPLANATION,
    }

    runtime = governed_runtime(
        sections=[section(kind) for kind in (DorarTafsirSectionKind)]
    )

    records = runtime_to_policy_records(runtime)

    assert len(records) == len(expected)

    actual = {
        kind: record.material_type
        for kind, record in zip(
            DorarTafsirSectionKind,
            records,
            strict=True,
        )
    }

    assert actual == expected

    assert all(
        record.material_type is not TafsirMaterialType.UNKNOWN for record in records
    )


def test_ungoverned_runtime_cannot_reach_policy():
    runtime = governed_runtime(
        sections=[
            section(DorarTafsirSectionKind.WORD_MEANING),
        ]
    )

    runtime.passport_id = "forged-passport"

    assert runtime_to_policy_records(runtime) == ()


def test_quran_context_routing_violation_fails_closed():
    current = section(DorarTafsirSectionKind.WORD_MEANING)

    current = current.model_copy(
        update={
            ("quran_context_text_nodes_routed_to_explanation"): 1,
        }
    )

    runtime = governed_runtime(
        sections=[
            current,
        ]
    )

    assert runtime_to_policy_records(runtime) == ()


def test_policy_usable_records_alone_are_promoted():
    runtime = governed_runtime(
        sections=[
            section(
                DorarTafsirSectionKind.WORD_MEANING,
                text="أول",
            ),
            section(
                DorarTafsirSectionKind.GENERAL_MEANING,
                text="ثان",
            ),
        ]
    )

    policy = Policy(usable_count=1)

    adapter = DorarTafsirEvidenceAdapter(
        retriever=Retriever(runtime),
        policy=policy,
    )

    nodes = adapter.retrieve(request())

    assert len(policy.records) == 2

    assert len(nodes) == 1

    assert nodes[0].text == "أول"

    assert nodes[0].claim_type == ("tafsir_linguistic_explanation")


def test_bridge_receives_policy_approved_tafsir():
    runtime = governed_runtime(
        sections=[
            section(DorarTafsirSectionKind.GENERAL_MEANING),
        ]
    )

    adapter = DorarTafsirEvidenceAdapter(
        retriever=Retriever(runtime),
        policy=Policy(),
    )

    bridge = CompetitionRetrievalBridge(
        evidence_adapters={
            OfficialDomain.TAFSIR: adapter,
        }
    )

    result = bridge.retrieve(request())

    assert result.unavailable is False

    assert len(result.evidence) == 1

    assert result.evidence[0].domain.value == "tafsir"


def test_ready_adapter_set_can_register_tafsir():
    runtime = governed_runtime(
        sections=[
            section(DorarTafsirSectionKind.GENERAL_MEANING),
        ]
    )

    adapter = DorarTafsirEvidenceAdapter(
        retriever=Retriever(runtime),
        policy=Policy(),
    )

    ready = build_ready_competition_adapters(tafsir=adapter)

    assert ready.evidence[OfficialDomain.TAFSIR] is adapter
