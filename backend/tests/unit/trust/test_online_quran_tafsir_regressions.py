from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from basira.api.service import (
    _enforce_promoted_language_constraints,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)
from basira.trust.runtime_constraints import (
    TAFSIR_LANGUAGE_SWITCH_ANCHOR_CONSTRAINT_ID,
)


def _result(
    intent: BasiraIntent,
    *,
    references: tuple[str, ...] = (),
):
    return SimpleNamespace(
        understanding=SimpleNamespace(
            primary_intent=intent,
        ),
        retrieval=SimpleNamespace(
            plan=SimpleNamespace(
                targets=(
                    SimpleNamespace(
                        references=references,
                    ),
                ),
            ),
        ),
    )


def _memory(
    path,
    *,
    enabled: bool,
) -> None:
    constraints = []

    if enabled:
        constraints.append(
            {
                "constraint_id":
                    TAFSIR_LANGUAGE_SWITCH_ANCHOR_CONSTRAINT_ID,
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


def test_online_arabic_tafsir_wording_is_quran_meaning() -> None:
    result = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما تفسير هذه الآية؟"
        )
    )

    assert (
        result.primary_intent
        is BasiraIntent.QURAN_MEANING
    )


def test_online_english_tafsir_wording_is_quran_meaning() -> None:
    result = (
        BasiraQueryUnderstandingService()
        .understand(
            "Explain the tafsir of verse 2:255"
        )
    )

    assert (
        result.primary_intent
        is BasiraIntent.QURAN_MEANING
    )


def test_quran_meaning_cannot_bypass_tafsir_anchor_by_intent_label(
    tmp_path,
    monkeypatch,
) -> None:
    memory = tmp_path / "memory.json"

    _memory(
        memory,
        enabled=True,
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(memory),
    )

    execution = _result(
        BasiraIntent.QURAN_MEANING,
    )

    with pytest.raises(
        ValueError,
        match="tafsir_canonical_anchor_required",
    ):
        _enforce_promoted_language_constraints(
            result=execution,
            question="ما تفسير هذه الآية؟",
            requested_language="ar",
        )


def test_quran_meaning_anchor_allows_issue_complete_route(
    tmp_path,
    monkeypatch,
) -> None:
    memory = tmp_path / "memory.json"

    _memory(
        memory,
        enabled=True,
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(memory),
    )

    _enforce_promoted_language_constraints(
        result=_result(
            BasiraIntent.QURAN_MEANING,
            references=("2:255",),
        ),
        question=(
            "ما معنى الكرسي في قوله تعالى "
            "وسع كرسيه السماوات والأرض؟"
        ),
        requested_language="ar",
    )


def test_same_online_failure_is_memory_causal(
    tmp_path,
    monkeypatch,
) -> None:
    memory = tmp_path / "memory.json"

    execution = _result(
        BasiraIntent.QURAN_MEANING,
    )

    _memory(
        memory,
        enabled=True,
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(memory),
    )

    with pytest.raises(
        ValueError,
        match="tafsir_canonical_anchor_required",
    ):
        _enforce_promoted_language_constraints(
            result=execution,
            question="ما تفسير هذه الآية؟",
            requested_language="ar",
        )

    _memory(
        memory,
        enabled=False,
    )

    _enforce_promoted_language_constraints(
        result=execution,
        question="ما تفسير هذه الآية؟",
        requested_language="ar",
    )
