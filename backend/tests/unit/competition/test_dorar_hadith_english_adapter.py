from pathlib import Path

from basira.competition.dorar_hadith_english_adapter import (
    DorarEnglishHadithEvidenceAdapter,
    DorarEnglishHadithRuntimeGate,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
)
from basira.retrieval.official_hadith_retriever import (
    _authenticity_candidate_matches,
)

ROOT = Path(__file__).resolve().parents[3]


def _request(
    query: str,
) -> CompetitionRetrievalRequest:
    return CompetitionRetrievalRequest(
        official_domain=(
            OfficialDomain.HADITH
        ),
        query=query,
        limit=10,
        references=(),
    )


def test_english_dorar_record_is_exact_hash_bound():
    gate = DorarEnglishHadithRuntimeGate(
        repo_root=ROOT,
    )

    record = gate.load_record()

    assert record.canonical_url == (
        "https://dorar.net/en/ahadith/45"
    )

    assert record.hadith_number == "54"

    assert record.collection_heading == (
        "Bukhari hadiths"
    )

    assert record.canonical_collection == (
        "Sahih al-Bukhari"
    )

    assert (
        "Actions are but by intentions"
        in record.hadith_text
    )

    assert (
        "Commentary"
        not in record.hadith_text
    )


def test_english_intentions_is_admitted_by_existing_sahihain_policy():
    adapter = (
        DorarEnglishHadithEvidenceAdapter(
            repo_root=ROOT,
        )
    )

    nodes = adapter.retrieve(
        _request(
            "Is the hadith "
            "“Actions are judged by intentions” "
            "authentic?"
        )
    )

    assert len(nodes) == 2

    text = next(
        node
        for node in nodes
        if node.claim_type
        == "hadith_text"
    )

    verification = next(
        node
        for node in nodes
        if node.claim_type
        == "hadith_grade"
    )

    assert (
        "Actions are but by intentions"
        in text.text
    )

    assert text.reference == (
        "https://dorar.net/en/ahadith/45"
    )

    assert text.work_title == (
        "Sahih al-Bukhari"
    )

    assert verification.topic == "sahih"

    assert (
        text.evidence_id
        in verification.related_hadith
    )


def test_unrelated_english_hadith_query_fails_closed():
    adapter = (
        DorarEnglishHadithEvidenceAdapter(
            repo_root=ROOT,
        )
    )

    assert (
        adapter.retrieve(
            _request(
                "Is the hadith about "
                "a completely unrelated topic "
                "authentic?"
            )
        )
        == ()
    )


def test_english_authenticity_identity_guard_ignores_request_scaffolding():
    assert _authenticity_candidate_matches(
        question=(
            "Is the hadith "
            "Actions are judged by intentions "
            "authentic?"
        ),
        hadith_text=(
            "Actions are but by intentions, "
            "and each person will have "
            "what he intended."
        ),
    )


def test_english_identity_guard_still_rejects_unrelated_text():
    assert not (
        _authenticity_candidate_matches(
            question=(
                "Is the hadith "
                "Actions are judged by intentions "
                "authentic?"
            ),
            hadith_text=(
                "The believers are like "
                "a structure supporting "
                "one another."
            ),
        )
    )
