from __future__ import annotations

from pydantic import BaseModel, Field


class QuranVerse(BaseModel):
    """
    Quran verse preserved from a specific source snapshot.

    Only fields common to trusted Quran sources are required.
    Source-specific metadata is optional.
    """

    source_id: str = Field(min_length=1)

    surah_number: int = Field(
        ge=1,
        le=114,
    )

    ayah_number: int = Field(
        ge=1,
    )

    text_uthmani: str = Field(
        min_length=1,
    )

    text_search: str = Field(
        min_length=1,
    )

    narration: str = "hafs"

    surah_name_ar: str | None = None
    surah_name_en: str | None = None

    juz_number: int | None = Field(
        default=None,
        ge=1,
        le=30,
    )

    page_number: int | None = Field(
        default=None,
        ge=1,
    )

    line_start: int | None = Field(
        default=None,
        ge=1,
    )

    line_end: int | None = Field(
        default=None,
        ge=1,
    )

    @property
    def reference(self) -> str:
        return (
            f"{self.surah_number}:"
            f"{self.ayah_number}"
        )