from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class HybridTopic(StrEnum):
    QURAN = "quran"
    HADITH = "hadith"
    TAFSIR = "tafsir"
    FIQH = "fiqh"

    AQEEDAH = "aqeedah"
    HISTORY = "history"
    SHUBUHAT = "shubuhat"

    DAWAH = "dawah"
    TERMINOLOGY = "terminology"

    GENERAL = "general_islamic"


class HybridLookupMode(StrEnum):
    IDENTIFIER = "identifier_resolution"
    PARTIAL_TEXT = "partial_text_resolution"
    CONCEPT = "concept_resolution"
    TRANSLATION = "terminology_translation"
    PERSONALIZED_APPLICATION = "personalized_application"


class ResponseGovernanceLevel(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass(
    frozen=True,
    slots=True,
)
class HybridQueryResolution:
    """
    Query-resolution output only.

    This object may decide:
    - what kind of problem the user asked;
    - which governed capability is needed;
    - which language is required;
    - whether identity resolution is needed;
    - how constrained publication must be.

    It MUST NOT:
    - select religious authority;
    - manufacture evidence;
    - choose a madhhab;
    - perform tarjih;
    - issue a personal fatwa.
    """

    topic: HybridTopic

    language: str

    lookup_mode: HybridLookupMode

    response_level: ResponseGovernanceLevel

    personalized: bool

    capability: str

    identifier_candidate: str | None = None

    # Source-native language is mandatory.
    # An Arabic source may not silently satisfy
    # an English evidence obligation.
    allow_cross_language_fallback: bool = False

    reasons: tuple[str, ...] = ()


_ARABIC_RE = re.compile(r"[\u0600-\u06ff]")

_DIGIT_RE = re.compile(r"(?<!\d)(\d{2,7})(?!\d)")


def _normalize(
    value: str,
) -> str:
    return " ".join(value.casefold().split())


def _language(
    question: str,
    requested_language: str | None,
) -> str:
    if requested_language in {
        "ar",
        "en",
    }:
        return requested_language

    if _ARABIC_RE.search(question):
        return "ar"

    return "en"


def _contains_any(
    text: str,
    values: tuple[str, ...],
) -> bool:
    return any(value in text for value in values)


_HADITH_TERMS = (
    "حديث",
    "الحديث",
    "hadith",
    "hadeeth",
)

_HADITH_AUTHENTICITY_TERMS = (
    "صحة حديث",
    "صحة الحديث",
    "هل الحديث صحيح",
    "درجة الحديث",
    "حكم الحديث",
    "حديث صحيح",
    "حديث ضعيف",
    "authentic hadith",
    "hadith authentic",
    "hadith sahih",
    "hadith weak",
    "grade of the hadith",
)

_QURAN_EXPLICIT_TERMS = (
    "القرآن",
    "القران",
    "آية",
    "اية",
    "سورة",
    "quran",
    "qur'an",
    "ayah",
    "verse",
    "surah",
)

_EXPLANATION_TERMS = (
    "ما معنى",
    "ماذا يعني",
    "اشرح",
    "تفسير",
    "meaning of",
    "what does",
    "what is the meaning",
    "explain",
)

_TRANSLATION_TERMS = (
    "ترجم",
    "ترجمة",
    "بالانجليزية",
    "بالإنجليزية",
    "باللغة الانجليزية",
    "باللغة الإنجليزية",
    "translate",
    "translation",
    "in english",
)

_AQEEDAH_TERMS = (
    "العقيدة",
    "عقيدة",
    "التوحيد",
    "توحيد",
    "اسماء الله وصفاته",
    "أسماء الله وصفاته",
    "أسماء وصفات",
    "aqeedah",
    "aqidah",
    "tawhid",
    "tawheed",
    "names and attributes of allah",
)

_HISTORY_TERMS = (
    "السيرة",
    "سيرة النبي",
    "التاريخ الاسلامي",
    "التاريخ الإسلامي",
    "غزوة",
    "الهجرة",
    "انتشر بالسيف",
    "seerah",
    "sirah",
    "islamic history",
    "prophetic biography",
    "hijrah",
    "spread by the sword",
    "spread by sword",
)

_HISTORICAL_SENSITIVE_TERMS = (
    "انتشر بالسيف",
    "spread by the sword",
    "spread by sword",
)

_SHUBUHAT_TERMS = (
    "شبهة",
    "الشبهات",
    "لماذا يعبد المسلمون الكعبة",
    "هل القرآن من تأليف محمد",
    "هل القران من تأليف محمد",
    "why do muslims worship the kaaba",
    "why do muslims worship kaaba",
    "did muhammad write the quran",
    "was the quran written by muhammad",
    "misconception",
)

_DAWAH_TERMS = (
    "كيف أدعو",
    "كيف ادعو",
    "الدعوة إلى الإسلام",
    "الدعوة الى الاسلام",
    "دعوة إلى الإسلام",
    "دعوة الى الاسلام",
    "التعريف بالإسلام",
    "التعريف بالاسلام",
    "أدعو صديقي",
    "ادعو صديقي",
    "أدعو شخص",
    "ادعو شخص",
    "how to invite someone to islam",
    "how do i invite someone to islam",
    "how to introduce islam",
    "introduce islam",
    "dawah",
    "da'wah",
)


_FIQH_TERMS = (
    "ما حكم",
    "هل يجوز",
    "يجوز لي",
    "حرام",
    "حلال",
    "ينقض الوضوء",
    "ينقض وضوئي",
    "فتوى",
    "what is the ruling",
    "is it permissible",
    "is this permissible",
    "is it allowed",
    "is this allowed",
    "is it haram",
    "is this haram",
    "is it halal",
    "invalidate wudu",
    "invalidates wudu",
    "break wudu",
    "breaks wudu",
    "personal fatwa",
)

_FIRST_PERSON_AR = (
    "أنا ",
    "انا ",
    "لي ",
    "عندي ",
    "زوجي",
    "زوجتي",
    "حالتي",
    "في دولتي",
    "في بلدي",
)

_FIRST_PERSON_EN = (
    "i ",
    "i'm ",
    "i am ",
    "my ",
    "for me",
    "my case",
    "my country",
)

_PRIVATE_PART_FIQH_TERMS = (
    "مس المرأة فرجها",
    "مس فرجها",
    "touching her private parts",
    "touching the private parts",
)


def _personalized(
    text: str,
    language: str,
) -> bool:
    first_person = _FIRST_PERSON_AR if language == "ar" else _FIRST_PERSON_EN

    return _contains_any(
        text,
        first_person,
    ) and _contains_any(
        text,
        _FIQH_TERMS,
    )


def resolve_hybrid_query(
    *,
    question: str,
    language: str | None = None,
) -> HybridQueryResolution:
    """
    Deterministic pre-retrieval resolver.

    Search may broaden.
    Authority may never broaden.
    """

    text = _normalize(question)

    resolved_language = _language(
        question,
        language,
    )

    mentions_hadith = _contains_any(
        text,
        _HADITH_TERMS,
    )

    identifier_match = _DIGIT_RE.search(text) if mentions_hadith else None

    # -------------------------------------------------
    # HADITH IDENTITY / AUTHENTICITY
    # -------------------------------------------------

    if mentions_hadith and identifier_match:
        return HybridQueryResolution(
            topic=HybridTopic.HADITH,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.IDENTIFIER),
            response_level=(ResponseGovernanceLevel.A),
            personalized=False,
            capability="hadith",
            identifier_candidate=(identifier_match.group(1)),
            reasons=(
                "hadith_identifier_candidate",
                "identity_must_resolve_before_publication",
            ),
        )

    if mentions_hadith and (
        _contains_any(
            text,
            _HADITH_AUTHENTICITY_TERMS,
        )
        or _contains_any(
            text,
            (
                "صحيح",
                "ضعيف",
                "حسن",
                "ثابت",
                "موضوع",
                "مكذوب",
                "authentic",
                "weak",
                "fabricated",
                "sahih",
                "hasan",
                "daif",
                "da'if",
            ),
        )
    ):
        return HybridQueryResolution(
            topic=HybridTopic.HADITH,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.PARTIAL_TEXT),
            response_level=(ResponseGovernanceLevel.A),
            personalized=False,
            capability="hadith",
            reasons=(
                "hadith_authenticity_request",
                "identity_required_before_grade",
            ),
        )

    # -------------------------------------------------
    # PERSONAL FIQH
    # Must precede generic concept routing.
    # -------------------------------------------------

    if _personalized(
        text,
        resolved_language,
    ):
        return HybridQueryResolution(
            topic=HybridTopic.FIQH,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.PERSONALIZED_APPLICATION),
            response_level=(ResponseGovernanceLevel.D),
            personalized=True,
            capability="general_fiqh",
            reasons=(
                "personalized_legal_application",
                "general_information_only",
                "no_personal_fatwa",
            ),
        )

    # -------------------------------------------------
    # TERMINOLOGY / TRANSLATION
    # -------------------------------------------------

    if _contains_any(
        text,
        _TRANSLATION_TERMS,
    ):
        return HybridQueryResolution(
            topic=HybridTopic.TERMINOLOGY,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.TRANSLATION),
            response_level=(ResponseGovernanceLevel.B),
            personalized=False,
            capability=("translation_terminology"),
            reasons=(
                "religious_terminology_translation",
                "source_native_target_language_required",
            ),
        )

    # -------------------------------------------------
    # EXPLICIT QURAN MEANING -> TAFSIR
    # A concept alone must NOT be promoted to Quran.
    # -------------------------------------------------

    if _contains_any(
        text,
        _QURAN_EXPLICIT_TERMS,
    ) and _contains_any(
        text,
        _EXPLANATION_TERMS,
    ):
        return HybridQueryResolution(
            topic=HybridTopic.TAFSIR,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.CONCEPT),
            response_level=(ResponseGovernanceLevel.B),
            personalized=False,
            capability="tafsir",
            reasons=(
                "explicit_quran_context",
                "interpretive_explanation",
            ),
        )

    # -------------------------------------------------
    # DAWAH / GENERAL GUIDANCE
    #
    # This selects a material capability only.
    # It grants no religious evidence authority.
    # -------------------------------------------------

    if _contains_any(
        text,
        _DAWAH_TERMS,
    ):
        return HybridQueryResolution(
            topic=HybridTopic.DAWAH,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.CONCEPT),
            response_level=(ResponseGovernanceLevel.B),
            personalized=False,
            capability=("dawah_general_content"),
            reasons=(
                "dawah_guidance_request",
                "material_only_capability",
            ),
        )

    # -------------------------------------------------
    # AQEEDAH
    # -------------------------------------------------

    if _contains_any(
        text,
        _AQEEDAH_TERMS,
    ):
        return HybridQueryResolution(
            topic=HybridTopic.AQEEDAH,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.CONCEPT),
            response_level=(ResponseGovernanceLevel.B),
            personalized=False,
            capability="aqeedah",
            reasons=(
                "aqeedah_concept",
                "authority_selected_by_policy_not_agent",
            ),
        )

    # -------------------------------------------------
    # HISTORY / SEERAH
    # -------------------------------------------------

    if _contains_any(
        text,
        _HISTORY_TERMS,
    ):
        sensitive = _contains_any(
            text,
            _HISTORICAL_SENSITIVE_TERMS,
        )

        return HybridQueryResolution(
            topic=HybridTopic.HISTORY,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.CONCEPT),
            response_level=(
                ResponseGovernanceLevel.C if sensitive else ResponseGovernanceLevel.B
            ),
            personalized=False,
            capability="seerah_history",
            reasons=(
                ("sensitive_historical_claim" if sensitive else "historical_context"),
                "historical_identity_must_remain_bounded",
            ),
        )

    # -------------------------------------------------
    # SHUBUHAT / MISCONCEPTION
    # -------------------------------------------------

    if _contains_any(
        text,
        _SHUBUHAT_TERMS,
    ):
        return HybridQueryResolution(
            topic=HybridTopic.SHUBUHAT,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.CONCEPT),
            response_level=(ResponseGovernanceLevel.B),
            personalized=False,
            capability="shubuhat_faq",
            reasons=(
                "misconception_or_faq",
                "claim_must_remain_source_grounded",
            ),
        )

    # -------------------------------------------------
    # GENERAL FIQH
    # -------------------------------------------------

    if _contains_any(
        text,
        _FIQH_TERMS,
    ) or _contains_any(
        text,
        _PRIVATE_PART_FIQH_TERMS,
    ):
        return HybridQueryResolution(
            topic=HybridTopic.FIQH,
            language=resolved_language,
            lookup_mode=(HybridLookupMode.CONCEPT),
            response_level=(ResponseGovernanceLevel.C),
            personalized=False,
            capability="general_fiqh",
            reasons=(
                "general_fiqh_question",
                "preserve_documented_disagreement",
                "no_automated_tarjih",
            ),
        )

    # -------------------------------------------------
    # Generic concept.
    #
    # Example:
    #   "ما هو الكرسي؟"
    #
    # This must NOT automatically become Quran/Tafsir.
    # -------------------------------------------------

    return HybridQueryResolution(
        topic=HybridTopic.GENERAL,
        language=resolved_language,
        lookup_mode=(HybridLookupMode.CONCEPT),
        response_level=(ResponseGovernanceLevel.B),
        personalized=False,
        capability="general_islamic",
        reasons=(
            "general_concept",
            "no_unjustified_domain_promotion",
        ),
    )
