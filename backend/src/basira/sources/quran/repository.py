from __future__ import annotations

from collections.abc import Iterable

from basira.models.quran import QuranVerse
from basira.normalization.quran import normalize_quran_search_text


class QuranVerseNotFoundError(KeyError):
    """Raised when a Quran reference is not available in the repository."""


class QuranRepository:
    """Local searchable repository of Quran verses."""

    def __init__(
        self,
        verses: Iterable[QuranVerse],
    ) -> None:
        self._verses = tuple(verses)

        self._by_reference: dict[
            tuple[int, int],
            QuranVerse,
        ] = {}

        self._normalized_text: dict[
            tuple[int, int],
            str,
        ] = {}

        for verse in self._verses:
            reference = (
                verse.surah_number,
                verse.ayah_number,
            )

            if reference in self._by_reference:
                raise ValueError(
                    "Duplicate Quran reference: "
                    f"{verse.reference}"
                )

            self._by_reference[reference] = verse

            self._normalized_text[reference] = (
                normalize_quran_search_text(
                    verse.text_search
                )
            )

    def __len__(self) -> int:
        return len(self._verses)

    def get(
        self,
        surah_number: int,
        ayah_number: int,
    ) -> QuranVerse | None:
        return self._by_reference.get(
            (
                surah_number,
                ayah_number,
            )
        )

    def require(
        self,
        surah_number: int,
        ayah_number: int,
    ) -> QuranVerse:
        verse = self.get(
            surah_number,
            ayah_number,
        )

        if verse is None:
            raise QuranVerseNotFoundError(
                f"Quran verse not found: "
                f"{surah_number}:{ayah_number}"
            )

        return verse

    def find_exact(
        self,
        text: str,
    ) -> tuple[QuranVerse, ...]:
        normalized = normalize_quran_search_text(
            text
        )

        if not normalized:
            return ()

        return tuple(
            verse
            for verse in self._verses
            if self._normalized_text[
                (
                    verse.surah_number,
                    verse.ayah_number,
                )
            ]
            == normalized
        )

    def find_containing(
        self,
        text: str,
    ) -> tuple[QuranVerse, ...]:
        """
        Find verses containing the normalized user quote.

        Useful when the user provides only part of an ayah.
        """

        normalized = normalize_quran_search_text(
            text
        )

        if not normalized:
            return ()

        return tuple(
            verse
            for verse in self._verses
            if normalized
            in self._normalized_text[
                (
                    verse.surah_number,
                    verse.ayah_number,
                )
            ]
        )

    def all(
        self,
    ) -> tuple[QuranVerse, ...]:
        return self._verses