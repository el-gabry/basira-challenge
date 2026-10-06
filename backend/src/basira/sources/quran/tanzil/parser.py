from __future__ import annotations

import re
from pathlib import Path

from basira.models.quran import QuranVerse

TANZIL_SOURCE_ID = "tanzil-quran-v1.1-uthmani"

EXPECTED_VERSE_COUNT = 6236

VERSE_PATTERN = re.compile(
    r"^(?P<surah>\d+)\|(?P<ayah>\d+)\|(?P<text>.*)$"
)


class TanzilDatasetError(ValueError):
    """Raised when Tanzil source files fail structural validation."""


class TanzilQuranParser:
    """
    Parse Tanzil Uthmani and Simple Plain Quran files.

    Uthmani text is preserved as the source/display representation.
    Simple Plain text is preserved as the search representation.
    """

    def parse_files(
        self,
        uthmani_path: Path,
        simple_plain_path: Path,
    ) -> tuple[QuranVerse, ...]:
        uthmani = self._load_file(
            uthmani_path
        )

        simple_plain = self._load_file(
            simple_plain_path
        )

        self._validate_pair(
            uthmani=uthmani,
            simple_plain=simple_plain,
        )

        verses: list[QuranVerse] = []

        for reference in sorted(
            uthmani,
            key=lambda value: (
                value[0],
                value[1],
            ),
        ):
            surah_number, ayah_number = (
                reference
            )

            verses.append(
                QuranVerse(
                    source_id=TANZIL_SOURCE_ID,
                    surah_number=surah_number,
                    ayah_number=ayah_number,
                    narration="hafs",
                    text_uthmani=uthmani[
                        reference
                    ],
                    text_search=simple_plain[
                        reference
                    ],
                )
            )

        return tuple(verses)

    def _load_file(
        self,
        path: Path,
    ) -> dict[tuple[int, int], str]:
        if not path.exists():
            raise FileNotFoundError(
                f"Tanzil file does not exist: {path}"
            )

        if not path.is_file():
            raise TanzilDatasetError(
                f"Tanzil path is not a file: {path}"
            )

        verses: dict[
            tuple[int, int],
            str,
        ] = {}

        for line_number, raw_line in enumerate(
            path.read_text(
                encoding="utf-8"
            ).splitlines(),
            start=1,
        ):
            match = VERSE_PATTERN.match(
                raw_line
            )

            # Tanzil files can contain comments,
            # metadata or license lines.
            if match is None:
                continue

            surah_number = int(
                match.group("surah")
            )

            ayah_number = int(
                match.group("ayah")
            )

            text = match.group(
                "text"
            ).strip()

            if not text:
                raise TanzilDatasetError(
                    "Empty Quran text at "
                    f"{surah_number}:{ayah_number} "
                    f"in {path.name}, "
                    f"line {line_number}."
                )

            reference = (
                surah_number,
                ayah_number,
            )

            if reference in verses:
                raise TanzilDatasetError(
                    "Duplicate Quran reference "
                    f"{surah_number}:{ayah_number} "
                    f"in {path.name}."
                )

            verses[reference] = text

        if len(verses) != EXPECTED_VERSE_COUNT:
            raise TanzilDatasetError(
                "Unexpected Tanzil verse count "
                f"in {path.name}. "
                f"Expected {EXPECTED_VERSE_COUNT}, "
                f"received {len(verses)}."
            )

        return verses

    @staticmethod
    def _validate_pair(
        uthmani: dict[
            tuple[int, int],
            str,
        ],
        simple_plain: dict[
            tuple[int, int],
            str,
        ],
    ) -> None:
        uthmani_refs = set(
            uthmani
        )

        simple_refs = set(
            simple_plain
        )

        if uthmani_refs == simple_refs:
            return

        missing_from_simple = (
            uthmani_refs - simple_refs
        )

        missing_from_uthmani = (
            simple_refs - uthmani_refs
        )

        raise TanzilDatasetError(
            "Tanzil Uthmani and Simple Plain "
            "references do not match. "
            f"Missing from Simple Plain: "
            f"{sorted(missing_from_simple)[:10]}. "
            f"Missing from Uthmani: "
            f"{sorted(missing_from_uthmani)[:10]}."
        )