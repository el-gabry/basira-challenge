from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from basira.models.hadith import (
    HadithGradeAssessment,
    HadithRecord,
    HadithReference,
    HadithTextVariant,
)
from basira.sources.hadith.grade_normalization import (
    categorize_hadith_grade,
)
from basira.sources.hadith.hadeethenc.models import (
    HadeethEncArabicRow,
    HadeethEncEnglishRow,
    HadeethEncRelease,
)
from basira.sources.hadith.hadeethenc.verification import (
    detect_cross_version_grade_conflict,
)


class HadeethEncParseError(
    ValueError
):
    pass


class HadeethEncOfficialParser:
    """
    Parse official HadeethEnc releases into Basira's
    canonical Hadith model.

    Arabic is primary evidence.
    English is an optional translated representation
    and never creates a second Hadith identity.
    """

    def __init__(
        self,
        *,
        source_id: str = (
            "hadeethenc-official"
        ),
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
        arabic_payload: Mapping[
            str,
            Any,
        ],
        *,
        arabic_release: HadeethEncRelease,
        english_payload: (
            Mapping[str, Any] | None
        ) = None,
        english_release: (
            HadeethEncRelease | None
        ) = None,
    ) -> HadithRecord:
        try:
            arabic = (
                HadeethEncArabicRow
                .model_validate(
                    arabic_payload
                )
            )
        except Exception as exc:
            raise HadeethEncParseError(
                "Invalid official HadeethEnc "
                "Arabic row."
            ) from exc

        english: (
            HadeethEncEnglishRow | None
        ) = None

        if english_payload is not None:
            if english_release is None:
                raise HadeethEncParseError(
                    "english_release is required "
                    "when English data is supplied."
                )

            try:
                english = (
                    HadeethEncEnglishRow
                    .model_validate(
                        english_payload
                    )
                )
            except Exception as exc:
                raise HadeethEncParseError(
                    "Invalid official HadeethEnc "
                    "English row."
                ) from exc

            if english.id != arabic.id:
                raise HadeethEncParseError(
                    "Arabic and English "
                    "HadeethEnc IDs differ."
                )

            if (
                english.lang
                .strip()
                .casefold()
                != "en"
            ):
                raise HadeethEncParseError(
                    "Expected English HadeethEnc "
                    "language code."
                )

        reference = HadithReference(
            source_id=self.source_id,
            collection_id="hadeethenc",
            hadith_number=str(
                arabic.id
            ),
            source_reference=(
                f"hadeethenc:{arabic.id}"
            ),
            source_url=arabic.link,
        )

        text_variant = HadithTextVariant(
            source_id=self.source_id,
            arabic_text=(
                arabic.hadith_text
            ),
            english_translation=(
                english.hadith_text
                if english is not None
                else None
            ),
            translation_source_id=(
                self.source_id
                if english is not None
                else None
            ),
        )

        assessments: tuple[
            HadithGradeAssessment,
            ...,
        ]

        if arabic.grade is None:
            assessments = ()
        else:
            assessments = (
                HadithGradeAssessment(
                    source_id=(
                        self.source_id
                    ),
                    grader_name=(
                        "HadeethEnc "
                        "editorial board"
                    ),
                    grade_text=(
                        arabic.grade
                    ),
                    category=(
                        categorize_hadith_grade(
                            arabic.grade
                        )
                    ),
                    source_reference=(
                        f"hadeethenc:"
                        f"{arabic.id}"
                    ),
                    source_url=(
                        arabic.link
                    ),
                    notes=(
                        "Official HadeethEnc "
                        f"Arabic release "
                        f"{arabic_release.version}; "
                        f"takhrij={arabic.takhrij!r}"
                    ),
                ),
            )

        release_notes = [
            (
                "official_ar_release="
                f"{arabic_release.version}"
            )
        ]

        if english_release is not None:
            release_notes.append(
                "official_en_release="
                f"{english_release.version}"
            )

        if (
            english is not None
            and english_release is not None
        ):
            conflict = (
                detect_cross_version_grade_conflict(
                    arabic,
                    english,
                    arabic_release=arabic_release,
                    english_release=english_release,
                )
            )

            if conflict is not None:
                conflict_group = (
                    f"hadeethenc:{arabic.id}:"
                    "grade:cross-version"
                )

                primary_assessment = (
                    assessments[0]
                    .model_copy(
                        update={
                            "conflict_group": (
                                conflict_group
                            ),
                            "conflict_type": (
                                conflict
                                .conflict_type
                                .value
                            ),
                        }
                    )
                )

                secondary_assessment = (
                    HadithGradeAssessment(
                        source_id=(
                            self.source_id
                        ),
                        grader_name=(
                            "HadeethEnc "
                            "editorial board"
                        ),
                        grade_text=(
                            conflict
                            .english_embedded_arabic_value
                        ),
                        category=(
                            categorize_hadith_grade(
                                conflict
                                .english_embedded_arabic_value
                            )
                        ),
                        source_reference=(
                            f"hadeethenc:"
                            f"{arabic.id}:"
                            "official-en:"
                            f"{conflict.english_release_version}:"
                            "grade_ar"
                        ),
                        source_url=(
                            english.link
                        ),
                        notes=(
                            "Arabic grade embedded "
                            "in official HadeethEnc "
                            "English release "
                            f"{conflict.english_release_version}"
                        ),
                        conflict_group=(
                            conflict_group
                        ),
                        conflict_type=(
                            conflict
                            .conflict_type
                            .value
                        ),
                    )
                )

                assessments = (
                    primary_assessment,
                    secondary_assessment,
                )

                release_notes.append(
                    f"{conflict.conflict_type.value}: "
                    f"official_ar["
                    f"{conflict.arabic_release_version}"
                    f"]={conflict.arabic_value!r}; "
                    f"official_en["
                    f"{conflict.english_release_version}"
                    f"].grade_ar="
                    f"{conflict.english_embedded_arabic_value!r}"
                )

        return HadithRecord(
            record_id=(
                f"{self.source_id}:"
                f"{arabic.id}"
            ),
            primary_reference=reference,
            text_variants=(
                text_variant,
            ),
            grade_assessments=(
                assessments
            ),
            notes="; ".join(
                release_notes
            ),
        )
