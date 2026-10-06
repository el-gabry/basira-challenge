from __future__ import annotations

import re
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
)

DORAR_FIQH_SEARCH_URL = "https://dorar.net/feqhia/search"


_SHORT_FIQH_PATH = re.compile(r"^/feqhia/\d+/?$")

_CANONICAL_FIQH_PATH = re.compile(r"^/feqhia/\d+/[^/?#]+/?$")


class DorarFiqhSourceError(RuntimeError):
    pass


class DorarFiqhSourcePayloadError(DorarFiqhSourceError):
    pass


class DorarTransportProtocol(Protocol):
    def fetch(
        self,
        url: str,
        *,
        purpose: DorarFetchPurpose,
    ) -> DorarFetchedResponse: ...

    def resolve_redirect_target(
        self,
        url: str,
    ) -> str: ...


@dataclass(
    frozen=True,
    slots=True,
)
class DorarFiqhSourceDocument:
    """
    Canonical fetched source document.

    This is NOT an EvidenceNode and is NOT yet an
    answer-bearing chunk.

    The raw body is intentionally preserved for the
    structural normalization/chunking layer.
    """

    discovery_url: str
    canonical_url: str

    response_sha256: str
    content_type: str

    body: bytes


@dataclass(
    frozen=True,
    slots=True,
)
class DorarFiqhSourceSearchResult:
    query: str

    request_url: str
    discovery_sha256: str

    discovered_urls: tuple[
        str,
        ...,
    ]

    documents: tuple[
        DorarFiqhSourceDocument,
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
        raise ValueError("Fiqh query must be nonblank.")

    if len(value) > 1000:
        raise ValueError("Fiqh query is too long.")

    return value


def build_dorar_fiqh_search_url(
    query: str,
) -> str:
    query = _clean_query(query)

    return (
        DORAR_FIQH_SEARCH_URL
        + "?"
        + urlencode(
            {
                "skeys": query,
            }
        )
    )


def _discovery_candidate(
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

    if parsed.username is not None or parsed.password is not None:
        return None

    if parsed.query or parsed.fragment:
        return None

    if not (
        _SHORT_FIQH_PATH.fullmatch(parsed.path)
        or _CANONICAL_FIQH_PATH.fullmatch(parsed.path)
    ):
        return None

    return "https://dorar.net" + parsed.path.rstrip("/")


def canonical_fiqh_url(
    value: str,
) -> str | None:
    parsed = urlsplit(value)

    if parsed.scheme != "https":
        return None

    if parsed.hostname != "dorar.net":
        return None

    if parsed.username is not None or parsed.password is not None:
        return None

    if parsed.query or parsed.fragment:
        return None

    if not (_CANONICAL_FIQH_PATH.fullmatch(parsed.path)):
        return None

    return "https://dorar.net" + parsed.path.rstrip("/")


def extract_fiqh_discovery_urls(
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
        candidate = _discovery_candidate(
            href,
            base_url=base_url,
        )

        if candidate is None or candidate in seen:
            continue

        seen.add(candidate)

        results.append(candidate)

    return tuple(results)


def _is_short_url(
    value: str,
) -> bool:
    return bool(_SHORT_FIQH_PATH.fullmatch(urlsplit(value).path))


class DorarFiqhSourceClient:
    """
    Authority-neutral Dorar Fiqh source acquisition.

    Responsibilities:
    - discover candidate Dorar Fiqh documents;
    - resolve short URLs without following redirects;
    - validate canonical Dorar routes;
    - fetch exact canonical responses;
    - preserve raw response bytes + SHA256.

    Explicitly NOT responsible for:
    - article-vs-index evidence classification;
    - structural chunking;
    - relevance;
    - source eligibility;
    - Fiqh policy;
    - EvidenceNode construction;
    - answer generation.
    """

    def __init__(
        self,
        *,
        transport: DorarTransportProtocol,
        max_candidates: int = 30,
    ) -> None:
        if max_candidates <= 0:
            raise ValueError("max_candidates must be positive.")

        self._transport = transport

        self._max_candidates = max_candidates

    def _canonicalize(
        self,
        discovery_url: str,
    ) -> str:
        if _is_short_url(discovery_url):
            target = self._transport.resolve_redirect_target(discovery_url)
        else:
            target = discovery_url

        canonical = canonical_fiqh_url(target)

        if canonical is None:
            raise (
                DorarFiqhSourcePayloadError(
                    "Dorar Fiqh discovery did not resolve to a canonical document."
                )
            )

        return canonical

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> DorarFiqhSourceSearchResult:
        if limit <= 0:
            raise ValueError("limit must be positive.")

        normalized = _clean_query(query)

        request_url = build_dorar_fiqh_search_url(normalized)

        discovery = self._transport.fetch(
            request_url,
            purpose=(DorarFetchPurpose.DISCOVERY),
        )

        try:
            discovery_html = discovery.body.decode("utf-8-sig")

        except UnicodeDecodeError as exc:
            raise (
                DorarFiqhSourcePayloadError(
                    "Dorar Fiqh discovery response is not valid UTF-8."
                )
            ) from exc

        discovered = extract_fiqh_discovery_urls(
            discovery_html,
            base_url=(discovery.final_url),
        )

        documents: list[DorarFiqhSourceDocument] = []

        seen_canonical: set[str] = set()

        for discovery_url in discovered[: self._max_candidates]:
            canonical_url = self._canonicalize(discovery_url)

            if canonical_url in seen_canonical:
                continue

            seen_canonical.add(canonical_url)

            response = self._transport.fetch(
                canonical_url,
                purpose=(DorarFetchPurpose.EVIDENCE),
            )

            documents.append(
                DorarFiqhSourceDocument(
                    discovery_url=(discovery_url),
                    canonical_url=(canonical_url),
                    response_sha256=(response.response_sha256),
                    content_type=(response.content_type),
                    body=(response.body),
                )
            )

            if len(documents) >= limit:
                break

        return DorarFiqhSourceSearchResult(
            query=normalized,
            request_url=request_url,
            discovery_sha256=(discovery.response_sha256),
            discovered_urls=(discovered),
            documents=tuple(documents),
        )
