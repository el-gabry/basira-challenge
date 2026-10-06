from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from basira.models.hadith import (
    HadithGradeAssessment,
    HadithGradeCategory,
    HadithRecord,
    HadithReference,
    HadithTextVariant,
)
from basira.sources.hadith.quranlab.models import (
    QuranLabHadeethEncRow,
    QuranLabHadithRow,
    QuranLabSingleGradeRow,
)


class QuranLabHadithParseError(ValueError):
    """Raised when a QuranLab row cannot be safely parsed."""


class QuranLabHadithParser:
    """
    Convert validated QuranLab Arabic rows into
    Basira HadithRecord objects.

    QuranLab remains the provenance source of the
    imported candidate. Parsing does not make a
    hadith or grading independently verified.
    """

    def __init__(
        self,
        *,
        source_id: str = "quranlab-hadith",
    ) -> None:
        normalized_source_id = " ".join(
            source_id.split()
        )

        if not normalized_source_id:
            raise ValueError(
                "source_id must not be blank."
            )

        self.source_id = normalized_source_id

    def parse(
        self,
        payload: Mapping[str, Any],
    ) -> HadithRecord:
        try:
            row = QuranLabHadithRow.model_validate(
                payload
            )
        except Exception as exc:
            raise QuranLabHadithParseError(
                "Invalid QuranLab hadith row."
            ) from exc

        if row.language.lower() != "ar":
            raise QuranLabHadithParseError(
                "QuranLabHadithParser accepts "
                "Arabic rows only."
            )

        reference = HadithReference(
            source_id=self.source_id,
            collection_id=row.collection,
            hadith_number=row.hadith_number,
            book_number=(
                str(row.book_number)
                if row.book_number is not None
                else None
            ),
            in_book_number=(
                str(row.in_book_number)
                if row.in_book_number is not None
                else None
            ),
            is_muallaq=row.is_muallaq,
            source_reference=row.hadith_key,
        )

        variant = HadithTextVariant(
            source_id=self.source_id,
            arabic_text=row.text,
        )

        assessments = tuple(
            HadithGradeAssessment(
                source_id=self.source_id,
                grader_name=grade.grader,
                grade_text=grade.grade,
                category=_grade_category(
                    grade.grade
                ),
                source_reference=row.hadith_key,
            )
            for grade in row.grades
        )

        return HadithRecord(
            record_id=(
                f"{self.source_id}:"
                f"{row.hadith_key}"
            ),
            primary_reference=reference,
            text_variants=(variant,),
            grade_assessments=assessments,
        )


def _grade_category(
    grade_text: str,
) -> HadithGradeCategory:
    """
    Conservatively normalize explicit grading labels.

    Raw grade_text always remains authoritative.
    Chain-only judgments and complex scholarly
    statements intentionally remain UNKNOWN.
    """

    normalized = (
        grade_text
        .strip()
        .casefold()
        .replace("’", "'")
        .replace("‘", "'")
    )

    sahih_prefixes = (
        "sahih",
        "ṣaḥīḥ",
        "authentic",
        "صحيح",
        "صحيحة",
        "صحيحان",
    )

    hasan_prefixes = (
        "hasan",
        "ḥasan",
        "good hadith",
        "حسن",
    )

    daif_prefixes = (
        "daif",
        "da'if",
        "ḍaʿīf",
        "weak hadith",
        "ضعيف",
    )

    mawdu_prefixes = (
        "mawdu",
        "mawdoo",
        "fabricated",
        "موضوع",
    )

    if normalized.startswith(
        sahih_prefixes
    ):
        return HadithGradeCategory.SAHIH

    if normalized.startswith(
        hasan_prefixes
    ):
        return HadithGradeCategory.HASAN

    if normalized.startswith(
        daif_prefixes
    ):
        return HadithGradeCategory.DAIF

    if normalized.startswith(
        mawdu_prefixes
    ):
        return HadithGradeCategory.MAWDU

    return HadithGradeCategory.UNKNOWN


class QuranLabSingleGradeParser:
    """
    Parser for the Ahmad and Darimi QuranLab schemas.

    The pinned QuranLab snapshot currently contains
    no scalar grading judgments for these configs.
    The parser nevertheless preserves a future
    attributed scalar grade if the source provides
    complete provenance.
    """

    def __init__(
        self,
        *,
        source_id: str = "quranlab-hadith",
    ) -> None:
        normalized = " ".join(
            source_id.split()
        )

        if not normalized:
            raise ValueError(
                "source_id must not be blank."
            )

        self.source_id = normalized

    def parse(
        self,
        payload: Mapping[str, Any],
    ) -> HadithRecord:
        try:
            row = (
                QuranLabSingleGradeRow
                .model_validate(payload)
            )
        except Exception as exc:
            raise QuranLabHadithParseError(
                "Invalid QuranLab single-grade row."
            ) from exc

        if row.language.lower() != "ar":
            raise QuranLabHadithParseError(
                "QuranLabSingleGradeParser accepts "
                "Arabic rows only."
            )

        reference = HadithReference(
            source_id=self.source_id,
            collection_id=row.collection,
            hadith_number=row.hadith_number,
            is_muallaq=row.is_muallaq,
            source_reference=row.hadith_key,
        )

        variant = HadithTextVariant(
            source_id=self.source_id,
            arabic_text=row.text,
        )

        assessments: tuple[
            HadithGradeAssessment,
            ...,
        ]

        if row.grade is None:
            assessments = ()
        else:
            assert row.grader is not None
            assert row.grade_source is not None

            assessments = (
                HadithGradeAssessment(
                    source_id=self.source_id,
                    grader_name=row.grader,
                    grade_text=row.grade,
                    category=_grade_category(
                        row.grade
                    ),
                    source_reference=(
                        row.hadith_key
                    ),
                    notes=(
                        "Grade source: "
                        f"{row.grade_source}"
                    ),
                ),
            )

        return HadithRecord(
            record_id=(
                f"{self.source_id}:"
                f"{row.hadith_key}"
            ),
            primary_reference=reference,
            text_variants=(variant,),
            grade_assessments=assessments,
        )


class QuranLabHadeethEncParser:
    """
    Build a Basira HadithRecord from the HadeethEnc
    Arabic row and an optional matching English row.

    Arabic is primary. English is attached only when
    it resolves to exactly the same HadeethEnc
    identity.
    """

    def __init__(
        self,
        *,
        source_id: str = "quranlab-hadith",
    ) -> None:
        normalized = " ".join(
            source_id.split()
        )

        if not normalized:
            raise ValueError(
                "source_id must not be blank."
            )

        self.source_id = normalized

    def parse(
        self,
        arabic_payload: Mapping[str, Any],
        *,
        english_payload: (
            Mapping[str, Any] | None
        ) = None,
    ) -> HadithRecord:
        try:
            arabic = (
                QuranLabHadeethEncRow
                .model_validate(arabic_payload)
            )
        except Exception as exc:
            raise QuranLabHadithParseError(
                "Invalid HadeethEnc Arabic row."
            ) from exc

        if arabic.collection != "hadeethenc":
            raise QuranLabHadithParseError(
                "Expected HadeethEnc collection."
            )

        if arabic.language.lower() != "ar":
            raise QuranLabHadithParseError(
                "Primary HadeethEnc row must be Arabic."
            )

        english: (
            QuranLabHadeethEncRow | None
        ) = None

        grade_translation_conflict = False

        if english_payload is not None:
            try:
                english = (
                    QuranLabHadeethEncRow
                    .model_validate(
                        english_payload
                    )
                )
            except Exception as exc:
                raise QuranLabHadithParseError(
                    "Invalid HadeethEnc English row."
                ) from exc

            if english.language.lower() != "en":
                raise QuranLabHadithParseError(
                    "Paired HadeethEnc row must "
                    "be English."
                )

            if (
                english.hadith_key
                != arabic.hadith_key
            ):
                raise QuranLabHadithParseError(
                    "HadeethEnc hadith_key mismatch."
                )

            if (
                english.hadeethenc_id
                != arabic.hadeethenc_id
            ):
                raise QuranLabHadithParseError(
                    "HadeethEnc identity mismatch."
                )

            ar_category = _grade_category(
                arabic.grade
            )
            en_category = _grade_category(
                english.grade
            )

            grade_translation_conflict = (
                ar_category
                is not HadithGradeCategory.UNKNOWN
                and en_category
                is not HadithGradeCategory.UNKNOWN
                and ar_category is not en_category
            )

        reference = HadithReference(
            source_id=self.source_id,
            collection_id="hadeethenc",
            hadith_number=str(
                arabic.hadeethenc_id
            ),
            source_reference=(
                arabic.hadith_key
            ),
        )

        variant = HadithTextVariant(
            source_id=self.source_id,
            arabic_text=arabic.text,
            english_translation=(
                english.text
                if english is not None
                else None
            ),
            translation_source_id=(
                self.source_id
                if english is not None
                else None
            ),
        )

        assessment = HadithGradeAssessment(
            source_id=self.source_id,
            grader_name=arabic.grader,
            grade_text=arabic.grade,
            category=_grade_category(
                arabic.grade
            ),
            source_reference=(
                arabic.hadith_key
            ),
            notes=(
                "Grade source: "
                f"{arabic.grade_source}. "
                "Attribution: "
                f"{arabic.attribution_text}"
            ),
        )

        return HadithRecord(
            record_id=(
                f"{self.source_id}:"
                f"{arabic.hadith_key}"
            ),
            primary_reference=reference,
            text_variants=(variant,),
            grade_assessments=(
                assessment,
            ),
            notes=(
                "hadeethenc_translation_grade_conflict: "
                f"arabic={arabic.grade!r}; "
                f"english={english.grade!r}"
                if (
                    grade_translation_conflict
                    and english is not None
                )
                else None
            ),
        )


class QuranLabSnapshotParser:
    """
    Dispatch QuranLab rows to the correct parser for
    the pinned local Hadith snapshot.
    """

    STANDARD_CONFIGS = frozenset(
        {
            "abudawud-ar",
            "bukhari-ar",
            "dehlawi-ar",
            "ibnmajah-ar",
            "malik-ar",
            "muslim-ar",
            "nasai-ar",
            "nawawi-ar",
            "qudsi-ar",
            "tirmidhi-ar",
        }
    )

    SINGLE_GRADE_CONFIGS = frozenset(
        {
            "ahmad-ar",
            "darimi-ar",
        }
    )

    def __init__(
        self,
        *,
        source_id: str = "quranlab-hadith",
    ) -> None:
        self.standard = QuranLabHadithParser(
            source_id=source_id
        )

        self.single_grade = (
            QuranLabSingleGradeParser(
                source_id=source_id
            )
        )

        self.hadeethenc = (
            QuranLabHadeethEncParser(
                source_id=source_id
            )
        )

    def parse(
        self,
        *,
        config: str,
        payload: Mapping[str, Any],
        paired_payload: (
            Mapping[str, Any] | None
        ) = None,
    ) -> HadithRecord:
        if config in self.STANDARD_CONFIGS:
            if paired_payload is not None:
                raise QuranLabHadithParseError(
                    "paired_payload is not supported "
                    "for standard collection configs."
                )

            return self.standard.parse(
                payload
            )

        if config in self.SINGLE_GRADE_CONFIGS:
            if paired_payload is not None:
                raise QuranLabHadithParseError(
                    "paired_payload is not supported "
                    "for Ahmad/Darimi configs."
                )

            return self.single_grade.parse(
                payload
            )

        if config == "hadeethenc-ar":
            return self.hadeethenc.parse(
                payload,
                english_payload=paired_payload,
            )

        if config == "hadeethenc-en":
            raise QuranLabHadithParseError(
                "HadeethEnc English must be paired "
                "with its Arabic primary record."
            )

        raise QuranLabHadithParseError(
            f"Unsupported QuranLab config: {config}"
        )
