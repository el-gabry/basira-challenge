from __future__ import annotations

import re
from dataclasses import dataclass

from basira.retrieval.arabic_query import (
    normalize_arabic_search_text,
)

_MAX_ATOMIC_QUERIES = 3

_EXACT_QURAN_REFERENCE_RE = re.compile(r"(?<!\d)\d{1,3}\s*[:،]\s*\d{1,3}(?!\d)")

_LATIN_RE = re.compile(r"[a-zA-Z]")

_ENGLISH_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(
    frozen=True,
    slots=True,
)
class AtomicQuery:
    """
    One bounded search representation.

    Atomic queries contain concepts / aliases only.
    They must never contain suggested Quran references,
    Hadith IDs, evidence IDs, or source IDs.
    """

    query_id: str
    concept: str
    search_text: str


@dataclass(
    frozen=True,
    slots=True,
)
class AtomicQueryPlan:
    route: str
    atomic_queries: tuple[AtomicQuery, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class _ConceptRule:
    concept: str

    arabic_triggers: tuple[str, ...]
    english_triggers: tuple[str, ...]

    search_variants: tuple[str, ...]


_CONCEPT_RULES = (
    _ConceptRule(
        concept="patience",
        arabic_triggers=(
            "الصبر",
            "صبر",
            "الثبات",
            "الشدائد",
            "الشدة",
            "البلاء",
            "المصيبة",
            "المصائب",
            "الاحتساب",
        ),
        english_triggers=(
            "patience",
            "patient",
            "hardship",
            "hardships",
            "adversity",
            "steadfast",
            "steadfastness",
            "calamity",
            "trial",
        ),
        search_variants=(
            "الصبر البلاء",
            "الصبر المصيبة",
            "الثبات الصبر الشدائد الاحتساب",
        ),
    ),
    _ConceptRule(
        concept="trust_in_god",
        arabic_triggers=(
            "التوكل",
            "توكل",
            "يفوض",
            "تفويض",
            "أفوض",
            "افوض",
            "المستقبل",
            "الثقة بالله",
        ),
        english_triggers=(
            "trust god",
            "trusting god",
            "rely on god",
            "reliance on god",
            "uncertain future",
            "future is uncertain",
            "depend on god",
        ),
        search_variants=(
            "التوكل على الله",
            "التوكل تفويض الأمر إلى الله",
            "الثقة بالله التوكل",
        ),
    ),
    _ConceptRule(
        concept="gratitude",
        arabic_triggers=(
            "الشكر",
            "شكر",
            "النعم",
            "النعمة",
            "نعم الله",
            "الفضل",
            "الشاكرين",
        ),
        english_triggers=(
            "gratitude",
            "grateful",
            "thankful",
            "thank god",
            "blessing",
            "blessings",
        ),
        search_variants=(
            "الشكر لله",
            "شكر النعمة",
            "النعم الشكر فضل الله",
        ),
    ),
    _ConceptRule(
        concept="parents",
        arabic_triggers=(
            "الوالدين",
            "الوالدان",
            "والديه",
            "والدي",
            "الأبوين",
            "الابوين",
            "أمه وأباه",
            "امه واباه",
            "أمه",
            "اباه",
            "يكبران",
            "الكبر",
        ),
        english_triggers=(
            "parents",
            "parent",
            "mother and father",
            "mother",
            "father",
            "become old",
            "old age",
        ),
        search_variants=(
            "بر الوالدين",
            "الإحسان إلى الوالدين",
            "الوالدين الكبر الرحمة",
        ),
    ),
    _ConceptRule(
        concept="justice",
        arabic_triggers=(
            "العدل",
            "عدل",
            "الحق",
            "القسط",
            "الشهادة",
            "مصلحته",
            "أقاربه",
            "اقاربه",
        ),
        english_triggers=(
            "justice",
            "just",
            "fair",
            "fairness",
            "own interests",
            "against yourself",
            "against your own",
        ),
        search_variants=(
            "العدل القسط",
            "الشهادة بالحق العدل",
            "العدل ولو على النفس والأقربين",
        ),
    ),
    _ConceptRule(
        concept="repentance_forgiveness",
        arabic_triggers=(
            "التوبة",
            "توبة",
            "المغفرة",
            "مغفرة",
            "يغفر",
            "الذنوب",
            "ذنوبه",
            "ذنب",
            "الرجوع إلى الله",
            "الرجوع الى الله",
        ),
        english_triggers=(
            "forgive",
            "forgiven",
            "forgiveness",
            "repent",
            "repentance",
            "sins",
            "sin",
            "return to god",
        ),
        search_variants=(
            "التوبة المغفرة",
            "مغفرة الذنوب",
            "الرجوع إلى الله التوبة",
        ),
    ),
    _ConceptRule(
        concept="charity",
        arabic_triggers=(
            "الصدقة",
            "صدقة",
            "الإنفاق",
            "الانفاق",
            "إنفاق",
            "انفاق",
            "مساعدة الفقراء",
        ),
        english_triggers=(
            "charity",
            "giving wealth",
            "give wealth",
            "help others",
            "spending wealth",
            "almsgiving",
        ),
        search_variants=(
            "الصدقة والإنفاق",
            "الإنفاق في سبيل الله",
            "إنفاق المال الخير",
        ),
    ),
    _ConceptRule(
        concept="anger",
        arabic_triggers=(
            "الغضب",
            "غضبه",
            "غاضب",
            "الرد",
            "الانتقام",
        ),
        english_triggers=(
            "anger",
            "angry",
            "rage",
            "revenge",
            "retaliate",
        ),
        search_variants=(
            "كظم الغيظ",
            "العفو عند الغضب",
            "الغضب العفو",
        ),
    ),
    _ConceptRule(
        concept="ease_after_hardship",
        arabic_triggers=(
            "الضيق",
            "العسر",
            "اليسر",
            "الفرج",
            "لن ينتهي",
            "الأمل",
            "الامل",
        ),
        english_triggers=(
            "hardship end",
            "hardship will end",
            "relief",
            "ease after hardship",
            "despair",
            "hope",
        ),
        search_variants=(
            "العسر اليسر",
            "الضيق الفرج",
            "الأمل بعد الشدة",
        ),
    ),
    _ConceptRule(
        concept="good_speech",
        arabic_triggers=(
            "الكلام",
            "كلامه",
            "كلام",
            "يقول",
            "يختار كلامه",
            "يختلف",
            "الاختلاف",
        ),
        english_triggers=(
            "speech",
            "words",
            "speak",
            "disagreement",
            "disagree",
            "talk to others",
        ),
        search_variants=(
            "قولوا للناس حسنا",
            "القول الحسن",
            "الكلمة الطيبة الاختلاف",
        ),
    ),
    _ConceptRule(
        concept="remembrance_tranquility",
        arabic_triggers=(
            "ذكر الله",
            "الذكر",
            "طمأنينة",
            "الطمأنينة",
            "راحة القلب",
        ),
        english_triggers=(
            "remembering god",
            "remembrance of god",
            "peace of heart",
            "peace in the heart",
            "tranquility",
        ),
        search_variants=(
            "ذكر الله تطمئن القلوب",
            "الذكر الطمأنينة",
            "طمأنينة القلب ذكر الله",
        ),
    ),
    _ConceptRule(
        concept="backbiting",
        arabic_triggers=(
            "الغيبة",
            "غيبة",
            "يغتاب",
            "اغتياب",
        ),
        english_triggers=(
            "backbiting",
            "backbite",
            "gossip about others",
        ),
        search_variants=(
            "الغيبة",
            "ولا يغتب بعضكم بعضا",
            "اغتياب الناس",
        ),
    ),
    _ConceptRule(
        concept="mercy",
        arabic_triggers=(
            "الرحمة",
            "رحمة",
            "الرحمن",
            "الرحيم",
        ),
        english_triggers=(
            "mercy",
            "merciful",
            "compassion",
        ),
        search_variants=(
            "رحمة الله",
            "الرحمة",
            "الرحمن الرحيم",
        ),
    ),
    _ConceptRule(
        concept="prayer",
        arabic_triggers=(
            "الصلاة",
            "صلاة",
            "يصلي",
            "أقيموا الصلاة",
            "اقيموا الصلاة",
        ),
        english_triggers=(
            "prayer",
            "pray",
            "salah",
        ),
        search_variants=(
            "الصلاة",
            "إقامة الصلاة",
            "المحافظة على الصلاة",
        ),
    ),
    _ConceptRule(
        concept="fasting",
        arabic_triggers=(
            "الصيام",
            "صيام",
            "الصوم",
            "رمضان",
        ),
        english_triggers=(
            "fasting",
            "fast",
            "ramadan",
        ),
        search_variants=(
            "الصيام",
            "الصوم",
            "صيام رمضان",
        ),
    ),
    _ConceptRule(
        concept="knowledge",
        arabic_triggers=(
            "العلم",
            "المعرفة",
            "يتعلم",
            "التعلم",
            "العلماء",
        ),
        english_triggers=(
            "knowledge",
            "learning",
            "learn",
            "scholar",
            "scholars",
        ),
        search_variants=(
            "العلم",
            "طلب العلم",
            "العلم المعرفة",
        ),
    ),
)


def _normalized_arabic(value: str) -> str:
    return normalize_arabic_search_text(value).casefold()


def _normalized_english(value: str) -> str:
    return " ".join(_ENGLISH_TOKEN_RE.findall(value.casefold()))


def _trigger_score(
    *,
    arabic_text: str,
    english_text: str,
    rule: _ConceptRule,
) -> int:
    score = 0

    for trigger in rule.arabic_triggers:
        normalized = _normalized_arabic(trigger)

        if normalized and normalized in arabic_text:
            score += 1

    for trigger in rule.english_triggers:
        normalized = _normalized_english(trigger)

        if normalized and f" {normalized} " in f" {english_text} ":
            score += 1

    return score


def plan_atomic_queries(
    question: str,
    *,
    max_queries: int = _MAX_ATOMIC_QUERIES,
) -> AtomicQueryPlan:
    """
    Build bounded query-side retrieval representations.

    This is intentionally conservative:
    - no source/evidence/reference prediction;
    - no generated religious claims;
    - no corpus-wide synthetic questions;
    - at most three query variants.
    """

    if max_queries <= 0:
        raise ValueError("max_queries must be greater than zero.")

    value = question.strip()

    if not value:
        return AtomicQueryPlan(
            route="empty",
            atomic_queries=(),
        )

    if _EXACT_QURAN_REFERENCE_RE.search(value):
        return AtomicQueryPlan(
            route="exact_reference",
            atomic_queries=(),
        )

    arabic_text = _normalized_arabic(value)
    english_text = _normalized_english(value)

    scored_rules = [
        (
            _trigger_score(
                arabic_text=arabic_text,
                english_text=english_text,
                rule=rule,
            ),
            index,
            rule,
        )
        for index, rule in enumerate(_CONCEPT_RULES)
    ]

    matched_rules = [
        (score, index, rule) for score, index, rule in scored_rules if score > 0
    ]

    matched_rules.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    if not matched_rules:
        return AtomicQueryPlan(
            route=("cross_lingual" if _LATIN_RE.search(value) else "conceptual"),
            atomic_queries=(),
        )

    selected: list[tuple[str, str]] = []

    seen_texts: set[str] = set()

    # Round-robin across matched concepts so one
    # concept cannot consume all three query slots.
    variant_index = 0

    while len(selected) < max_queries:
        added = False

        for _, _, rule in matched_rules:
            if variant_index >= len(rule.search_variants):
                continue

            search_text = rule.search_variants[variant_index].strip()

            normalized = _normalized_arabic(search_text)

            if normalized and normalized not in seen_texts:
                seen_texts.add(normalized)
                selected.append(
                    (
                        rule.concept,
                        search_text,
                    )
                )
                added = True

            if len(selected) >= max_queries:
                break

        if not added:
            break

        variant_index += 1

    return AtomicQueryPlan(
        route=("cross_lingual" if _LATIN_RE.search(value) else "conceptual"),
        atomic_queries=tuple(
            AtomicQuery(
                query_id=f"AQ{index}",
                concept=concept,
                search_text=search_text,
            )
            for index, (
                concept,
                search_text,
            ) in enumerate(
                selected,
                start=1,
            )
        ),
    )
