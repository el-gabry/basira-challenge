from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
from urllib.parse import urljoin

from basira.competition.dorar_fiqh_english_admission import (
    DorarEnglishFiqhAdmission,
    DorarEnglishFiqhAdmissionError,
    DorarEnglishFiqhRuntimeGate,
    canonical_english_fiqh_url,
)
from basira.competition.dorar_fiqh_source import (
    DorarTransportProtocol,
)
from basira.competition.dorar_transport import (
    DorarFetchPurpose,
    DorarTransportError,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
    CompetitionSourceUnavailable,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)

INDEX_URL = "https://dorar.net/en/feqhia"


MADHHAB_TERMS = {
    "hanafi": (
        "hanafi",
        "hanafis",
        "hanafiyyah",
    ),
    "maliki": (
        "maliki",
        "malikis",
        "malikiyyah",
    ),
    "shafii": (
        "shafi`i",
        "shafi'i",
        "shafi‘i",
        "shafii",
        "shafiis",
        "shafis",
    ),
    "hanbali": (
        "hanbali",
        "hanbalis",
        "hanabilah",
    ),
}


QUERY_EQUIVALENTS = {
    "wudu": (
        "ablution",
    ),
    "wudhu": (
        "ablution",
    ),
    "invalidates": (
        "nullifies",
        "nullifier",
        "nullifiers",
    ),
    "invalidate": (
        "nullifies",
        "nullifier",
        "nullifiers",
    ),
    "invalidating": (
        "nullifies",
        "nullifier",
        "nullifiers",
    ),
    "break": (
        "nullifies",
        "nullifier",
        "nullifiers",
    ),
    "breaks": (
        "nullifies",
        "nullifier",
        "nullifiers",
    ),
}


STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "does",
        "do",
        "for",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "what",
        "when",
        "whether",
    }
)


GENERIC_FIQH_RELEVANCE_TERMS = frozenset(
    {
        "ablution",
        "wudu",
        "wudhu",
        "invalidate",
        "invalidates",
        "invalidating",
        "nullify",
        "nullifies",
        "nullifier",
        "nullifiers",
        "break",
        "breaks",
        "breaking",
        "ruling",
        "rule",
        "rulings",
    }
)


@dataclass(
    frozen=True,
    slots=True,
)
class EnglishFiqhPosition:
    ordinal: int

    text: str

    madhhabs: tuple[
        str,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class EnglishFiqhIssue:
    ordinal: int

    context: str

    full_text: str

    positions: tuple[
        EnglishFiqhPosition,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class EnglishFiqhPage:
    source_id: str

    canonical_url: str

    title: str

    full_text: str

    issues: tuple[
        EnglishFiqhIssue,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class EnglishFiqhDocument:
    canonical_url: str

    body: bytes

    response_sha256: str

    content_type: str | None


class _IndexParser(
    HTMLParser
):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self._href: str | None = None

        self._text: list[str] = []

        self.links: list[
            tuple[
                str,
                str,
            ]
        ] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[
                str,
                str | None,
            ]
        ],
    ) -> None:
        if tag.casefold() != "a":
            return

        href = None

        for name, value in attrs:
            if (
                name.casefold() == "href"
                and value
            ):
                href = value
                break

        self._href = href
        self._text = []

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag.casefold() != "a"
            or self._href is None
        ):
            return

        text = _flat_text(
            " ".join(self._text)
        )

        self.links.append(
            (
                self._href,
                text,
            )
        )

        self._href = None
        self._text = []


class _ArticleParser(
    HTMLParser
):
    """
    Capture visible text plus individual DIV blocks.

    We intentionally require a source-authored block
    containing both "The first:" and "The second:".
    """

    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.visible: list[str] = []

        self.title_parts: list[str] = []

        self._in_title = False

        self._skip = 0

        self._div_stack: list[
            list[str]
        ] = []

        # Track whether a DIV contains another DIV.
        # Only leaf DIVs may become structural
        # Fiqh issue containers. This prevents a
        # page wrapper from duplicating child issues.
        self._div_has_child: list[
            bool
        ] = []

        self.div_blocks: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[
                str,
                str | None,
            ]
        ],
    ) -> None:
        del attrs

        name = tag.casefold()

        if name in {
            "script",
            "style",
            "noscript",
        }:
            self._skip += 1
            return

        if self._skip:
            return

        if name == "title":
            self._in_title = True

        if name == "div":
            if self._div_has_child:
                self._div_has_child[-1] = True

            self._div_stack.append(
                []
            )

            self._div_has_child.append(
                False
            )

        if name in {
            "br",
            "div",
            "p",
            "li",
            "section",
        }:
            self._append("\n")

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        name = tag.casefold()

        if name in {
            "script",
            "style",
            "noscript",
        }:
            if self._skip:
                self._skip -= 1
            return

        if self._skip:
            return

        if name == "title":
            self._in_title = False

        if (
            name == "div"
            and self._div_stack
        ):
            block = _multiline_text(
                "".join(
                    self._div_stack.pop()
                )
            )

            had_child = (
                self._div_has_child.pop()
            )

            if (
                block
                and not had_child
            ):
                self.div_blocks.append(
                    block
                )

        if name in {
            "div",
            "p",
            "li",
            "section",
        }:
            self._append("\n")

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._skip:
            return

        if self._in_title:
            self.title_parts.append(data)

        self._append(data)

    def _append(
        self,
        value: str,
    ) -> None:
        self.visible.append(value)

        for buffer in self._div_stack:
            buffer.append(value)


def _flat_text(
    value: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _multiline_text(
    value: str,
) -> str:
    value = value.replace(
        "\xa0",
        " ",
    )

    value = re.sub(
        r"[ \t\r\f\v]+",
        " ",
        value,
    )

    value = re.sub(
        r" *\n *",
        "\n",
        value,
    )

    value = re.sub(
        r"\n{2,}",
        "\n",
        value,
    )

    return value.strip()


def _tokens(
    value: str,
    *,
    expand: bool = False,
) -> frozenset[str]:
    raw = {
        token
        for token in re.findall(
            r"[a-z0-9'`]+",
            value.casefold(),
        )
        if (
            len(token) >= 3
            and token not in STOPWORDS
        )
    }

    expanded = set(raw)

    # Minimal lexical normalization for retrieval
    # relevance only. Evidence text is never changed.
    #
    # This allows e.g. "part" to match "parts"
    # without semantic rewriting.
    for token in tuple(raw):
        if (
            len(token) > 4
            and token.endswith("s")
        ):
            expanded.add(
                token[:-1]
            )

    if expand:
        for token in tuple(raw):
            expanded.update(
                QUERY_EQUIVALENTS.get(
                    token,
                    (),
                )
            )

    return frozenset(expanded)


def _topic_tokens(
    query: str,
) -> frozenset[str]:
    """
    Extract discriminative topic terms only.

    Generic legal words such as "ablution" and
    "invalidates" may help rank after an issue is
    topically admitted, but may never admit an
    unrelated issue by themselves.
    """

    return frozenset(
        token
        for token in _tokens(
            query,
            expand=False,
        )
        if token
        not in GENERIC_FIQH_RELEVANCE_TERMS
    )


def _score(
    query: str,
    text: str,
) -> int:
    query_tokens = _tokens(
        query,
        expand=True,
    )

    target_tokens = _tokens(text)

    if not query_tokens:
        return 0

    overlap = (
        query_tokens
        & target_tokens
    )

    return len(overlap)


def _madhhabs(
    value: str,
) -> tuple[
    str,
    ...,
]:
    lowered = value.casefold()

    found: list[str] = []

    for madhhab, terms in (
        MADHHAB_TERMS.items()
    ):
        if any(
            term.casefold() in lowered
            for term in terms
        ):
            found.append(madhhab)

    return tuple(found)


def _issue_chunks(
    block: str,
) -> tuple[
    str,
    ...,
]:
    """
    Split a Dorar leaf DIV into source-authored
    Fiqh sub-issues.

    Dorar may place several numbered questions in
    one DIV, for example:

        1- A man touching his penis ...
        Scholars have differed ...
        The first: ...
        The second: ...

        2- A woman touching her private parts ...
        Scholars have differed ...
        The first: ...
        The second: ...

    The HTML DIV is therefore not necessarily the
    smallest religious evidence unit.
    """

    lines = tuple(
        line.strip()
        for line in block.splitlines()
        if line.strip()
    )

    if not lines:
        return ()

    scholar_indexes = tuple(
        index
        for index, line in enumerate(lines)
        if (
            "scholars have differed"
            in line.casefold()
        )
    )

    # Some simple Dorar blocks contain one
    # first/second structure without the standard
    # disagreement sentence. Preserve that proven
    # structural case only.
    if not scholar_indexes:
        lowered = block.casefold()

        if (
            lowered.count(
                "the first:"
            )
            == 1
            and lowered.count(
                "the second:"
            )
            == 1
        ):
            return (block,)

        return ()

    starts: list[int] = []

    for scholar_index in scholar_indexes:
        start_index = scholar_index

        # The source-authored local heading is
        # normally the immediately preceding line:
        #
        #   2- A woman touching her private parts:
        #   Scholars have differed ...
        #
        # Bring that heading into the issue context.
        if scholar_index > 0:
            previous = (
                lines[
                    scholar_index - 1
                ]
            )

            previous_lower = (
                previous.casefold()
            )

            if (
                "the first:"
                not in previous_lower
                and "the second:"
                not in previous_lower
            ):
                start_index = (
                    scholar_index - 1
                )

        starts.append(
            start_index
        )

    chunks: list[str] = []

    seen: set[str] = set()

    for offset, start_index in enumerate(
        starts
    ):
        end_index = (
            starts[offset + 1]
            if offset + 1 < len(starts)
            else len(lines)
        )

        chunk = _multiline_text(
            "\n".join(
                lines[
                    start_index:end_index
                ]
            )
        )

        lowered = chunk.casefold()

        if (
            lowered.count(
                "the first:"
            )
            != 1
            or lowered.count(
                "the second:"
            )
            != 1
        ):
            continue

        if chunk in seen:
            continue

        seen.add(chunk)
        chunks.append(chunk)

    return tuple(chunks)


def _extract_issues_from_block(
    *,
    block: str,
    start_ordinal: int,
) -> tuple[
    EnglishFiqhIssue,
    ...,
]:
    issues: list[
        EnglishFiqhIssue
    ] = []

    for chunk in _issue_chunks(
        block
    ):
        lowered = chunk.casefold()

        first = lowered.find(
            "the first:"
        )

        second = lowered.find(
            "the second:"
        )

        if (
            first == -1
            or second == -1
            or second <= first
        ):
            continue

        context = chunk[
            :first
        ].strip()

        first_text = chunk[
            first:second
        ].strip()

        second_text = chunk[
            second:
        ].strip()

        first_madhhabs = (
            _madhhabs(
                first_text
            )
        )

        second_madhhabs = (
            _madhhabs(
                second_text
            )
        )

        # Attribution remains mandatory.
        # Do not create unattributed positions.
        if (
            not first_madhhabs
            or not second_madhhabs
        ):
            continue

        issues.append(
            EnglishFiqhIssue(
                ordinal=(
                    start_ordinal
                    + len(issues)
                ),
                context=context,
                full_text=chunk,
                positions=(
                    EnglishFiqhPosition(
                        ordinal=1,
                        text=first_text,
                        madhhabs=(
                            first_madhhabs
                        ),
                    ),
                    EnglishFiqhPosition(
                        ordinal=2,
                        text=second_text,
                        madhhabs=(
                            second_madhhabs
                        ),
                    ),
                ),
            )
        )

    return tuple(issues)


def parse_english_fiqh_page(
    *,
    html: str,
    canonical_url: str,
    article_id: str,
) -> EnglishFiqhPage:
    parser = _ArticleParser()

    parser.feed(html)

    full_text = _multiline_text(
        "".join(parser.visible)
    )

    if not full_text:
        raise ValueError(
            "empty English Fiqh page"
        )

    issues: list[
        EnglishFiqhIssue
    ] = []

    seen: set[str] = set()

    for block in parser.div_blocks:
        if block in seen:
            continue

        seen.add(block)

        block_issues = (
            _extract_issues_from_block(
                block=block,
                start_ordinal=(
                    len(issues) + 1
                ),
            )
        )

        issues.extend(
            block_issues
        )

    if not issues:
        raise ValueError(
            "no source-authored English "
            "Fiqh disagreement blocks"
        )

    title = _flat_text(
        " ".join(
            parser.title_parts
        )
    )

    title = re.sub(
        r"^\s*Summary of Feqh\s*-\s*",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()

    return EnglishFiqhPage(
        source_id=(
            f"dorar:fiqh:en:{article_id}"
        ),
        canonical_url=canonical_url,
        title=(
            title
            or f"Dorar English Fiqh {article_id}"
        ),
        full_text=full_text,
        issues=tuple(issues),
    )


class DorarEnglishFiqhSourceClient:
    def __init__(
        self,
        *,
        transport: DorarTransportProtocol,
        max_candidates: int = 6,
    ) -> None:
        if max_candidates <= 0:
            raise ValueError(
                "max_candidates must be positive"
            )

        self.transport = transport

        self.max_candidates = (
            max_candidates
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> tuple[
        EnglishFiqhDocument,
        ...,
    ]:
        query = query.strip()

        if not query or limit <= 0:
            return ()

        discovery = self.transport.fetch(
            INDEX_URL,
            purpose=(
                DorarFetchPurpose.DISCOVERY
            ),
        )

        try:
            html = discovery.body.decode(
                "utf-8-sig",
                errors="strict",
            )
        except UnicodeDecodeError as exc:
            raise ValueError(
                "English Fiqh index "
                "is not UTF-8"
            ) from exc

        parser = _IndexParser()

        parser.feed(html)

        ranked: list[
            tuple[
                int,
                int,
                str,
            ]
        ] = []

        seen: set[str] = set()

        for href, title in parser.links:
            absolute = urljoin(
                discovery.final_url,
                href,
            )

            identity = (
                canonical_english_fiqh_url(
                    absolute
                )
            )

            if identity is None:
                continue

            canonical, article_id = (
                identity
            )

            if canonical in seen:
                continue

            seen.add(canonical)

            score = _score(
                query,
                title,
            )

            if score <= 0:
                continue

            ranked.append(
                (
                    score,
                    -int(article_id),
                    canonical,
                )
            )

        ranked.sort(
            reverse=True
        )

        fetch_count = min(
            len(ranked),
            max(
                limit,
                self.max_candidates,
            ),
        )

        documents: list[
            EnglishFiqhDocument
        ] = []

        for (
            _score_value,
            _tie,
            canonical,
        ) in ranked[:fetch_count]:
            response = self.transport.fetch(
                canonical,
                purpose=(
                    DorarFetchPurpose.EVIDENCE
                ),
            )

            body = response.body

            if not isinstance(
                body,
                bytes,
            ):
                body = str(body).encode(
                    "utf-8"
                )

            documents.append(
                EnglishFiqhDocument(
                    canonical_url=canonical,
                    body=body,
                    response_sha256=(
                        response
                        .response_sha256
                    ),
                    content_type=(
                        response.content_type
                    ),
                )
            )

        return tuple(documents)


def _stable_id(
    *parts: str,
) -> str:
    digest = sha256(
        "\x1f".join(parts).encode(
            "utf-8"
        )
    ).hexdigest()[:24]

    return (
        f"dorar-fiqh-en:{digest}"
    )


class DorarFiqhEnglishEvidenceAdapter:
    def __init__(
        self,
        *,
        client: DorarEnglishFiqhSourceClient,
        gate: DorarEnglishFiqhRuntimeGate,
    ) -> None:
        self.client = client

        self.gate = gate

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if (
            request.official_domain
            is not OfficialDomain.GENERAL_FIQH
        ):
            raise ValueError(
                "English Dorar Fiqh requires "
                "GENERAL_FIQH."
            )

        query = request.query.strip()

        if (
            not query
            or request.limit <= 0
        ):
            return ()

        try:
            documents = self.client.search(
                query,
                limit=request.limit,
            )
        except (
            DorarTransportError,
            ValueError,
        ) as exc:
            raise CompetitionSourceUnavailable(
                "dorar_fiqh_en"
            ) from exc

        candidates: list[
            tuple[
                int,
                EnglishFiqhPage,
                EnglishFiqhIssue,
                DorarEnglishFiqhAdmission,
            ]
        ] = []

        for document in documents:
            try:
                admission = self.gate.admit(
                    canonical_url=(
                        document
                        .canonical_url
                    ),
                    body=document.body,
                    response_sha256=(
                        document
                        .response_sha256
                    ),
                    content_type=(
                        document
                        .content_type
                    ),
                )

                html = (
                    document.body.decode(
                        "utf-8",
                        errors="strict",
                    )
                )

                page = parse_english_fiqh_page(
                    html=html,
                    canonical_url=(
                        admission.canonical_url
                    ),
                    article_id=(
                        admission.article_id
                    ),
                )

            except (
                UnicodeDecodeError,
                ValueError,
                DorarEnglishFiqhAdmissionError,
            ):
                # Candidate-local failure.
                continue

            for issue in page.issues:
                # ISSUE-FIRST relevance.
                #
                # The page title is broad ("Nullifiers of
                # Ablution") and must never cause every
                # issue on the page to tie.
                #
                # Source-authored local issue context is
                # the strongest signal. Position text is
                # supporting relevance only. The page
                # title contributes at most one point.
                topic_tokens = (
                    _topic_tokens(query)
                )

                context_tokens = _tokens(
                    issue.context,
                    expand=False,
                )

                topic_overlap = len(
                    topic_tokens
                    & context_tokens
                )

                # HARD TOPIC GATE:
                #
                # Generic words such as ablution,
                # nullifies, ruling, etc. may never
                # make an unrelated Fiqh issue
                # evidence for this claim.
                #
                # For:
                #   touching private part + wudu
                #
                # an issue about dry ablution/water
                # is therefore rejected even though
                # both contain "ablution".
                if (
                    topic_tokens
                    and topic_overlap == 0
                ):
                    continue

                context_score = _score(
                    query,
                    issue.context,
                )

                position_score = _score(
                    query,
                    " ".join(
                        position.text
                        for position
                        in issue.positions
                    ),
                )

                title_score = min(
                    _score(
                        query,
                        page.title,
                    ),
                    1,
                )

                score = (
                    (topic_overlap * 100)
                    + (context_score * 8)
                    + (position_score * 2)
                    + title_score
                )

                if score <= 0:
                    continue

                candidates.append(
                    (
                        score,
                        page,
                        issue,
                        admission,
                    )
                )

        if not candidates:
            return ()

        best = max(
            score
            for (
                score,
                _page,
                _issue,
                _admission,
            )
            in candidates
        )

        evidence: list[
            EvidenceNode
        ] = []

        seen: set[str] = set()

        for (
            score,
            page,
            issue,
            admission,
        ) in candidates:
            if score != best:
                continue

            conflict_group = (
                f"fiqh:{page.source_id}:"
                f"issue:{issue.ordinal}"
            )

            reference = page.title

            if issue.context:
                reference += (
                    " — "
                    + _flat_text(
                        issue.context
                    )[:180]
                )

            for position in issue.positions:
                if (
                    position.text
                    not in issue.full_text
                ):
                    continue

                for scope in (
                    position.madhhabs
                ):
                    evidence_id = (
                        _stable_id(
                            page.source_id,
                            str(
                                issue.ordinal
                            ),
                            str(
                                position.ordinal
                            ),
                            scope,
                            position.text,
                        )
                        + ":position"
                    )

                    if evidence_id in seen:
                        continue

                    seen.add(evidence_id)

                    evidence.append(
                        EvidenceNode(
                            evidence_id=(
                                evidence_id
                            ),
                            domain=(
                                EvidenceDomain
                                .FIQH
                            ),
                            text=(
                                position.text
                            ),
                            source_id=(
                                page.source_id
                            ),
                            source_version=(
                                admission
                                .response_sha256
                            ),
                            reference=(
                                reference
                            ),
                            source_url=(
                                page
                                .canonical_url
                            ),
                            work_id=(
                                "dorar-fiqh-en"
                            ),
                            work_title=(
                                page.title
                            ),
                            institution=(
                                admission
                                .provider
                            ),
                            publisher=(
                                admission
                                .provider
                            ),
                            topic=(
                                issue.context
                                or page.title
                            ),
                            claim_type=(
                                "fiqh_position"
                            ),
                            authority_scope=(
                                scope
                            ),
                            related_fiqh=(
                                page.source_id,
                            ),
                            conflict_group=(
                                conflict_group
                            ),
                            conflict_type=(
                                "fiqh_position"
                            ),
                        )
                    )

        return tuple(evidence)
