from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from basira.evidence.models import (
    ContextRequirement,
    EvidenceNeed,
)
from basira.retrieval.arabic_query import (
    ArabicQuery,
    build_arabic_query,
)
from basira.trust.runtime_constraints import (
    is_quran_verification_request,
)


class BasiraIntent(StrEnum):
    QURAN_LOOKUP = "quran_lookup"
    QURAN_MEANING = "quran_meaning"

    HADITH_LOOKUP = "hadith_lookup"
    HADITH_AUTHENTICITY = "hadith_authenticity"
    HADITH_EXPLANATION = "hadith_explanation"

    TAFSIR_CONTEXT = "tafsir_context"

    FIQH_QUESTION = "fiqh_question"
    FATWA_LOOKUP = "fatwa_lookup"

    SOURCE_VERIFICATION = "source_verification"

    QUOTE_VERIFICATION = "quote_verification"

    HISTORICAL_CONTEXT = "historical_context"

    THEOLOGY = "theology"

    GENERAL_ISLAMIC_QUESTION = "general_islamic_question"


class RiskTag(StrEnum):
    ARMED_CONFLICT = "armed_conflict"
    TAKFIR = "takfir"
    HUDUD = "hudud"

    CRIMINAL_PUNISHMENT = "criminal_punishment"

    SECTARIAN_CONFLICT = "sectarian_conflict"

    SELF_HARM = "self_harm"
    HARM_TO_OTHERS = "harm_to_others"

    CONTEXT_SENSITIVE = "context_sensitive"


@dataclass(
    frozen=True,
    slots=True,
)
class QueryEntity:
    entity_type: str
    value: str


@dataclass(
    frozen=True,
    slots=True,
)
class BasiraQueryUnderstanding:
    query: ArabicQuery

    primary_intent: BasiraIntent

    risk_tags: frozenset[RiskTag]

    entities: tuple[
        QueryEntity,
        ...,
    ]

    context_requirement: ContextRequirement

    confidence: float


_HADITH_AUTHENTICITY_TERMS = (
    "صحة الحديث",
    "صحيح الحديث",
    "الحديث صحيح",
    "الحديث ضعيف",
    "حكم الحديث",
    "درجة الحديث",
    "هل الحديث صحيح",
    "هل هذا الحديث صحيح",
    "هل الحديث ثابت",
    "هل هذا الحديث ثابت",
)

_HADITH_EXPLANATION_TERMS = (
    "شرح الحديث",
    "معنى الحديث",
    "ماذا يعني الحديث",
)

_QURAN_MEANING_TERMS = (
    "معنى الاية",
    "تفسير الاية",
    "ما معنى الاية",
    "ماذا تعني الاية",
)

_REVELATION_CONTEXT_TERMS = (
    "سبب نزول",
    "سبب النزول",
    "اسباب النزول",
    "أسباب النزول",
    "لماذا نزلت الاية",
    "لماذا نزلت الآية",
)

_FIQH_TERMS = (
    "ما حكم",
    # English legal-question markers.
    #
    # Keep these phrase-level and bounded:
    # one generic word such as "wudu", "ruling",
    # "allowed", or "halal" must not by itself
    # route a query to Fiqh.
    "what is the ruling",
    "what is the islamic ruling",
    "what is islamic ruling",
    "is it permissible",
    "is this permissible",
    "is it allowed",
    "is this allowed",
    "is it haram",
    "is this haram",
    "is it halal",
    "is this halal",
    "invalidate wudu",
    "invalidates wudu",
    "invalidating wudu",
    "break wudu",
    "breaks wudu",
    "breaking wudu",
    "nullify wudu",
    "nullifies wudu",
    "invalidate wudhu",
    "invalidates wudhu",
    "break wudhu",
    "breaks wudhu",
    "nullify wudhu",
    "nullifies wudhu",
    "invalidate ablution",
    "invalidates ablution",
    "invalidating ablution",
    "break ablution",
    "breaks ablution",
    "breaking ablution",
    "nullify ablution",
    "nullifies ablution",
    "حكم الشرع",
    "حلال",
    "حرام",
    "يجوز",
    "لا يجوز",
)

_SOURCE_VERIFICATION_TERMS = (
    "المصدر",
    "هل المصدر صحيح",
    "تحقق من المصدر",
    "صحة المصدر",
)

_QUOTE_VERIFICATION_TERMS = (
    "هل قال",
    "هل ورد",
    "هل هذا النص",
    "تحقق من النص",
)


_RISK_TERMS: dict[
    RiskTag,
    tuple[str, ...],
] = {
    RiskTag.ARMED_CONFLICT: (
        "قتل",
        "قتال",
        "جهاد",
        "حرب",
        "المشركين",
    ),
    RiskTag.TAKFIR: (
        "تكفير",
        "كافر",
        "مرتد",
        "ردة",
    ),
    RiskTag.HUDUD: (
        "الحد",
        "حد السرقة",
        "حد الزنا",
        "الرجم",
        "جلد",
    ),
    RiskTag.CRIMINAL_PUNISHMENT: (
        "عقوبة",
        "قصاص",
        "إعدام",
    ),
    RiskTag.SECTARIAN_CONFLICT: (
        "طائفة",
        "شيعة",
        "سني",
        "خوارج",
    ),
    RiskTag.SELF_HARM: (
        "انتحار",
        "قتل نفسي",
        "أقتل نفسي",
    ),
    RiskTag.HARM_TO_OTHERS: (
        "أقتل",
        "اقتله",
        "أؤذيه",
        "اضربه",
    ),
}


_HADITH_REFERENCE_RE = re.compile(r"(?:حديث|رقم)\s*(\d+)")

_QURAN_REFERENCE_RE = re.compile(
    r"(?:سورة\s+)?"
    r"([\u0600-\u06ff]+)"
    r"\s*[:،]\s*(\d+)"
)


_QURAN_NUMERIC_REFERENCE_RE = re.compile(
    r"(?<!\d)"
    r"(\d{1,3})"
    r"\s*[:،]\s*"
    r"(\d{1,3})"
    r"(?!\d)"
)


def _contains_any(
    text: str,
    terms: tuple[str, ...],
) -> bool:
    return any(term in text for term in terms)


def _tokens(
    value: str,
) -> tuple[str, ...]:
    return tuple(value.split())


def _mentions_hadith(
    value: str,
) -> bool:
    return any("حديث" in token for token in _tokens(value))


def _mentions_quran_reference(
    query: ArabicQuery,
) -> bool:
    text = query.intent_text

    source_surfaces = (
        query.original_text,
        query.search_text,
        query.intent_text,
    )

    source_cues = (
        # Original Arabic surface.
        "قال تعالى",
        "قوله تعالى",
        "قول الله تعالى",
        "قال الله تعالى",
        "في القرآن",
        "من القرآن",
        # Search/intent normalized surface.
        "قال تعالي",
        "قوله تعالي",
        "قول الله تعالي",
        "قال الله تعالي",
        "في القران",
        "من القران",
    )

    return (
        any(
            ("اية" in token or "آية" in token or "سورة" in token)
            for token in _tokens(text)
        )
        or "آية" in query.original_text
        or any(cue in surface for surface in source_surfaces for cue in source_cues)
    )


def _has_hadith_authenticity_cue(
    value: str,
) -> bool:
    cues = (
        "صحة",
        "صحيح",
        "ضعيف",
        "ثابت",
        "درجة",
        "حكم",
        "موضوع",
        "حسن",
    )

    return any(cue in value for cue in cues)


def _has_explanation_cue(
    value: str,
) -> bool:
    cues = (
        "معنى",
        "معني",
        "شرح",
        "تفسير",
        "يعني",
        "تعني",
    )

    return any(cue in value for cue in cues)


def _detect_intent(
    query: ArabicQuery,
) -> tuple[
    BasiraIntent,
    float,
]:
    text = query.intent_text

    mentions_hadith = _mentions_hadith(text)

    mentions_quran = _mentions_quran_reference(query)

    # Self-hardening runtime memory:
    # promoted governance memory may require verification,
    # but it never supplies Quran content or religious truth.
    if is_quran_verification_request(
        original_text=query.original_text,
        intent_text=query.intent_text,
    ):
        return (
            BasiraIntent.QUOTE_VERIFICATION,
            0.99,
        )

    # Concept-based rules come before the older
    # phrase dictionary. This makes routing robust
    # across MSA and dialect paraphrases.
    if mentions_hadith and _has_hadith_authenticity_cue(text):
        return (
            BasiraIntent.HADITH_AUTHENTICITY,
            0.95,
        )

    if mentions_hadith and _has_explanation_cue(text):
        return (
            BasiraIntent.HADITH_EXPLANATION,
            0.92,
        )

    if _contains_any(
        text,
        _REVELATION_CONTEXT_TERMS,
    ):
        return (
            BasiraIntent.TAFSIR_CONTEXT,
            0.95,
        )

    if mentions_quran and _has_explanation_cue(text):
        return (
            BasiraIntent.QURAN_MEANING,
            0.92,
        )

    # Keep explicit phrase rules as secondary
    # signals for wording not covered above.
    if _contains_any(
        text,
        _HADITH_AUTHENTICITY_TERMS,
    ):
        return (
            BasiraIntent.HADITH_AUTHENTICITY,
            0.90,
        )

    if _contains_any(
        text,
        _HADITH_EXPLANATION_TERMS,
    ):
        return (
            BasiraIntent.HADITH_EXPLANATION,
            0.88,
        )

    if _contains_any(
        text,
        _QURAN_MEANING_TERMS,
    ):
        return (
            BasiraIntent.QURAN_MEANING,
            0.88,
        )

    if _contains_any(
        text,
        _SOURCE_VERIFICATION_TERMS,
    ):
        return (
            BasiraIntent.SOURCE_VERIFICATION,
            0.85,
        )

    if _contains_any(
        text,
        _QUOTE_VERIFICATION_TERMS,
    ):
        return (
            BasiraIntent.QUOTE_VERIFICATION,
            0.80,
        )

    if _contains_any(
        text,
        _FIQH_TERMS,
    ):
        return (
            BasiraIntent.FIQH_QUESTION,
            0.80,
        )

    if mentions_hadith:
        return (
            BasiraIntent.HADITH_LOOKUP,
            0.70,
        )

    if mentions_quran:
        return (
            BasiraIntent.QURAN_LOOKUP,
            0.70,
        )

    return (
        BasiraIntent.GENERAL_ISLAMIC_QUESTION,
        0.40,
    )


def _detect_risks(
    query: ArabicQuery,
) -> frozenset[RiskTag]:
    text = query.intent_text

    detected = {
        tag
        for tag, terms in _RISK_TERMS.items()
        if _contains_any(
            text,
            terms,
        )
    }

    if detected:
        detected.add(RiskTag.CONTEXT_SENSITIVE)

    return frozenset(detected)


def _extract_entities(
    query: ArabicQuery,
) -> tuple[
    QueryEntity,
    ...,
]:
    entities: list[QueryEntity] = []

    hadith_match = _HADITH_REFERENCE_RE.search(query.intent_text)

    if hadith_match is not None:
        entities.append(
            QueryEntity(
                entity_type=("hadith_number"),
                value=(hadith_match.group(1)),
            )
        )

    # Structured references such as 2:255 must be
    # extracted from the original query. Search/intent
    # normalization intentionally replaces punctuation
    # and would otherwise destroy the ":" separator.
    numeric_quran_match = _QURAN_NUMERIC_REFERENCE_RE.search(query.original_text)

    if numeric_quran_match is not None:
        surah_number = int(numeric_quran_match.group(1))

        ayah_number = int(numeric_quran_match.group(2))

        if 1 <= surah_number <= 114 and ayah_number >= 1:
            entities.extend(
                [
                    QueryEntity(
                        entity_type=("surah_number"),
                        value=str(surah_number),
                    ),
                    QueryEntity(
                        entity_type=("ayah_number"),
                        value=str(ayah_number),
                    ),
                ]
            )

    quran_match = _QURAN_REFERENCE_RE.search(query.intent_text)

    if quran_match is not None:
        entities.extend(
            [
                QueryEntity(
                    entity_type=("surah"),
                    value=(quran_match.group(1)),
                ),
                QueryEntity(
                    entity_type=("ayah"),
                    value=(quran_match.group(2)),
                ),
            ]
        )

    return tuple(entities)


def _context_requirement(
    intent: BasiraIntent,
    risks: frozenset[RiskTag],
) -> ContextRequirement:
    if intent is BasiraIntent.HADITH_AUTHENTICITY:
        return ContextRequirement(
            required=frozenset(
                {
                    EvidenceNeed.HADITH_TEXT,
                    EvidenceNeed.HADITH_GRADE,
                    EvidenceNeed.SOURCE_PROVENANCE,
                }
            ),
        )

    if intent in {
        BasiraIntent.HADITH_LOOKUP,
        BasiraIntent.HADITH_EXPLANATION,
    }:
        return ContextRequirement(
            required=frozenset(
                {
                    EvidenceNeed.HADITH_TEXT,
                    EvidenceNeed.SOURCE_PROVENANCE,
                }
            ),
            optional=frozenset(
                {
                    EvidenceNeed.HADITH_GRADE,
                }
            ),
        )

    if intent is BasiraIntent.TAFSIR_CONTEXT:
        return ContextRequirement(
            required=frozenset(
                {
                    EvidenceNeed.CANONICAL_TEXT,
                    EvidenceNeed.TAFSIR,
                    EvidenceNeed.REVELATION_CONTEXT,
                    EvidenceNeed.SOURCE_PROVENANCE,
                }
            ),
            optional=frozenset(
                {
                    EvidenceNeed.SURROUNDING_CONTEXT,
                    EvidenceNeed.RELATED_HADITH,
                }
            ),
        )

    if intent in {
        BasiraIntent.QURAN_LOOKUP,
        BasiraIntent.QURAN_MEANING,
    }:
        required = {
            EvidenceNeed.CANONICAL_TEXT,
            EvidenceNeed.SOURCE_PROVENANCE,
        }

        optional = {
            EvidenceNeed.TAFSIR,
            EvidenceNeed.SURROUNDING_CONTEXT,
        }

        # Important:
        # We declare the future protected context
        # contract now, but enforcement happens in
        # the advanced Basira pipeline.
        if RiskTag.CONTEXT_SENSITIVE in risks:
            required.update(
                {
                    EvidenceNeed.SURROUNDING_CONTEXT,
                    EvidenceNeed.TAFSIR,
                    EvidenceNeed.RELATED_HADITH,
                    EvidenceNeed.FIQH_CONSTRAINTS,
                    EvidenceNeed.ACTOR_AUTHORITY,
                    EvidenceNeed.APPLICABILITY_CONDITIONS,
                }
            )

        return ContextRequirement(
            required=frozenset(required),
            optional=frozenset(optional - required),
        )

    if intent is BasiraIntent.FIQH_QUESTION:
        return ContextRequirement(
            required=frozenset(
                {
                    EvidenceNeed.FIQH_EVIDENCE,
                    EvidenceNeed.SOURCE_PROVENANCE,
                }
            ),
            optional=frozenset(
                {
                    EvidenceNeed.RELATED_HADITH,
                    EvidenceNeed.TAFSIR,
                    EvidenceNeed.CONTEMPORARY_GUIDANCE,
                }
            ),
        )

    return ContextRequirement(
        required=frozenset(
            {
                EvidenceNeed.SOURCE_PROVENANCE,
            }
        ),
    )


def context_requirement_for(
    intent: BasiraIntent,
    risks: frozenset[RiskTag,],
) -> ContextRequirement:
    """
    Public deterministic policy boundary for converting
    an effective intent + risk set into evidence/context
    requirements.

    This delegates to the existing single policy
    implementation; callers must not duplicate the
    intent/risk -> EvidenceNeed mapping.
    """
    return _context_requirement(
        intent,
        risks,
    )


def _detect_english_intent(
    value: str,
) -> tuple[BasiraIntent, float] | None:
    """
    Deterministic English semantic cues.

    Request language is deliberately NOT passed into
    religious reasoning. These cues only understand
    what the user asked; governed routing, evidence,
    sufficiency, and publication remain unchanged.
    """

    text = " ".join(value.casefold().split())

    if not text:
        return None

    hadith_cues = (
        "hadith",
        "hadeeth",
    )

    hadith_authenticity_cues = (
        "authentic",
        "authenticity",
        "sahih",
        "sound hadith",
        "weak hadith",
        "fabricated",
        "grade this hadith",
        "hadith grade",
    )

    if any(cue in text for cue in hadith_cues) and any(
        cue in text for cue in hadith_authenticity_cues
    ):
        return (
            BasiraIntent.HADITH_AUTHENTICITY,
            0.98,
        )

    if any(cue in text for cue in hadith_cues) and any(
        cue in text
        for cue in (
            "explain",
            "meaning",
            "what does",
            "what is meant",
        )
    ):
        return (
            BasiraIntent.HADITH_EXPLANATION,
            0.96,
        )

    revelation_context_cues = (
        "occasion of revelation",
        "reason for revelation",
        "context of revelation",
        "asbab al-nuzul",
        "asbab al nuzul",
        "why was this verse revealed",
        "when was this verse revealed",
    )

    if any(cue in text for cue in revelation_context_cues):
        return (
            BasiraIntent.TAFSIR_CONTEXT,
            0.97,
        )

    # Asking for tafsir/exegesis normally means Quran meaning +
    # governed Tafsir evidence. TAFSIR_CONTEXT is reserved for
    # requests that genuinely require revelation context.
    if any(
        cue in text
        for cue in (
            "tafsir",
            "exegesis",
        )
    ):
        return (
            BasiraIntent.QURAN_MEANING,
            0.97,
        )

    quran_cues = (
        "quran",
        "qur'an",
        "koran",
        "ayah",
        "ayat",
        "verse",
        "surah",
        "sura",
        "kursi",
    )

    quran_meaning_cues = (
        "what does",
        "what is the meaning",
        "what does it mean",
        "mean in",
        "meaning of",
        "explain",
        "interpret",
        "what does",
        "what does ayat",
        "what does verse",
        "what does surah",
        "what does kursi",
        "say",
    )

    if any(cue in text for cue in quran_cues) and any(
        cue in text for cue in quran_meaning_cues
    ):
        return (
            BasiraIntent.QURAN_MEANING,
            0.97,
        )

    if any(cue in text for cue in quran_cues):
        return (
            BasiraIntent.QURAN_LOOKUP,
            0.92,
        )

    if any(cue in text for cue in hadith_cues):
        return (
            BasiraIntent.HADITH_LOOKUP,
            0.92,
        )

    return None


class BasiraQueryUnderstandingService:
    def understand(
        self,
        value: str,
    ) -> BasiraQueryUnderstanding:
        query = build_arabic_query(value)

        intent, confidence = _detect_intent(query)

        if intent is BasiraIntent.GENERAL_ISLAMIC_QUESTION:
            english_intent = _detect_english_intent(value)

            if english_intent is not None:
                intent, confidence = english_intent

        risks = _detect_risks(query)

        return BasiraQueryUnderstanding(
            query=query,
            primary_intent=intent,
            risk_tags=risks,
            entities=(_extract_entities(query)),
            context_requirement=(
                _context_requirement(
                    intent,
                    risks,
                )
            ),
            confidence=confidence,
        )
