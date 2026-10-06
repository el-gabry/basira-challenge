from __future__ import annotations

import re
from enum import StrEnum
from html import unescape
from html.parser import HTMLParser
from typing import Literal

from pydantic import BaseModel, Field


class DorarAqeedahParseError(ValueError):
    pass


class AqeedahTextOrigin(StrEnum):
    TITLE = "title"

    EXPLANATION = "explanation"

    QURAN_CONTEXT = "quran_context"

    QURAN_REFERENCE = "quran_reference"

    SOURCE_NOTE = "source_note"


class AqeedahTextDestination(StrEnum):
    TITLE = "title"

    EXPLANATION = "explanation"

    QURAN_CONTEXT = "quran_context"

    QURAN_REFERENCE = "quran_reference"

    SOURCE_NOTE = "source_note"


class DorarAqeedahSourceNoteKind(StrEnum):
    HADITH_SOURCE_NOTE = (
        "hadith_source_note"
    )

    REPORTED_HADITH_GRADING = (
        "reported_hadith_grading"
    )

    BIBLIOGRAPHIC_REFERENCE = (
        "bibliographic_reference"
    )

    UNCLASSIFIED_SOURCE_NOTE = (
        "unclassified_source_note"
    )


class DorarAqeedahQuranContext(BaseModel):
    text: str

    order: int

    # Quran displayed in Aqeedah is context only.
    canonical_quran_witness: Literal[
        False
    ] = False


class DorarAqeedahQuranReference(BaseModel):
    text: str

    order: int

    href: str | None = None

    # We deliberately do not force pairing with a Quran
    # context because the real observed page has 5 contexts
    # and 4 references.
    automatically_paired_to_context: Literal[
        False
    ] = False


class DorarAqeedahSourceNote(BaseModel):
    text: str

    order: int

    note_number: str | None = None

    kinds: tuple[
        DorarAqeedahSourceNoteKind,
        ...
    ]

    cited_titles: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    citation_locators: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    requires_hadith_foundation: bool = False

    # The adapter preserves what Dorar reports.
    # It never produces its own Hadith authenticity ruling.
    independent_authenticity_judgment: Literal[
        False
    ] = False

    # A bibliographic citation is not automatically promoted
    # into primary Aqeedah authority.
    aqeedah_authority_promotion: Literal[
        False
    ] = False


class AqeedahRoutingSummary(BaseModel):
    routed_text_node_count: int

    title_text_node_count: int

    explanation_text_node_count: int

    quran_context_text_node_count: int

    quran_reference_text_node_count: int

    source_note_text_node_count: int

    provenance_violation_count: int

    canonical_root_count: int

    direct_article_body_count: int


class DorarAqeedahPassage(BaseModel):
    canonical_url: str

    title: str

    explanation_text: str

    quran_contexts: tuple[
        DorarAqeedahQuranContext,
        ...
    ]

    quran_references: tuple[
        DorarAqeedahQuranReference,
        ...
    ]

    source_notes: tuple[
        DorarAqeedahSourceNote,
        ...
    ]

    routing: AqeedahRoutingSummary

    # The current observed DOM does not structurally delimit
    # Hadith matn from surrounding Aqeedah prose.
    #
    # We therefore do not fabricate a Hadith-record channel.
    hadith_matn_structurally_extractable: Literal[
        False
    ] = False


class _Frame:
    __slots__ = (
        "tag",
        "element_id",
        "classes",
    )

    def __init__(
        self,
        *,
        tag: str,
        element_id: str | None,
        classes: tuple[str, ...],
    ) -> None:

        self.tag = tag

        self.element_id = element_id

        self.classes = classes


class _SpecialCapture:
    __slots__ = (
        "origin",
        "depth",
        "parts",
        "href",
    )

    def __init__(
        self,
        *,
        origin: AqeedahTextOrigin,
        depth: int,
    ) -> None:

        self.origin = origin

        self.depth = depth

        self.parts: list[str] = []

        self.href: str | None = None


_ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


_VOID_TAGS = {
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


def _clean(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        unescape(
            value
        ),
    ).strip()


def _normalize_arabic(
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

    return _clean(
        value
    )


def _classify_source_note(
    text: str,
) -> tuple[
    DorarAqeedahSourceNoteKind,
    ...,
]:

    normalized = (
        _normalize_arabic(
            text
        )
    )

    result: list[
        DorarAqeedahSourceNoteKind
    ] = []

    if re.search(
        r"(?:اخرجه|رواه)\s+",
        normalized,
    ):
        result.append(
            DorarAqeedahSourceNoteKind
            .HADITH_SOURCE_NOTE
        )

    if re.search(
        r"(?:"
        r"صححه|"
        r"حسنه|"
        r"ضعفه|"
        r"صحح\s+اسناده|"
        r"حسن\s+اسناده|"
        r"ضعف\s+اسناده"
        r")",
        normalized,
    ):
        result.append(
            DorarAqeedahSourceNoteKind
            .REPORTED_HADITH_GRADING
        )

    if "ينظر" in normalized:
        result.append(
            DorarAqeedahSourceNoteKind
            .BIBLIOGRAPHIC_REFERENCE
        )

    if not result:
        result.append(
            DorarAqeedahSourceNoteKind
            .UNCLASSIFIED_SOURCE_NOTE
        )

    return tuple(
        result
    )


def _extract_note_number(
    text: str,
) -> str | None:

    match = re.match(
        r"\s*\[(\d{1,8})\]",
        text,
    )

    if not match:
        return None

    return match.group(1)


def _extract_cited_titles(
    text: str,
) -> tuple[str, ...]:

    values = []

    for value in re.findall(
        r"\(\(([^()]{1,250})\)\)",
        text,
    ):
        cleaned = _clean(
            value
        )

        if (
            cleaned
            and cleaned not in values
        ):
            values.append(
                cleaned
            )

    return tuple(
        values
    )


def _extract_locators(
    text: str,
) -> tuple[str, ...]:

    result = []

    patterns = (
        r"\(\s*ص\s*:\s*"
        r"\d+(?:\s*-\s*\d+)?\s*\)",

        r"\(\s*"
        r"\d+\s*/\s*"
        r"\d+(?:\s*-\s*\d+)?"
        r"\s*\)",
    )

    for pattern in patterns:

        for match in re.findall(
            pattern,
            text,
        ):
            value = _clean(
                match
            )

            if value not in result:
                result.append(
                    value
                )

    return tuple(
        result
    )


class _DorarAqeedahParser(
    HTMLParser
):
    def __init__(
        self,
        *,
        canonical_url: str,
    ) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.canonical_url = canonical_url

        self.stack: list[
            _Frame
        ] = []

        self.root_depth: int | None = None

        self.root_count = 0

        self.body_depth: int | None = None

        self.body_count = 0

        self.title_depth: int | None = None

        self.title_parts: list[str] = []

        self.explanation_parts: list[
            str
        ] = []

        self.quran_contexts: list[
            DorarAqeedahQuranContext
        ] = []

        self.quran_references: list[
            DorarAqeedahQuranReference
        ] = []

        self.source_notes: list[
            DorarAqeedahSourceNote
        ] = []

        self.special_stack: list[
            _SpecialCapture
        ] = []

        self.route_counts = {
            AqeedahTextOrigin.TITLE:
                0,

            AqeedahTextOrigin.EXPLANATION:
                0,

            AqeedahTextOrigin.QURAN_CONTEXT:
                0,

            AqeedahTextOrigin.QURAN_REFERENCE:
                0,

            AqeedahTextOrigin.SOURCE_NOTE:
                0,
        }

        self.route_destinations = {
            AqeedahTextDestination.TITLE:
                0,

            AqeedahTextDestination.EXPLANATION:
                0,

            AqeedahTextDestination.QURAN_CONTEXT:
                0,

            AqeedahTextDestination.QURAN_REFERENCE:
                0,

            AqeedahTextDestination.SOURCE_NOTE:
                0,
        }

        self.provenance_violation_count = 0

    def _inside_root(
        self,
    ) -> bool:

        if self.root_depth is None:
            return False

        return (
            len(self.stack)
            > self.root_depth
        )

    def _inside_body(
        self,
    ) -> bool:

        if self.body_depth is None:
            return False

        return (
            len(self.stack)
            > self.body_depth
        )

    def _ancestor_has_class(
        self,
        value: str,
    ) -> bool:

        return any(
            value in frame.classes
            for frame in self.stack
        )

    def _route_text(
        self,
        *,
        origin: AqeedahTextOrigin,
        value: str,
    ) -> None:

        value = _clean(
            value
        )

        if not value:
            return

        destination = (
            AqeedahTextDestination(
                origin.value
            )
        )

        self.route_counts[
            origin
        ] += 1

        self.route_destinations[
            destination
        ] += 1

        if origin.value != destination.value:
            self.provenance_violation_count += 1

        if (
            destination
            is AqeedahTextDestination.TITLE
        ):
            self.title_parts.append(
                value
            )

            return

        if (
            destination
            is AqeedahTextDestination.EXPLANATION
        ):
            self.explanation_parts.append(
                value
            )

            return

        if not self.special_stack:
            self.provenance_violation_count += 1
            return

        self.special_stack[
            -1
        ].parts.append(
            value
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

        classes = tuple(
            value
            for value in (
                attrs_dict.get(
                    "class"
                )
                or ""
            ).split()
            if value
        )

        element_id = attrs_dict.get(
            "id"
        )

        parent = (
            self.stack[
                -1
            ]
            if self.stack
            else None
        )

        frame = _Frame(
            tag=tag,
            element_id=element_id,
            classes=classes,
        )

        self.stack.append(
            frame
        )

        depth = (
            len(self.stack)
            - 1
        )

        # --------------------------------------------
        # Canonical root.
        # --------------------------------------------

        if (
            tag == "div"
            and element_id == "cntnt"
            and "card-body" in classes
        ):
            self.root_count += 1

            if self.root_depth is None:
                self.root_depth = depth

        # --------------------------------------------
        # Canonical title.
        # --------------------------------------------

        if (
            self.root_depth is not None
            and tag == "h1"
            and self._ancestor_has_class(
                "card-title"
            )
        ):
            self.title_depth = depth

        # --------------------------------------------
        # Canonical direct article body.
        # --------------------------------------------

        if (
            self.root_depth is not None
            and parent is not None
            and parent.element_id == "cntnt"
            and tag == "div"
            and "w-100" in classes
            and "mt-4" in classes
        ):
            self.body_count += 1

            if self.body_depth is None:
                self.body_depth = depth

        # --------------------------------------------
        # Typed source nodes.
        # --------------------------------------------

        if self.body_depth is not None:

            origin: (
                AqeedahTextOrigin | None
            ) = None

            if (
                tag == "span"
                and "aaya" in classes
            ):
                origin = (
                    AqeedahTextOrigin
                    .QURAN_CONTEXT
                )

            elif (
                tag == "span"
                and "sora" in classes
            ):
                origin = (
                    AqeedahTextOrigin
                    .QURAN_REFERENCE
                )

            elif (
                tag == "span"
                and "tip" in classes
            ):
                origin = (
                    AqeedahTextOrigin
                    .SOURCE_NOTE
                )

            if origin is not None:
                self.special_stack.append(
                    _SpecialCapture(
                        origin=origin,
                        depth=depth,
                    )
                )

        # Preserve nested Quran-reference href.
        if (
            tag == "a"
            and self.special_stack
            and (
                self.special_stack[
                    -1
                ].origin
                is AqeedahTextOrigin
                .QURAN_REFERENCE
            )
        ):
            href = attrs_dict.get(
                "href"
            )

            if href:
                self.special_stack[
                    -1
                ].href = href

        if tag in _VOID_TAGS:
            self._close_depth(
                depth
            )

    def handle_startendtag(
        self,
        tag: str,
        attrs,
    ) -> None:

        self.handle_starttag(
            tag,
            attrs,
        )

    def _finalize_special(
        self,
        capture: _SpecialCapture,
    ) -> None:

        text = _clean(
            " ".join(
                capture.parts
            )
        )

        if not text:
            return

        if (
            capture.origin
            is AqeedahTextOrigin
            .QURAN_CONTEXT
        ):
            self.quran_contexts.append(
                DorarAqeedahQuranContext(
                    text=text,
                    order=(
                        len(
                            self.quran_contexts
                        )
                        + 1
                    ),
                )
            )

            return

        if (
            capture.origin
            is AqeedahTextOrigin
            .QURAN_REFERENCE
        ):
            self.quran_references.append(
                DorarAqeedahQuranReference(
                    text=text,
                    order=(
                        len(
                            self.quran_references
                        )
                        + 1
                    ),
                    href=capture.href,
                )
            )

            return

        if (
            capture.origin
            is AqeedahTextOrigin
            .SOURCE_NOTE
        ):
            kinds = (
                _classify_source_note(
                    text
                )
            )

            requires_hadith = bool(
                {
                    DorarAqeedahSourceNoteKind
                    .HADITH_SOURCE_NOTE,

                    DorarAqeedahSourceNoteKind
                    .REPORTED_HADITH_GRADING,
                }
                & set(
                    kinds
                )
            )

            self.source_notes.append(
                DorarAqeedahSourceNote(
                    text=text,
                    order=(
                        len(
                            self.source_notes
                        )
                        + 1
                    ),
                    note_number=(
                        _extract_note_number(
                            text
                        )
                    ),
                    kinds=kinds,
                    cited_titles=(
                        _extract_cited_titles(
                            text
                        )
                    ),
                    citation_locators=(
                        _extract_locators(
                            text
                        )
                    ),
                    requires_hadith_foundation=(
                        requires_hadith
                    ),
                )
            )

            return

    def _close_depth(
        self,
        depth: int,
    ) -> None:

        while (
            self.special_stack
            and (
                self.special_stack[
                    -1
                ].depth
                >= depth
            )
        ):
            capture = (
                self.special_stack.pop()
            )

            self._finalize_special(
                capture
            )

        if (
            self.title_depth is not None
            and self.title_depth >= depth
        ):
            self.title_depth = None

        if (
            self.body_depth is not None
            and self.body_depth >= depth
        ):
            self.body_depth = None

        if (
            self.root_depth is not None
            and self.root_depth >= depth
        ):
            self.root_depth = None

        if (
            depth
            < len(
                self.stack
            )
        ):
            del self.stack[
                depth:
            ]

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        tag = tag.lower()

        for index in range(
            len(
                self.stack
            ) - 1,
            -1,
            -1,
        ):
            if (
                self.stack[
                    index
                ].tag
                == tag
            ):
                self._close_depth(
                    index
                )

                return

    def handle_data(
        self,
        data: str,
    ) -> None:

        value = _clean(
            data
        )

        if not value:
            return

        # Title is outside the canonical article body.
        if self.title_depth is not None:
            self._route_text(
                origin=(
                    AqeedahTextOrigin.TITLE
                ),
                value=value,
            )

            return

        if self.body_depth is None:
            return

        if self.special_stack:
            self._route_text(
                origin=(
                    self.special_stack[
                        -1
                    ].origin
                ),
                value=value,
            )

            return

        self._route_text(
            origin=(
                AqeedahTextOrigin.EXPLANATION
            ),
            value=value,
        )

    def build(
        self,
    ) -> DorarAqeedahPassage:

        if self.root_count != 1:
            raise DorarAqeedahParseError(
                "expected exactly one canonical "
                "#cntnt.card-body root; got "
                f"{self.root_count}"
            )

        if self.body_count != 1:
            raise DorarAqeedahParseError(
                "expected exactly one direct "
                "div.w-100.mt-4 article body; got "
                f"{self.body_count}"
            )

        title = _clean(
            " ".join(
                self.title_parts
            )
        )

        if not title:
            raise DorarAqeedahParseError(
                "canonical Aqeedah title missing"
            )

        explanation = _clean(
            " ".join(
                self.explanation_parts
            )
        )

        if not explanation:
            raise DorarAqeedahParseError(
                "canonical Aqeedah explanation missing"
            )

        total_nodes = sum(
            self.route_counts.values()
        )

        return DorarAqeedahPassage(
            canonical_url=self.canonical_url,
            title=title,
            explanation_text=explanation,
            quran_contexts=tuple(
                self.quran_contexts
            ),
            quran_references=tuple(
                self.quran_references
            ),
            source_notes=tuple(
                self.source_notes
            ),
            routing=(
                AqeedahRoutingSummary(
                    routed_text_node_count=(
                        total_nodes
                    ),
                    title_text_node_count=(
                        self.route_counts[
                            AqeedahTextOrigin
                            .TITLE
                        ]
                    ),
                    explanation_text_node_count=(
                        self.route_counts[
                            AqeedahTextOrigin
                            .EXPLANATION
                        ]
                    ),
                    quran_context_text_node_count=(
                        self.route_counts[
                            AqeedahTextOrigin
                            .QURAN_CONTEXT
                        ]
                    ),
                    quran_reference_text_node_count=(
                        self.route_counts[
                            AqeedahTextOrigin
                            .QURAN_REFERENCE
                        ]
                    ),
                    source_note_text_node_count=(
                        self.route_counts[
                            AqeedahTextOrigin
                            .SOURCE_NOTE
                        ]
                    ),
                    provenance_violation_count=(
                        self.provenance_violation_count
                    ),
                    canonical_root_count=(
                        self.root_count
                    ),
                    direct_article_body_count=(
                        self.body_count
                    ),
                )
            ),
        )


def parse_dorar_aqeedah_passage(
    *,
    html: str,
    canonical_url: str,
) -> DorarAqeedahPassage:

    parser = _DorarAqeedahParser(
        canonical_url=canonical_url
    )

    parser.feed(
        html
    )

    parser.close()

    return parser.build()
