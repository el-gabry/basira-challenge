from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

from basira.competition.dorar_hadith import (
    DorarHadithRecord,
    match_dorar_hadith_full_text,
    parse_dorar_api_payload,
    parse_dorar_hadith_search_articles,
)
from basira.competition.dorar_transport import (
    DorarFetchedResponse,
    DorarFetchPurpose,
)

DORAR_HADITH_API_URL = "https://dorar.net/dorar_api.json"
DORAR_HADITH_HTML_SEARCH_URL = "https://dorar.net/hadith/search"


class DorarHadithRetrievalError(RuntimeError):
    pass


class DorarHadithPayloadError(DorarHadithRetrievalError):
    pass


class DorarTransportProtocol(Protocol):
    def fetch(
        self,
        url: str,
        *,
        purpose: DorarFetchPurpose,
    ) -> DorarFetchedResponse: ...


HadithPayloadParser = Callable[
    [dict],
    list[DorarHadithRecord],
]


@dataclass(
    frozen=True,
    slots=True,
)
class DorarHadithSearchResult:
    """
    Parsed Dorar search result before religious policy.

    `records` are source records, not trusted
    EvidenceNodes.

    OfficialHadithPolicy still has to decide whether
    each candidate is usable for the requested claim.
    """

    query: str
    request_url: str
    response_sha256: str

    records: tuple[
        DorarHadithRecord,
        ...,
    ]


def build_dorar_hadith_search_url(
    query: str,
) -> str:
    normalized = " ".join(query.split())

    if not normalized:
        raise ValueError("Hadith query must be nonblank.")

    if len(normalized) > 1000:
        raise ValueError("Hadith query is too long.")

    encoded = urlencode(
        {
            "skey": normalized,
        }
    )

    return f"{DORAR_HADITH_API_URL}?{encoded}"


def build_dorar_hadith_html_search_url(
    query: str,
) -> str:
    cleaned = " ".join(query.split())

    if not cleaned:
        raise ValueError(
            "query must not be blank."
        )

    return (
        DORAR_HADITH_HTML_SEARCH_URL
        + "?"
        + urlencode(
            {
                "q": cleaned,
            }
        )
    )


class DorarHadithRetriever:
    """
    Real Dorar Hadith source retrieval.

    Boundary:
        query
        -> official Dorar API
        -> governed Dorar transport
        -> exact payload parser
        -> DorarHadithRecord

    This class intentionally does NOT:
    - grant authority;
    - assess authenticity;
    - collapse conflicting gradings;
    - construct EvidenceNodes;
    - answer the user.
    """

    def __init__(
        self,
        *,
        transport: DorarTransportProtocol,
        parser: HadithPayloadParser = (parse_dorar_api_payload),
    ) -> None:
        self._transport = transport
        self._parser = parser

    def search_full_text(
        self,
        query: str,
        *,
        limit: int = 15,
    ) -> DorarHadithSearchResult:
        """
        Join Dorar API metadata with the complete matn rendered
        by Dorar's official HTML search page.

        No model completion and no inferred hadith text.
        """

        base = self.search(
            query,
            limit=limit,
        )

        html_url = (
            build_dorar_hadith_html_search_url(
                query
            )
        )

        response = self._transport.fetch(
            html_url,
            purpose=(
                DorarFetchPurpose.DISCOVERY
            ),
        )

        try:
            html = response.body.decode(
                "utf-8-sig"
            )
        except UnicodeDecodeError as exc:
            raise DorarHadithPayloadError(
                "Dorar Hadith HTML search "
                "is not valid UTF-8."
            ) from exc

        full_candidates = (
            parse_dorar_hadith_search_articles(
                html
            )
        )

        hydrated: list[
            DorarHadithRecord
        ] = []

        for record in base.records:
            full_text = (
                match_dorar_hadith_full_text(
                    record.hadith_text,
                    full_candidates,
                )
            )

            # Fail closed. Never attach grading / narrator
            # metadata to an HTML matn unless textual identity
            # proves the association.
            if full_text is None:
                continue

            hydrated.append(
                DorarHadithRecord(
                    rank=record.rank,
                    hadith_text=full_text,
                    narrator=record.narrator,
                    muhaddith=record.muhaddith,
                    source=record.source,
                    page_or_number=(
                        record.page_or_number
                    ),
                    verdict=record.verdict,
                    extra_fields=dict(
                        record.extra_fields
                    ),
                )
            )

        if not hydrated:
            raise DorarHadithPayloadError(
                "Dorar Hadith HTML search "
                "did not yield rank-matched "
                "full-text records."
            )

        return DorarHadithSearchResult(
            query=base.query,
            request_url=html_url,
            response_sha256=(
                response.response_sha256
            ),
            records=tuple(
                hydrated[:limit]
            ),
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 15,
    ) -> DorarHadithSearchResult:
        if limit <= 0:
            raise ValueError("limit must be positive.")

        url = build_dorar_hadith_search_url(query)

        response = self._transport.fetch(
            url,
            purpose=(DorarFetchPurpose.DISCOVERY),
        )

        try:
            decoded = response.body.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DorarHadithPayloadError(
                "Dorar Hadith response is not valid UTF-8."
            ) from exc

        try:
            payload = json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise DorarHadithPayloadError(
                "Dorar Hadith response is not valid JSON."
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise DorarHadithPayloadError("Dorar Hadith payload must be a JSON object.")

        records = self._parser(payload)

        if not isinstance(
            records,
            list,
        ):
            raise DorarHadithPayloadError(
                "Dorar Hadith parser returned invalid result."
            )

        return DorarHadithSearchResult(
            query=" ".join(query.split()),
            request_url=url,
            response_sha256=(response.response_sha256),
            records=tuple(records[:limit]),
        )
