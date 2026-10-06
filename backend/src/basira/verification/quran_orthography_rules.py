from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class QuranOrthographyRuleId(StrEnum):
    VOCATIVE_YA_ALIF_OMISSION = (
        "vocative_ya_alif_omission"
    )

    ISRAIL_ALIF_RASM_VARIANT = (
        "israil_alif_rasm_variant"
    )

    WORD_BOUNDARY_ONLY = (
        "word_boundary_only"
    )

    DIACRITICS_ONLY = (
        "diacritics_only"
    )

    BASMALA_PREFIX_LAYOUT = (
        "basmala_prefix_layout"
    )


class QuranOrthographyEvidence(BaseModel):
    evidence_id: str = Field(
        min_length=1,
    )

    title: str = Field(
        min_length=1,
    )

    authority: str = Field(
        min_length=1,
    )

    url: str = Field(
        min_length=1,
    )

    note_ar: str = Field(
        min_length=1,
    )


class QuranOrthographyRule(BaseModel):
    rule_id: QuranOrthographyRuleId

    name_ar: str
    name_en: str

    explanation_ar: str

    is_textual_change: bool

    evidence: tuple[
        QuranOrthographyEvidence,
        ...,
    ]


VOCATIVE_YA_RULE = QuranOrthographyRule(
    rule_id=(
        QuranOrthographyRuleId
        .VOCATIVE_YA_ALIF_OMISSION
    ),
    name_ar=(
        "حذف ألف ياء النداء في الرسم العثماني"
    ),
    name_en=(
        "Vocative ya alif omission "
        "in Uthmani rasm"
    ),
    explanation_ar=(
        "هذا اختلاف موثق في الرسم العثماني، "
        "حيث تحذف ألف ياء النداء في مواضع "
        "من رسم المصحف. لا يُعد هذا وحده "
        "تغييرًا في ألفاظ الآية."
    ),
    is_textual_change=False,
    evidence=(
        QuranOrthographyEvidence(
            evidence_id=(
                "azhar-uthmani-rasm-"
                "vocative-ya"
            ),
            title=(
                "نظام كتابة المصحف - "
                "نماذج للحذف"
            ),
            authority=(
                "جامعة الأزهر"
            ),
            url=(
                "https://azharegypt.org/"
                "lcms/cntopen.php"
                "?cid=3&cnt=86"
                "&lid=838&page=p03"
            ),
            note_ar=(
                "يذكر المصدر صراحة حذف "
                "الألف من ياء النداء في "
                "الرسم العثماني."
            ),
        ),
    ),
)


ISRAIL_ALIF_RULE = QuranOrthographyRule(
    rule_id=(
        QuranOrthographyRuleId
        .ISRAIL_ALIF_RASM_VARIANT
    ),
    name_ar=(
        "اختلاف إثبات ألف إسرائيل "
        "وحذفها في رسم المصاحف"
    ),
    name_en=(
        "Isra'il alif rasm variant"
    ),
    explanation_ar=(
        "ورد اختلاف منقول في رسم كلمة "
        "إسرائيل بين المصاحف في إثبات "
        "الألف وحذفها. لذلك لا يجوز "
        "اعتبار هذا الاختلاف وحده "
        "تغييرًا في ألفاظ الآية."
    ),
    is_textual_change=False,
    evidence=(
        QuranOrthographyEvidence(
            evidence_id=(
                "salihoglu-2024-israil"
            ),
            title=(
                "Analysis of Rare Maghrebi "
                "Qur'anic Manuscripts"
            ),
            authority=(
                "KSÜ Faculty of Theology Journal"
            ),
            url=(
                "https://isamveri.org/"
                "pdfdrg/D02628/2024_44/"
                "2024_44_SALIHOGLU.pdf"
            ),
            note_ar=(
                "ينقل البحث اختلاف المصاحف "
                "في إثبات ألف إسرائيل، "
                "وأن الداني رجح الإثبات "
                "في الأكثر، بينما اتبع "
                "المشارقة الحذف."
            ),
        ),
        QuranOrthographyEvidence(
            evidence_id=(
                "abu-dawud-israil-rasm"
            ),
            title=(
                "مختصر التبيين "
                "لهجاء التنزيل"
            ),
            authority=(
                "أبو داود سليمان بن نجاح"
            ),
            url=(
                "https://ablibrary.net/"
                "book_content/b/8410/116"
            ),
            note_ar=(
                "يعرض اختلاف المصاحف "
                "في رسم إسرائيل بين "
                "الإثبات والحذف."
            ),
        ),
    ),
)


RULES_BY_ID: dict[
    QuranOrthographyRuleId,
    QuranOrthographyRule,
] = {
    VOCATIVE_YA_RULE.rule_id: (
        VOCATIVE_YA_RULE
    ),
    ISRAIL_ALIF_RULE.rule_id: (
        ISRAIL_ALIF_RULE
    ),
}


def require_orthography_rule(
    rule_id: QuranOrthographyRuleId,
) -> QuranOrthographyRule:
    try:
        return RULES_BY_ID[
            rule_id
        ]
    except KeyError as exc:
        raise KeyError(
            "No source-backed Quran "
            "orthography rule registered "
            f"for {rule_id!s}."
        ) from exc