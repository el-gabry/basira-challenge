from __future__ import annotations

from enum import StrEnum

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class HadeethEncLanguage(StrEnum):
    ARABIC = "ar"
    ENGLISH = "en"


class HadeethEncRelease(BaseModel):
    language: HadeethEncLanguage

    version: str = Field(
        min_length=1
    )

    last_updated: str = Field(
        min_length=1
    )

    source_url: str = Field(
        min_length=1
    )

    update_check_url: str = Field(
        min_length=1
    )


class HadeethEncArabicRow(BaseModel):
    """
    One row from the official Arabic HadeethEnc XLSX.

    Evidence-bearing text is preserved exactly as
    provided by the source.
    """

    id: int = Field(gt=0)

    title: str

    hadith_text: str = Field(
        min_length=1
    )

    explanation: str = ""

    word_meanings: str = ""

    benefits: str = ""

    grade: str | None = None

    takhrij: str | None = None

    link: str = Field(
        min_length=1
    )

    @field_validator("hadith_text")
    @classmethod
    def preserve_hadith_text(
        cls,
        value: str,
    ) -> str:
        if not value.strip():
            raise ValueError(
                "hadith_text must not be blank."
            )

        return value

    @field_validator(
        "grade",
        "takhrij",
    )
    @classmethod
    def optional_evidence(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not value.strip():
            return None

        return value


class HadeethEncEnglishRow(BaseModel):
    """
    One row from the official English HadeethEnc
    release.

    This release contains both embedded Arabic fields
    and their English representations.
    """

    id: int = Field(gt=0)

    title_ar: str = ""

    title: str = ""

    hadith_text_ar: str = Field(
        min_length=1
    )

    hadith_text: str = Field(
        min_length=1
    )

    explanation_ar: str = ""

    explanation: str = ""

    benefits_ar: str = ""

    benefits: str = ""

    grade_ar: str | None = None

    takhrij_ar: str | None = None

    grade: str | None = None

    takhrij: str | None = None

    lang: str = Field(
        min_length=1
    )

    link: str = Field(
        min_length=1
    )

    @field_validator(
        "hadith_text_ar",
        "hadith_text",
    )
    @classmethod
    def preserve_text(
        cls,
        value: str,
    ) -> str:
        if not value.strip():
            raise ValueError(
                "Hadith text must not be blank."
            )

        return value

    @field_validator(
        "grade_ar",
        "takhrij_ar",
        "grade",
        "takhrij",
    )
    @classmethod
    def optional_evidence(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not value.strip():
            return None

        return value
