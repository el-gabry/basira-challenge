from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import (
    urlencode,
    urljoin,
    urlsplit,
)

from basira.competition.dorar_transport import (
    DorarFetchedResponse,
    DorarFetchPurpose,
    DorarTransportError,
)

DORAR_TAFSIR_SEARCH_URL = "https://dorar.net/site/search"

_CANONICAL_PATH = re.compile(r"^/tafseer/\d+/\d+/?$")


class DorarTafsirRetrievalError(RuntimeError):
    pass


class DorarTafsirPayloadError(DorarTafsirRetrievalError):
    pass


class DorarTafsirCoverageUnavailable(DorarTafsirPayloadError):
    """Canonical page has no extractable Quran coverage metadata."""


class DorarTransportProtocol(Protocol):
    def fetch(
        self,
        url: str,
        *,
        purpose: DorarFetchPurpose,
    ) -> DorarFetchedResponse: ...


class DorarTafsirGateProtocol(Protocol):
    def admit(
        self,
        *,
        html: str | bytes,
        canonical_url: str,
    ) -> object: ...


@dataclass(
    frozen=True,
    slots=True,
)
class DorarTafsirRetrievedPassage:
    canonical_url: str
    response_sha256: str

    # Admission result from the existing
    # DorarTafsirRuntimeGate.
    #
    # The exact religious/policy contract remains
    # owned by the existing Competition modules.
    admitted: object

    # Canonical Quran identity covered by this
    # Dorar passage. Separate from source locator.
    quran_references: tuple[str, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class DorarTafsirSearchResult:
    query: str

    request_url: str

    discovery_sha256: str

    discovered_urls: tuple[
        str,
        ...,
    ]

    passages: tuple[
        DorarTafsirRetrievedPassage,
        ...,
    ]


class _LinkCollector(HTMLParser):
    def __init__(
        self,
    ) -> None:
        super().__init__(convert_charrefs=True)

        self.hrefs: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:
        if tag.lower() != "a":
            return

        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)


def _clean_query(
    query: str,
) -> str:
    value = " ".join(query.split())

    if not value:
        raise ValueError("Tafsir query must be nonblank.")

    if len(value) > 1000:
        raise ValueError("Tafsir query is too long.")

    return value


def build_dorar_tafsir_search_url(
    query: str,
) -> str:
    """
    Use Dorar's current official global discovery
    search.

    Search results are discovery-only. The retriever
    still admits ONLY canonical Tafsir URLs matching
    /tafseer/<surah>/<passage>.
    """

    query = _clean_query(query)

    return (
        DORAR_TAFSIR_SEARCH_URL
        + "?"
        + urlencode(
            {
                "div": "2",
                "skeys": query,
            }
        )
    )


def _canonical_candidate(
    href: str,
    *,
    base_url: str,
) -> str | None:
    absolute = urljoin(
        base_url,
        href,
    )

    parsed = urlsplit(absolute)

    if parsed.scheme != "https":
        return None

    if parsed.hostname != "dorar.net":
        return None

    if parsed.username is not None:
        return None

    if parsed.password is not None:
        return None

    if parsed.query:
        return None

    if parsed.fragment:
        return None

    if not _CANONICAL_PATH.fullmatch(parsed.path):
        return None

    return "https://dorar.net" + parsed.path.rstrip("/")


def extract_canonical_tafsir_urls(
    html: str,
    *,
    base_url: str,
) -> tuple[
    str,
    ...,
]:
    parser = _LinkCollector()

    parser.feed(html)

    results: list[str] = []

    seen: set[str] = set()

    for href in parser.hrefs:
        candidate = _canonical_candidate(
            href,
            base_url=base_url,
        )

        if candidate is None or candidate in seen:
            continue

        seen.add(candidate)

        results.append(candidate)

    return tuple(results)


_ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)

_DORAR_TAFSIR_ROUTE = re.compile(
    r"^https://dorar\.net/"
    r"tafseer/(?P<surah>\d{1,3})/"
    r"(?P<passage>\d+)/?$"
)

_DORAR_QURAN_COVERAGE = re.compile(
    r"الآي(?:ة|ات)"
    r"\s*\(\s*"
    r"(?P<start>\d{1,3})"
    r"(?:\s*[-–—]\s*(?P<end>\d{1,3}))?"
    r"\s*\)"
)


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def extract_quran_references(
    *,
    html: str,
    canonical_url: str,
) -> tuple[str, ...]:
    """
    Extract Quran coverage from canonical Dorar
    structural metadata.

    The second /tafseer/<surah>/<id> component is a
    Dorar passage id and MUST NOT be treated as an
    ayah number.

    Parsing is deliberately tolerant of:
    - Arabic/European digits;
    - diacritics/tatweel;
    - bidi formatting marks;
    - nested heading markup.

    Multiple different ranges fail closed.
    """

    route = _DORAR_TAFSIR_ROUTE.fullmatch(canonical_url)

    if route is None:
        raise DorarTafsirPayloadError("invalid canonical Dorar Tafsir route")

    surah = int(route.group("surah"))

    class _CoverageCollector(HTMLParser):
        _CAPTURE_TAGS = frozenset(
            {
                "title",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
            }
        )

        def __init__(
            self,
        ) -> None:
            super().__init__(convert_charrefs=True)

            self.candidates: list[str] = []

            self._active_tag: str | None = None

            self._parts: list[str] = []

            self.all_text: list[str] = []

        def handle_starttag(
            self,
            tag: str,
            attrs,
        ) -> None:
            tag = tag.lower()

            if tag in self._CAPTURE_TAGS and self._active_tag is None:
                self._active_tag = tag
                self._parts = []

            if tag != "meta":
                return

            values = {
                str(key).lower(): str(value)
                for key, value in attrs
                if (key is not None and value is not None)
            }

            marker = (values.get("property") or values.get("name") or "").lower()

            content = values.get("content")

            if content and marker in {
                "og:title",
                "twitter:title",
            }:
                self.candidates.append(content)

        def handle_endtag(
            self,
            tag: str,
        ) -> None:
            tag = tag.lower()

            if self._active_tag is None or tag != self._active_tag:
                return

            value = " ".join(self._parts)

            if value:
                self.candidates.append(value)

            self._active_tag = None
            self._parts = []

        def handle_data(
            self,
            data: str,
        ) -> None:
            value = " ".join(data.split())

            if not value:
                return

            self.all_text.append(value)

            if self._active_tag is not None:
                self._parts.append(value)

    def normalize(
        value: str,
    ) -> str:
        value = unicodedata.normalize(
            "NFKD",
            value,
        ).translate(_ARABIC_DIGITS)

        cleaned = []

        for char in value:
            if char == "\u0640":
                # Arabic tatweel.
                continue

            category = unicodedata.category(char)

            if category in {
                "Mn",
                "Me",
                "Cf",
            }:
                # Diacritics + bidi/control
                # formatting.
                continue

            cleaned.append(char)

        return " ".join("".join(cleaned).split())

    coverage_pattern = re.compile(
        r"الاي(?:ة|ات)"
        r"[\s:：]*"
        r"(?:من\s*)?"
        r"[\(\[\{]?\s*"
        r"(?P<start>\d{1,3})"
        r"(?:"
        r"\s*(?:-|–|—|الى)\s*"
        r"(?P<end>\d{1,3})"
        r")?"
        r"\s*[\)\]\}]?"
    )

    def ranges_from(
        values,
    ) -> set[
        tuple[
            int,
            int,
        ]
    ]:
        ranges: set[
            tuple[
                int,
                int,
            ]
        ] = set()

        for raw in values:
            value = normalize(raw)

            for match in coverage_pattern.finditer(value):
                start = int(match.group("start"))

                end = int(match.group("end") or start)

                if start <= 0 or end < start or end > 286:
                    continue

                ranges.add(
                    (
                        start,
                        end,
                    )
                )

        return ranges

    collector = _CoverageCollector()

    collector.feed(html)

    # Prefer explicit document metadata:
    # title / h1-h6 / og:title.
    ranges = ranges_from(collector.candidates)

    # Safe fallback for markup variants where the
    # visible heading is fragmented unusually.
    if not ranges:
        ranges = ranges_from((" ".join(collector.all_text),))

    if not ranges:
        raise (
            DorarTafsirCoverageUnavailable(
                "canonical Dorar Tafsir page exposes no Quran coverage metadata"
            )
        )

    if len(ranges) != 1:
        raise DorarTafsirPayloadError(
            "canonical Dorar Tafsir page exposes conflicting Quran coverage ranges"
        )

    start_ayah, end_ayah = next(iter(ranges))

    return tuple(
        f"{surah}:{ayah}"
        for ayah in range(
            start_ayah,
            end_ayah + 1,
        )
    )


class DorarTafsirRetriever:
    """
    Question -> Dorar Tafsir discovery
             -> canonical passage URL
             -> governed HTTP transport
             -> existing runtime admission gate.

    Discovery does not grant authority.

    Only pages admitted by the existing
    DorarTafsirRuntimeGate leave this retriever.
    """

    def __init__(
        self,
        *,
        transport: DorarTransportProtocol,
        gate: DorarTafsirGateProtocol,
        max_candidates: int = 30,
    ) -> None:
        if max_candidates <= 0:
            raise ValueError("max_candidates must be positive.")

        self._transport = transport
        self._gate = gate
        self._max_candidates = max_candidates

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        required_quran_references: tuple[str, ...] = (),
    ) -> DorarTafsirSearchResult:
        if limit <= 0:
            raise ValueError("limit must be positive.")

        normalized = _clean_query(query)

        required = tuple(
            dict.fromkeys(
                value.strip() for value in required_quran_references if value.strip()
            )
        )

        request_url = build_dorar_tafsir_search_url(normalized)

        # Discovery transport is source-level.
        # Failure here must propagate fail closed.
        discovery = self._transport.fetch(
            request_url,
            purpose=(DorarFetchPurpose.DISCOVERY),
        )

        try:
            html = discovery.body.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DorarTafsirPayloadError(
                "Dorar Tafsir discovery response is not valid UTF-8."
            ) from exc

        discovered = extract_canonical_tafsir_urls(
            html,
            base_url=(discovery.final_url),
        )

        admitted: list[DorarTafsirRetrievedPassage] = []

        anchored = bool(required)

        candidate_budget = (
            min(
                self._max_candidates,
                3,
            )
            if anchored
            else self._max_candidates
        )

        candidate_failures: list[Exception] = []

        structurally_readable = False

        for canonical_url in discovered[:candidate_budget]:
            try:
                response = self._transport.fetch(
                    canonical_url,
                    purpose=(DorarFetchPurpose.EVIDENCE),
                )
            except DorarTransportError as exc:
                if not anchored:
                    raise

                candidate_failures.append(exc)
                continue

            # Authority admission MUST happen before
            # Quran coverage enrichment.
            #
            # Admission failure is NOT candidate noise:
            # it remains a fail-closed authority error.
            runtime_evidence = self._gate.admit(
                html=response.body,
                canonical_url=(canonical_url),
            )

            try:
                evidence_html = response.body.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                if not anchored:
                    raise DorarTafsirPayloadError(
                        "Canonical Dorar Tafsir response is not valid UTF-8."
                    ) from exc

                candidate_failures.append(exc)
                continue

            try:
                quran_references = extract_quran_references(
                    html=evidence_html,
                    canonical_url=(canonical_url),
                )
            except (
                DorarTafsirCoverageUnavailable,
                DorarTafsirPayloadError,
            ) as exc:
                if not anchored:
                    if isinstance(
                        exc,
                        DorarTafsirCoverageUnavailable,
                    ):
                        quran_references = ()
                    else:
                        raise
                else:
                    # Candidate-local structural
                    # failure: reject and try next.
                    candidate_failures.append(exc)
                    continue

            structurally_readable = True

            if anchored:
                coverage = set(quran_references)

                if not all(reference in coverage for reference in required):
                    # Valid Dorar passage, but it does
                    # not satisfy the hard Quran identity.
                    continue

            admitted.append(
                DorarTafsirRetrievedPassage(
                    canonical_url=(canonical_url),
                    response_sha256=(response.response_sha256),
                    admitted=(runtime_evidence),
                    quran_references=(quran_references),
                )
            )

            if len(admitted) >= limit:
                break

        if (
            anchored
            and not admitted
            and candidate_failures
            and not structurally_readable
        ):
            # All inspected candidates failed at the
            # transport/structural layer. Do not turn
            # source unavailability into "zero hits".
            raise candidate_failures[-1]

        return DorarTafsirSearchResult(
            query=normalized,
            request_url=request_url,
            discovery_sha256=(discovery.response_sha256),
            discovered_urls=(discovered),
            passages=tuple(admitted),
        )
