from __future__ import annotations

from hashlib import sha256

import httpx
import pytest

from basira.competition.dorar_transport import (
    DorarFetchPurpose,
    DorarHttpTransport,
    DorarTransportBlocked,
    DorarTransportUnavailable,
)


def transport(
    handler,
    *,
    max_response_bytes=1024,
):
    client = httpx.Client(
        transport=(httpx.MockTransport(handler)),
        follow_redirects=False,
    )

    return DorarHttpTransport(
        client=client,
        max_response_bytes=(max_response_bytes),
    )


def test_fetch_preserves_exact_body_and_hash():
    body = b"<html><body>source text</body></html>"

    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": ("text/html; charset=utf-8")},
            content=body,
            request=request,
        )

    result = transport(handler).fetch(
        "https://dorar.net/tafsir/1",
        purpose=(DorarFetchPurpose.EVIDENCE),
    )

    assert result.body == body

    assert result.response_sha256 == sha256(body).hexdigest()

    assert result.final_url == "https://dorar.net/tafsir/1"


def test_discovery_query_url_is_transportable():
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": ("text/html")},
            content=b"<html></html>",
            request=request,
        )

    result = transport(handler).fetch(
        ("https://dorar.net/site/search?skeys=test"),
        purpose=(DorarFetchPurpose.DISCOVERY),
    )

    assert result.purpose is DorarFetchPurpose.DISCOVERY


@pytest.mark.parametrize(
    "url",
    (
        "http://dorar.net/tafsir/1",
        ("https://example.com/tafsir/1"),
        ("https://user:pass@dorar.net/tafsir/1"),
        ("https://dorar.net/tafsir/1#fragment"),
    ),
)
def test_unsafe_urls_fail_closed(
    url,
):
    def handler(request):
        raise AssertionError("network must not run")

    with pytest.raises(DorarTransportBlocked):
        transport(handler).fetch(
            url,
            purpose=(DorarFetchPurpose.EVIDENCE),
        )


def test_redirect_is_not_followed():
    calls = []

    def handler(request):
        calls.append(str(request.url))

        return httpx.Response(
            302,
            headers={
                "location": ("https://example.com/evil"),
                "content-type": ("text/html"),
            },
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="redirect_not_allowed",
    ):
        transport(handler).fetch(
            "https://dorar.net/tafsir/1",
            purpose=(DorarFetchPurpose.EVIDENCE),
        )

    assert calls == ["https://dorar.net/tafsir/1"]


def test_non_200_is_unavailable_not_zero_hits():
    def handler(request):
        return httpx.Response(
            503,
            headers={"content-type": ("text/html")},
            request=request,
        )

    with pytest.raises(
        DorarTransportUnavailable,
        match="http_status:503",
    ):
        transport(handler).fetch(
            "https://dorar.net/tafsir/1",
            purpose=(DorarFetchPurpose.EVIDENCE),
        )


def test_missing_content_type_fails_closed():
    def handler(request):
        return httpx.Response(
            200,
            content=b"source",
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="missing_content_type",
    ):
        transport(handler).fetch(
            "https://dorar.net/tafsir/1",
            purpose=(DorarFetchPurpose.EVIDENCE),
        )


def test_binary_content_type_fails_closed():
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": ("application/octet-stream")},
            content=b"\x00\x01",
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="unsupported_content_type",
    ):
        transport(handler).fetch(
            "https://dorar.net/tafsir/1",
            purpose=(DorarFetchPurpose.EVIDENCE),
        )


def test_response_size_is_bounded():
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": ("text/html")},
            content=b"x" * 101,
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="response_too_large",
    ):
        transport(
            handler,
            max_response_bytes=100,
        ).fetch(
            "https://dorar.net/tafsir/1",
            purpose=(DorarFetchPurpose.EVIDENCE),
        )


def test_json_transport_is_supported():
    body = b'{"data": []}'

    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": ("application/json")},
            content=body,
            request=request,
        )

    result = transport(handler).fetch(
        "https://dorar.net/dorar_api.json",
        purpose=(DorarFetchPurpose.DISCOVERY),
    )

    assert result.content_type == "application/json"

    assert result.body == body


def test_redirect_target_can_be_resolved_without_following():
    calls = []

    def handler(request):
        calls.append(str(request.url))

        return httpx.Response(
            302,
            headers={
                "location": ("/feqhia/8687/canonical-slug"),
                "content-type": ("text/html"),
            },
            request=request,
        )

    result = transport(handler).resolve_redirect_target("https://dorar.net/feqhia/8687")

    assert result == ("https://dorar.net/feqhia/8687/canonical-slug")

    assert calls == ["https://dorar.net/feqhia/8687"]


def test_redirect_target_rejects_external_host():
    def handler(request):
        return httpx.Response(
            302,
            headers={
                "location": ("https://evil.example/feqhia/8687/x"),
            },
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="unexpected_host",
    ):
        transport(handler).resolve_redirect_target("https://dorar.net/feqhia/8687")


def test_redirect_resolution_requires_redirect():
    def handler(request):
        return httpx.Response(
            200,
            headers={
                "content-type": ("text/html"),
            },
            content=b"not a redirect",
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="redirect_expected",
    ):
        transport(handler).resolve_redirect_target("https://dorar.net/feqhia/8687")
