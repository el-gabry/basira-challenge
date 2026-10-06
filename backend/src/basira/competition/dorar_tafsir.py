from __future__ import annotations

import re
from enum import StrEnum
from html import unescape
from html.parser import HTMLParser

from pydantic import BaseModel, Field


class DorarTafsirSectionKind(StrEnum):
    GENERAL_MEANING = "general_meaning"

    WORD_MEANING = "word_meaning"

    GRAMMAR = "grammar"

    TAFSIR_AYAT = "tafsir_ayat"

    EDUCATIONAL_BENEFITS = (
        "educational_benefits"
    )

    SCHOLARLY_BENEFITS = (
        "scholarly_benefits"
    )

    RHETORIC = "rhetoric"


class DorarReportedGradeCitation(BaseModel):
    citation_text: str

    explicit_grade_language: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


class DorarTafsirSection(BaseModel):
    section_kind: DorarTafsirSectionKind

    article_id: str | None

    heading: str

    explanation_text: str

    quran_contexts: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    quran_references: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    citations: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    narration_citations: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    reported_grade_citations: tuple[
        DorarReportedGradeCitation,
        ...
    ] = Field(
        default_factory=tuple
    )

    # Structural provenance metrics.
    #
    # These measure source-node routing, not lexical overlap.
    quran_context_text_node_count: int = 0

    quran_context_text_nodes_routed_to_explanation: int = 0


class DorarTafsirPassage(BaseModel):
    source_id: str

    canonical_url: str

    sections: tuple[
        DorarTafsirSection,
        ...
    ]


_ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


def clean_text(
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

    value = re.sub(
        r"[^\w\u0600-\u06ff]+",
        " ",
        value,
    )

    return clean_text(
        value
    )


_SECTION_HEADINGS = {
    normalize_arabic(
        "المعنى الإجمالي"
    ):
        DorarTafsirSectionKind
        .GENERAL_MEANING,

    normalize_arabic(
        "غريب الكلمات"
    ):
        DorarTafsirSectionKind
        .WORD_MEANING,

    normalize_arabic(
        "مشكل الإعراب"
    ):
        DorarTafsirSectionKind
        .GRAMMAR,

    normalize_arabic(
        "تفسير الآيات"
    ):
        DorarTafsirSectionKind
        .TAFSIR_AYAT,

    normalize_arabic(
        "الفوائد التربوية"
    ):
        DorarTafsirSectionKind
        .EDUCATIONAL_BENEFITS,

    normalize_arabic(
        "الفوائد العلمية واللطائف"
    ):
        DorarTafsirSectionKind
        .SCHOLARLY_BENEFITS,

    normalize_arabic(
        "بلاغة الآيات"
    ):
        DorarTafsirSectionKind
        .RHETORIC,
}


_NARRATION_SOURCE_PATTERNS = (
    re.compile(
        r"(?:رواه|أخرجه)",
        re.UNICODE,
    ),
)


_GRADE_PATTERNS: tuple[
    tuple[str, re.Pattern[str]],
    ...
] = (
    (
        "authenticated",
        re.compile(
            r"صح(?:حه|َّحه|حه)",
            re.UNICODE,
        ),
    ),
    (
        "graded_hasan",
        re.compile(
            r"حس(?:نه|َّنه|ن إسناد|َّن إسناد)",
            re.UNICODE,
        ),
    ),
    (
        "graded_weak",
        re.compile(
            r"ضع(?:فه|َّفه)",
            re.UNICODE,
        ),
    ),
    (
        "isnad_language",
        re.compile(
            r"إسناد(?:ه|ُه|َه|ِه)",
            re.UNICODE,
        ),
    ),
    (
        "rijal_sahih",
        re.compile(
            r"رجال(?:ه|ُه|َه|ِه)\s+رجال",
            re.UNICODE,
        ),
    ),
)


def _is_narration_citation(
    text: str,
) -> bool:

    return any(
        pattern.search(text)
        for pattern
        in _NARRATION_SOURCE_PATTERNS
    )


def _reported_grade_language(
    text: str,
) -> tuple[str, ...]:

    found = []

    for name, pattern in (
        _GRADE_PATTERNS
    ):
        if pattern.search(
            text
        ):
            found.append(
                name
            )

    return tuple(
        found
    )


class _ArticleBuffer:
    def __init__(
        self,
        *,
        article_id: str | None,
    ) -> None:

        self.article_id = article_id

        self.heading_parts: list[str] = []

        self.body_parts: list[str] = []

        self.quran_contexts: list[str] = []

        self.quran_references: list[str] = []

        self.citations: list[str] = []

        # Provenance accounting.
        #
        # Quran-context text nodes must be routed to the
        # Quran-context channel and never to explanation text.
        self.quran_context_text_node_count = 0

        self.quran_context_text_nodes_routed_to_explanation = 0

        self.heading_depth: int | None = None

        self.special_type: str | None = None

        self.special_depth: int | None = None

        self.special_parts: list[str] = []


_VOID_HTML_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class _DorarTafsirHTMLParser(
    HTMLParser
):
    """
    Parse only canonical content inside div#cntnt.

    Important:

    Article termination is based on the ARTICLE tag itself,
    not on global DOM depth.

    This matters because real Dorar pages contain many HTML
    void elements such as <br> that have no closing tag.
    """

    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.in_cntnt = False

        # Number of open DIVs beginning with div#cntnt.
        self.cntnt_div_depth = 0

        self.article: (
            _ArticleBuffer | None
        ) = None

        # Nested article is not expected, but tracking it
        # makes closure fail-safe rather than depth-based.
        self.article_nesting = 0

        self.heading_tag: str | None = None

        # Stack only for the currently captured special
        # span (.aaya / .sora / .tip).
        #
        # Void elements are deliberately excluded.
        self.special_stack: list[str] = []

        self.skip_depth = 0

        self.sections: list[
            DorarTafsirSection
        ] = []

    def _begin_special(
        self,
        special_type: str,
    ) -> None:

        assert self.article is not None

        self.article.special_type = (
            special_type
        )

        self.article.special_depth = None

        self.article.special_parts = []

        self.special_stack = [
            "span"
        ]

    def _finish_special(
        self,
    ) -> None:

        assert self.article is not None

        value = clean_text(
            " ".join(
                self.article.special_parts
            )
        )

        if value:

            if (
                self.article.special_type
                == "aaya"
            ):
                self.article.quran_contexts.append(
                    value
                )

            elif (
                self.article.special_type
                == "sora"
            ):
                self.article.quran_references.append(
                    value
                )

            elif (
                self.article.special_type
                == "tip"
            ):
                self.article.citations.append(
                    value
                )

        self.article.special_type = None

        self.article.special_depth = None

        self.article.special_parts = []

        self.special_stack = []

    def _close_special_tag(
        self,
        tag: str,
    ) -> bool:
        """
        Close a tag inside the currently captured special span.

        Returns True when this end tag was handled as part of
        special-span state.
        """

        if not self.special_stack:
            return False

        if tag not in self.special_stack:
            return False

        # HTML may not be perfectly nested. Close from the
        # matching tag outward rather than trusting a global
        # numeric depth.
        index = len(
            self.special_stack
        ) - 1

        while (
            index >= 0
            and self.special_stack[index]
            != tag
        ):
            index -= 1

        if index < 0:
            return False

        del self.special_stack[
            index:
        ]

        if not self.special_stack:
            self._finish_special()

        return True

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

        if self.skip_depth:
            return

        # ----------------------------------------------------
        # Locate canonical Dorar content root.
        # ----------------------------------------------------

        if not self.in_cntnt:

            if (
                tag == "div"
                and attrs_dict.get(
                    "id"
                ) == "cntnt"
            ):
                self.in_cntnt = True
                self.cntnt_div_depth = 1

            return

        # Every nested div below #cntnt contributes only to
        # #cntnt closure tracking.
        if tag == "div":
            self.cntnt_div_depth += 1

        # ----------------------------------------------------
        # Open canonical article.
        # ----------------------------------------------------

        if self.article is None:

            if tag == "article":

                self.article = (
                    _ArticleBuffer(
                        article_id=(
                            attrs_dict.get(
                                "id"
                            )
                        )
                    )
                )

                self.article_nesting = 1

            return

        # ----------------------------------------------------
        # Article already open.
        # ----------------------------------------------------

        if tag == "article":
            self.article_nesting += 1
            return

        # If we are inside a special span, preserve nested
        # elements such as:
        #
        # span.sora > a
        # span.tip  > a / span / strong
        #
        # but NEVER push void elements such as <br>.
        if (
            self.article.special_type
            is not None
        ):

            if tag not in _VOID_HTML_TAGS:
                self.special_stack.append(
                    tag
                )

            return

        if (
            tag == "h5"
            and self.heading_tag
            is None
        ):
            self.heading_tag = "h5"
            return

        classes = set(
            (
                attrs_dict.get(
                    "class",
                    ""
                )
            ).split()
        )

        if "aaya" in classes:
            self._begin_special(
                "aaya"
            )
            return

        if "sora" in classes:
            self._begin_special(
                "sora"
            )
            return

        if "tip" in classes:
            self._begin_special(
                "tip"
            )
            return

    def handle_startendtag(
        self,
        tag: str,
        attrs,
    ) -> None:
        """
        Explicit self-closing HTML.

        Void tags never affect structural state.
        """

        tag = tag.lower()

        if tag in _VOID_HTML_TAGS:
            return

        self.handle_starttag(
            tag,
            attrs,
        )

        self.handle_endtag(
            tag
        )

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

        if self.skip_depth:
            return

        # ----------------------------------------------------
        # Article-specific state.
        # ----------------------------------------------------

        if self.article is not None:

            if (
                self.article.special_type
                is not None
            ):
                if self._close_special_tag(
                    tag
                ):
                    return

            if (
                self.heading_tag
                == tag
            ):
                self.heading_tag = None
                return

            if tag == "article":

                self.article_nesting -= 1

                if self.article_nesting <= 0:
                    self._finish_article()

                    self.article_nesting = 0

                return

        # ----------------------------------------------------
        # Canonical content-root closure.
        # ----------------------------------------------------

        if (
            self.in_cntnt
            and tag == "div"
        ):
            self.cntnt_div_depth -= 1

            if self.cntnt_div_depth <= 0:
                self.in_cntnt = False
                self.cntnt_div_depth = 0

    def handle_data(
        self,
        data: str,
    ) -> None:

        if (
            self.skip_depth
            or self.article is None
        ):
            return

        value = clean_text(
            data
        )

        if not value:
            return

        if (
            self.article.special_type
            is not None
        ):
            if (
                self.article.special_type
                == "aaya"
            ):
                # This exact source data event originated
                # inside span.aaya.
                #
                # It is routed only to the Quran-context
                # buffer. The immediate return below is the
                # provenance boundary.
                self.article.quran_context_text_node_count += 1

            self.article.special_parts.append(
                value
            )

            return

        if self.heading_tag is not None:
            self.article.heading_parts.append(
                value
            )
            return

        self.article.body_parts.append(
            value
        )

    def _finish_article(
        self,
    ) -> None:

        assert self.article is not None

        heading = clean_text(
            " ".join(
                self.article.heading_parts
            )
        )

        normalized_heading = (
            normalize_arabic(
                heading
            )
        )

        section_kind = (
            _SECTION_HEADINGS.get(
                normalized_heading
            )
        )

        if section_kind is not None:

            body = clean_text(
                " ".join(
                    self.article.body_parts
                )
            )

            citations = tuple(
                dict.fromkeys(
                    self.article.citations
                )
            )

            narration_citations = tuple(
                citation
                for citation in citations
                if _is_narration_citation(
                    citation
                )
            )

            grade_citations = []

            for citation in citations:

                grade_language = (
                    _reported_grade_language(
                        citation
                    )
                )

                if grade_language:

                    grade_citations.append(
                        DorarReportedGradeCitation(
                            citation_text=citation,

                            explicit_grade_language=(
                                grade_language
                            ),
                        )
                    )

            self.sections.append(
                DorarTafsirSection(
                    section_kind=section_kind,

                    article_id=(
                        self.article.article_id
                    ),

                    heading=heading,

                    explanation_text=body,

                    quran_contexts=tuple(
                        dict.fromkeys(
                            self.article.quran_contexts
                        )
                    ),

                    quran_references=tuple(
                        dict.fromkeys(
                            self.article.quran_references
                        )
                    ),

                    citations=citations,

                    narration_citations=(
                        narration_citations
                    ),

                    reported_grade_citations=(
                        tuple(
                            grade_citations
                        )
                    ),

                    quran_context_text_node_count=(
                        self.article
                        .quran_context_text_node_count
                    ),

                    quran_context_text_nodes_routed_to_explanation=(
                        self.article
                        .quran_context_text_nodes_routed_to_explanation
                    ),
                )
            )

        self.article = None

        self.article_nesting = 0

        self.heading_tag = None

        self.special_stack = []


def parse_dorar_tafsir_passage(
    *,
    html: str,
    canonical_url: str,
) -> DorarTafsirPassage:

    source_match = re.search(
        r"/tafseer/(\d+)(?:/(\d+))?",
        canonical_url,
    )

    if not source_match:
        raise ValueError(
            "canonical Dorar Tafsir URL required"
        )

    parser = _DorarTafsirHTMLParser()

    parser.feed(
        html
    )

    if not parser.sections:
        raise ValueError(
            "no canonical Dorar Tafsir sections found"
        )

    kinds = [
        section.section_kind
        for section in parser.sections
    ]

    if len(kinds) != len(set(kinds)):
        raise ValueError(
            "duplicate canonical Tafsir sections"
        )

    suffix = (
        ":"
        + source_match.group(2)
        if source_match.group(2)
        else ""
    )

    return DorarTafsirPassage(
        source_id=(
            "dorar:tafseer:"
            + source_match.group(1)
            + suffix
        ),
        canonical_url=canonical_url,
        sections=tuple(
            parser.sections
        ),
    )
