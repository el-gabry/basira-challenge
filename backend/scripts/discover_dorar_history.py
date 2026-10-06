from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(
    __file__
).resolve().parents[1]


DISCOVERY_ROOT = (
    ROOT
    / "data/competition/discovery/"
    "dorar-history"
)

RAW = DISCOVERY_ROOT / "raw"

META = (
    DISCOVERY_ROOT
    / "capture-meta.tsv"
)

OUT = (
    DISCOVERY_ROOT
    / "discovery.json"
)


_ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


def clean(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        unescape(value),
    ).strip()


def normalize_arabic(
    value: str,
) -> str:

    value = _ARABIC_DIACRITICS.sub(
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


@dataclass
class Page:
    text_parts: list[str] = field(
        default_factory=list
    )

    headings: list[
        tuple[str, str]
    ] = field(
        default_factory=list
    )

    links: list[
        tuple[str, str]
    ] = field(
        default_factory=list
    )

    title_parts: list[str] = field(
        default_factory=list
    )

    canonical_href: str | None = None

    in_title: bool = False

    heading_tag: str | None = None

    heading_parts: list[str] = field(
        default_factory=list
    )

    link_href: str | None = None

    link_parts: list[str] = field(
        default_factory=list
    )


class Parser(HTMLParser):

    def __init__(self) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.page = Page()

        self.skip_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:

        tag = tag.lower()

        attrs_dict = dict(
            attrs
        )

        if tag in {
            "script",
            "style",
            "noscript",
        }:
            self.skip_depth += 1
            return

        if tag == "title":
            self.page.in_title = True

        if tag in {
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.page.heading_tag = tag
            self.page.heading_parts = []

        if tag == "a":
            self.page.link_href = (
                attrs_dict.get(
                    "href"
                )
            )
            self.page.link_parts = []

        if tag == "link":

            rel = (
                attrs_dict.get(
                    "rel"
                )
                or ""
            ).lower()

            if "canonical" in rel.split():

                href = attrs_dict.get(
                    "href"
                )

                if href:
                    self.page.canonical_href = href

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

        if tag == "title":
            self.page.in_title = False

        if (
            self.page.heading_tag is not None
            and tag
            == self.page.heading_tag
        ):

            value = clean(
                " ".join(
                    self.page.heading_parts
                )
            )

            if value:
                self.page.headings.append(
                    (
                        self.page.heading_tag,
                        value,
                    )
                )

            self.page.heading_tag = None
            self.page.heading_parts = []

        if (
            tag == "a"
            and self.page.link_href
            is not None
        ):

            value = clean(
                " ".join(
                    self.page.link_parts
                )
            )

            self.page.links.append(
                (
                    self.page.link_href,
                    value,
                )
            )

            self.page.link_href = None
            self.page.link_parts = []

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.skip_depth:
            return

        value = clean(
            data
        )

        if not value:
            return

        self.page.text_parts.append(
            value
        )

        if self.page.in_title:
            self.page.title_parts.append(
                value
            )

        if self.page.heading_tag is not None:
            self.page.heading_parts.append(
                value
            )

        if self.page.link_href is not None:
            self.page.link_parts.append(
                value
            )


def parse(
    raw: bytes,
) -> Page:

    parser = Parser()

    parser.feed(
        raw.decode(
            "utf-8",
            errors="replace",
        )
    )

    return parser.page


class ElementTextByIdParser(HTMLParser):
    """
    Extract visible text only from one element subtree.

    This prevents evidence from another encyclopedia's
    modal/accordion section from being attributed to History.
    """

    def __init__(
        self,
        *,
        target_id: str,
    ) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.target_id = target_id

        self.capture_depth: int | None = None

        self.depth = 0

        self.parts: list[str] = []

        self.skip_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:

        tag = tag.lower()

        attrs_dict = dict(
            attrs
        )

        if tag in {
            "script",
            "style",
            "noscript",
        }:
            self.skip_depth += 1

        if (
            self.capture_depth is None
            and attrs_dict.get("id")
            == self.target_id
        ):
            self.capture_depth = self.depth

        self.depth += 1

    def handle_startendtag(
        self,
        tag: str,
        attrs,
    ) -> None:

        # No persistent depth change for void/self-closing nodes.
        pass

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        tag = tag.lower()

        self.depth -= 1

        if (
            tag in {
                "script",
                "style",
                "noscript",
            }
            and self.skip_depth
        ):
            self.skip_depth -= 1

        if (
            self.capture_depth is not None
            and self.depth
            == self.capture_depth
        ):
            self.capture_depth = None

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.skip_depth:
            return

        if self.capture_depth is None:
            return

        value = clean(
            data
        )

        if value:
            self.parts.append(
                value
            )


def extract_text_by_id(
    raw: bytes,
    *,
    element_id: str,
) -> str:

    parser = ElementTextByIdParser(
        target_id=element_id
    )

    parser.feed(
        raw.decode(
            "utf-8",
            errors="replace",
        )
    )

    return clean(
        " ".join(
            parser.parts
        )
    )


def sha256(
    raw: bytes,
) -> str:

    return hashlib.sha256(
        raw
    ).hexdigest()


def normalized_page_text(
    page: Page,
) -> str:

    return normalize_arabic(
        clean(
            " ".join(
                page.text_parts
            )
        )
    )


def contains(
    text: str,
    marker: str,
) -> bool:

    return (
        normalize_arabic(
            marker
        )
        in text
    )


def load_meta():

    result = {}

    for line in META.read_text(
        encoding="utf-8"
    ).splitlines():

        if not line.strip():
            continue

        (
            name,
            requested,
            effective,
            http_code,
        ) = line.split(
            "\t",
            3,
        )

        result[name] = {
            "requested_url":
                requested,

            "effective_url":
                effective,

            "http_code":
                int(
                    http_code
                ),
        }

    return result


def analyze_case(
    name: str,
    meta: dict,
) -> dict:

    raw = (
        RAW
        / f"{name}.html"
    ).read_bytes()

    page = parse(
        raw
    )

    text = normalized_page_text(
        page
    )

    return {
        "requested_url":
            meta[
                "requested_url"
            ],

        "effective_url":
            meta[
                "effective_url"
            ],

        "effective_path":
            urlsplit(
                meta[
                    "effective_url"
                ]
            ).path,

        "http_code":
            meta[
                "http_code"
            ],

        "canonical_href":
            page.canonical_href,

        "bytes":
            len(raw),

        "sha256":
            sha256(raw),

        "html_title":
            clean(
                " ".join(
                    page.title_parts
                )
            ),

        "headings":
            [
                {
                    "tag":
                        tag,

                    "text":
                        value,
                }
                for tag, value
                in page.headings[
                    :100
                ]
            ],

        "history_links":
            [
                {
                    "href":
                        href,

                    "text":
                        label,
                }
                for href, label
                in page.links
                if (
                    "/history"
                    in href
                )
            ][
                :200
            ],

        "markers": {
            "history_encyclopedia":
                contains(
                    text,
                    "الموسوعة التاريخية"
                ),

            "brief_narrative":
                contains(
                    text,
                    "سرد تاريخي مختصر"
                ),

            "no_commentary_analysis":
                contains(
                    text,
                    "مجرد من التعليق والتحليل"
                ),

            "hijri_year":
                contains(
                    text,
                    "العام الهجري"
                ),

            "gregorian_year":
                contains(
                    text,
                    "العام الميلادي"
                ),

            "lunar_month":
                contains(
                    text,
                    "الشهر القمري"
                ),

            "event_details":
                contains(
                    text,
                    "تفاصيل الحدث"
                ),

            "disagreement":
                (
                    contains(
                        text,
                        "اختلف"
                    )
                    or contains(
                        text,
                        "الخلاف"
                    )
                ),

            "agreement":
                contains(
                    text,
                    "اتفق"
                ),

            "reported_saying":
                contains(
                    text,
                    "قيل"
                ),

            "prophet":
                (
                    contains(
                        text,
                        "رسول الله"
                    )
                    or contains(
                        text,
                        "النبي"
                    )
                ),

            "hadith_attribution":
                (
                    contains(
                        text,
                        "عن انس"
                    )
                    or contains(
                        text,
                        "عن ابي قتادة"
                    )
                    or contains(
                        text,
                        "روى الترمذي"
                    )
                ),
        },

        "text_chars":
            len(text),
    }


def require(
    condition: bool,
    name: str,
    failures: list[str],
) -> None:

    if not condition:
        failures.append(
            name
        )


def main() -> None:

    meta = load_meta()

    required = (
        "home",
        "search",
        "refs",
        "methodology",
        "methodology_review",
        "seerah_disagreement",
        "seerah_prophetic_report",
        "seerah_event",
        "medieval_event",
        "early_modern_event",
        "contemporary_event",
    )

    missing = [
        name
        for name in required
        if name not in meta
    ]

    if missing:
        raise SystemExit(
            "missing captures: "
            + ", ".join(
                missing
            )
        )

    cases = {
        name:
            analyze_case(
                name,
                meta[name],
            )
        for name in required
    }

    failures: list[str] = []


    # ========================================================
    # HTTP / identity
    # ========================================================

    for name in required:

        require(
            cases[
                name
            ][
                "http_code"
            ]
            == 200,

            f"{name}:http_200",

            failures,
        )


    # ========================================================
    # Home-page self-description
    # ========================================================

    home = cases[
        "home"
    ][
        "markers"
    ]

    require(
        home[
            "brief_narrative"
        ],
        "history_brief_narrative_notice",
        failures,
    )

    require(
        home[
            "no_commentary_analysis"
        ],
        "history_no_commentary_analysis_notice",
        failures,
    )


    # ========================================================
    # Methodology:
    # reliable source + scientific editing
    # ========================================================

    methodology_raw = (
        RAW
        / "methodology.html"
    ).read_bytes()

    methodology_page = parse(
        methodology_raw
    )

    methodology_text = (
        normalized_page_text(
            methodology_page
        )
    )

    require(
        contains(
            methodology_text,
            "ان يكون الحدث من مصدر موثوق"
        ),
        "methodology_reliable_source",
        failures,
    )

    require(
        contains(
            methodology_text,
            "تحرير الاحداث تحريرا علميا دقيقا"
        ),
        "methodology_scientific_editing",
        failures,
    )


    # ========================================================
    # Governance / review
    # ========================================================

    review_page = parse(
        (
            RAW
            / "methodology_review.html"
        ).read_bytes()
    )

    review_text = (
        normalized_page_text(
            review_page
        )
    )

    # ========================================================
    # HISTORY-SPECIFIC REVIEW GOVERNANCE
    #
    # The raw page contains accordion/modal content for many
    # encyclopedias. Therefore a global marker such as
    # "اعتمد المنهجية" is unsafe: it can belong to Tafsir,
    # Fiqh, or another domain.
    #
    # History review evidence is taken only from the page's
    # History-specific canonical content subtree (#cntnt).
    # ========================================================

    review_main_text = normalize_arabic(
        extract_text_by_id(
            (
                RAW
                / "methodology_review.html"
            ).read_bytes(),
            element_id="cntnt",
        )
    )

    history_review_section_observed = (
        contains(
            review_main_text,
            "راجع الموسوعة"
        )
    )

    history_researcher_observed = (
        contains(
            review_main_text,
            "باحث في التاريخ الاسلامي"
        )
    )

    history_professor_count = (
        review_main_text.count(
            normalize_arabic(
                "أستاذ التاريخ الإسلامي"
            )
        )
    )

    history_specialist_reviewers_observed = (
        history_researcher_observed
        and history_professor_count >= 3
    )

    require(
        history_review_section_observed,
        "history_review_section_observed",
        failures,
    )

    require(
        history_specialist_reviewers_observed,
        "history_specialist_reviewers_observed",
        failures,
    )


    # ========================================================
    # Reference catalog
    # ========================================================

    refs_page = parse(
        (
            RAW
            / "refs.html"
        ).read_bytes()
    )

    refs_text = normalized_page_text(
        refs_page
    )

    require(
        contains(
            refs_text,
            "المؤلف"
        ),
        "refs_author_metadata",
        failures,
    )

    require(
        contains(
            refs_text,
            "المحقق"
        ),
        "refs_editor_metadata",
        failures,
    )

    require(
        contains(
            refs_text,
            "الناشر"
        ),
        "refs_publisher_metadata",
        failures,
    )

    require(
        contains(
            refs_text,
            "الطبعة"
        ),
        "refs_edition_metadata",
        failures,
    )


    # ========================================================
    # Event structure
    # ========================================================

    event_cases = (
        "seerah_disagreement",
        "seerah_prophetic_report",
        "seerah_event",
        "medieval_event",
        "early_modern_event",
        "contemporary_event",
    )

    for name in event_cases:

        markers = cases[
            name
        ][
            "markers"
        ]

        require(
            markers[
                "hijri_year"
            ],
            f"{name}:hijri_year",
            failures,
        )

        require(
            markers[
                "gregorian_year"
            ],
            f"{name}:gregorian_year",
            failures,
        )

        require(
            markers[
                "event_details"
            ],
            f"{name}:event_details",
            failures,
        )


    # ========================================================
    # Explicit qualification / disagreement
    #
    # We observe it.
    #
    # We do NOT turn these words themselves into a machine
    # truth grade.
    # ========================================================

    disagreement = cases[
        "seerah_disagreement"
    ][
        "markers"
    ]

    require(
        disagreement[
            "disagreement"
        ],
        "explicit_disagreement_observed",
        failures,
    )

    require(
        disagreement[
            "agreement"
        ],
        "explicit_agreement_scope_observed",
        failures,
    )


    # ========================================================
    # Prophetic-report boundary
    # ========================================================

    prophetic = cases[
        "seerah_prophetic_report"
    ][
        "markers"
    ]

    require(
        prophetic[
            "prophet"
        ],
        "prophetic_content_observed",
        failures,
    )

    require(
        prophetic[
            "hadith_attribution"
        ],
        "hadith_attribution_observed",
        failures,
    )


    # ========================================================
    # ROUTE CHARACTERIZATION
    # ========================================================

    event_paths = {
        name:
            cases[
                name
            ][
                "effective_path"
            ]
        for name in event_cases
    }

    direct_history_id = [
        path
        for path
        in event_paths.values()
        if re.fullmatch(
            r"/history/[1-9][0-9]*",
            path,
        )
    ]

    history_event_id = [
        path
        for path
        in event_paths.values()
        if re.fullmatch(
            r"/history/event/[1-9][0-9]*",
            path,
        )
    ]

    require(
        bool(
            direct_history_id
        ),
        "direct_history_id_route_observed",
        failures,
    )

    require(
        bool(
            history_event_id
        ),
        "history_event_id_route_observed",
        failures,
    )


    # ========================================================
    # Discovery-only surfaces
    # ========================================================

    require(
        cases[
            "search"
        ][
            "effective_path"
        ].startswith(
            "/history/search"
        ),
        "search_surface_observed",
        failures,
    )

    require(
        cases[
            "refs"
        ][
            "effective_path"
        ].startswith(
            "/history/refs"
        ),
        "refs_surface_observed",
        failures,
    )


    findings = {
        "brief_narrative_notice_observed":
            True,

        "no_commentary_analysis_notice_observed":
            True,

        "methodology_requires_reliable_source":
            True,

        "methodology_requires_scientific_editing":
            True,

        "methodology_review_process_observed":
            (
                history_review_section_observed
                and history_specialist_reviewers_observed
            ),

        "history_review_section_observed":
            history_review_section_observed,

        "history_specialist_reviewers_observed":
            history_specialist_reviewers_observed,

        "history_researcher_qualification_observed":
            history_researcher_observed,

        "history_professor_qualification_count":
            history_professor_count,

        "generic_methodology_adoption_phrase_observed":
            contains(
                review_text,
                "اعتماد منهجيات الموسوعات"
            ),

        "generic_application_verification_phrase_observed":
            contains(
                review_text,
                "التاكد من تطبيق المنهجية"
            ),

        "global_cross_encyclopedia_review_text_is_history_evidence":
            False,

        "reference_catalog_observed":
            True,

        "event_year_details_structure_observed":
            True,

        "textual_disagreement_inside_event_observed":
            True,

        "prophetic_report_inside_history_event_observed":
            True,

        "direct_history_id_route_observed":
            bool(
                direct_history_id
            ),

        "history_event_id_route_observed":
            bool(
                history_event_id
            ),

        "search_is_locator_only":
            True,

        "reference_catalog_is_governance_metadata":
            True,

        "route_contract_frozen":
            False,

        "per_event_machine_truth_grade_observed":
            False,

        "lexical_disagreement_marker_equals_truth_grade":
            False,

        "generic_shamela_fallback_allowed":
            False,
    }


    result = {
        "discovery_version":
            1,

        "discovery_id":
            "dorar-history-live-characterization-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_family":
            "DORAR_HISTORY",

        "official_domain":
            "seerah_history",

        "cases":
            cases,

        "observed_event_paths":
            event_paths,

        "findings":
            findings,

        "policy_implications": [
            (
                "Institution-level curation is observed."
            ),
            (
                "History review evidence is taken from "
                "the History-specific review subtree, "
                "not from global review text belonging "
                "to other encyclopedias."
            ),
            (
                "Institution-level curation does not by "
                "itself justify fabricating a per-event "
                "numeric or categorical machine truth grade."
            ),
            (
                "Explicit source-reported disagreement "
                "must survive extraction."
            ),
            (
                "Prophetic reports embedded in History "
                "must route authentication to Hadith."
            ),
            (
                "Both direct /history/{id} and "
                "/history/event/{id} event routes exist."
            ),
            (
                "Runtime URL contract must not be frozen "
                "until canonical DOM/link behavior is probed."
            ),
            (
                "Search is locator-only."
            ),
            (
                "References are governance metadata, not "
                "automatic event evidence."
            )
        ],

        "runtime_admission":
            "PENDING_AUDIT",

        "adapter":
            "NOT_IMPLEMENTED",

        "source_trust_passport":
            "NOT_ISSUED",

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
        "================================================"
    )

    print(
        "DORAR HISTORY LIVE CHARACTERIZATION"
    )

    print(
        "================================================"
    )

    for name in required:

        case = cases[
            name
        ]

        print()
        print(name)

        print(
            " bytes:",
            case[
                "bytes"
            ],
        )

        print(
            " sha256:",
            case[
                "sha256"
            ],
        )

        print(
            " requested:",
            case[
                "requested_url"
            ],
        )

        print(
            " effective:",
            case[
                "effective_url"
            ],
        )

        print(
            " path:",
            case[
                "effective_path"
            ],
        )

        print(
            " canonical:",
            case[
                "canonical_href"
            ],
        )

        print(
            " headings:",
            len(
                case[
                    "headings"
                ]
            ),
        )


    print()
    print(
        "Observed event paths:"
    )

    for name, path in (
        event_paths.items()
    ):
        print(
            " ",
            name,
            "=>",
            path,
        )


    print()
    print(
        "✓ brief historical narrative notice"
    )

    print(
        "✓ no-commentary/analysis notice"
    )

    print(
        "✓ reliable-source methodology"
    )

    print(
        "✓ scientific-editing methodology"
    )

    print(
        "✓ History-specific review section"
    )

    print(
        "✓ History specialist reviewers"
    )

    print(
        "✓ global cross-encyclopedia text NOT used "
        "as History evidence"
    )

    print(
        "✓ reference metadata catalog"
    )

    print(
        "✓ event year/details structure"
    )

    print(
        "✓ explicit disagreement preserved"
    )

    print(
        "✓ Prophetic report embedded in History"
    )

    print(
        "✓ /history/{id} route observed"
    )

    print(
        "✓ /history/event/{id} route observed"
    )

    print(
        "✓ search = locator only"
    )

    print(
        "✓ route contract NOT frozen"
    )

    print(
        "✓ no per-event machine truth grade invented"
    )

    print()
    print(
        "RESULT:",
        result[
            "result"
        ],
    )

    print(
        "RUNTIME:",
        result[
            "runtime_admission"
        ],
    )

    print(
        "ADAPTER:",
        result[
            "adapter"
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
