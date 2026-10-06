from __future__ import annotations

from enum import StrEnum

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class HadithGradeCategory(StrEnum):
    """
    Broad normalized category for a hadith grading.

    The original grading wording must always be
    preserved separately in grade_text.

    This category is for filtering and retrieval,
    not for replacing the scholar's exact wording.
    """

    SAHIH = "sahih"
    HASAN = "hasan"
    DAIF = "daif"
    MAWDU = "mawdu"
    UNKNOWN = "unknown"
    OTHER = "other"


class HadithReference(BaseModel):
    """
    A source-specific reference to a hadith.

    Hadith numbering may vary across collections,
    editions, websites, and publishers. Basira
    therefore keeps the source and collection
    provenance with every reference.
    """

    source_id: str = Field(min_length=1)

    collection_id: str = Field(min_length=1)

    hadith_number: str = Field(min_length=1)

    collection_name: str | None = None

    book_number: str | None = None
    in_book_number: str | None = None
    book_name: str | None = None

    is_muallaq: bool | None = None

    chapter_number: str | None = None
    chapter_name: str | None = None

    edition: str | None = None

    source_reference: str | None = None

    source_url: HttpUrl | None = None

    @field_validator(
        "source_id",
        "collection_id",
        "hadith_number",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "Field must not be blank."
            )

        return normalized

    @field_validator(
        "collection_name",
        "book_number",
        "in_book_number",
        "book_name",
        "chapter_number",
        "chapter_name",
        "edition",
        "source_reference",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(value.split())

        return normalized or None

    @property
    def key(self) -> tuple[str, str, str]:
        """
        Source-specific stable reference key.
        """

        return (
            self.source_id,
            self.collection_id,
            self.hadith_number,
        )


class HadithTextVariant(BaseModel):
    """
    One attributed textual representation of a hadith.

    Basira does not assume that all sources expose
    identical wording, punctuation, isnad layout, or
    translation.

    Original text must remain untouched. Normalized
    retrieval forms belong in the retrieval layer.
    """

    source_id: str = Field(min_length=1)

    arabic_text: str = Field(min_length=1)

    matn_text: str | None = None
    isnad_text: str | None = None
    narrator_text: str | None = None

    english_translation: str | None = None
    translation_source_id: str | None = None

    notes: str | None = None

    @field_validator("source_id")
    @classmethod
    def normalize_source_id(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "source_id must not be blank."
            )

        return normalized

    @field_validator("arabic_text")
    @classmethod
    def validate_arabic_text(
        cls,
        value: str,
    ) -> str:
        if not value.strip():
            raise ValueError(
                "arabic_text must not be blank."
            )

        # Preserve source text exactly as received.
        return value

    @field_validator(
        "matn_text",
        "isnad_text",
        "narrator_text",
        "translation_source_id",
        "notes",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(value.split())

        return normalized or None

    @field_validator("english_translation")
    @classmethod
    def preserve_english_translation(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not value.strip():
            raise ValueError(
                "english_translation must not be blank."
            )

        # Preserve attributed source translation exactly.
        return value

    @model_validator(mode="after")
    def validate_translation_provenance(
        self,
    ) -> HadithTextVariant:
        """
        A translation must have explicit provenance.

        Basira must never surface an unattributed
        translation as if it were part of the
        original Arabic source.
        """

        if (
            self.english_translation is not None
            and self.translation_source_id is None
        ):
            raise ValueError(
                "translation_source_id is required "
                "when english_translation is present."
            )

        if (
            self.translation_source_id is not None
            and self.english_translation is None
        ):
            raise ValueError(
                "english_translation is required "
                "when translation_source_id is present."
            )

        return self


class HadithGradeAssessment(BaseModel):
    """
    An attributed scholarly grading assessment.

    A grade is evidence attributed to a grader and
    source. It is not stored as an absolute property
    of HadithRecord.
    """

    source_id: str = Field(min_length=1)

    grader_name: str = Field(min_length=1)

    grade_text: str = Field(min_length=1)

    category: HadithGradeCategory = (
        HadithGradeCategory.UNKNOWN
    )

    grader_id: str | None = None

    source_reference: str | None = None

    source_url: HttpUrl | None = None

    notes: str | None = None

    conflict_group: str | None = None

    conflict_type: str | None = None

    @field_validator(
        "source_id",
        "grader_name",
        "grade_text",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "Field must not be blank."
            )

        return normalized

    @field_validator(
        "grader_id",
        "source_reference",
        "notes",
        "conflict_group",
        "conflict_type",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(value.split())

        return normalized or None


class HadithRecord(BaseModel):
    """
    Basira's internal representation of a hadith
    identity candidate.

    Important:
    A HadithRecord does not mean Basira has proven
    that every textual variant is identical.

    Cross-source matching and variant verification
    belong to the Hadith verification layer.
    """

    record_id: str = Field(min_length=1)

    primary_reference: HadithReference

    alternate_references: tuple[
        HadithReference,
        ...,
    ] = ()

    text_variants: tuple[
        HadithTextVariant,
        ...,
    ] = Field(min_length=1)

    grade_assessments: tuple[
        HadithGradeAssessment,
        ...,
    ] = ()

    companion_narrator: str | None = None

    notes: str | None = None

    @field_validator("record_id")
    @classmethod
    def normalize_record_id(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "record_id must not be blank."
            )

        return normalized

    @field_validator(
        "companion_narrator",
        "notes",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(value.split())

        return normalized or None

    @model_validator(mode="after")
    def validate_reference_uniqueness(
        self,
    ) -> HadithRecord:
        references = (
            self.primary_reference,
            *self.alternate_references,
        )

        keys = [
            reference.key
            for reference in references
        ]

        if len(keys) != len(set(keys)):
            raise ValueError(
                "Hadith references must be unique "
                "within a HadithRecord."
            )

        return self

    @property
    def references(
        self,
    ) -> tuple[HadithReference, ...]:
        return (
            self.primary_reference,
            *self.alternate_references,
        )

    @property
    def has_grading(
        self,
    ) -> bool:
        return bool(
            self.grade_assessments
        )

    @property
    def source_ids(
        self,
    ) -> frozenset[str]:
        """
        Return every source contributing references,
        texts, translations, or grading assessments.
        """

        result: set[str] = set()

        for reference in self.references:
            result.add(
                reference.source_id
            )

        for variant in self.text_variants:
            result.add(
                variant.source_id
            )

            if (
                variant.translation_source_id
                is not None
            ):
                result.add(
                    variant.translation_source_id
                )

        for assessment in self.grade_assessments:
            result.add(
                assessment.source_id
            )

        return frozenset(result)
