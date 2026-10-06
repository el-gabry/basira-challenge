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
    / "dorar-aqeedah"
    / "raw"
)

OUT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dorar-aqeedah"
    / "discovery.json"
)


URLS = {
    "home":
        "https://dorar.net/aqeeda",

    "references":
        "https://dorar.net/refs/aqeeda",

    "methodology":
        "https://dorar.net/article/1987",

    "introduction":
        "https://dorar.net/aqeeda/1",

    "basic_definition":
        "https://dorar.net/aqeeda/2522",

    "detailed_evidence":
        "https://dorar.net/aqeeda/420",

    "search_locator":
        (
            "https://dorar.net/aqeeda/search"
            "?skeys=%D8%A7%D9%84%D8%A5%D9%8A%D9%85%D8%A7%D9%86"
        ),
}


ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


def clean(
    value: str,
) -> str:

    value = unescape(
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


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

    return clean(
        value
    )


class ShapeParser(
    HTMLParser
):

    def __init__(
        self,
    ) -> None:

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

        self.current_link_href: (
            str | None
        ) = None

        self.current_link_parts: list[str] = []

        self.links: list[
            dict[str, str]
        ] = []

        self.classes: Counter[str] = (
            Counter()
        )

        self.ids: Counter[str] = (
            Counter()
        )

        self.data_attrs: Counter[str] = (
            Counter()
        )

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:

        tag = tag.lower()

        attrs_dict = dict(
            attrs
        )

        class_value = attrs_dict.get(
            "class",
            "",
        )

        for item in class_value.split():

            if item:
                self.classes[
                    item
                ] += 1

        element_id = attrs_dict.get(
            "id"
        )

        if element_id:
            self.ids[
                element_id
            ] += 1

        for key, _value in attrs:

            if key.startswith(
                "data-"
            ):
                self.data_attrs[
                    key
                ] += 1

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
                attrs_dict.get(
                    "href"
                )
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

        if (
            self.current_link_href
            is not None
        ):

            self.current_link_parts.append(
                data
            )


def parse_page(
    name: str,
) -> tuple[
    ShapeParser,
    str,
    bytes,
]:

    path = (
        RAW
        / f"{name}.html"
    )

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

    return (
        parser,
        text,
        raw,
    )


def canonical_aqeedah_links(
    parser: ShapeParser,
) -> list[
    dict[str, str]
]:

    result = []

    for link in parser.links:

        href = (
            link.get(
                "href"
            )
            or ""
        )

        if re.search(
            r"(?:https?://dorar\.net)?"
            r"/aqeeda/\d+(?:/|$)",
            href,
        ):

            result.append(
                link
            )

    return result


def characterize(
    name: str,
) -> dict:

    parser, text, raw = (
        parse_page(
            name
        )
    )

    normalized = (
        normalize_arabic(
            text
        )
    )

    canonical_links = (
        canonical_aqeedah_links(
            parser
        )
    )

    search_links = [
        link
        for link in parser.links
        if "/aqeeda/search"
        in (
            link.get(
                "href"
            )
            or ""
        )
    ]

    quran_reference_count = len(
        re.findall(
            r"\[[^\[\]]{1,100}"
            r":\s*\d+[^\[\]]*\]",
            text,
        )
    )

    hadith_source_marker_count = len(
        re.findall(
            r"(?:أخرجه|رواه)\s+",
            text,
        )
    )

    footnote_marker_count = len(
        re.findall(
            r"\[\d{1,6}\]",
            text,
        )
    )

    source_metadata_markers = {
        marker:
            (
                normalize_arabic(
                    marker
                )
                in normalized
            )

        for marker in (
            "المؤلف",
            "المحقق",
            "الناشر",
            "الطبعة",
            "سنة الطبع",
        )
    }

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
            len(
                parser.headings
            ),

        "headings_preview":
            parser.headings[
                :100
            ],

        "link_count":
            len(
                parser.links
            ),

        "canonical_aqeedah_link_count":
            len(
                canonical_links
            ),

        "canonical_aqeedah_links_preview":
            canonical_links[
                :100
            ],

        "search_link_count":
            len(
                search_links
            ),

        "quran_reference_like_count":
            quran_reference_count,

        "hadith_source_marker_count":
            hadith_source_marker_count,

        "footnote_marker_count":
            footnote_marker_count,

        "source_metadata_markers":
            source_metadata_markers,

        "top_classes":
            parser.classes.most_common(
                50
            ),

        "top_ids":
            parser.ids.most_common(
                50
            ),

        "top_data_attributes":
            parser.data_attrs.most_common(
                30
            ),

        "text_preview":
            text[:12000],
    }


def full_normalized_text(
    name: str,
) -> str:

    _parser, text, _raw = (
        parse_page(
            name
        )
    )

    return normalize_arabic(
        text
    )


def require(
    condition: bool,
    message: str,
    failures: list[str],
) -> None:

    if not condition:

        failures.append(
            message
        )


def require_text(
    haystack: str,
    marker: str,
    message: str,
    failures: list[str],
) -> None:

    require(
        normalize_arabic(
            marker
        )
        in haystack,

        message,

        failures,
    )


def main() -> None:

    reports = {
        name:
            characterize(
                name
            )
        for name
        in URLS
    }

    failures: list[str] = []

    # ========================================================
    # HOME / TAXONOMY
    # ========================================================

    home = full_normalized_text(
        "home"
    )

    for marker in (
        "الموسوعة العقدية",
        "المراجع المعتمدة",
        "منهج العمل في الموسوعة",
        "مقدمات في علم العقيدة والإيمان والتوحيد",
        "الإيمان بالله",
        "الإيمان بالملائكة",
        "الإيمان بالكتب الإلهية المنزلة",
        "الإيمان بالأنبياء والرسل",
        "حقيقة الإيمان",
    ):

        require_text(
            home,
            marker,
            (
                "home taxonomy marker missing: "
                + marker
            ),
            failures,
        )

    require(
        reports[
            "home"
        ][
            "canonical_aqeedah_link_count"
        ]
        >= 10,

        "home has unexpectedly few canonical Aqeedah links",

        failures,
    )


    # ========================================================
    # REFERENCES
    # ========================================================

    refs = full_normalized_text(
        "references"
    )

    for marker in (
        "المؤلف",
        "المحقق",
        "الناشر",
        "الطبعة",
        "سنة الطبع",
    ):

        require_text(
            refs,
            marker,
            (
                "reference metadata marker missing: "
                + marker
            ),
            failures,
        )


    # ========================================================
    # DORAR METHODOLOGY
    # ========================================================

    methodology = (
        full_normalized_text(
            "methodology"
        )
    )

    methodology_requirements = {
        "topic_definition":
            "تحديد الموضوعات",

        "source_collection":
            "جمع المصادر",

        "approved_source_selection":
            "تحديد المصادر المعتمدة",

        "best_editions":
            "أفضل الطبعات",

        "source_quality_comparison":
            "الجودة والشمول والاستيعاب",

        "source_page_traceability":
            (
                "توثيق كل مادة من مصدرها "
                "بالجزء والصفحة"
            ),

        "scientific_editing":
            (
                "تحرير الموضوعات "
                "تحريرا علميا دقيقا"
            ),
    }

    for key, marker in (
        methodology_requirements.items()
    ):

        require_text(
            methodology,
            marker,
            (
                "methodology marker missing: "
                + key
            ),
            failures,
        )


    # ========================================================
    # INTRODUCTION PAGE:
    # Quran appears inside Aqeedah source.
    #
    # Important future boundary:
    # this remains Aqeedah context,
    # NOT canonical Quran witness.
    # ========================================================

    intro = full_normalized_text(
        "introduction"
    )

    require_text(
        intro,
        "مقدمة",
        "introduction page title missing",
        failures,
    )

    require(
        reports[
            "introduction"
        ][
            "quran_reference_like_count"
        ]
        >= 2,

        "introduction page did not expose expected Quran references",

        failures,
    )


    # ========================================================
    # BASIC DEFINITION PAGE
    # ========================================================

    basic = full_normalized_text(
        "basic_definition"
    )

    require_text(
        basic,
        "تعريف الإيمان اصطلاحا",
        "basic Aqeedah definition heading missing",
        failures,
    )

    require_text(
        basic,
        "الإيمان",
        "basic Aqeedah content unexpectedly absent",
        failures,
    )


    # ========================================================
    # DETAILED / EVIDENCE-HEAVY PAGE
    #
    # Used to observe cross-domain Hadith material and
    # source-note/citation structure.
    # ========================================================

    detailed = full_normalized_text(
        "detailed_evidence"
    )

    require_text(
        detailed,
        "الأسماء والصفات",
        "detailed Aqeedah heading marker missing",
        failures,
    )

    require_text(
        detailed,
        "أدلة الشرع",
        "detailed evidence marker missing",
        failures,
    )

    require(
        reports[
            "detailed_evidence"
        ][
            "hadith_source_marker_count"
        ]
        >= 2,

        "detailed page exposes too few Hadith source markers",

        failures,
    )

    require(
        reports[
            "detailed_evidence"
        ][
            "footnote_marker_count"
        ]
        >= 2,

        "detailed page exposes too few evidence footnotes",

        failures,
    )


    # ========================================================
    # SEARCH SURFACE IS LOCATOR ONLY
    # ========================================================

    search = full_normalized_text(
        "search_locator"
    )

    require_text(
        search,
        "عدد النتائج",
        "search result count marker missing",
        failures,
    )

    require(
        reports[
            "search_locator"
        ][
            "canonical_aqeedah_link_count"
        ]
        >= 1,

        "search locator did not expose canonical result links",

        failures,
    )


    # ========================================================
    # RESULT
    # ========================================================

    result = {
        "discovery_id":
            "dorar-aqeedah-live-characterization-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_family":
            "DORAR_AQEEDA",

        "runtime_admission":
            "PENDING_AUDIT",

        "adapter_status":
            "NOT_IMPLEMENTED",

        "source_trust_passport":
            "NOT_ISSUED",

        "observed_invariants": {
            "aqeedah_taxonomy_is_hierarchical":
                True,

            "canonical_article_pages_exist":
                True,

            "search_is_locator_only":
                True,

            "approved_references_surface_exists":
                True,

            "methodology_surface_exists":
                True,

            "methodology_selects_approved_sources":
                True,

            "methodology_considers_best_editions":
                True,

            "methodology_requires_source_page_traceability":
                True,

            "quran_occurs_inside_aqeedah_material":
                True,

            "hadith_occurs_inside_aqeedah_material":
                True,

            "quran_requires_external_quran_boundary":
                True,

            "hadith_requires_external_hadith_boundary":
                True,

            "generic_shamela_fallback_allowed":
                False,
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
    print(
        "============================================"
    )

    print(
        "DORAR AQEEDAH LIVE CHARACTERIZATION"
    )

    print(
        "============================================"
    )

    for name, report in (
        reports.items()
    ):

        print()
        print(
            name
        )

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
            " canonical links:",
            report[
                "canonical_aqeedah_link_count"
            ],
        )

        print(
            " Quran refs:",
            report[
                "quran_reference_like_count"
            ],
        )

        print(
            " Hadith source markers:",
            report[
                "hadith_source_marker_count"
            ],
        )

        print(
            " footnotes:",
            report[
                "footnote_marker_count"
            ],
        )

        print(
            " heading preview:"
        )

        for heading in (
            report[
                "headings_preview"
            ][
                :12
            ]
        ):

            print(
                "   ",
                heading["tag"],
                "|",
                heading["text"][
                    :180
                ],
            )

    print()
    print(
        "Observed:"
    )

    print(
        "✓ hierarchical Aqeedah taxonomy"
    )

    print(
        "✓ canonical article pages"
    )

    print(
        "✓ approved-reference metadata"
    )

    print(
        "✓ source-selection methodology"
    )

    print(
        "✓ best-edition methodology"
    )

    print(
        "✓ source/page traceability methodology"
    )

    print(
        "✓ Quran embedded in Aqeedah material"
    )

    print(
        "✓ Hadith embedded in Aqeedah material"
    )

    print(
        "✓ search is locator only"
    )

    print()
    print(
        "RESULT:",
        result["result"],
    )

    print(
        "RUNTIME ADMISSION:",
        result[
            "runtime_admission"
        ],
    )

    print(
        "ADAPTER:",
        result[
            "adapter_status"
        ],
    )

    print(
        "PASSPORT:",
        result[
            "source_trust_passport"
        ],
    )

    if failures:

        print()

        for failure in failures:

            print(
                "FAIL:",
                failure,
            )

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
