from __future__ import annotations

import json
import re
from functools import cached_property
from hashlib import sha256
from html import unescape
from pathlib import Path
from typing import Any

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)

QURANPEDIA_TRANSLATION_PASSPORT_PATH = Path(
    "data/competition/passports/"
    "quranpedia-sahih-international-en.json"
)

QURANPEDIA_TRANSLATION_MANIFEST_PATH = Path(
    "data/competition/manifests/quran/"
    "quranpedia-sahih-international-en-2026-10-06.json"
)

QURANPEDIA_TRANSLATION_SOURCE_ID = (
    "quranpedia:translation:en:13638"
)

QURANPEDIA_TRANSLATION_SOURCE_URL = (
    "https://quranpedia.net/"
    "translation-books/13638.json"
)

_TRANSLATION_ID = 13638

_STANDARD_RE = re.compile(
    r"^\s*"
    r"<div\s+style=['\"]direction:\s*ltr['\"]>"
    r"(?P<english>.*?)"
    r"</div>"
    r"\s*$",
    re.IGNORECASE | re.DOTALL,
)

_MIXED_RE = re.compile(
    r"^\s*"
    r"<div\s+class=['\"]ayah quran-page['\"]>"
    r".*?"
    r"</div>"
    r"\s*<br\s*/?>\s*"
    r"<div\s+style=['\"]direction:\s*ltr['\"]>"
    r"(?P<english>.*?)"
    r"</div>"
    r"\s*$",
    re.IGNORECASE | re.DOTALL,
)


class QuranpediaTranslationAdmissionError(
    ValueError
):
    """Governed Quran translation admission failed."""


def _load_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise QuranpediaTranslationAdmissionError(
            f"cannot_load_json:{path}"
        ) from exc

    if not isinstance(value, dict):
        raise QuranpediaTranslationAdmissionError(
            f"json_root_not_object:{path}"
        )

    return value


def _sha256(
    path: Path,
) -> str:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise QuranpediaTranslationAdmissionError(
            f"cannot_read_snapshot:{path}"
        ) from exc

    return sha256(
        payload
    ).hexdigest()


def _clean_translation(
    value: Any,
) -> str:
    if not isinstance(value, str):
        raise QuranpediaTranslationAdmissionError(
            "translated_text_not_string"
        )

    raw = value.strip()

    match = _STANDARD_RE.fullmatch(
        raw
    )

    if match is None:
        match = _MIXED_RE.fullmatch(
            raw
        )

    if match is None:
        raise QuranpediaTranslationAdmissionError(
            "unadmitted_translation_markup"
        )

    english = match.group(
        "english"
    )

    if "<" in english or ">" in english:
        raise QuranpediaTranslationAdmissionError(
            "nested_translation_markup"
        )

    text = unescape(
        english
    ).strip()

    if not text:
        raise QuranpediaTranslationAdmissionError(
            "translation_text_blank"
        )

    return text


class QuranpediaTranslationEvidenceAdapter:
    """
    Governed source-native English Quran translation.

    It is a companion to canonical Arabic Quran evidence,
    never a replacement for canonical Quran text.
    """

    def __init__(
        self,
        *,
        repo_root: Path | str = ".",
    ) -> None:
        self._repo_root = Path(
            repo_root
        ).resolve()

    @cached_property
    def _records(
        self,
    ) -> dict[
        tuple[int, int],
        str,
    ]:
        passport = _load_json(
            self._repo_root
            / QURANPEDIA_TRANSLATION_PASSPORT_PATH
        )

        manifest = _load_json(
            self._repo_root
            / QURANPEDIA_TRANSLATION_MANIFEST_PATH
        )

        for document in (
            passport,
            manifest,
        ):
            if (
                document.get("provider")
                != "Quranpedia"
            ):
                raise QuranpediaTranslationAdmissionError(
                    "provider_mismatch"
                )

            if (
                document.get("role")
                != "quran_translation"
            ):
                raise QuranpediaTranslationAdmissionError(
                    "role_mismatch"
                )

            if (
                document.get("source_id")
                != QURANPEDIA_TRANSLATION_SOURCE_ID
            ):
                raise QuranpediaTranslationAdmissionError(
                    "source_identity_mismatch"
                )

            if (
                document.get("language")
                != "English"
                or document.get("locale_code")
                != "en"
                or document.get("direction")
                != "ltr"
            ):
                raise QuranpediaTranslationAdmissionError(
                    "language_identity_mismatch"
                )

        passport_snapshot = passport.get(
            "snapshot"
        )

        manifest_snapshot = manifest.get(
            "snapshot"
        )

        if (
            not isinstance(
                passport_snapshot,
                dict,
            )
            or not isinstance(
                manifest_snapshot,
                dict,
            )
        ):
            raise QuranpediaTranslationAdmissionError(
                "snapshot_contract_missing"
            )

        if (
            passport_snapshot
            != manifest_snapshot
        ):
            raise QuranpediaTranslationAdmissionError(
                "snapshot_contract_mismatch"
            )

        snapshot_rel = (
            manifest_snapshot.get("path")
        )

        expected_hash = (
            manifest_snapshot.get("sha256")
        )

        expected_count = (
            manifest_snapshot.get(
                "record_count"
            )
        )

        if (
            not isinstance(
                snapshot_rel,
                str,
            )
            or not snapshot_rel
        ):
            raise QuranpediaTranslationAdmissionError(
                "snapshot_path_invalid"
            )

        if (
            not isinstance(
                expected_hash,
                str,
            )
            or not expected_hash
        ):
            raise QuranpediaTranslationAdmissionError(
                "snapshot_hash_invalid"
            )

        if expected_count != 6236:
            raise QuranpediaTranslationAdmissionError(
                "snapshot_count_invalid"
            )

        snapshot_path = (
            self._repo_root
            / snapshot_rel
        )

        if (
            _sha256(snapshot_path)
            != expected_hash
        ):
            raise QuranpediaTranslationAdmissionError(
                "snapshot_hash_mismatch"
            )

        payload = _load_json(
            snapshot_path
        )

        if (
            payload.get("id")
            != _TRANSLATION_ID
        ):
            raise QuranpediaTranslationAdmissionError(
                "translation_id_mismatch"
            )

        if (
            payload.get("language")
            != "English"
            or payload.get("locale_code")
            != "en"
            or payload.get("direction")
            != "ltr"
        ):
            raise QuranpediaTranslationAdmissionError(
                "translation_identity_mismatch"
            )

        ayahs = payload.get(
            "ayahs"
        )

        if (
            not isinstance(ayahs, list)
            or len(ayahs) != 6236
        ):
            raise QuranpediaTranslationAdmissionError(
                "translation_record_count_mismatch"
            )

        records: dict[
            tuple[int, int],
            str,
        ] = {}

        for row in ayahs:
            if not isinstance(row, dict):
                raise QuranpediaTranslationAdmissionError(
                    "translation_record_invalid"
                )

            try:
                reference = (
                    int(
                        row["surah_number"]
                    ),
                    int(
                        row["ayah_number"]
                    ),
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ) as exc:
                raise QuranpediaTranslationAdmissionError(
                    "translation_reference_invalid"
                ) from exc

            if reference in records:
                raise QuranpediaTranslationAdmissionError(
                    "duplicate_translation_reference"
                )

            records[
                reference
            ] = _clean_translation(
                row.get(
                    "translated_text"
                )
            )

        if len(records) != 6236:
            raise QuranpediaTranslationAdmissionError(
                "translation_reference_count_mismatch"
            )

        return records

    def records(
        self,
    ) -> tuple[
        tuple[int, int, str],
        ...,
    ]:
        """
        Return the admitted governed translation corpus.

        This exposes only text that has already passed the
        passport / manifest / snapshot SHA256 admission gate.

        It grants no new religious authority.
        """

        return tuple(
            (
                surah,
                ayah,
                text,
            )
            for (
                surah,
                ayah,
            ), text in sorted(
                self._records.items()
            )
        )

    def get(
        self,
        *,
        surah: int,
        ayah: int,
    ) -> EvidenceNode | None:
        reference = (
            int(surah),
            int(ayah),
        )

        text = self._records.get(
            reference
        )

        if text is None:
            return None

        quran_reference = (
            f"{reference[0]}:"
            f"{reference[1]}"
        )

        return EvidenceNode(
            evidence_id=(
                f"{QURANPEDIA_TRANSLATION_SOURCE_ID}:"
                f"{quran_reference}"
            ),
            domain=EvidenceDomain.QURAN,
            text=text,
            source_id=(
                QURANPEDIA_TRANSLATION_SOURCE_ID
            ),
            source_version=(
                "translation-book:13638"
            ),
            reference=quran_reference,
            source_url=(
                QURANPEDIA_TRANSLATION_SOURCE_URL
            ),
            work_id=str(
                _TRANSLATION_ID
            ),
            work_title=(
                "Sahih International "
                "- English translation"
            ),
            claim_type="quran_translation",
            authority_scope=(
                "translation_of_quran_meanings"
            ),
            related_quran=(
                quran_reference,
            ),
        )
