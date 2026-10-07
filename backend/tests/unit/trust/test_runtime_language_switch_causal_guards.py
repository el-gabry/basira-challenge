from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from basira.api.service import (
    _enforce_promoted_language_constraints,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
)
from basira.trust.runtime_constraints import (
    HADITH_LANGUAGE_SWITCH_RETRIEVAL_CONSTRAINT_ID,
    QURAN_VERIFICATION_LANGUAGE_SWITCH_CONSTRAINT_ID,
    TAFSIR_LANGUAGE_SWITCH_ANCHOR_CONSTRAINT_ID,
)


def _result(
    intent: BasiraIntent,
    *,
    references: tuple[str, ...] = (),
):
    target = SimpleNamespace(
        references=references,
    )

    plan = SimpleNamespace(
        targets=(target,),
    )

    retrieval = SimpleNamespace(
        plan=plan,
    )

    understanding = SimpleNamespace(
        primary_intent=intent,
    )

    return SimpleNamespace(
        understanding=understanding,
        retrieval=retrieval,
    )


def _write_memory(
    path,
    constraint_id: str | None,
) -> None:
    constraints = []

    if constraint_id is not None:
        constraints.append(
            {
                "constraint_id":
                    constraint_id,
                "religious_evidence_authority":
                    0,
            }
        )

    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "religious_evidence_authority": 0,
                "constraints": constraints,
            }
        ),
        encoding="utf-8",
    )


def test_quran_language_switch_guard_is_memory_causal(
    tmp_path,
    monkeypatch,
) -> None:
    memory = tmp_path / "memory.json"

    _write_memory(
        memory,
        QURAN_VERIFICATION_LANGUAGE_SWITCH_CONSTRAINT_ID,
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(memory),
    )

    result = _result(
        BasiraIntent.QUOTE_VERIFICATION,
    )

    with pytest.raises(
        ValueError,
        match=(
            "quran_target_language_"
            "verification_required"
        ),
    ):
        _enforce_promoted_language_constraints(
            result=result,
            question=(
                "هل هذا النص القرآني صحيح: "
                "نص للاختبار"
            ),
            requested_language="en",
        )

    _write_memory(
        memory,
        None,
    )

    _enforce_promoted_language_constraints(
        result=result,
        question=(
            "هل هذا النص القرآني صحيح: "
            "نص للاختبار"
        ),
        requested_language="en",
    )


def test_tafsir_anchor_guard_is_memory_causal(
    tmp_path,
    monkeypatch,
) -> None:
    memory = tmp_path / "memory.json"

    _write_memory(
        memory,
        TAFSIR_LANGUAGE_SWITCH_ANCHOR_CONSTRAINT_ID,
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(memory),
    )

    unanchored = _result(
        BasiraIntent.QURAN_MEANING,
    )

    with pytest.raises(
        ValueError,
        match="tafsir_canonical_anchor_required",
    ):
        _enforce_promoted_language_constraints(
            result=unanchored,
            question="ما معنى هذا في التفسير؟",
            requested_language="ar",
        )

    anchored = _result(
        BasiraIntent.QURAN_MEANING,
        references=("2:255",),
    )

    _enforce_promoted_language_constraints(
        result=anchored,
        question="ما معنى هذا في التفسير؟",
        requested_language="ar",
    )

    _write_memory(
        memory,
        None,
    )

    _enforce_promoted_language_constraints(
        result=unanchored,
        question="ما معنى هذا في التفسير؟",
        requested_language="ar",
    )


def test_hadith_language_switch_guard_is_memory_causal(
    tmp_path,
    monkeypatch,
) -> None:
    memory = tmp_path / "memory.json"

    _write_memory(
        memory,
        HADITH_LANGUAGE_SWITCH_RETRIEVAL_CONSTRAINT_ID,
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(memory),
    )

    result = _result(
        BasiraIntent.HADITH_AUTHENTICITY,
    )

    with pytest.raises(
        ValueError,
        match=(
            "hadith_target_language_"
            "governed_retrieval_required"
        ),
    ):
        _enforce_promoted_language_constraints(
            result=result,
            question=(
                "هل هذا الحديث صحيح؟"
            ),
            requested_language="en",
        )

    _write_memory(
        memory,
        None,
    )

    _enforce_promoted_language_constraints(
        result=result,
        question="هل هذا الحديث صحيح؟",
        requested_language="en",
    )


def test_matching_target_language_controls_still_pass(
    tmp_path,
    monkeypatch,
) -> None:
    memory = tmp_path / "memory.json"

    memory.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "religious_evidence_authority": 0,
                "constraints": [
                    {
                        "constraint_id":
                            QURAN_VERIFICATION_LANGUAGE_SWITCH_CONSTRAINT_ID,
                        "religious_evidence_authority":
                            0,
                    },
                    {
                        "constraint_id":
                            HADITH_LANGUAGE_SWITCH_RETRIEVAL_CONSTRAINT_ID,
                        "religious_evidence_authority":
                            0,
                    },
                    {
                        "constraint_id":
                            TAFSIR_LANGUAGE_SWITCH_ANCHOR_CONSTRAINT_ID,
                        "religious_evidence_authority":
                            0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(memory),
    )

    _enforce_promoted_language_constraints(
        result=_result(
            BasiraIntent.QUOTE_VERIFICATION,
        ),
        question=(
            "Is this Quran quotation correct: "
            "test wording"
        ),
        requested_language="en",
    )

    _enforce_promoted_language_constraints(
        result=_result(
            BasiraIntent.HADITH_AUTHENTICITY,
        ),
        question=(
            "Is this hadith authentic?"
        ),
        requested_language="en",
    )

    _enforce_promoted_language_constraints(
        result=_result(
            BasiraIntent.TAFSIR_CONTEXT,
            references=("2:255",),
        ),
        question="What is the explanation?",
        requested_language="en",
    )
