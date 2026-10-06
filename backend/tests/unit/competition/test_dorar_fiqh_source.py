from __future__ import annotations

from hashlib import sha256
from urllib.parse import (
    parse_qs,
    urlsplit,
)

import pytest

from basira.competition.dorar_fiqh_source import (
    DORAR_FIQH_SEARCH_URL,
    DorarFiqhSourceClient,
    DorarFiqhSourcePayloadError,
    build_dorar_fiqh_search_url,
    canonical_fiqh_url,
    extract_fiqh_discovery_urls,
)
from basira.competition.dorar_transport import (
    DorarFetchedResponse,
    DorarFetchPurpose,
)


def response(
    url: str,
    body: bytes,
    *,
    purpose: DorarFetchPurpose,
) -> DorarFetchedResponse:
    return DorarFetchedResponse(
        requested_url=url,
        final_url=url,
        purpose=purpose,
        status_code=200,
        content_type="text/html",
        body=body,
        response_sha256=(sha256(body).hexdigest()),
    )


class FakeTransport:
    def __init__(
        self,
        pages,
        *,
        redirects=None,
    ):
        self.pages = dict(pages)

        self.redirects = dict(redirects or {})

        self.calls = []

    def fetch(
        self,
        url,
        *,
        purpose,
    ):
        self.calls.append(
            (
                "fetch",
                url,
                purpose,
            )
        )

        return response(
            url,
            self.pages[url],
            purpose=purpose,
        )

    def resolve_redirect_target(
        self,
        url,
    ):
        self.calls.append(
            (
                "resolve",
                url,
                None,
            )
        )

        return self.redirects[url]


def test_builds_official_fiqh_search_url():
    url = build_dorar_fiqh_search_url("الشفعة")

    parsed = urlsplit(url)

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == DORAR_FIQH_SEARCH_URL

    assert parse_qs(parsed.query)["skeys"] == ["الشفعة"]


@pytest.mark.parametrize(
    "query",
    (
        "",
        " ",
        "\n\t",
    ),
)
def test_blank_query_rejected(
    query,
):
    with pytest.raises(
        ValueError,
        match="nonblank",
    ):
        build_dorar_fiqh_search_url(query)


def test_discovery_accepts_short_and_canonical_routes():
    html = """
    <a href="/feqhia/8713">
      short
    </a>

    <a href="/feqhia/8786/full-slug">
      full
    </a>

    <a href="/feqhia/search?skeys=x">
      search
    </a>

    <a href="/tafseer/2/255">
      wrong domain
    </a>

    <a href="https://evil.example/feqhia/1/x">
      wrong host
    </a>
    """

    result = extract_fiqh_discovery_urls(
        html,
        base_url=(DORAR_FIQH_SEARCH_URL),
    )

    assert result == (
        ("https://dorar.net/feqhia/8713"),
        ("https://dorar.net/feqhia/8786/full-slug"),
    )


def test_canonical_validator():
    assert canonical_fiqh_url("https://dorar.net/feqhia/8713/leaf") == (
        "https://dorar.net/feqhia/8713/leaf"
    )

    assert canonical_fiqh_url("https://dorar.net/feqhia/8713") is None

    assert canonical_fiqh_url("https://evil.example/feqhia/8713/leaf") is None


def test_source_client_resolves_and_preserves_raw_document():
    search_url = build_dorar_fiqh_search_url("الشفعة")

    short = "https://dorar.net/feqhia/8713"

    canonical = "https://dorar.net/feqhia/8713/canonical-leaf"

    source_body = b"<html><body>raw source document</body></html>"

    transport = FakeTransport(
        {
            search_url: (b'<a href="/feqhia/8713">x</a>'),
            canonical: source_body,
        },
        redirects={
            short: canonical,
        },
    )

    result = DorarFiqhSourceClient(
        transport=transport,
    ).search(
        "الشفعة",
        limit=1,
    )

    assert len(result.documents) == 1

    document = result.documents[0]

    assert document.discovery_url == short

    assert document.canonical_url == canonical

    assert document.body == source_body

    assert document.response_sha256 == sha256(source_body).hexdigest()

    assert transport.calls == [
        (
            "fetch",
            search_url,
            DorarFetchPurpose.DISCOVERY,
        ),
        (
            "resolve",
            short,
            None,
        ),
        (
            "fetch",
            canonical,
            DorarFetchPurpose.EVIDENCE,
        ),
    ]


def test_source_client_does_not_classify_page_shape():
    search_url = build_dorar_fiqh_search_url("الشفعة")

    canonical = "https://dorar.net/feqhia/8685/index-like"

    body = b"""
    <html>
      <body>
        search UI
        navigation
        chapter hierarchy
      </body>
    </html>
    """

    transport = FakeTransport(
        {
            search_url: (b'<a href="/feqhia/8685/index-like">x</a>'),
            canonical: body,
        }
    )

    result = DorarFiqhSourceClient(
        transport=transport,
    ).search(
        "الشفعة",
        limit=1,
    )

    assert len(result.documents) == 1

    assert result.documents[0].body == body


def test_invalid_redirect_target_fails_closed():
    search_url = build_dorar_fiqh_search_url("test")

    short = "https://dorar.net/feqhia/9999"

    transport = FakeTransport(
        {
            search_url: (b'<a href="/feqhia/9999">x</a>'),
        },
        redirects={
            short: ("https://dorar.net/history/9999"),
        },
    )

    with pytest.raises(
        DorarFiqhSourcePayloadError,
        match="canonical document",
    ):
        DorarFiqhSourceClient(
            transport=transport,
        ).search("test")


def test_zero_hits_is_valid_empty_result():
    search_url = build_dorar_fiqh_search_url("لا توجد")

    result = DorarFiqhSourceClient(
        transport=FakeTransport(
            {
                search_url: b"<html></html>",
            }
        ),
    ).search("لا توجد")

    assert result.discovered_urls == ()

    assert result.documents == ()
