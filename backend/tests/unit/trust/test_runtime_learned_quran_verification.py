from __future__ import annotations

import json
from pathlib import Path

from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)
from basira.trust.runtime_constraints import (
    QURAN_VERIFICATION_INTENT_CONSTRAINT_ID,
    extract_quran_verification_text,
    learned_constraint_enabled,
)


def _promoted_memory(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "principle": (
                    "Basira does not learn beliefs; "
                    "it learns constraints."
                ),
                "religious_evidence_authority": 0,
                "constraints": [
                    {
                        "constraint_id": (
                            QURAN_VERIFICATION_INTENT_CONSTRAINT_ID
                        ),
                        "source_certificate_id": (
                            "failure:quran-verification-"
                            "intent-fallthrough:v1"
                        ),
                        "rule": (
                            "Quran correctness questions "
                            "require canonical verification."
                        ),
                        "replay_test_ids": [
                            "runtime-test"
                        ],
                        "religious_evidence_authority": 0,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_promoted_constraint_routes_quran_correctness_to_quote_verification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    memory = tmp_path / "promoted.json"

    _promoted_memory(memory)

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(memory),
    )

    result = (
        BasiraQueryUnderstandingService()
        .understand(
            "هل هذه الآية صحيحة: "
            "يا أيها الذين آمنوا "
            "استعينوا بالصبر والصلاة "
            "إن الله يحب الصابرين؟"
        )
    )

    assert (
        result.primary_intent
        is BasiraIntent.QUOTE_VERIFICATION
    )

    assert learned_constraint_enabled(
        QURAN_VERIFICATION_INTENT_CONSTRAINT_ID
    )


def test_memory_does_not_route_quran_meaning_question_to_quote_verification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    memory = tmp_path / "promoted.json"

    _promoted_memory(memory)

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(memory),
    )

    result = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما معنى آية الكرسي؟"
        )
    )

    assert (
        result.primary_intent
        is not BasiraIntent.QUOTE_VERIFICATION
    )


def test_unpromoted_constraint_does_not_change_behavior(
    tmp_path: Path,
    monkeypatch,
) -> None:
    missing = tmp_path / "missing.json"

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(missing),
    )

    result = (
        BasiraQueryUnderstandingService()
        .understand(
            "هل هذه الآية صحيحة: "
            "إن الله يحب الصابرين؟"
        )
    )

    assert (
        result.primary_intent
        is not BasiraIntent.QUOTE_VERIFICATION
    )


def test_nonzero_religious_authority_memory_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    unsafe = tmp_path / "unsafe.json"

    unsafe.write_text(
        json.dumps(
            {
                "religious_evidence_authority": 1,
                "constraints": [
                    {
                        "constraint_id": (
                            QURAN_VERIFICATION_INTENT_CONSTRAINT_ID
                        ),
                        "religious_evidence_authority": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(unsafe),
    )

    assert not learned_constraint_enabled(
        QURAN_VERIFICATION_INTENT_CONSTRAINT_ID
    )


def test_extracts_quran_literal_after_colon() -> None:
    question = (
        "الكلام ده من القرآن مضبوط ولا فيه تغيير: "
        "يا أيها الذين آمنوا "
        "استعينوا بالصبر والصلاة "
        "إن الله يحب الصابرين؟"
    )

    assert (
        extract_quran_verification_text(
            question
        )
        == (
            "يا أيها الذين آمنوا "
            "استعينوا بالصبر والصلاة "
            "إن الله يحب الصابرين"
        )
    )
