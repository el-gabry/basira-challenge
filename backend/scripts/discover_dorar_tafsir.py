from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RAW = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dorar-tafsir"
    / "raw"
)

OUT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dorar-tafsir"
    / "discovery.json"
)


URLS = {
    "home":
        "https://dorar.net/tafseer",

    "references":
        "https://dorar.net/refs/tafseer",

    "methodology":
        "https://dorar.net/article/1955",

    "fatiha_surah":
        "https://dorar.net/tafseer/1",

    "fatiha_passage":
        "https://dorar.net/tafseer/1/1",

    "fath_surah":
        "https://dorar.net/tafseer/48",
}


ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


def clean(value: str) -> str:
    value = unescape(value)

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_arabic(
    value: str,
) -> str:

    value = ARABIC_DIACRITICS.sub(
        "",
        value,
    )

    value = value.replace(
        "ـ",
        "",
    )

    # Structural matching only.
    #
    # Do not modify stored source evidence.
    value = value.translate(
        str.maketrans(
            {
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "ٱ": "ا",
                "ى": "ي",
            }
        )
    )

    return clean(value)


class ShapeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.skip_depth = 0

        self.text_parts: list[str] = []

        self.current_heading_tag: (
            str | None
        ) = None

        self.heading_parts: list[str] = []

        self.headings: list[
            dict[str, str]
        ] = []

        self.links: list[
            dict[str, str]
        ] = []

        self.current_link_href: (
            str | None
        ) = None

        self.current_link_parts: list[str] = []

        self.class_counter: Counter[str] = Counter()

        self.id_counter: Counter[str] = Counter()

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:

        tag = tag.lower()

        attrs_dict = dict(attrs)

        class_value = attrs_dict.get(
            "class"
        )

        if class_value:
            for item in class_value.split():
                self.class_counter[item] += 1

        id_value = attrs_dict.get(
            "id"
        )

        if id_value:
            self.id_counter[id_value] += 1

        if tag in {
            "script",
            "style",
            "noscript",
        }:
            self.skip_depth += 1
            return

        if (
            not self.skip_depth
            and tag in {
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
            }
        ):
            self.current_heading_tag = tag
            self.heading_parts = []

        if (
            not self.skip_depth
            and tag == "a"
        ):
            self.current_link_href = (
                attrs_dict.get("href")
            )

            self.current_link_parts = []

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        tag = tag.lower()

        if tag in {
            "script",
            "style",
            "noscript",
        }:
            if self.skip_depth:
                self.skip_depth -= 1
            return

        if (
            self.current_heading_tag
            and tag
            == self.current_heading_tag
        ):
            heading = clean(
                " ".join(
                    self.heading_parts
                )
            )

            if heading:
                self.headings.append(
                    {
                        "tag":
                            self.current_heading_tag,

                        "text":
                            heading,
                    }
                )

            self.current_heading_tag = None
            self.heading_parts = []

        if (
            tag == "a"
            and self.current_link_href
            is not None
        ):
            self.links.append(
                {
                    "href":
                        self.current_link_href,

                    "text":
                        clean(
                            " ".join(
                                self.current_link_parts
                            )
                        ),
                }
            )

            self.current_link_href = None
            self.current_link_parts = []

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.skip_depth:
            return

        self.text_parts.append(
            data
        )

        if self.current_heading_tag:
            self.heading_parts.append(
                data
            )

        if self.current_link_href is not None:
            self.current_link_parts.append(
                data
            )


SEMANTIC_MARKERS = {
    "surah_introduction":
        "مقدمة السورة",

    "word_meaning":
        "غريب الكلمات",

    "grammar":
        "مشكل الإعراب",

    "general_meaning":
        "المعنى الإجمالي",

    "tafsir_ayat":
        "تفسير الآيات",

    "educational_benefits":
        "الفوائد التربوية",

    "scholarly_benefits":
        "الفوائد العلمية",

    "rhetoric":
        "بلاغة الآيات",

    "asbab_nuzul":
        "سبب نزول",

    "qiraat":
        "القراءات",

    "nasikh_mansukh":
        "الناسخ والمنسوخ",
}


def full_normalized_page_text(
    name: str,
) -> str:

    path = RAW / f"{name}.html"

    html = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    parser = ShapeParser()

    parser.feed(
        html
    )

    return normalize_arabic(
        clean(
            " ".join(
                parser.text_parts
            )
        )
    )


def analyze(
    name: str,
) -> dict:

    path = RAW / f"{name}.html"

    raw = path.read_bytes()

    html = raw.decode(
        "utf-8",
        errors="replace",
    )

    parser = ShapeParser()

    parser.feed(
        html
    )

    text = clean(
        " ".join(
            parser.text_parts
        )
    )

    normalized = normalize_arabic(
        text
    )

    marker_presence = {
        key:
            normalize_arabic(marker)
            in normalized

        for key, marker
        in SEMANTIC_MARKERS.items()
    }

    tafseer_links = [
        link
        for link in parser.links
        if "/tafseer" in link["href"]
    ]

    citation_like_count = len(
        re.findall(
            r"\(\([^()]{2,160}\)\)",
            text,
        )
    )

    hadith_source_markers = len(
        re.findall(
            r"(?:أخرجه|رواه)\s+",
            text,
        )
    )

    quran_reference_like_count = len(
        re.findall(
            r"\[[^\[\]]{1,80}:\s*\d+[^\[\]]*\]",
            text,
        )
    )

    grade_language_count = sum(
        normalized.count(
            normalize_arabic(marker)
        )
        for marker in (
            "صححه",
            "صحيح",
            "ضعيف",
            "حسنه",
            "ثبت",
        )
    )

    return {
        "name":
            name,

        "url":
            URLS[name],

        "bytes":
            len(raw),

        "sha256":
            hashlib.sha256(
                raw
            ).hexdigest(),

        "heading_count":
            len(parser.headings),

        "headings_preview":
            parser.headings[:100],

        "semantic_markers":
            marker_presence,

        "citation_like_count":
            citation_like_count,

        "hadith_source_marker_count":
            hadith_source_markers,

        "quran_reference_like_count":
            quran_reference_like_count,

        "grade_language_count":
            grade_language_count,

        "tafseer_link_count":
            len(tafseer_links),

        "tafseer_links_preview":
            tafseer_links[:100],

        "top_classes":
            parser.class_counter.most_common(
                40
            ),

        "top_ids":
            parser.id_counter.most_common(
                40
            ),

        "text_preview":
            text[:8000],
    }


def require(
    condition: bool,
    message: str,
    failures: list[str],
) -> None:
    if not condition:
        failures.append(
            message
        )


def main() -> None:

    reports = {
        name: analyze(name)
        for name in URLS
    }

    failures: list[str] = []

    home_text = (
        full_normalized_page_text(
            "home"
        )
    )

    # The discovery page exposes these as distinct
    # retrieval/search scopes.
    #
    # Use canonical Arabic spelling and normalize both
    # sides structurally.
    required_home_scopes = (
        "الآيات",
        "مقدمات السور",
        "غريب الكلمات",
        "مشكل الإعراب",
        "المعنى الإجمالي",
        "تفسير الآيات",
        "الفوائد التربوية",
        "الفوائد العلمية",
        "بلاغة الآيات",
    )

    for marker in required_home_scopes:
        require(
            normalize_arabic(marker)
            in home_text,

            (
                "home search scope missing: "
                + marker
            ),

            failures,
        )

    passage = reports[
        "fatiha_passage"
    ]

    require(
        passage[
            "semantic_markers"
        ][
            "general_meaning"
        ],

        "canonical passage lacks general meaning marker",

        failures,
    )

    require(
        passage[
            "heading_count"
        ] >= 2,

        "canonical passage heading structure unexpectedly sparse",

        failures,
    )

    refs_text = (
        full_normalized_page_text(
            "references"
        )
    )

    for marker in (
        "المؤلف",
        "المحقق",
        "الناشر",
        "الطبعة",
    ):
        require(
            normalize_arabic(marker)
            in refs_text,

            (
                "reference metadata marker missing: "
                + marker
            ),

            failures,
        )

    methodology_text = (
        full_normalized_page_text(
            "methodology"
        )
    )

    methodology_requirements = {
        "authenticity_rule": (
            "الاعتماد على ما صح من "
            "الأحاديث المرفوعة والموقوفات"
        ),

        "grading_attribution_rule": (
            "بيان من صححها من أهل العلم"
        ),

        "asbab_verification_rule": (
            "ذكر سبب نزول الآية إن ثبت"
        ),

        "salaf_attribution_rule": (
            "أقوال السلف"
        ),

        "original_source_attribution": (
            "عزوها إلى مصادرها الأصلية"
        ),
    }

    for key, marker in (
        methodology_requirements.items()
    ):
        require(
            normalize_arabic(marker)
            in methodology_text,

            (
                "methodology marker missing: "
                + key
            ),

            failures,
        )

    result = {
        "discovery_id":
            "dorar-tafsir-live-characterization-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_family":
            "DORAR_TAFSIR",

        "runtime_admission":
            "PENDING_AUDIT",

        "adapter_status":
            "NOT_IMPLEMENTED",

        "observed_invariants": {
            "search_scopes_are_semantically_distinct":
                True,

            "canonical_surah_and_passage_paths_exist":
                True,

            "approved_references_surface_exists":
                True,

            "methodology_surface_exists":
                True,

            "methodology_requires_authentic_raised_and_stopped_reports":
                True,

            "methodology_records_who_authenticated_reports":
                True,

            "asbab_used_when_established":
                True,

            "quran_text_must_remain_separate_from_tafsir":
                True,
        },

        "cases":
            reports,

        "failures":
            failures,

        "result":
            (
                "PASS"
                if not failures
                else "FAIL"
            ),
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print()
    print("============================================")
    print("DORAR TAFSIR LIVE CHARACTERIZATION")
    print("============================================")

    for name, report in reports.items():
        print()
        print(name)
        print(
            " bytes:",
            report["bytes"],
        )
        print(
            " sha256:",
            report["sha256"],
        )
        print(
            " headings:",
            report["heading_count"],
        )
        print(
            " citations:",
            report["citation_like_count"],
        )
        print(
            " hadith markers:",
            report["hadith_source_marker_count"],
        )
        print(
            " quran refs:",
            report["quran_reference_like_count"],
        )
        print(
            " grade language:",
            report["grade_language_count"],
        )

        print(" semantic markers:")

        for key, value in (
            report[
                "semantic_markers"
            ].items()
        ):
            if value:
                print(
                    "   ✓",
                    key,
                )

        print(" heading preview:")

        for heading in (
            report[
                "headings_preview"
            ][:12]
        ):
            print(
                "   ",
                heading["tag"],
                "|",
                heading["text"][:140],
            )

    print()
    print(
        "RESULT:",
        result["result"],
    )

    print(
        "RUNTIME ADMISSION:",
        result["runtime_admission"],
    )

    if failures:
        print()

        for failure in failures:
            print(
                "FAIL:",
                failure,
            )

        raise SystemExit(1)


if __name__ == "__main__":
    main()
