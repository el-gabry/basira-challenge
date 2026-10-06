from __future__ import annotations

from enum import StrEnum

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class ScholarlyDomain(StrEnum):
    TAFSIR = "tafsir"
    REVELATION_CONTEXT = "revelation_context"
    FIQH = "fiqh"
    AQIDAH = "aqidah"
    FATWA = "fatwa"
    SIRA = "sira"
    HISTORY = "history"
    LANGUAGE = "language"
    GENERAL = "general"


class ScholarlyPassage(BaseModel):
    """
    One attributable passage from a scholarly work.

    This is intentionally broader than TafsirRecord so
    Basira can use the same evidence contract for
    tafsir, fiqh, aqidah, fatwa, and classical books.

    The original scholarly text must be preserved
    exactly as received from its source snapshot.
    """

    passage_id: str = Field(
        min_length=1
    )

    source_id: str = Field(
        min_length=1
    )

    domain: ScholarlyDomain

    work_id: str = Field(
        min_length=1
    )

    work_title: str = Field(
        min_length=1
    )

    text: str = Field(
        min_length=1
    )

    author_name: str | None = None
    institution: str | None = None
    publisher: str | None = None

    source_version: str | None = None
    source_url: str | None = None

    section_title: str | None = None
    chapter_title: str | None = None

    volume: str | None = None
    page: str | None = None

    surah_number: int | None = Field(
        default=None,
        ge=1,
        le=114,
    )

    ayah_start: int | None = Field(
        default=None,
        ge=1,
    )

    ayah_end: int | None = Field(
        default=None,
        ge=1,
    )

    metadata: dict[
        str,
        str,
    ] = Field(
        default_factory=dict
    )

    @model_validator(
        mode="after"
    )
    def validate_quran_span(
        self,
    ) -> ScholarlyPassage:
        quran_fields = (
            self.surah_number,
            self.ayah_start,
            self.ayah_end,
        )

        if all(
            value is None
            for value in quran_fields
        ):
            return self

        if (
            self.surah_number is None
            or self.ayah_start is None
        ):
            raise ValueError(
                "Quran-linked passages require "
                "surah_number and ayah_start."
            )

        if (
            self.ayah_end is not None
            and self.ayah_end
            < self.ayah_start
        ):
            raise ValueError(
                "ayah_end cannot be before "
                "ayah_start."
            )

        return self

    @property
    def quran_reference(
        self,
    ) -> str | None:
        if (
            self.surah_number is None
            or self.ayah_start is None
        ):
            return None

        if (
            self.ayah_end is None
            or self.ayah_end
            == self.ayah_start
        ):
            return (
                f"{self.surah_number}:"
                f"{self.ayah_start}"
            )

        return (
            f"{self.surah_number}:"
            f"{self.ayah_start}-"
            f"{self.ayah_end}"
        )
