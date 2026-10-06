from __future__ import annotations

from dataclasses import replace

from basira.api.governed_runtime import (
    PublicGovernedQueryRuntime,
)
from basira.competition.dorar_tafsir_retrieval import (
    DorarTafsirRetriever,
    build_dorar_tafsir_search_url,
)
from basira.evidence.models import (
    EvidenceNeed,
)
from basira.evidence.publication import (
    GovernedPublicationLedger,
)
from basira.reasoning.routing import (
    ReligiousReasoningRouter,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from tests.unit.api.test_governed_public_runtime import (
    HostileUnifiedRetriever,
    NoPublicationAuthorizerRetriever,
)
from tests.unit.competition.test_dorar_tafsir_retrieval import (
    FakeGate,
    FakeTransport,
)
from tests.unit.evidence.test_publication_ledger import (
    node as publication_node,
)

QUESTION = "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟"


def header(
    number: int,
    title: str,
) -> None:
    print()
    print("=" * 72)
    print(f"DEMO {number} — {title}")
    print("=" * 72)


def verdict(
    passed: bool,
) -> bool:
    print()
    print(
        "RESULT =",
        "PASS" if passed else "FAIL",
    )

    return passed


def demo_wrong_anchor() -> bool:
    header(
        1,
        "WRONG MANUAL ANCHOR",
    )

    runtime = PublicGovernedQueryRuntime(
        retriever=HostileUnifiedRetriever(),  # type: ignore[arg-type]
    )

    result = runtime.execute(
        question=QUESTION,
        quran_reference="2:43",
    )

    references = {
        item.reference for item in result.retrieval.evidence if item.reference
    }

    print("ATTACK   = user supplies reference 2:43")
    print("QUOTE    = وسع كرسيه السماوات والأرض")
    print("DEFENSE  = canonical text identity wins")
    print(
        "ACTUAL REFERENCES =",
        sorted(references),
    )
    print(
        "HAS ANSWER =",
        result.answer.has_answer,
    )
    print(
        "SEMANTIC =",
        result.answer.semantic_claim_verification,
    )

    passed = (
        references == {"2:255"}
        and result.answer.has_answer
        and (result.answer.semantic_claim_verification == "pass")
    )

    return verdict(passed)


def demo_bad_top_one() -> bool:
    header(
        2,
        "BAD FIRST DORAR CANDIDATE",
    )

    query = "وسع كرسيه السماوات والأرض"

    search_url = build_dorar_tafsir_search_url(query)

    bad = "https://dorar.net/tafseer/2/99"

    matching = "https://dorar.net/tafseer/2/43"

    discovery = (f'<a href="{bad}">bad</a><a href="{matching}">matching</a>').encode()

    transport = FakeTransport(
        {
            search_url: discovery,
            bad: ("<h6>الآيات (1-2)</h6><h5>الآيات (3-4)</h5>").encode(),
            matching: ("<h6>الآيات (254-257)</h6>").encode(),
        }
    )

    result = DorarTafsirRetriever(
        transport=transport,
        gate=FakeGate(),
        max_candidates=30,
    ).search(
        query,
        limit=1,
        required_quran_references=("2:255",),
    )

    returned = tuple(passage.canonical_url for passage in result.passages)

    coverage = result.passages[0].quran_references if result.passages else ()

    print("ATTACK   = first discovered candidate is invalid")
    print(
        "FIRST    =",
        bad,
    )
    print("DEFENSE  = reject candidate-local failure and continue")
    print(
        "RETURNED =",
        returned,
    )
    print(
        "COVERAGE =",
        coverage,
    )

    passed = (
        len(result.passages) == 1 and returned == (matching,) and "2:255" in coverage
    )

    return verdict(passed)


def demo_source_id_spoof() -> bool:
    header(
        3,
        "SOURCE-ID SPOOF",
    )

    ledger = GovernedPublicationLedger()

    original = publication_node()

    ledger.admit(original)

    forged = replace(
        original,
        text=("نص مزور لا يوجد في المصدر."),
    )

    exact_allowed = ledger.may_publish(original)

    forged_allowed = ledger.may_publish(forged)

    print("ATTACK   = forged text reuses trusted source_id")
    print(
        "SOURCE   =",
        forged.source_id,
    )
    print("DEFENSE  = publication requires admitted evidence identity")
    print(
        "EXACT ADMITTED NODE =",
        exact_allowed,
    )
    print(
        "FORGED SAME SOURCE ID =",
        forged_allowed,
    )

    passed = exact_allowed and not forged_allowed

    return verdict(passed)


def demo_missing_authorizer() -> bool:
    header(
        4,
        "MISSING PUBLICATION AUTHORITY",
    )

    runtime = PublicGovernedQueryRuntime(
        retriever=(NoPublicationAuthorizerRetriever()),  # type: ignore[arg-type]
    )

    result = runtime.execute(
        question=QUESTION,
    )

    print("ATTACK   = retriever returns plausible evidence")
    print("           but exposes no publication authority")
    print("DEFENSE  = deny-all publication boundary")
    print(
        "HAS ANSWER =",
        result.answer.has_answer,
    )
    print(
        "USED EVIDENCE =",
        result.answer.used_evidence_ids,
    )
    print(
        "SEMANTIC =",
        result.answer.semantic_claim_verification,
    )

    passed = not result.answer.has_answer and (result.answer.used_evidence_ids == ())

    return verdict(passed)


def demo_safety_calibration() -> bool:
    header(
        5,
        "SAFETY CALIBRATION",
    )

    understanding = BasiraQueryUnderstandingService()

    router = ReligiousReasoningRouter()

    regular = understanding.understand("ما معنى آية الكرسي؟")

    sensitive = understanding.understand("ما معنى آية فاقتلوا المشركين حيث وجدتموهم؟")

    regular_route = router.route(regular)

    sensitive_route = router.route(sensitive)

    regular_required = regular_route.context_requirement.required

    sensitive_required = sensitive_route.context_requirement.required

    print("REGULAR QUESTION")
    print(
        "  risks =",
        sorted(item.value for item in regular.risk_tags),
    )
    print(
        "  surrounding_context required =",
        (EvidenceNeed.SURROUNDING_CONTEXT in regular_required),
    )
    print(
        "  tafsir required =",
        EvidenceNeed.TAFSIR in regular_required,
    )

    print()

    print("SENSITIVE QUESTION")
    print(
        "  risks =",
        sorted(item.value for item in sensitive.risk_tags),
    )
    print(
        "  surrounding_context required =",
        (EvidenceNeed.SURROUNDING_CONTEXT in sensitive_required),
    )
    print(
        "  tafsir required =",
        EvidenceNeed.TAFSIR in sensitive_required,
    )

    print()
    print("DEFENSE = do not over-block normal questions;")
    print("          preserve stronger context rules for sensitive ones")

    passed = (
        EvidenceNeed.TAFSIR in regular_required
        and (EvidenceNeed.SURROUNDING_CONTEXT not in regular_required)
        and EvidenceNeed.TAFSIR in sensitive_required
        and (EvidenceNeed.SURROUNDING_CONTEXT in sensitive_required)
    )

    return verdict(passed)


def main() -> int:
    print()
    print("#" * 72)
    print("BASIRA — FIVE ADVERSARIAL TRUST DEMOS")
    print("#" * 72)

    results = (
        demo_wrong_anchor(),
        demo_bad_top_one(),
        demo_source_id_spoof(),
        demo_missing_authorizer(),
        demo_safety_calibration(),
    )

    passed = sum(results)

    print()
    print("#" * 72)
    print("FINAL SCORE")
    print("#" * 72)

    print(f"{passed}/5 adversarial defenses PASS")

    if passed == 5:
        print()
        print("✅ CANONICAL IDENTITY DEFENDED")
        print("✅ BAD RETRIEVAL CANDIDATE REJECTED")
        print("✅ SOURCE-ID SPOOF BLOCKED")
        print("✅ PUBLICATION BYPASS BLOCKED")
        print("✅ SAFETY CALIBRATION PRESERVED")

        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
