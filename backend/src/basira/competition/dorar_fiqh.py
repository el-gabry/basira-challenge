from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

from pydantic import BaseModel, Field

from basira.competition.fiqh_policy import Madhhab


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.parts: list[str] = []

        self.skip_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:
        if tag in {
            "script",
            "style",
            "noscript",
        }:
            self.skip_depth += 1

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag
            in {
                "script",
                "style",
                "noscript",
            }
            and self.skip_depth
        ):
            self.skip_depth -= 1

    def handle_data(
        self,
        data: str,
    ) -> None:
        if not self.skip_depth:
            self.parts.append(
                data
            )


def clean_text(
    value: str,
) -> str:

    value = unescape(value)

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def html_to_text(
    html: str,
) -> str:

    parser = _TextExtractor()
    parser.feed(html)

    return clean_text(
        " ".join(
            parser.parts
        )
    )


MADHHAB_TERMS: dict[
    Madhhab,
    tuple[str, ...],
] = {
    Madhhab.HANAFI: (
        "الحنفية",
        "الحنفي",
        "مذهب الحنفية",
    ),

    Madhhab.MALIKI: (
        "المالكية",
        "المالكي",
        "مذهب المالكية",
    ),

    Madhhab.SHAFII: (
        "الشافعية",
        "الشافعي",
        "مذهب الشافعية",
    ),

    Madhhab.HANBALI: (
        "الحنابلة",
        "الحنبلي",
        "مذهب الحنابلة",
    ),
}


class DorarFiqhPosition(BaseModel):
    ordinal: int

    text: str

    madhhabs: tuple[
        Madhhab,
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


class DorarFiqhArticle(BaseModel):
    source_id: str

    canonical_url: str

    article_title: str | None

    full_text: str

    explicit_disagreement: bool

    explicit_consensus_language: bool

    positions: tuple[
        DorarFiqhPosition,
        ...
    ] = Field(
        default_factory=tuple
    )


def _normalize_arabic_match_text(
    value: str,
) -> str:
    """
    Normalize Arabic only for structural matching.

    The original evidence text is NEVER modified.
    """

    value = re.sub(
        r"[\u0610-\u061a"
        r"\u064b-\u065f"
        r"\u0670"
        r"\u06d6-\u06ed]",
        "",
        value,
    )

    value = value.replace(
        "ـ",
        "",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def detect_madhhabs(
    text: str,
) -> tuple[Madhhab, ...]:

    normalized_text = (
        _normalize_arabic_match_text(
            text
        )
    )

    found = []

    for madhhab, terms in (
        MADHHAB_TERMS.items()
    ):
        normalized_terms = (
            _normalize_arabic_match_text(
                term
            )
            for term in terms
        )

        if any(
            term in normalized_text
            for term in normalized_terms
        ):
            found.append(
                madhhab
            )

    return tuple(found)


def extract_citations(
    text: str,
) -> tuple[str, ...]:
    """
    Preserve Dorar-style book/reference strings.

    Examples:
    ((المجموع)) للنووي (2/43)
    ((المغني)) لابن قدامة (1/134)

    This is intentionally extraction, not authority inference.
    """

    patterns = [
        r"\(\([^)]+\)\)"
        r"(?:\s+ل[^،.]{1,80})?"
        r"\s*\([^)]{1,40}\)",

        r"\(\([^)]+\)\)"
        r"\s*\([^)]{1,40}\)",
    ]

    matches: list[str] = []

    for pattern in patterns:
        for match in re.findall(
            pattern,
            text,
        ):
            cleaned = clean_text(
                match
            )

            if (
                cleaned
                and cleaned not in matches
            ):
                matches.append(
                    cleaned
                )

    return tuple(matches)


_ARABIC_DIACRITICS_PATTERN = (
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]*"
)


def _arabic_token_pattern(
    token: str,
) -> str:
    """
    Match the same Arabic letters with arbitrary tashkeel
    between/after characters.

    Example:

    الأول
    الأوّل
    الأوَّل

    all represent the same position marker for our
    structural parsing purpose.
    """

    return "".join(
        re.escape(char)
        + _ARABIC_DIACRITICS_PATTERN
        for char in token
    )


def _position_pattern(
    ordinal_word: str,
) -> re.Pattern[str]:

    return re.compile(
        _arabic_token_pattern(
            "القول"
        )
        + r"\s+"
        + _arabic_token_pattern(
            ordinal_word
        )
    )


_POSITION_PATTERNS = (
    (
        _position_pattern("الأول"),
        1,
    ),
    (
        _position_pattern("الثاني"),
        2,
    ),
    (
        _position_pattern("الثالث"),
        3,
    ),
    (
        _position_pattern("الرابع"),
        4,
    ),
)


def _position_boundaries(
    text: str,
) -> list[tuple[int, int]]:

    found: list[
        tuple[int, int]
    ] = []

    for pattern, ordinal in (
        _POSITION_PATTERNS
    ):
        for match in pattern.finditer(
            text
        ):
            found.append(
                (
                    match.start(),
                    ordinal,
                )
            )

    found.sort(
        key=lambda row: row[0]
    )

    return found


def extract_positions(
    text: str,
) -> tuple[
    DorarFiqhPosition,
    ...
]:
    boundaries = (
        _position_boundaries(
            text
        )
    )

    if not boundaries:
        return ()

    positions = []

    for index, (
        start,
        ordinal,
    ) in enumerate(
        boundaries
    ):
        if index + 1 < len(
            boundaries
        ):
            end = boundaries[
                index + 1
            ][0]
        else:
            # Stop before the later FAQ material where possible.
            faq = text.find(
                "المادة في سؤال وجواب",
                start,
            )

            end = (
                faq
                if faq >= 0
                else len(text)
            )

        segment = clean_text(
            text[start:end]
        )

        positions.append(
            DorarFiqhPosition(
                ordinal=ordinal,
                text=segment,
                madhhabs=(
                    detect_madhhabs(
                        segment
                    )
                ),
                citations=(
                    extract_citations(
                        segment
                    )
                ),
            )
        )

    return tuple(
        positions
    )


def extract_title(
    html: str,
) -> str | None:

    match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    if not match:
        return None

    title = re.sub(
        r"<[^>]+>",
        " ",
        match.group(1),
    )

    return clean_text(
        title
    )


def _article_heading_from_title(
    title: str | None,
) -> str:
    if not title:
        raise ValueError(
            "Dorar article title is missing"
        )

    suffixes = (
        " - الموسوعة الفقهية - الدرر السنية",
        " - الموسوعة الفقهية",
    )

    heading = title

    for suffix in suffixes:
        if heading.endswith(suffix):
            heading = heading[
                : -len(suffix)
            ].strip()
            break

    if not heading:
        raise ValueError(
            "Dorar article heading is empty"
        )

    return heading


class _CanonicalArticleBodyParser(HTMLParser):
    """
    Capture text only after the canonical article heading.

    This prevents navigation, methodology text and duplicated
    FAQ material from becoming primary Fiqh evidence.
    """

    HEADING_TAGS = {
        "h1",
        "h2",
        "h3",
        "h4",
    }

    SKIP_TAGS = {
        "script",
        "style",
        "noscript",
    }

    def __init__(
        self,
        *,
        target_heading: str,
    ) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.target_heading = (
            _normalize_article_heading(
                target_heading
            )
        )

        self.capture = False

        self.skip_depth = 0

        self.heading_tag: str | None = None

        self.heading_parts: list[str] = []

        self.body_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:

        tag = tag.lower()

        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return

        # Once the canonical body begins, all ordinary visible
        # content belongs to the body. We no longer search for
        # another heading with the same text.
        if self.capture:
            return

        if (
            self.skip_depth == 0
            and tag in self.HEADING_TAGS
            and self.heading_tag is None
        ):
            self.heading_tag = tag
            self.heading_parts = []

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        tag = tag.lower()

        if tag in self.SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return

        if (
            not self.capture
            and self.heading_tag is not None
            and tag == self.heading_tag
        ):
            heading = clean_text(
                " ".join(
                    self.heading_parts
                )
            )

            normalized = (
                _normalize_article_heading(
                    heading
                )
            )

            heading_matches = (
                normalized
                == self.target_heading
                or normalized.startswith(
                    self.target_heading
                    + " "
                )
            )

            if heading_matches:
                self.capture = True

                # Some canonical Dorar pages place
                # source-authored article text in the
                # same H1 after the canonical heading.
                #
                # Keep that visible source text rather
                # than rejecting the document merely
                # because the H1 is longer than <title>.
                if (
                    normalized
                    != self.target_heading
                ):
                    self.body_parts.append(
                        heading
                    )

            self.heading_tag = None
            self.heading_parts = []

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.skip_depth:
            return

        if (
            not self.capture
            and self.heading_tag is not None
        ):
            self.heading_parts.append(
                data
            )
            return

        if self.capture:
            self.body_parts.append(
                data
            )


def _normalize_article_heading(
    value: str,
) -> str:

    # Arabic tashkeel
    value = re.sub(
        r"[\u0610-\u061a"
        r"\u064b-\u065f"
        r"\u0670"
        r"\u06d6-\u06ed]",
        "",
        value,
    )

    # Tatweel
    value = value.replace(
        "ـ",
        "",
    )

    value = re.sub(
        r"[^\w\u0600-\u06ff]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


_DORAR_FIQH_BODY_PREFIX_NOISE = (
    "محتويات الصفحة",
    "انظر أيضا",
    "الرابط المختصر",
    "عرض الهوامش",
    "السابق",
    "التالي",
    "إضافة تعليق",
    "حفظ",
    "غلق",
    "انشر المادة",
    "نسخ الرابط المختصر",
)


def _trim_dorar_fiqh_body_prefix_noise(
    value: str,
) -> str:
    """
    Remove known Dorar presentation chrome from the
    beginning of an already-isolated canonical article body.

    This is source-boundary cleanup only.
    It never rewrites religious content.
    """

    text = clean_text(value)

    changed = True

    while changed:
        changed = False

        for marker in _DORAR_FIQH_BODY_PREFIX_NOISE:
            if text.startswith(marker):
                text = clean_text(
                    text[len(marker):]
                )
                changed = True

    return text


def extract_primary_article_text(
    *,
    html: str,
    article_title: str | None,
) -> str:
    """
    Isolate the real canonical Fiqh article body.

    Boundary:

    canonical structural heading
        ↓
    primary article text
        ↓
    STOP before "المادة في سؤال وجواب"
    """

    heading = _article_heading_from_title(
        article_title
    )

    parser = _CanonicalArticleBodyParser(
        target_heading=heading
    )

    parser.feed(
        html
    )

    if not parser.capture:
        raise ValueError(
            "canonical Dorar Fiqh structural "
            "heading was not found"
        )

    body = clean_text(
        " ".join(
            parser.body_parts
        )
    )

    body = _trim_dorar_fiqh_body_prefix_noise(
        body
    )

    faq_marker = (
        "المادة في سؤال وجواب"
    )

    faq_index = body.find(
        faq_marker
    )

    if faq_index >= 0:
        body = clean_text(
            body[:faq_index]
        )

    if not body:
        raise ValueError(
            "canonical Dorar Fiqh "
            "article body is empty"
        )

    return body


def parse_dorar_fiqh_article(
    *,
    html: str,
    canonical_url: str,
) -> DorarFiqhArticle:

    article_title = extract_title(
        html
    )

    text = extract_primary_article_text(
        html=html,
        article_title=article_title,
    )

    positions = extract_positions(
        text
    )

    explicit_disagreement = any(
        marker in text
        for marker in (
            "اختلف أهل العلم",
            "اختلف أهلُ العِلم",
            "على قولين",
            "على ثلاثة أقوال",
            "على أقوال",
        )
    )

    explicit_consensus = any(
        marker in text
        for marker in (
            "باتفاق المذاهب",
            "باتِّفاق المذاهب",
            "بإجماع",
            "أجمع",
            "الإجماع",
        )
    )

    source_id_match = re.search(
        r"/feqhia/(\d+)",
        canonical_url,
    )

    if not source_id_match:
        raise ValueError(
            "canonical Dorar Fiqh URL "
            "does not contain article id"
        )

    return DorarFiqhArticle(
        source_id=(
            "dorar:fiqh:"
            + source_id_match.group(1)
        ),
        canonical_url=canonical_url,
        article_title=article_title,

        # IMPORTANT:
        # This is now the canonical article body,
        # not navigation + FAQ + footer.
        full_text=text,

        explicit_disagreement=(
            explicit_disagreement
        ),
        explicit_consensus_language=(
            explicit_consensus
        ),
        positions=positions,
    )
