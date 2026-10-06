from __future__ import annotations

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class QuranLabGrade(BaseModel):
    """
    One grading attribution exactly as exposed
    by the QuranLab dataset.
    """

    grader: str = Field(min_length=1)
    grade: str = Field(min_length=1)

    @field_validator("grader")
    @classmethod
    def normalize_grader(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "grader must not be blank."
            )

        return normalized

    @field_validator("grade")
    @classmethod
    def validate_grade(
        cls,
        value: str,
    ) -> str:
        if not value.strip():
            raise ValueError(
                "grade must not be blank."
            )

        # Preserve grading wording from source.
        return value


class QuranLabHadithRow(BaseModel):
    """
    Source-specific representation of one QuranLab
    collection/language row.

    This model deliberately retains QuranLab metadata
    that does not belong in Basira's canonical
    HadithRecord.
    """

    hadith_key: str = Field(min_length=1)

    urn: int

    seq: int = Field(ge=1)

    collection: str = Field(min_length=1)

    language: str = Field(min_length=1)

    hadith_number: str = Field(min_length=1)

    number_sort: int | None = None

    book_number: int | str | None = None

    in_book_number: int | str | None = None

    sunnah_url: HttpUrl | None = None

    text: str = Field(min_length=1)

    grades: tuple[QuranLabGrade, ...] = ()

    n_grades: int = Field(ge=0)

    grade_summary: str | None = None

    is_muallaq: bool | None = None

    @field_validator(
        "hadith_key",
        "collection",
        "language",
        "hadith_number",
    )
    @classmethod
    def normalize_identifier(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "Identifier must not be blank."
            )

        return normalized

    @field_validator("text")
    @classmethod
    def preserve_source_text(
        cls,
        value: str,
    ) -> str:
        if not value.strip():
            raise ValueError(
                "text must not be blank."
            )

        # Exact source text is evidence.
        return value

    @model_validator(mode="after")
    def validate_grade_count(
        self,
    ) -> QuranLabHadithRow:
        if self.n_grades != len(self.grades):
            raise ValueError(
                "n_grades does not match grades length."
            )

        return self


class QuranLabSingleGradeRow(BaseModel):
    """
    QuranLab row shape used by Musnad Ahmad and
    Sunan al-Darimi.

    The current pinned snapshot exposes grade,
    grader, and grade_source as nullable scalar
    fields rather than the grades[] structure used
    by the main collection configs.
    """

    hadith_key: str = Field(min_length=1)

    urn: int

    seq: int = Field(ge=1)

    collection: str = Field(min_length=1)

    hadith_number: str = Field(min_length=1)

    number_sort: int | None = None

    language: str = Field(min_length=1)

    text: str = Field(min_length=1)

    grade: str | None = None
    grader: str | None = None
    grade_source: str | None = None

    is_muallaq: bool | None = None

    @field_validator(
        "hadith_key",
        "collection",
        "hadith_number",
        "language",
    )
    @classmethod
    def normalize_identifier(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(
                "Identifier must not be blank."
            )

        return normalized

    @field_validator("text")
    @classmethod
    def preserve_source_text(
        cls,
        value: str,
    ) -> str:
        if not value.strip():
            raise ValueError(
                "text must not be blank."
            )

        return value

    @field_validator(
        "grade",
        "grader",
        "grade_source",
    )
    @classmethod
    def normalize_optional_metadata(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(
            value.split()
        )

        return normalized or None

    @model_validator(mode="after")
    def validate_grade_provenance(
        self,
    ) -> QuranLabSingleGradeRow:
        has_grade = self.grade is not None

        provenance_present = (
            self.grader is not None
            or self.grade_source is not None
        )

        if has_grade and (
            self.grader is None
            or self.grade_source is None
        ):
            raise ValueError(
                "grader and grade_source are required "
                "when grade is present."
            )

        if (
            not has_grade
            and provenance_present
        ):
            raise ValueError(
                "grader/grade_source cannot be present "
                "without grade."
            )

        return self


class QuranLabHadeethEncRow(BaseModel):
    """
    QuranLab representation of one HadeethEnc
    language row.

    Arabic is treated as the primary representation.
    Other languages are joined through hadith_key.
    """

    hadith_key: str = Field(min_length=1)

    hadeethenc_id: int = Field(gt=0)

    collection: str = Field(min_length=1)

    language: str = Field(min_length=1)

    title: str

    text: str = Field(min_length=1)

    intro: str

    grade: str = Field(min_length=1)

    grader: str = Field(min_length=1)

    grade_source: str = Field(min_length=1)

    attribution_text: str

    explanation: str

    @field_validator(
        "hadith_key",
        "collection",
        "language",
        "grader",
        "grade_source",
    )
    @classmethod
    def normalize_identifier(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(
            value.split()
        )

        if not normalized:
            raise ValueError(
                "Field must not be blank."
            )

        return normalized

    @field_validator(
        "text",
        "grade",
    )
    @classmethod
    def preserve_evidence_text(
        cls,
        value: str,
    ) -> str:
        if not value.strip():
            raise ValueError(
                "Evidence text must not be blank."
            )

        return value
