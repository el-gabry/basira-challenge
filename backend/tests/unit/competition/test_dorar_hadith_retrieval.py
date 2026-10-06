from __future__ import annotations

from hashlib import sha256
from urllib.parse import (
    parse_qs,
    urlsplit,
)

import httpx
import pytest

from basira.competition.dorar_hadith_retrieval import (
    DORAR_HADITH_API_URL,
    DorarHadithPayloadError,
    DorarHadithRetriever,
    build_dorar_hadith_search_url,
)
from basira.competition.dorar_transport import (
    DorarHttpTransport,
)


def transport(
    handler,
):
    client = httpx.Client(
        transport=(httpx.MockTransport(handler)),
        follow_redirects=False,
    )

    return DorarHttpTransport(client=client)


def test_search_url_uses_official_api_and_skey():
    url = build_dorar_hadith_search_url("إنما الأعمال بالنيات")

    parsed = urlsplit(url)

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == DORAR_HADITH_API_URL

    assert parse_qs(parsed.query)["skey"] == ["إنما الأعمال بالنيات"]


@pytest.mark.parametrize(
    "query",
    (
        "",
        " ",
        "\n\t",
    ),
)
def test_blank_query_is_rejected(
    query,
):
    with pytest.raises(
        ValueError,
        match="nonblank",
    ):
        build_dorar_hadith_search_url(query)


def test_query_is_normalized_before_transport():
    seen = {}

    body = b'{"ok": true}'

    def handler(request):
        seen["url"] = str(request.url)

        return httpx.Response(
            200,
            headers={"content-type": ("application/json")},
            content=body,
            request=request,
        )

    parser_payloads = []

    def parser(payload):
        parser_payloads.append(payload)

        return []

    result = DorarHadithRetriever(
        transport=transport(handler),
        parser=parser,
    ).search("  إنما   الأعمال   بالنيات  ")

    query = parse_qs(urlsplit(seen["url"]).query)

    assert query["skey"] == ["إنما الأعمال بالنيات"]

    assert parser_payloads == [
        {
            "ok": True,
        }
    ]

    assert result.query == ("إنما الأعمال بالنيات")

    assert result.records == ()

    assert result.response_sha256 == sha256(body).hexdigest()


def test_limit_is_applied_after_parser():
    body = b'{"fixture": true}'

    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": ("application/json")},
            content=body,
            request=request,
        )

    first = object()
    second = object()
    third = object()

    result = DorarHadithRetriever(
        transport=transport(handler),
        parser=lambda payload: [
            first,
            second,
            third,
        ],
    ).search(
        "حديث",
        limit=2,
    )

    assert result.records == (
        first,
        second,
    )


def test_invalid_json_fails_closed():
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": ("application/json")},
            content=b"{not-json",
            request=request,
        )

    with pytest.raises(
        DorarHadithPayloadError,
        match="valid JSON",
    ):
        DorarHadithRetriever(transport=transport(handler)).search("حديث")


def test_non_object_json_fails_closed():
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": ("application/json")},
            content=b"[]",
            request=request,
        )

    with pytest.raises(
        DorarHadithPayloadError,
        match="JSON object",
    ):
        DorarHadithRetriever(transport=transport(handler)).search("حديث")


def test_parser_is_authority_neutral():
    body = b'{"fixture": true}'

    seen = []

    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": ("application/json")},
            content=body,
            request=request,
        )

    def parser(payload):
        seen.append(payload)

        return []

    result = DorarHadithRetriever(
        transport=transport(handler),
        parser=parser,
    ).search("ما صحة الحديث؟")

    assert seen == [
        {
            "fixture": True,
        }
    ]

    assert result.records == ()
