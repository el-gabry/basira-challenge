from __future__ import annotations

import unicodedata
from enum import StrEnum

from pydantic import BaseModel, Field

from basira.verification.quran_orthography_rules import (
    RULES_BY_ID,
    QuranOrthographyRuleId,
)


class QuranScriptType(StrEnum):
    UTHMANI = "uthmani"
    IMLAEI = "imlaei"
    UNKNOWN = "unknown"


class QuranOrthographyRelation(StrEnum):
    EXACT_MATCH = "exact_match"
    DIACRITIC_VARIANT = "diacritic_variant"
    TOKEN_BOUNDARY_VARIANT = "token_boundary_variant"
    UTHMANI_RASM_VARIANT = "uthmani_rasm_variant"
    BASMALA_LAYOUT_VARIANT = "basmala_layout_variant"
    UNRESOLVED = "unresolved"


class QuranSourceProfile(BaseModel):
    """
    Describes the Quran text representation supplied
    by a source.

    Basira keeps source representation explicit so
    Uthmani and Imla'i text are not treated as if
    their Unicode spelling must always be identical.
    """

    source_id: str = Field(min_length=1)

    script: QuranScriptType

    narration: str = "hafs"

    source_name: str | None = None
    source_url: str | None = None


class QuranOrthographyAssessment(BaseModel):
    """
    Result of the Quran orthography layer.

    is_textual_error=False
        The difference is explained safely by an
        accepted representation / orthography rule.

    is_textual_error=None
        This layer cannot explain the difference.

        This does NOT mean that the Quran text is
        wrong. It must be passed to the lexical /
        source verification layer.
    """

    relation: QuranOrthographyRelation

    rule_id: QuranOrthographyRuleId | None = None

    rule_name_ar: str | None = None
    rule_name_en: str | None = None

    left_text: str
    right_text: str

    normalized_left: str
    normalized_right: str

    left_script: QuranScriptType
    right_script: QuranScriptType

    is_textual_error: bool | None = None

    explanation_ar: str | None = None

    evidence_source_ids: tuple[str, ...] = ()
    rule_evidence_ids: tuple[str, ...] = ()
    rule_evidence_urls: tuple[str, ...] = ()


class QuranOrthographyComparator:
    """
    Compare Quran writing representations.

    This layer may explain differences caused by:

    - diacritics
    - Quranic presentation marks
    - Unicode Quran encodings
    - Uthmani rasm rules
    - token/word boundaries
    - Basmala layout conventions

    Safety rule
    -----------
    An unknown difference is NEVER automatically
    classified as a Quran textual error.

    Unknown differences return:

        relation = UNRESOLVED
        is_textual_error = None
    """

    BASMALA = "بسم الله الرحمن الرحيم"

    def compare(
        self,
        *,
        left_text: str,
        right_text: str,
        left_profile: QuranSourceProfile,
        right_profile: QuranSourceProfile,
        surah_number: int | None = None,
        ayah_number: int | None = None,
    ) -> QuranOrthographyAssessment:
        # =====================================================
        # 1. Exact source-level equality
        # =====================================================

        if left_text == right_text:
            normalized = self._normalize_letters(
                left_text
            )

            return self._assessment(
                relation=(
                    QuranOrthographyRelation.EXACT_MATCH
                ),
                left_text=left_text,
                right_text=right_text,
                normalized_left=normalized,
                normalized_right=normalized,
                left_profile=left_profile,
                right_profile=right_profile,
                is_textual_error=False,
                explanation_ar=(
                    "النصان متطابقان كما وردا "
                    "في المصدرين."
                ),
            )

        normalized_left = self._normalize_letters(
            left_text
        )

        normalized_right = self._normalize_letters(
            right_text
        )

        # =====================================================
        # 2. Same lexical letters after controlled
        #    representation normalization
        # =====================================================

        if normalized_left == normalized_right:
            return self._assessment(
                relation=(
                    QuranOrthographyRelation
                    .DIACRITIC_VARIANT
                ),
                rule_id=(
                    QuranOrthographyRuleId
                    .DIACRITICS_ONLY
                ),
                left_text=left_text,
                right_text=right_text,
                normalized_left=normalized_left,
                normalized_right=normalized_right,
                left_profile=left_profile,
                right_profile=right_profile,
                is_textual_error=False,
                explanation_ar=(
                    "الحروف الأساسية متطابقة بعد "
                    "التطبيع المحافظ، والاختلاف "
                    "ناتج عن الضبط أو علامات الرسم "
                    "أو طريقة تمثيلها رقمياً. "
                    "لا يمثل ذلك تغييراً في ألفاظ "
                    "الآية."
                ),
            )

        # =====================================================
        # 3. Basmala structural representation
        # =====================================================

        if self._is_basmala_layout_variant(
            normalized_left=normalized_left,
            normalized_right=normalized_right,
            surah_number=surah_number,
            ayah_number=ayah_number,
        ):
            return self._assessment(
                relation=(
                    QuranOrthographyRelation
                    .BASMALA_LAYOUT_VARIANT
                ),
                rule_id=(
                    QuranOrthographyRuleId
                    .BASMALA_PREFIX_LAYOUT
                ),
                left_text=left_text,
                right_text=right_text,
                normalized_left=normalized_left,
                normalized_right=normalized_right,
                left_profile=left_profile,
                right_profile=right_profile,
                is_textual_error=False,
                explanation_ar=(
                    "الاختلاف ناتج عن طريقة تمثيل "
                    "البسملة في بداية السورة داخل "
                    "بيانات المصدر، وليس دليلاً "
                    "على اختلاف ألفاظ الآية."
                ),
            )

        # =====================================================
        # 4. Source-backed Uthmani rasm rules
        # =====================================================

        known_rasm_rule = (
            self._detect_known_rasm_rule(
                left=normalized_left,
                right=normalized_right,
                left_profile=left_profile,
                right_profile=right_profile,
            )
        )

        if known_rasm_rule is not None:
            return self._assessment_from_rule(
                rule_id=known_rasm_rule,
                relation=(
                    QuranOrthographyRelation
                    .UTHMANI_RASM_VARIANT
                ),
                left_text=left_text,
                right_text=right_text,
                normalized_left=normalized_left,
                normalized_right=normalized_right,
                left_profile=left_profile,
                right_profile=right_profile,
            )

        # =====================================================
        # 5. Token / word-boundary difference
        # =====================================================

        compact_left = self._compact(
            normalized_left
        )

        compact_right = self._compact(
            normalized_right
        )

        if compact_left == compact_right:
            return self._assessment(
                relation=(
                    QuranOrthographyRelation
                    .TOKEN_BOUNDARY_VARIANT
                ),
                rule_id=(
                    QuranOrthographyRuleId
                    .WORD_BOUNDARY_ONLY
                ),
                left_text=left_text,
                right_text=right_text,
                normalized_left=normalized_left,
                normalized_right=normalized_right,
                left_profile=left_profile,
                right_profile=right_profile,
                is_textual_error=False,
                explanation_ar=(
                    "تسلسل الحروف متطابق بعد "
                    "تجاهل الفصل والوصل بين الكلمات؛ "
                    "لذلك فإن الاختلاف هنا في حدود "
                    "الكلمات أو المسافات وليس تغييراً "
                    "في ألفاظ الآية."
                ),
            )

        # =====================================================
        # 6. Conservative fallback
        # =====================================================

        return self._assessment(
            relation=(
                QuranOrthographyRelation.UNRESOLVED
            ),
            left_text=left_text,
            right_text=right_text,
            normalized_left=normalized_left,
            normalized_right=normalized_right,
            left_profile=left_profile,
            right_profile=right_profile,
            is_textual_error=None,
            explanation_ar=(
                "لا تستطيع طبقة الرسم الحالية "
                "تفسير هذا الاختلاف بقاعدة موثقة. "
                "لا يعني ذلك أن النص خاطئ، وإنما "
                "يجب الانتقال إلى فحص الألفاظ "
                "والمصادر قبل إصدار أي حكم."
            ),
        )

    def _detect_known_rasm_rule(
        self,
        *,
        left: str,
        right: str,
        left_profile: QuranSourceProfile,
        right_profile: QuranSourceProfile,
    ) -> QuranOrthographyRuleId | None:
        """
        Detect only explicitly registered,
        source-backed Uthmani/Imla'i rules.

        No generic letter deletion is allowed.
        """

        scripts = {
            left_profile.script,
            right_profile.script,
        }

        if scripts != {
            QuranScriptType.UTHMANI,
            QuranScriptType.IMLAEI,
        }:
            return None

        if (
            left_profile.script
            == QuranScriptType.UTHMANI
        ):
            uthmani = left
            imlaei = right
        else:
            uthmani = right
            imlaei = left

        if self._is_vocative_ya_variant(
            uthmani=uthmani,
            imlaei=imlaei,
        ):
            return (
                QuranOrthographyRuleId
                .VOCATIVE_YA_ALIF_OMISSION
            )

        if self._is_israil_rasm_variant(
            uthmani=uthmani,
            imlaei=imlaei,
        ):
            return (
                QuranOrthographyRuleId
                .ISRAIL_ALIF_RASM_VARIANT
            )

        return None

    def _is_vocative_ya_variant(
        self,
        *,
        uthmani: str,
        imlaei: str,
    ) -> bool:
        """
        Detect the controlled Uthmani convention
        involving omission of the alif in vocative يا.

        Examples:

            يا أيها -> يأيها
            يا بني  -> يبني
            يا موسى -> يموسى

        Only an explicit independent token "يا" is
        transformed. Arbitrary alifs are never removed.
        """

        imlaei_tokens = imlaei.split()

        if len(imlaei_tokens) < 2:
            return False

        uthmani_compact = self._compact(
            uthmani
        )

        for index, token in enumerate(
            imlaei_tokens[:-1]
        ):
            if token != "يا":
                continue

            following_token = (
                imlaei_tokens[
                    index + 1
                ]
            )

            joined_vocative = (
                "ي"
                + following_token
            )

            candidate_tokens = (
                imlaei_tokens[:index]
                + [joined_vocative]
                + imlaei_tokens[
                    index + 2:
                ]
            )

            candidate = self._compact(
                " ".join(
                    candidate_tokens
                )
            )

            if candidate == uthmani_compact:
                return True

        return False

    def _is_israil_rasm_variant(
        self,
        *,
        uthmani: str,
        imlaei: str,
    ) -> bool:
        """
        Detect only the registered Isra'il
        orthographic/rāsm variant.

        This is lexeme-specific and is deliberately
        NOT implemented as a general alif rule.
        """

        uthmani_tokens = uthmani.split()
        imlaei_tokens = imlaei.split()

        if (
            len(uthmani_tokens)
            != len(imlaei_tokens)
        ):
            return False

        difference_count = 0

        for (
            uthmani_token,
            imlaei_token,
        ) in zip(
            uthmani_tokens,
            imlaei_tokens,
            strict=True,
        ):
            if (
                uthmani_token
                == imlaei_token
            ):
                continue

            if self._is_israil_token_pair(
                uthmani_token=uthmani_token,
                imlaei_token=imlaei_token,
            ):
                difference_count += 1
                continue

            # Another unexplained difference exists
            # in the same span.
            return False

        return difference_count > 0

    @staticmethod
    def _is_israil_token_pair(
        *,
        uthmani_token: str,
        imlaei_token: str,
    ) -> bool:
        """
        Controlled Isra'il comparison forms.

        No broad replacement is performed.
        """

        known_pairs = {
            (
                "اسرءيل",
                "اسرائيل",
            ),
            (
                "اسريءيل",
                "اسرائيل",
            ),
            (
                "اسريءيل",
                "اسرايءيل",
            ),
        }

        return (
            uthmani_token,
            imlaei_token,
        ) in known_pairs

    def _is_basmala_layout_variant(
        self,
        *,
        normalized_left: str,
        normalized_right: str,
        surah_number: int | None,
        ayah_number: int | None,
    ) -> bool:
        """
        Detect structural Basmala placement
        differences.

        Safety constraints:

        - only ayah 1
        - Surah 1 excluded
        - Surah 9 excluded
        - exactly one side has the prefix
        - remaining text must match
        """

        if (
            surah_number is None
            or ayah_number is None
        ):
            return False

        if ayah_number != 1:
            return False

        if surah_number in {
            1,
            9,
        }:
            return False

        left_without = (
            self._remove_basmala_prefix(
                normalized_left
            )
        )

        right_without = (
            self._remove_basmala_prefix(
                normalized_right
            )
        )

        left_had_basmala = (
            left_without
            != normalized_left
        )

        right_had_basmala = (
            right_without
            != normalized_right
        )

        if (
            left_had_basmala
            == right_had_basmala
        ):
            return False

        return (
            self._compact(
                left_without
            )
            == self._compact(
                right_without
            )
        )

    def _remove_basmala_prefix(
        self,
        text: str,
    ) -> str:
        if text == self.BASMALA:
            return ""

        prefix = (
            self.BASMALA
            + " "
        )

        if text.startswith(
            prefix
        ):
            return text[
                len(prefix):
            ].strip()

        return text

    @staticmethod
    def _compact(
        text: str,
    ) -> str:
        """
        Remove whitespace from the comparison
        representation only.

        Source Quran text remains untouched.
        """

        return "".join(
            text.split()
        )

    @staticmethod
    def _normalize_letters(
        text: str,
    ) -> str:
        """
        Produce a conservative Quran comparison
        representation.

        Original source text is NEVER modified.

        Unicode strategy
        ----------------
        Use NFD so canonically equivalent Arabic
        letters are exposed as base + combining mark.

        Examples:

            أ -> ا + HAMZA ABOVE
            إ -> ا + HAMZA BELOW
            ؤ -> و + HAMZA ABOVE
            ئ -> ي + HAMZA ABOVE

        Quranic texts may additionally encode hamza
        using:

            TATWEEL + HAMZA ABOVE

        Therefore combining hamza cannot simply be
        removed and cannot always be converted to a
        standalone hamza.

        Basira handles it according to context.
        """

        normalized = unicodedata.normalize(
            "NFD",
            text,
        )

        characters = list(
            normalized
        )

        output: list[str] = []

        hamza_marks = {
            "\u0654",  # ARABIC HAMZA ABOVE
            "\u0655",  # ARABIC HAMZA BELOW
        }

        ignored_quranic_annotations = {
            "\u06e5",  # ARABIC SMALL WAW
        }

        for index, character in enumerate(
            characters
        ):
            # -----------------------------------------
            # Verse-number digits
            # -----------------------------------------

            if character.isdigit():
                continue

            # -----------------------------------------
            # Quranic annotation marks ignored only
            # for lexical comparison.
            # -----------------------------------------

            if (
                character
                in ignored_quranic_annotations
            ):
                continue

            # -----------------------------------------
            # Combining Hamza
            #
            # MUST run before generic mark removal.
            # -----------------------------------------

            if character in hamza_marks:
                if (
                    QuranOrthographyComparator
                    ._is_quranic_alef_hamza_sequence(
                        characters=characters,
                        hamza_index=index,
                    )
                ):
                    continue

                QuranOrthographyComparator._apply_combining_hamza(
                    output
                )

                continue

            # -----------------------------------------
            # Tatweel
            # -----------------------------------------

            if character == "\u0640":
                continue

            category = (
                unicodedata.category(
                    character
                )
            )

            # -----------------------------------------
            # Remaining combining marks:
            #
            # harakat
            # sukun
            # shadda
            # superscript alef
            # Quranic presentation marks
            # -----------------------------------------

            if category.startswith("M"):
                continue

            # -----------------------------------------
            # Alef Wasla
            # -----------------------------------------

            if character == "ٱ":
                character = "ا"

            # -----------------------------------------
            # Alef Maqsura
            # -----------------------------------------

            if character == "ى":
                character = "ي"

            # -----------------------------------------
            # Whitespace
            # -----------------------------------------

            if character.isspace():
                output.append(" ")
                continue

            # -----------------------------------------
            # Preserve lexical letters only
            # -----------------------------------------

            if (
                unicodedata.category(
                    character
                ).startswith("L")
            ):
                output.append(
                    character
                )

        return " ".join(
            "".join(
                output
            ).split()
        )

    @staticmethod
    def _is_quranic_alef_hamza_sequence(
        *,
        characters: list[str],
        hamza_index: int,
    ) -> bool:
        """
        Detect a Quranic Unicode representation where
        HAMZA ABOVE / BELOW is positioned on tatweel
        before a following Alef.

        Example:

            ـَٔا

        This must NOT be confused with:

            ـَٔت

        because in the second case the hamza remains
        lexically significant.

        Safety requirements:

        1. Tatweel must precede the hamza.
        2. The next lexical base must be Alef.

        Therefore arbitrary hamzas are not deleted.
        """

        previous_index = (
            hamza_index - 1
        )

        while previous_index >= 0:
            character = (
                characters[
                    previous_index
                ]
            )

            if (
                unicodedata.category(
                    character
                ).startswith("M")
            ):
                previous_index -= 1
                continue

            break

        if previous_index < 0:
            return False

        if (
            characters[
                previous_index
            ]
            != "\u0640"
        ):
            return False

        next_index = (
            hamza_index + 1
        )

        while next_index < len(
            characters
        ):
            character = (
                characters[
                    next_index
                ]
            )

            if character.isspace():
                return False

            if character.isdigit():
                next_index += 1
                continue

            if character == "\u0640":
                next_index += 1
                continue

            if character == "\u06e5":
                next_index += 1
                continue

            category = (
                unicodedata.category(
                    character
                )
            )

            if category.startswith("M"):
                next_index += 1
                continue

            return character in {
                "ا",
                "أ",
                "إ",
                "آ",
                "ٱ",
            }

        return False

    @staticmethod
    def _apply_combining_hamza(
        output: list[str],
    ) -> None:
        """
        Preserve lexical hamza while canonicalizing
        its carrier.

        Canonical comparison forms:

            ي + hamza -> ئ
            و + hamza -> ؤ
            ا + hamza -> ا
            other base + hamza -> base + ء

        Alef+Hamza is intentionally collapsed to Alef
        in this comparison representation because the
        existing Basira comparison policy treats:

            أ / إ / آ

        as Alef-level spelling variants.

        Original source text is never changed.
        """

        base_index: int | None = None

        for index in range(
            len(output) - 1,
            -1,
            -1,
        ):
            candidate = (
                output[index]
            )

            if candidate == " ":
                break

            if (
                unicodedata.category(
                    candidate
                ).startswith("L")
            ):
                base_index = index
                break

        if base_index is None:
            output.append("ء")
            return

        base = output[
            base_index
        ]

        if base == "ي":
            output[
                base_index
            ] = "ئ"
            return

        if base == "و":
            output[
                base_index
            ] = "ؤ"
            return

        if base == "ا":
            return

        output.append("ء")

    def _assessment_from_rule(
        self,
        *,
        rule_id: QuranOrthographyRuleId,
        relation: QuranOrthographyRelation,
        left_text: str,
        right_text: str,
        normalized_left: str,
        normalized_right: str,
        left_profile: QuranSourceProfile,
        right_profile: QuranSourceProfile,
    ) -> QuranOrthographyAssessment:
        """
        Build an assessment from a registered,
        source-backed orthography rule.
        """

        rule = RULES_BY_ID.get(
            rule_id
        )

        if rule is None:
            raise ValueError(
                "Detected Quran orthography rule "
                "has no registered evidence: "
                f"{rule_id}"
            )

        return QuranOrthographyAssessment(
            relation=relation,
            rule_id=rule.rule_id,
            rule_name_ar=rule.name_ar,
            rule_name_en=rule.name_en,
            left_text=left_text,
            right_text=right_text,
            normalized_left=normalized_left,
            normalized_right=normalized_right,
            left_script=left_profile.script,
            right_script=right_profile.script,
            is_textual_error=(
                rule.is_textual_change
            ),
            explanation_ar=(
                rule.explanation_ar
            ),
            evidence_source_ids=(
                left_profile.source_id,
                right_profile.source_id,
            ),
            rule_evidence_ids=tuple(
                evidence.evidence_id
                for evidence in rule.evidence
            ),
            rule_evidence_urls=tuple(
                evidence.url
                for evidence in rule.evidence
            ),
        )

    @staticmethod
    def _assessment(
        *,
        relation: QuranOrthographyRelation,
        left_text: str,
        right_text: str,
        normalized_left: str,
        normalized_right: str,
        left_profile: QuranSourceProfile,
        right_profile: QuranSourceProfile,
        is_textual_error: bool | None,
        explanation_ar: str,
        rule_id: QuranOrthographyRuleId | None = None,
    ) -> QuranOrthographyAssessment:
        """
        Build a deterministic comparison assessment.
        """

        return QuranOrthographyAssessment(
            relation=relation,
            rule_id=rule_id,
            left_text=left_text,
            right_text=right_text,
            normalized_left=normalized_left,
            normalized_right=normalized_right,
            left_script=left_profile.script,
            right_script=right_profile.script,
            is_textual_error=is_textual_error,
            explanation_ar=explanation_ar,
            evidence_source_ids=(
                left_profile.source_id,
                right_profile.source_id,
            ),
        )