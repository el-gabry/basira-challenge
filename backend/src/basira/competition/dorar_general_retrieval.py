from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import (
    urlencode,
    urljoin,
    urlsplit,
)

from basira.competition.dorar_transport import (
    DorarFetchPurpose,
    DorarHttpTransport,
    DorarTransportError,
)

_DORAR_SEARCH = "https://dorar.net/site/search"

_AQEEDAH_ROUTE = re.compile(r"^/aqeeda/(?P<id>\d+)(?:/.*)?$")

_HISTORY_EVENT_ROUTE = re.compile(r"^/history/event/(?P<id>\d+)(?:/.*)?$")

_HISTORY_DIRECT_ROUTE = re.compile(r"^/history/(?P<id>\d+)(?:/.*)?$")


@dataclass(
    frozen=True,
    slots=True,
)
class DorarGovernedRawPage:
    canonical_url: str
    body: bytes
    response_sha256: str


class _HrefCollector(HTMLParser):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self.hrefs: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:
        if tag.casefold() != "a":
            return

        href = dict(attrs).get("href")

        if isinstance(
            href,
            str,
        ):
            self.hrefs.append(href)


def build_dorar_site_search_url(
    query: str,
) -> str:
    cleaned = " ".join(query.split())

    if not cleaned:
        raise ValueError("Dorar search query must be nonblank.")

    return (
        _DORAR_SEARCH
        + "?"
        + urlencode(
            {
                "div": "2",
                "skeys": cleaned,
            }
        )
    )


def _canonical_candidate(
    href: str,
    *,
    family: str,
) -> str | None:
    absolute = urljoin(
        "https://dorar.net/",
        href,
    )

    parsed = urlsplit(absolute)

    if parsed.scheme != "https" or parsed.hostname != "dorar.net":
        return None

    path = parsed.path.rstrip("/")

    if family == "aqeedah":
        match = _AQEEDAH_ROUTE.fullmatch(path)

        if match is None:
            return None

        return "https://dorar.net/aqeeda/" + match.group("id")

    if family == "history":
        event = _HISTORY_EVENT_ROUTE.fullmatch(path)

        if event is not None:
            return "https://dorar.net/history/event/" + event.group("id")

        direct = _HISTORY_DIRECT_ROUTE.fullmatch(path)

        if direct is not None:
            return "https://dorar.net/history/" + direct.group("id")

        return None

    raise ValueError(f"unsupported Dorar family: {family}")


def _candidate_urls(
    html: str,
    *,
    family: str,
) -> tuple[
    str,
    ...,
]:
    parser = _HrefCollector()
    parser.feed(html)

    result: list[str] = []
    seen: set[str] = set()

    for href in parser.hrefs:
        candidate = _canonical_candidate(
            href,
            family=family,
        )

        if candidate is None or candidate in seen:
            continue

        seen.add(candidate)
        result.append(candidate)

    return tuple(result)


class DorarGovernedPageClient:
    """
    Authority-neutral acquisition.

    Discovery may broaden to find candidate URLs.
    Only domain admission/policy may turn a fetched
    page into religious evidence.
    """

    def __init__(
        self,
        *,
        transport: DorarHttpTransport,
    ) -> None:
        self.transport = transport

    def search(
        self,
        *,
        query: str,
        family: str,
        limit: int,
    ) -> tuple[
        DorarGovernedRawPage,
        ...,
    ]:
        if limit <= 0:
            return ()

        discovery = self.transport.fetch(
            build_dorar_site_search_url(query),
            purpose=(DorarFetchPurpose.DISCOVERY),
        )

        try:
            html = discovery.body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DorarTransportError("Dorar discovery is not UTF-8.") from exc

        candidates = _candidate_urls(
            html,
            family=family,
        )

        pages: list[DorarGovernedRawPage] = []

        fetch_failures = 0

        # Acquisition may inspect more candidates than
        # it returns. Authority is still not widened.
        for url in candidates[
            : max(
                limit * 3,
                limit,
            )
        ]:
            try:
                response = self.transport.fetch(
                    url,
                    purpose=(DorarFetchPurpose.EVIDENCE),
                )
            except DorarTransportError:
                fetch_failures += 1
                continue

            pages.append(
                DorarGovernedRawPage(
                    canonical_url=url,
                    body=response.body,
                    response_sha256=(response.response_sha256),
                )
            )

            if len(pages) >= limit:
                break

        if candidates and not pages and fetch_failures:
            raise DorarTransportError("all governed Dorar candidate fetches failed")

        return tuple(pages)
