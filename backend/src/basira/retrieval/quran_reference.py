from __future__ import annotations

import re

_ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)

_QURAN_REFERENCE = re.compile(
    r"^(?:quran:)?"
    r"(?P<start_surah>\d{1,3}):"
    r"(?P<start_ayah>\d{1,3})"
    r"(?:-(?:(?P<end_surah>\d{1,3}):)?"
    r"(?P<end_ayah>\d{1,3}))?$"
)


def normalize_quran_reference(
    value: str,
) -> str:
    value = value.translate(_ARABIC_DIGITS).strip().lower()

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    value = re.sub(
        r"[/：]",
        ":",
        value,
    )

    value = re.sub(
        r"[–—]",
        "-",
        value,
    )

    return value


def expand_quran_reference(
    value: str,
    *,
    max_ayahs: int = 100,
) -> (
    tuple[
        tuple[int, int],
        ...,
    ]
    | None
):
    """
    Convert one Quran execution reference into concrete
    same-surah ayah points.

    This is an execution parser only. It does not discover,
    infer, or validate a user's intended Quran anchor.

    Cross-surah ranges deliberately fail closed because
    expanding them safely requires canonical verse-count
    knowledge that belongs to the Quran repository layer.
    """

    if max_ayahs < 1:
        raise ValueError("max_ayahs must be positive")

    normalized = normalize_quran_reference(value)

    match = _QURAN_REFERENCE.fullmatch(normalized)

    if match is None:
        return None

    start_surah = int(match.group("start_surah"))
    start_ayah = int(match.group("start_ayah"))

    end_ayah_text = match.group("end_ayah")

    if end_ayah_text is None:
        end_surah = start_surah
        end_ayah = start_ayah
    else:
        end_surah = int(match.group("end_surah") or start_surah)
        end_ayah = int(end_ayah_text)

    if not 1 <= start_surah <= 114:
        return None

    if not 1 <= end_surah <= 114:
        return None

    if start_ayah < 1 or end_ayah < 1:
        return None

    if end_surah != start_surah:
        return None

    if end_ayah < start_ayah:
        return None

    count = end_ayah - start_ayah + 1

    if count > max_ayahs:
        return None

    return tuple(
        (
            start_surah,
            ayah,
        )
        for ayah in range(
            start_ayah,
            end_ayah + 1,
        )
    )
