from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from basira.models.quran import QuranVerse
from basira.sources.quran.kfgqpc import KFGQPC_HAFS_MIRROR_SOURCE_ID

EXPECTED_VERSE_COUNT = 6236


class KfgqpcDatasetError(ValueError):
    """Raised when the KFGQPC dataset does not satisfy Basira expectations."""


class KfgqpcQuranParser:
    """Parse and validate a KFGQPC Hafs JSON dataset."""

    REQUIRED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "id",
            "jozz",
            "sora",
            "sora_name_en",
            "sora_name_ar",
            "page",
            "line_start",
            "line_end",
            "aya_no",
            "aya_text",
            "aya_text_emlaey",
        }
    )

    def parse_file(
        self,
        path: Path,
    ) -> tuple[QuranVerse, ...]:
        if not path.exists():
            raise FileNotFoundError(
                f"KFGQPC JSON file does not exist: {path}"
            )

        with path.open(encoding="utf-8") as file:
            raw_data = json.load(file)

        return self.parse(raw_data)

    def parse(
        self,
        raw_data: Any,
    ) -> tuple[QuranVerse, ...]:
        if not isinstance(raw_data, list):
            raise KfgqpcDatasetError(
                "KFGQPC dataset root must be a JSON list."
            )

        if len(raw_data) != EXPECTED_VERSE_COUNT:
            raise KfgqpcDatasetError(
                "Unexpected KFGQPC verse count. "
                f"Expected {EXPECTED_VERSE_COUNT}, "
                f"received {len(raw_data)}."
            )

        verses: list[QuranVerse] = []
        references: set[tuple[int, int]] = set()

        for index, row in enumerate(raw_data, start=1):
            if not isinstance(row, dict):
                raise KfgqpcDatasetError(
                    f"Record {index} must be an object."
                )

            missing_fields = self.REQUIRED_FIELDS - row.keys()

            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                raise KfgqpcDatasetError(
                    f"Record {index} is missing fields: {missing}"
                )

            verse = QuranVerse(
                source_id=KFGQPC_HAFS_MIRROR_SOURCE_ID,
                surah_number=row["sora"],
                ayah_number=row["aya_no"],
                surah_name_ar=row["sora_name_ar"],
                surah_name_en=row["sora_name_en"],
                juz_number=row["jozz"],
                page_number=row["page"],
                line_start=row["line_start"],
                line_end=row["line_end"],
                text_uthmani=row["aya_text"],
                text_search=row["aya_text_emlaey"],
            )

            reference = (
                verse.surah_number,
                verse.ayah_number,
            )

            if reference in references:
                raise KfgqpcDatasetError(
                    "Duplicate Quran reference detected: "
                    f"{verse.reference}"
                )

            references.add(reference)
            verses.append(verse)

        return tuple(verses)
