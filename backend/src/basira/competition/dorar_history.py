from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from basira.competition.history_policy import (
    HistoricalReportStatus,
    HistorySourceUseMode,
)


class DorarHistoryParseError(
    ValueError
):
    pass


class DorarHistoryRouteFamily(StrEnum):
    DIRECT_HISTORY_ID = (
        "direct_history_id"
    )

    HISTORY_EVENT_ID = (
        "history_event_id"
    )


class DorarHistoryStructuralAudit(BaseModel):
    canonical_root_count: int

    event_accordion_count: int

    event_container_count: int

    event_card_count: int

    title_node_count: int

    details_body_count: int

    hijri_field_count: int

    gregorian_field_count: int

    lunar_month_field_count: int

    details_heading_count: int

    structural_reference_candidate_count: int

    quran_structural_candidate_count: int

    hadith_structural_candidate_count: int

    provenance_violation_count: int = 0


class DorarHistoryEvent(BaseModel):
    source_id: str = "dorar-history-v1"

    source_family: str = "DORAR_HISTORY"

    source_use_mode: HistorySourceUseMode = (
        HistorySourceUseMode
        .CURATED_HISTORY_REFERENCE
    )

    canonical_url: str

    route_family: DorarHistoryRouteFamily

    event_id: int

    title: str

    hijri_year_text: str

    gregorian_year_text: str

    lunar_month_text: str | None = None

    details_text: str

    historical_report_status: (
        HistoricalReportStatus
    ) = HistoricalReportStatus.UNASSESSED

    disagreement_lexical_signal: bool = False

    prophetic_lexical_signal: bool = False

    lexical_signal_is_truth_grade: bool = False

    lexical_signal_is_hadith_authentication: bool = False

    hadith_matn_structurally_extractable: bool = False

    event_reference_channel_established: bool = False

    quran_typed_channel_established: bool = False

    hadith_typed_channel_established: bool = False

    promoted_event_reference_count: int = 0

    promoted_quran_witness_count: int = 0

    independent_hadith_authentication_count: int = 0

    per_event_machine_truth_grade_count: int = 0

    structural_audit: DorarHistoryStructuralAudit


def _clean(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        unescape(value),
    ).strip()


_ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


def _norm(
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
    ).casefold()


@dataclass
class _Node:
    tag: str

    attrs: dict[
        str,
        str | None,
    ]

    parent: "_Node | None" = None

    content: list[
        str | "_Node"
    ] = field(
        default_factory=list
    )

    @property
    def children(
        self,
    ) -> list["_Node"]:

        return [
            value
            for value in self.content
            if isinstance(
                value,
                _Node,
            )
        ]

    @property
    def element_id(
        self,
    ) -> str | None:

        return self.attrs.get(
            "id"
        )

    @property
    def classes(
        self,
    ) -> tuple[str, ...]:

        return tuple(
            value
            for value in (
                self.attrs.get(
                    "class"
                )
                or ""
            ).split()
            if value
        )

    def full_text(
        self,
    ) -> str:

        values: list[str] = []

        for item in self.content:

            if isinstance(
                item,
                str,
            ):
                values.append(
                    item
                )

            else:
                text = item.full_text()

                if text:
                    values.append(
                        text
                    )

        return _clean(
            " ".join(
                values
            )
        )

    def descendants(
        self,
    ):

        for child in self.children:
            yield child
            yield from child.descendants()


_VOID = {
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


class _TreeParser(
    HTMLParser
):

    def __init__(
        self,
    ) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.root = _Node(
            tag="document",
            attrs={},
        )

        self.stack = [
            self.root
        ]

        self.skip_depth = 0

        self.canonical_href: (
            str | None
        ) = None

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:

        tag = tag.lower()

        attrs_dict = dict(
            attrs
        )

        if self.skip_depth:

            if tag in {
                "script",
                "style",
                "noscript",
            }:
                self.skip_depth += 1

            return

        if tag in {
            "script",
            "style",
            "noscript",
        }:
            self.skip_depth = 1
            return

        if tag == "link":

            rel = (
                attrs_dict.get(
                    "rel"
                )
                or ""
            ).lower()

            if (
                "canonical"
                in rel.split()
            ):

                href = attrs_dict.get(
                    "href"
                )

                if href:
                    self.canonical_href = href

        parent = self.stack[-1]

        node = _Node(
            tag=tag,
            attrs=attrs_dict,
            parent=parent,
        )

        parent.content.append(
            node
        )

        if tag not in _VOID:
            self.stack.append(
                node
            )

    def handle_startendtag(
        self,
        tag: str,
        attrs,
    ) -> None:

        if self.skip_depth:
            return

        parent = self.stack[-1]

        parent.content.append(
            _Node(
                tag=tag.lower(),
                attrs=dict(
                    attrs
                ),
                parent=parent,
            )
        )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        tag = tag.lower()

        if self.skip_depth:

            if tag in {
                "script",
                "style",
                "noscript",
            }:
                self.skip_depth -= 1

            return

        for index in range(
            len(self.stack) - 1,
            0,
            -1,
        ):

            if (
                self.stack[
                    index
                ].tag
                == tag
            ):
                del self.stack[
                    index:
                ]

                return

    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.skip_depth:
            return

        value = _clean(
            data
        )

        if value:

            self.stack[
                -1
            ].content.append(
                value
            )


def _has_classes(
    node: _Node,
    required: tuple[
        str,
        ...
    ],
) -> bool:

    classes = set(
        node.classes
    )

    return all(
        value in classes
        for value in required
    )


def _direct(
    node: _Node,
    *,
    tag: str | None = None,
    element_id: str | None = None,
    classes: tuple[
        str,
        ...
    ] = (),
) -> list[_Node]:

    result = []

    for child in node.children:

        if (
            tag is not None
            and child.tag
            != tag
        ):
            continue

        if (
            element_id is not None
            and child.element_id
            != element_id
        ):
            continue

        if not _has_classes(
            child,
            classes,
        ):
            continue

        result.append(
            child
        )

    return result


def _descendants(
    node: _Node,
    *,
    tag: str | None = None,
) -> list[_Node]:

    result = []

    for candidate in node.descendants():

        if (
            tag is None
            or candidate.tag
            == tag
        ):
            result.append(
                candidate
            )

    return result


def _exactly_one(
    values: list[_Node],
    *,
    label: str,
) -> _Node:

    if len(values) != 1:

        raise DorarHistoryParseError(
            f"expected exactly one "
            f"{label}; got "
            f"{len(values)}"
        )

    return values[0]


def _route(
    url: str,
) -> tuple[
    DorarHistoryRouteFamily,
    int,
]:

    parsed = urlsplit(
        url
    )

    if parsed.scheme != "https":
        raise DorarHistoryParseError(
            "https_required"
        )

    if parsed.hostname != "dorar.net":
        raise DorarHistoryParseError(
            "exact_dorar_host_required"
        )

    if (
        parsed.port is not None
        or parsed.username
        or parsed.password
    ):
        raise DorarHistoryParseError(
            "noncanonical_authority"
        )

    if parsed.query:
        raise DorarHistoryParseError(
            "query_not_allowed"
        )

    if parsed.fragment:
        raise DorarHistoryParseError(
            "fragment_not_allowed"
        )

    direct = re.fullmatch(
        r"/history/([1-9][0-9]*)",
        parsed.path,
    )

    if direct:

        return (
            DorarHistoryRouteFamily
            .DIRECT_HISTORY_ID,
            int(
                direct.group(1)
            ),
        )

    event = re.fullmatch(
        r"/history/event/([1-9][0-9]*)",
        parsed.path,
    )

    if event:

        return (
            DorarHistoryRouteFamily
            .HISTORY_EVENT_ID,
            int(
                event.group(1)
            ),
        )

    raise DorarHistoryParseError(
        "noncanonical_history_event_route"
    )


def _labeled_strong(
    body: _Node,
    *,
    label: str,
    required: bool,
) -> tuple[
    str | None,
    int,
]:

    normalized_label = _norm(
        label
    )

    matches = []

    for child in body.children:

        if child.tag != "strong":
            continue

        text = child.full_text()

        normalized = _norm(
            text
        )

        if normalized.startswith(
            normalized_label
        ):
            matches.append(
                child
            )

    if required and len(matches) != 1:

        raise DorarHistoryParseError(
            f"expected exactly one "
            f"{label} field; got "
            f"{len(matches)}"
        )

    if not required and len(matches) > 1:

        raise DorarHistoryParseError(
            f"expected at most one "
            f"{label} field; got "
            f"{len(matches)}"
        )

    if not matches:

        return (
            None,
            0,
        )

    text = matches[
        0
    ].full_text()

    pieces = re.split(
        r"\s*[:：]\s*",
        text,
        maxsplit=1,
    )

    if len(pieces) != 2:

        raise DorarHistoryParseError(
            f"{label} value missing"
        )

    value = _clean(
        pieces[1]
    )

    if not value:

        raise DorarHistoryParseError(
            f"{label} value empty"
        )

    return (
        value,
        1,
    )


def _details_heading(
    body: _Node,
) -> tuple[
    _Node,
    int,
]:

    matches = []

    target = _norm(
        "تفاصيل الحدث"
    )

    for child in body.children:

        if child.tag != "h6":
            continue

        value = _norm(
            child.full_text()
        ).rstrip(
            ":："
        ).strip()

        if value == target:

            matches.append(
                child
            )

    return (
        _exactly_one(
            matches,
            label=(
                "event details heading"
            ),
        ),
        len(
            matches
        ),
    )


def _text_after_child(
    parent: _Node,
    child: _Node,
) -> str:

    seen = False

    parts: list[str] = []

    for item in parent.content:

        if (
            isinstance(
                item,
                _Node,
            )
            and item is child
        ):
            seen = True
            continue

        if not seen:
            continue

        if isinstance(
            item,
            str,
        ):
            value = item

        else:
            value = item.full_text()

        if value:
            parts.append(
                value
            )

    return _clean(
        " ".join(
            parts
        )
    )


def _structural_reference_candidates(
    event_card: _Node,
) -> int:

    count = 0

    for node in event_card.descendants():

        href = (
            node.attrs.get(
                "href"
            )
            or ""
        ).casefold()

        token_string = " ".join(
            (
                node.element_id
                or "",
                *node.classes,
            )
        ).casefold()

        if (
            "/history/refs"
            in href
            or any(
                token in token_string
                for token in (
                    "citation",
                    "footnote",
                    "source-note",
                    "reference-note",
                )
            )
        ):
            count += 1

    return count


def _quran_structural_candidates(
    event_card: _Node,
) -> int:

    count = 0

    for node in event_card.descendants():

        href = (
            node.attrs.get(
                "href"
            )
            or ""
        ).casefold()

        tokens = {
            value.casefold()
            for value in node.classes
        }

        if (
            any(
                any(
                    marker in token
                    for marker in (
                        "quran",
                        "ayah",
                        "aaya",
                        "sora",
                    )
                )
                for token in tokens
            )
            or "/quran"
            in href
            or "/tafseer/"
            in href
        ):
            count += 1

    return count


def _hadith_structural_candidates(
    event_card: _Node,
) -> int:

    count = 0

    for node in event_card.descendants():

        href = (
            node.attrs.get(
                "href"
            )
            or ""
        ).casefold()

        tokens = " ".join(
            node.classes
        ).casefold()

        if (
            "hadith"
            in tokens
            or "hadeeth"
            in tokens
            or "/hadith"
            in href
        ):
            count += 1

    return count


def parse_dorar_history_event(
    *,
    html: str,
    canonical_url: str,
) -> DorarHistoryEvent:

    route_family, event_id = (
        _route(
            canonical_url
        )
    )

    parser = _TreeParser()

    parser.feed(
        html
    )

    if (
        parser.canonical_href
        != canonical_url
    ):
        raise DorarHistoryParseError(
            "canonical_link_mismatch"
        )

    all_nodes = list(
        parser.root.descendants()
    )

    roots = [
        node
        for node in all_nodes
        if (
            node.tag == "div"
            and node.element_id
            == "cntnt"
            and _has_classes(
                node,
                (
                    "card-body",
                ),
            )
        )
    ]

    root = _exactly_one(
        roots,
        label=(
            "#cntnt.card-body root"
        ),
    )

    accordions = _direct(
        root,
        tag="div",
        element_id="accordionEx",
        classes=(
            "accordion",
            "md-accordion",
            "dorar_custom_accordion",
            "amiri_custom_content",
        ),
    )

    accordion = _exactly_one(
        accordions,
        label=(
            "canonical History accordion"
        ),
    )

    # --------------------------------------------------------
    # EVENT-CONTAINER UNIQUENESS
    #
    # The canonical structure has exactly one event-container
    # below the History accordion, and that container must be a
    # direct child.
    #
    # Counting only direct children is insufficient: an
    # adversarial or drifted DOM could hide another nested
    # event-container inside the canonical one and create
    # ambiguous provenance while still satisfying the direct
    # child count.
    #
    # Therefore:
    #
    # EXACTLY ONE event-container in the entire canonical
    # accordion subtree
    #
    # AND
    #
    # that one container must be direct.
    # --------------------------------------------------------

    all_event_containers = [
        node
        for node in accordion.descendants()
        if (
            node.tag == "div"
            and _has_classes(
                node,
                (
                    "event-container",
                ),
            )
        )
    ]

    container = _exactly_one(
        all_event_containers,
        label=(
            "event-container"
        ),
    )

    if container.parent is not accordion:
        raise DorarHistoryParseError(
            "event-container must be direct child "
            "of canonical History accordion"
        )

    containers = [
        container
    ]

    cards = _direct(
        container,
        tag="div",
        classes=(
            "card",
            "scroll-pos",
            "z-depth-0",
            "mb-0",
        ),
    )

    card = _exactly_one(
        cards,
        label="event card",
    )

    expected_heading_id = (
        f"headingTwo{event_id}"
    )

    headers = _direct(
        card,
        tag="div",
        element_id=(
            expected_heading_id
        ),
        classes=(
            "card-header",
            "p-0",
        ),
    )

    header = _exactly_one(
        headers,
        label=(
            expected_heading_id
        ),
    )

    title_nodes = _descendants(
        header,
        tag="h6",
    )

    title_node = _exactly_one(
        title_nodes,
        label="event title h6",
    )

    title = title_node.full_text()

    if not title:
        raise DorarHistoryParseError(
            "event_title_missing"
        )

    expected_collapse_id = (
        f"collapseTwo{event_id}"
    )

    collapses = _direct(
        card,
        tag="div",
        element_id=(
            expected_collapse_id
        ),
        classes=(
            "show",
        ),
    )

    collapse = _exactly_one(
        collapses,
        label=(
            expected_collapse_id
        ),
    )

    bodies = _direct(
        collapse,
        tag="div",
        classes=(
            "card-body",
        ),
    )

    body = _exactly_one(
        bodies,
        label="event details body",
    )

    (
        hijri_year,
        hijri_count,
    ) = _labeled_strong(
        body,
        label="العام الهجري",
        required=True,
    )

    (
        gregorian_year,
        gregorian_count,
    ) = _labeled_strong(
        body,
        label="العام الميلادي",
        required=True,
    )

    (
        lunar_month,
        lunar_count,
    ) = _labeled_strong(
        body,
        label="الشهر القمري",
        required=False,
    )

    (
        details_heading,
        details_heading_count,
    ) = _details_heading(
        body
    )

    details_text = _text_after_child(
        body,
        details_heading,
    )

    if not details_text:

        raise DorarHistoryParseError(
            "event_details_missing"
        )

    normalized_details = _norm(
        details_text
    )

    disagreement_signal = any(
        marker
        in normalized_details
        for marker in (
            _norm("اختلف"),
            _norm("اتفق"),
            _norm("قيل"),
        )
    )

    prophetic_signal = any(
        marker
        in normalized_details
        for marker in (
            _norm("رسول الله"),
            _norm("النبي"),
            _norm("عن أنس"),
            _norm("عن أبي قتادة"),
        )
    )

    structural_refs = (
        _structural_reference_candidates(
            card
        )
    )

    quran_candidates = (
        _quran_structural_candidates(
            card
        )
    )

    hadith_candidates = (
        _hadith_structural_candidates(
            card
        )
    )

    return DorarHistoryEvent(
        canonical_url=canonical_url,
        route_family=route_family,
        event_id=event_id,
        title=title,
        hijri_year_text=(
            hijri_year
            or ""
        ),
        gregorian_year_text=(
            gregorian_year
            or ""
        ),
        lunar_month_text=(
            lunar_month
        ),
        details_text=details_text,
        disagreement_lexical_signal=(
            disagreement_signal
        ),
        prophetic_lexical_signal=(
            prophetic_signal
        ),
        structural_audit=(
            DorarHistoryStructuralAudit(
                canonical_root_count=(
                    len(
                        roots
                    )
                ),
                event_accordion_count=(
                    len(
                        accordions
                    )
                ),
                event_container_count=(
                    len(
                        containers
                    )
                ),
                event_card_count=(
                    len(
                        cards
                    )
                ),
                title_node_count=(
                    len(
                        title_nodes
                    )
                ),
                details_body_count=(
                    len(
                        bodies
                    )
                ),
                hijri_field_count=(
                    hijri_count
                ),
                gregorian_field_count=(
                    gregorian_count
                ),
                lunar_month_field_count=(
                    lunar_count
                ),
                details_heading_count=(
                    details_heading_count
                ),
                structural_reference_candidate_count=(
                    structural_refs
                ),
                quran_structural_candidate_count=(
                    quran_candidates
                ),
                hadith_structural_candidate_count=(
                    hadith_candidates
                ),
            )
        ),
    )
