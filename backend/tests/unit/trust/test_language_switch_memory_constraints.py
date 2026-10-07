from __future__ import annotations

import json
from pathlib import Path

from basira.trust.runtime_constraints import (
    HADITH_LANGUAGE_SWITCH_RETRIEVAL_CONSTRAINT_ID,
    QURAN_VERIFICATION_LANGUAGE_SWITCH_CONSTRAINT_ID,
    TAFSIR_LANGUAGE_SWITCH_ANCHOR_CONSTRAINT_ID,
    learned_constraint_enabled,
)

IDS = (
    QURAN_VERIFICATION_LANGUAGE_SWITCH_CONSTRAINT_ID,
    TAFSIR_LANGUAGE_SWITCH_ANCHOR_CONSTRAINT_ID,
    HADITH_LANGUAGE_SWITCH_RETRIEVAL_CONSTRAINT_ID,
)


def _memory(
    path: Path,
    *,
    authority: int,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "principle": (
                    "Basira does not learn beliefs; "
                    "it learns constraints."
                ),
                "religious_evidence_authority": (
                    authority
                ),
                "constraints": [
                    {
                        "constraint_id": item,
                        "source_certificate_id": (
                            item.removeprefix(
                                "constraint:"
                            )
                        ),
                        "rule": (
                            "Behavioral safety constraint."
                        ),
                        "replay_test_ids": [
                            "replay"
                        ],
                        "religious_evidence_authority": (
                            authority
                        ),
                    }
                    for item in IDS
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_zero_authority_language_switch_constraints_are_loadable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "memory.json"

    _memory(
        path,
        authority=0,
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(path),
    )

    assert all(
        learned_constraint_enabled(
            item
        )
        for item in IDS
    )


def test_nonzero_authority_language_switch_constraints_fail_closed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "unsafe.json"

    _memory(
        path,
        authority=1,
    )

    monkeypatch.setenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH",
        str(path),
    )

    assert not any(
        learned_constraint_enabled(
            item
        )
        for item in IDS
    )
