"""
Runtime consumer for promoted Basira safety constraints.

Important:
- learned constraints have ZERO religious authority;
- they may change safety / verification behavior only;
- they never provide Quran, Hadith, Fiqh, or other
  religious evidence.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_PROMOTED_CONSTRAINTS = (
    PROJECT_ROOT
    / "data"
    / "trust"
    / "self-hardening"
    / "promoted-constraints-v1.json"
)

QURAN_VERIFICATION_INTENT_CONSTRAINT_ID = (
    "constraint:"
    "failure:quran-verification-intent-fallthrough:v1"
)


QURAN_VERIFICATION_LANGUAGE_SWITCH_CONSTRAINT_ID = (
    "constraint:"
    "failure:quran-verification-language-switch-"
    "requires-new-verification:v1"
)

TAFSIR_LANGUAGE_SWITCH_ANCHOR_CONSTRAINT_ID = (
    "constraint:"
    "failure:tafsir-language-switch-"
    "preserves-canonical-anchor:v1"
)

HADITH_LANGUAGE_SWITCH_RETRIEVAL_CONSTRAINT_ID = (
    "constraint:"
    "failure:hadith-language-switch-"
    "requires-target-language-governed-retrieval:v1"
)


def _constraints_path() -> Path:
    configured = os.getenv(
        "BASIRA_PROMOTED_CONSTRAINTS_PATH"
    )

    if configured:
        return Path(configured)

    return DEFAULT_PROMOTED_CONSTRAINTS


def promoted_constraint_ids() -> frozenset[str]:
    """
    Load active governance constraints.

    Fail closed:
    memory may influence runtime only when both the
    document and the individual constraint explicitly
    retain religious_evidence_authority == 0.
    """

    path = _constraints_path()

    if not path.exists():
        return frozenset()

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return frozenset()

    if payload.get(
        "religious_evidence_authority"
    ) != 0:
        return frozenset()

    records = payload.get("constraints")

    if not isinstance(records, list):
        return frozenset()

    result: set[str] = set()

    for record in records:
        if not isinstance(record, dict):
            continue

        if record.get(
            "religious_evidence_authority"
        ) != 0:
            continue

        constraint_id = record.get(
            "constraint_id"
        )

        if isinstance(
            constraint_id,
            str,
        ):
            result.add(constraint_id)

    return frozenset(result)


def learned_constraint_enabled(
    constraint_id: str,
) -> bool:
    return (
        constraint_id
        in promoted_constraint_ids()
    )


def is_quran_verification_request(
    *,
    original_text: str,
    intent_text: str,
) -> bool:
    """
    Classify the learned *behavioral* condition.

    This does not decide whether Quran text is correct.
    It only decides that canonical verification is
    mandatory before general answering.
    """

    if not learned_constraint_enabled(
        QURAN_VERIFICATION_INTENT_CONSTRAINT_ID
    ):
        return False

    # Learned behavior must generalize across presentation
    # language. This memory still has ZERO religious authority:
    # it decides only that verification is mandatory.
    #
    # The downstream verifier remains responsible for choosing
    # the correct governed evidence surface:
    # - Arabic Quran literal -> canonical Mushaf verification
    # - English meaning/quotation -> governed translation lane
    surfaces = tuple(
        " ".join(
            value.casefold().split()
        )
        for value in (
            original_text,
            intent_text,
        )
    )

    quran_cues = (
        # Arabic
        "آية",
        "اية",
        "القرآن",
        "القران",
        "قرآني",
        "قراني",
        "من القرآن",
        "من القران",

        # English
        "quran",
        "qur'an",
        "koran",
        "quran quotation",
        "quran quote",
        "quranic quotation",
        "quranic quote",
        "ayah",
        "verse",
    )

    verification_cues = (
        # Arabic
        "صحيح",
        "صحيحة",
        "صح",
        "محرف",
        "محرفة",
        "محرّف",
        "محرّفة",
        "تحريف",
        "خطأ",
        "غلط",
        "مضبوط",
        "تغيير",
        "تغير",
        "تأكد",
        "تحقق",

        # English — deliberately bounded verification phrases.
        "quotation correct",
        "quote correct",
        "quoted correctly",
        "quotation accurate",
        "quote accurate",
        "verify this quotation",
        "verify this quote",
        "check this quotation",
        "check this quote",
        "misquoted",
        "misquote",
        "altered quotation",
        "altered quote",
    )

    mentions_quran = any(
        cue in surface
        for surface in surfaces
        for cue in quran_cues
    )

    asks_for_verification = any(
        cue in surface
        for surface in surfaces
        for cue in verification_cues
    )

    return (
        mentions_quran
        and asks_for_verification
    )


def extract_quran_verification_text(
    question: str,
) -> str:
    """
    Extract the candidate Quran literal from an explicit
    verification question.

    This is only input isolation for the canonical matcher;
    it does not supply or correct religious content.
    """

    cleaned = question.strip()

    for separator in (
        ":",
        "：",
        "\n",
    ):
        if separator in cleaned:
            candidate = cleaned.split(
                separator,
                1,
            )[1].strip()

            if candidate:
                return candidate.rstrip(
                    " ؟?،,.!"
                )

    return cleaned.rstrip(
        " ؟?،,.!"
    )
