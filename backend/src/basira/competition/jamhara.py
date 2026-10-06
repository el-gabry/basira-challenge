from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

SOURCE_FAMILY = (
    "AL_JAMHARA_ISLAMIC_TERMINOLOGY"
)

BASE_URL = (
    "https://islamic-content.com"
)

TERMINOLOGY_SECTION_SOURCE = (
    "من موسوعة المصطلحات الإسلامية"
)

REFERRAL_SECTION_SOURCE = (
    "من معجم المصطلحات الشرعية"
)

SEMANTIC_FIELDS = (
    "canonical_arabic_term",
    "localized_term",
    "category",
    "definition",
    "linguistic_definition",
    "terminological_meaning",
    "short_explanation",
    "cross_reference",
)



def validate_jamhara_response_url(
    requested_url: str,
    final_url: str,
) -> None:
    """
    Fail closed if a live Jamhara request leaves the
    governed official HTTPS origin.

    Redirects inside the official origin are allowed.
    Redirects to another host or scheme are not.
    """

    requested = urlsplit(
        requested_url
    )

    final = urlsplit(
        final_url
    )

    if (
        requested.scheme != "https"
        or requested.hostname
        != "islamic-content.com"
    ):
        raise ValueError(
            "requested Jamhara URL is outside "
            "the governed official origin"
        )

    if (
        final.scheme != "https"
        or final.hostname
        != "islamic-content.com"
    ):
        raise ValueError(
            "Jamhara response left the governed "
            "official HTTPS origin"
        )

_HEADING_TO_FIELD = {
    "التعريف": "definition",
    "التعريف اللغوي": (
        "linguistic_definition"
    ),
    "المعنى الاصطلاحي": (
        "terminological_meaning"
    ),
    "الشرح المختصر": (
        "short_explanation"
    ),
}

_LANGUAGE_RE = re.compile(
    r"^[a-z]{2}$"
)

_TITLE_RE = re.compile(
    r"^معنى\s*:\s*"
    r"(.*?)"
    r"\s*-\s*"
    r"(.*?)"
    r"\s*-\s*"
    r"الجمهرة$"
)


def _clean_text(
    value: str,
) -> str:
    return " ".join(
        value.split()
    ).strip()


class _JamharaHTMLParser(
    HTMLParser
):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.title_parts: list[str] = []
        self.entries: list[
            dict[str, object]
        ] = []

        self._in_title = False

        self._entry_depth = 0
        self._entry_source_parts: list[
            str
        ] = []
        self._entry_text_parts: list[
            str
        ] = []

        self._in_h5 = False
        self._in_h2 = False

        self._heading_parts: list[
            str
        ] = []

        self._current_heading: (
            str | None
        ) = None

        self._section_parts: list[
            str
        ] = []

        self._sections: dict[
            str,
            str,
        ] = {}

    @staticmethod
    def _classes(
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> set[str]:
        for key, value in attrs:
            if (
                key == "class"
                and value
            ):
                return set(
                    value.split()
                )

        return set()

    def _flush_section(
        self,
    ) -> None:
        if not self._current_heading:
            self._section_parts = []
            return

        body = _clean_text(
            " ".join(
                self._section_parts
            )
        )

        if body:
            previous = self._sections.get(
                self._current_heading
            )

            if previous:
                body = _clean_text(
                    f"{previous} {body}"
                )

            self._sections[
                self._current_heading
            ] = body

        self._section_parts = []

    def _finish_entry(
        self,
    ) -> None:
        self._flush_section()

        source = _clean_text(
            " ".join(
                self._entry_source_parts
            )
        )

        text = _clean_text(
            " ".join(
                self._entry_text_parts
            )
        )

        self.entries.append(
            {
                "source": source,
                "text": text,
                "sections": dict(
                    self._sections
                ),
            }
        )

        self._entry_source_parts = []
        self._entry_text_parts = []
        self._heading_parts = []
        self._current_heading = None
        self._section_parts = []
        self._sections = {}
        self._in_h5 = False
        self._in_h2 = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        if tag == "title":
            self._in_title = True

        if (
            self._entry_depth == 0
            and tag == "div"
            and "entry-main-content"
            in self._classes(attrs)
        ):
            self._entry_depth = 1
            self._entry_source_parts = []
            self._entry_text_parts = []
            self._heading_parts = []
            self._current_heading = None
            self._section_parts = []
            self._sections = {}
            return

        if self._entry_depth == 0:
            return

        if tag == "div":
            self._entry_depth += 1

        if tag == "h5":
            self._in_h5 = True

        elif tag == "h2":
            self._flush_section()
            self._heading_parts = []
            self._in_h2 = True

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if tag == "title":
            self._in_title = False

        if self._entry_depth == 0:
            return

        if tag == "h5":
            self._in_h5 = False

        elif tag == "h2":
            heading = _clean_text(
                " ".join(
                    self._heading_parts
                )
            )

            self._current_heading = (
                heading or None
            )

            self._heading_parts = []
            self._section_parts = []
            self._in_h2 = False

        if tag == "div":
            self._entry_depth -= 1

            if self._entry_depth == 0:
                self._finish_entry()

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._in_title:
            self.title_parts.append(
                data
            )

        if self._entry_depth == 0:
            return

        self._entry_text_parts.append(
            data
        )

        if self._in_h5:
            self._entry_source_parts.append(
                data
            )

        elif self._in_h2:
            self._heading_parts.append(
                data
            )

        elif self._current_heading:
            self._section_parts.append(
                data
            )


def jamhara_source_url(
    word_id: int,
    language: str,
) -> str:
    if word_id <= 0:
        raise ValueError(
            "word_id must be positive"
        )

    if not _LANGUAGE_RE.fullmatch(
        language
    ):
        raise ValueError(
            "language must be a two-letter "
            "lowercase code"
        )

    return (
        f"{BASE_URL}/dictionary/"
        f"word/{word_id}/{language}"
    )


def _title_terms(
    title: str,
    *,
    language: str,
) -> tuple[
    str | None,
    str | None,
]:
    match = _TITLE_RE.fullmatch(
        _clean_text(title)
    )

    if not match:
        return (
            None,
            None,
        )

    primary = (
        _clean_text(
            match.group(1)
        )
        or None
    )

    secondary = (
        _clean_text(
            match.group(2)
        )
        or None
    )

    localized_term = primary

    canonical_arabic_term = (
        secondary
    )

    if (
        canonical_arabic_term is None
        and language == "ar"
    ):
        canonical_arabic_term = (
            localized_term
        )

    return (
        localized_term,
        canonical_arabic_term,
    )


def parse_jamhara_word_page(
    html: str,
    *,
    word_id: int,
    language: str,
) -> dict[str, object] | None:
    """
    Parse one Jamhara localized terminology view.

    A HTTP-success page is not automatically a
    usable localized terminology unit. Pages with
    identity only and no localized lexical or
    explanatory payload fail closed as unavailable.

    Jamhara terminology content never becomes
    cross-domain primary evidence here.
    """

    source_url = jamhara_source_url(
        word_id,
        language,
    )

    parser = _JamharaHTMLParser()
    parser.feed(html)
    parser.close()

    title = _clean_text(
        " ".join(
            parser.title_parts
        )
    )

    (
        localized_term,
        canonical_arabic_term,
    ) = _title_terms(
        title,
        language=language,
    )

    extracted: dict[
        str,
        str | None,
    ] = {
        "canonical_arabic_term": (
            canonical_arabic_term
        ),
        "localized_term": (
            localized_term
        ),
        "category": None,
        "definition": None,
        "linguistic_definition": None,
        "terminological_meaning": None,
        "short_explanation": None,
        "cross_reference": None,
    }

    section_sources: list[str] = []

    for entry in parser.entries:
        source = str(
            entry.get("source")
            or ""
        )

        if (
            source
            and source
            not in section_sources
        ):
            section_sources.append(
                source
            )

        sections = entry.get(
            "sections"
        )

        if (
            source
            == TERMINOLOGY_SECTION_SOURCE
            and isinstance(
                sections,
                dict,
            )
        ):
            for heading, field in (
                _HEADING_TO_FIELD.items()
            ):
                value = sections.get(
                    heading
                )

                if (
                    isinstance(
                        value,
                        str,
                    )
                    and value
                ):
                    extracted[field] = (
                        _clean_text(
                            value
                        )
                    )

        if source == REFERRAL_SECTION_SOURCE:
            text = _clean_text(
                str(
                    entry.get("text")
                    or ""
                )
            )

            for prefix in (
                "يُحيل هذا المصطلح",
                "يحيل هذا المصطلح",
            ):
                position = text.find(
                    prefix
                )

                if position >= 0:
                    extracted[
                        "cross_reference"
                    ] = text[position:]
                    break

    localized_payload = any(
        extracted[field]
        for field in (
            "localized_term",
            "definition",
            "linguistic_definition",
            "terminological_meaning",
            "short_explanation",
            "cross_reference",
        )
    )

    if not localized_payload:
        return None

    return {
        "word_id": word_id,
        "language": language,
        "source_url": source_url,
        **extracted,
        "provenance": {
            "page_title": (
                title or None
            ),
            "section_sources": (
                section_sources
            ),
        },
        "source_role": {
            "terminology_authority": True,
            "universal_primary_evidence": False,
            "cross_domain_primary_evidence": False,
        },
    }


def canonicalize_jamhara_units(
    units: list[
        dict[str, object]
    ],
) -> list[
    dict[str, object]
]:
    seen: set[
        tuple[int, str]
    ] = set()

    canonical = []

    for unit in units:
        word_id = unit.get(
            "word_id"
        )

        language = unit.get(
            "language"
        )

        if not isinstance(
            word_id,
            int,
        ):
            raise ValueError(
                "unit word_id must be int"
            )

        if not isinstance(
            language,
            str,
        ):
            raise ValueError(
                "unit language must be str"
            )

        key = (
            word_id,
            language,
        )

        if key in seen:
            raise ValueError(
                "duplicate Jamhara unit identity: "
                f"{key!r}"
            )

        seen.add(key)
        canonical.append(
            unit
        )

    return sorted(
        canonical,
        key=lambda item: (
            int(
                item["word_id"]
            ),
            str(
                item["language"]
            ),
        ),
    )
