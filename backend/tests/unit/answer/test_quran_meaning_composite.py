from basira.api.app import get_query_service


def test_quran_meaning_publishes_canonical_and_focused_tafsir() -> None:
    question = (
        "ما معنى الكرسي في قوله تعالى "
        "وسع كرسيه السماوات والأرض؟"
    )

    result = (
        get_query_service()
        .governed_runtime
        .execute(question=question)
    )

    assert result.answer is not None

    answer = result.answer
    used = answer.used_evidence_ids

    assert used[0] == "quranpedia:mushaf:1:2:255"
    assert len(used) == 2
    assert used[1].startswith("dorar-tafsir:")

    assert len(answer.claims) == 2

    quran_claim, tafsir_claim = answer.claims

    assert quran_claim.axis_id == "quran"
    assert tafsir_claim.axis_id == "tafsir"

    assert (
        "وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالْأَرْضَ"
        in quran_claim.text
    )

    assert not quran_claim.text.endswith("…")

    assert (
        answer.semantic_claim_verification
        == "pass"
    )
