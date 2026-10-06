from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import Any

from pydantic import BaseModel


class DorarHadithRecord(BaseModel):
    rank: int | None = None

    hadith_text: str

    narrator: str | None = None

    muhaddith: str | None = None

    source: str | None = None

    page_or_number: str | None = None

    verdict: str | None = None

    extra_fields: dict[str, str] = {}


class _BlockParser(HTMLParser):
    """
    Extract Dorar result blocks while tolerating imperfect HTML.
    """

    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.current_class: str | None = None
        self.current_parts: list[str] = []

        self.blocks: list[
            tuple[str, str]
        ] = []

        self.depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:

        if tag != "div":
            return

        attrs_dict = dict(attrs)

        css = (
            attrs_dict.get("class")
            or ""
        )

        classes = set(
            css.split()
        )

        if (
            self.current_class is None
            and (
                "hadith" in classes
                or "hadith-info" in classes
            )
        ):
            self.current_class = (
                "hadith"
                if "hadith" in classes
                else "hadith-info"
            )

            self.current_parts = []
            self.depth = 1
            return

        if self.current_class is not None:
            self.depth += 1

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        if (
            tag != "div"
            or self.current_class is None
        ):
            return

        self.depth -= 1

        if self.depth != 0:
            return

        text = _clean(
            " ".join(
                self.current_parts
            )
        )

        self.blocks.append(
            (
                self.current_class,
                text,
            )
        )

        self.current_class = None
        self.current_parts = []

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.current_class is not None:
            self.current_parts.append(
                data
            )


def _clean(
    value: str,
) -> str:

    value = unescape(
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


FIELD_LABELS = (
    "الراوي:",
    "المحدث:",
    "المصدر:",
    "الصفحة أو الرقم:",
    "خلاصة حكم المحدث:",
    "توضيح حكم المحدث:",
    "التخريج:",
)


def _parse_info(
    text: str,
) -> dict[str, str]:

    label_pattern = "|".join(
        re.escape(label)
        for label in FIELD_LABELS
    )

    matches = list(
        re.finditer(
            label_pattern,
            text,
        )
    )

    result: dict[str, str] = {}

    for index, match in enumerate(
        matches
    ):
        label = match.group(0)

        start = match.end()

        if index + 1 < len(matches):
            end = matches[
                index + 1
            ].start()
        else:
            end = len(text)

        value = _clean(
            text[start:end]
        )

        result[
            label.rstrip(":")
        ] = value

    return result


def _strip_rank(
    text: str,
) -> tuple[int | None, str]:

    match = re.match(
        r"^\s*(\d+)\s*[-–—]\s*(.*)$",
        text,
    )

    if not match:
        return None, text

    return (
        int(match.group(1)),
        _clean(match.group(2)),
    )


def parse_dorar_result_html(
    html: str,
) -> list[DorarHadithRecord]:

    parser = _BlockParser()
    parser.feed(html)

    records: list[
        DorarHadithRecord
    ] = []

    pending_hadith: tuple[
        int | None,
        str,
    ] | None = None

    for block_type, text in parser.blocks:

        if block_type == "hadith":
            rank, hadith_text = (
                _strip_rank(text)
            )

            pending_hadith = (
                rank,
                hadith_text,
            )

            continue

        if (
            block_type == "hadith-info"
            and pending_hadith is not None
        ):
            info = _parse_info(
                text
            )

            rank, hadith_text = (
                pending_hadith
            )

            known = {
                "الراوي",
                "المحدث",
                "المصدر",
                "الصفحة أو الرقم",
                "خلاصة حكم المحدث",
            }

            records.append(
                DorarHadithRecord(
                    rank=rank,
                    hadith_text=hadith_text,
                    narrator=info.get(
                        "الراوي"
                    ),
                    muhaddith=info.get(
                        "المحدث"
                    ),
                    source=info.get(
                        "المصدر"
                    ),
                    page_or_number=(
                        info.get(
                            "الصفحة أو الرقم"
                        )
                    ),
                    verdict=info.get(
                        "خلاصة حكم المحدث"
                    ),
                    extra_fields={
                        k: v
                        for k, v
                        in info.items()
                        if k not in known
                    },
                )
            )

            pending_hadith = None

    return records


def parse_dorar_api_payload(
    payload: dict[str, Any],
) -> list[DorarHadithRecord]:

    ahadith = payload.get(
        "ahadith"
    )

    if not isinstance(
        ahadith,
        dict,
    ):
        raise ValueError(
            "Dorar payload ahadith "
            "must be an object"
        )

    result = ahadith.get(
        "result"
    )

    if not isinstance(
        result,
        str,
    ):
        raise ValueError(
            "Dorar payload ahadith.result "
            "must be an HTML string"
        )

    return parse_dorar_result_html(
        result
    )



class _HadithSearchArticleParser(HTMLParser):
    """
    Extract the complete hadith text rendered inside Dorar
    HTML-search <article> elements.

    Dorar's readmore.js only collapses these articles visually;
    it does not fetch or synthesize the text.
    """

    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.in_article = False
        self.parts: list[str] = []
        self.articles: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs

        if (
            tag == "article"
            and not self.in_article
        ):
            self.in_article = True
            self.parts = []

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag != "article"
            or not self.in_article
        ):
            return

        value = _clean(
            " ".join(self.parts)
        )

        if value:
            self.articles.append(value)

        self.in_article = False
        self.parts = []

    def handle_data(
        self,
        data: str,
    ) -> None:
        if not self.in_article:
            return

        value = _clean(data)

        if value:
            self.parts.append(value)


def parse_dorar_hadith_search_articles(
    html: str,
) -> tuple[str, ...]:
    """
    Preserve every Dorar HTML-search article.

    Visible result numbers can repeat across page sections, so
    article position/rank must never be used as an API join key.
    """

    parser = _HadithSearchArticleParser()
    parser.feed(html)

    records: list[str] = []

    for article in parser.articles:
        _rank, hadith_text = _strip_rank(
            article
        )

        if not hadith_text:
            continue

        records.append(
            hadith_text
        )

    return tuple(records)


def parse_dorar_hadith_search_html(
    html: str,
) -> dict[int, str]:
    """
    Compatibility/debug view keyed by visible Dorar result rank.

    Do not use this mapping to associate API metadata with HTML
    matn: visible ranks may repeat across page sections.
    """

    parser = _HadithSearchArticleParser()
    parser.feed(html)

    records: dict[int, str] = {}

    for article in parser.articles:
        rank, hadith_text = _strip_rank(
            article
        )

        if (
            rank is None
            or not hadith_text
        ):
            continue

        records[rank] = hadith_text

    return records



def _hadith_match_key(value: str) -> str:
    import unicodedata

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    chars: list[str] = []

    for char in value:
        if unicodedata.category(char) == "Mn":
            continue

        if char in "إأآٱ":
            char = "ا"
        elif char == "ى":
            char = "ي"

        if (
            "\u0621" <= char <= "\u064a"
            or char.isdigit()
        ):
            chars.append(char)

    return "".join(chars)


def _hadith_source_text_is_explicitly_truncated(
    value: str,
) -> bool:
    compact = " ".join(value.split())

    markers = (
        "...",
        "…",
        ". .",
        "الحَديث",
        "الحديث...",
        "الحديث …",
    )

    return any(
        marker in compact
        for marker in markers
    )


def match_dorar_hadith_full_text(
    source_text: str,
    candidates: list[str] | tuple[str, ...],
) -> str | None:
    """
    Associate a Dorar API hadith record with Dorar HTML text
    only when the text itself proves the association.

    No rank/ordinal association is permitted.

    Rules:
    1. Explicitly truncated API snippets never hydrate.
    2. Exact normalized textual matches are accepted.
    3. A containment match is accepted only when all matching
       candidates reduce to one distinct normalized full text.
    4. Ambiguous matches fail closed.
    """

    if _hadith_source_text_is_explicitly_truncated(
        source_text
    ):
        return None

    source_key = _hadith_match_key(
        source_text
    )

    if not source_key:
        return None

    usable: list[tuple[str, str]] = []

    for candidate in candidates:
        candidate_key = _hadith_match_key(
            candidate
        )

        if not candidate_key:
            continue

        if _hadith_source_text_is_explicitly_truncated(
            candidate
        ):
            continue

        usable.append(
            (
                candidate,
                candidate_key,
            )
        )

    # Strongest proof: exact normalized text.
    exact = [
        candidate
        for candidate, candidate_key in usable
        if candidate_key == source_key
    ]

    if exact:
        # Exact duplicates are semantically the same matn.
        exact.sort(
            key=len,
            reverse=True,
        )
        return exact[0]

    # Second proof: source is a literal normalized portion of
    # exactly one distinct full matn.
    contained = [
        (
            candidate,
            candidate_key,
        )
        for candidate, candidate_key in usable
        if source_key in candidate_key
    ]

    if not contained:
        return None

    distinct_keys = {
        candidate_key
        for _, candidate_key in contained
    }

    if len(distinct_keys) != 1:
        return None

    contained.sort(
        key=lambda item: len(item[0]),
        reverse=True,
    )

    return contained[0][0]
