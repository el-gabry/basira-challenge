from __future__ import annotations

import json
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
    cache_root=None,
):
    client = httpx.Client(
        transport=(httpx.MockTransport(handler)),
        follow_redirects=False,
    )

    return DorarHttpTransport(
        client=client,
        max_response_bytes=(max_response_bytes),
        cache_root=cache_root,
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


def _write_cache(
    root,
    *,
    url,
    purpose,
    body,
    content_type="text/html",
    expected_sha256=None,
):
    digest = sha256(body).hexdigest()

    bodies = root / "bodies"
    bodies.mkdir(
        parents=True,
        exist_ok=True,
    )

    body_name = digest + ".body"
    body_path = bodies / body_name
    body_path.write_bytes(body)

    manifest = {
        "cache_version": 1,
        "provider": "Dorar al-Sunniyyah",
        "fetches": [
            {
                "requested_url": url,
                "final_url": url,
                "purpose": purpose.value,
                "status_code": 200,
                "content_type": content_type,
                "response_sha256": (
                    expected_sha256
                    if expected_sha256 is not None
                    else digest
                ),
                "response_bytes": len(body),
                "body_path": "bodies/" + body_name,
            }
        ],
    }

    (root / "manifest.json").write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return digest


def test_unavailable_live_response_uses_hash_bound_cache(
    tmp_path,
):
    url = "https://dorar.net/tafseer/2/43"
    body = b"<html>official cached response</html>"

    digest = _write_cache(
        tmp_path,
        url=url,
        purpose=DorarFetchPurpose.EVIDENCE,
        body=body,
    )

    calls = []

    def handler(request):
        calls.append(str(request.url))

        return httpx.Response(
            403,
            headers={
                "content-type": "text/html",
            },
            request=request,
        )

    result = transport(
        handler,
        cache_root=tmp_path,
    ).fetch(
        url,
        purpose=DorarFetchPurpose.EVIDENCE,
    )

    assert calls == [url]
    assert result.body == body
    assert result.response_sha256 == digest
    assert result.final_url == url


def test_live_success_wins_over_configured_cache(
    tmp_path,
):
    url = "https://dorar.net/tafseer/2/43"

    _write_cache(
        tmp_path,
        url=url,
        purpose=DorarFetchPurpose.EVIDENCE,
        body=b"<html>cached</html>",
    )

    live_body = b"<html>live</html>"

    def handler(request):
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html",
            },
            content=live_body,
            request=request,
        )

    result = transport(
        handler,
        cache_root=tmp_path,
    ).fetch(
        url,
        purpose=DorarFetchPurpose.EVIDENCE,
    )

    assert result.body == live_body
    assert result.response_sha256 == (
        sha256(live_body).hexdigest()
    )


def test_cache_miss_preserves_live_unavailable(
    tmp_path,
):
    cached_url = "https://dorar.net/tafseer/2/43"

    _write_cache(
        tmp_path,
        url=cached_url,
        purpose=DorarFetchPurpose.EVIDENCE,
        body=b"<html>cached</html>",
    )

    requested_url = "https://dorar.net/tafseer/2/999"

    def handler(request):
        return httpx.Response(
            403,
            headers={
                "content-type": "text/html",
            },
            request=request,
        )

    with pytest.raises(
        DorarTransportUnavailable,
        match="http_status:403",
    ):
        transport(
            handler,
            cache_root=tmp_path,
        ).fetch(
            requested_url,
            purpose=DorarFetchPurpose.EVIDENCE,
        )


def test_cache_purpose_mismatch_fails_closed_as_unavailable(
    tmp_path,
):
    url = "https://dorar.net/site/search?skeys=test"

    _write_cache(
        tmp_path,
        url=url,
        purpose=DorarFetchPurpose.DISCOVERY,
        body=b"<html>discovery</html>",
    )

    def handler(request):
        return httpx.Response(
            403,
            headers={
                "content-type": "text/html",
            },
            request=request,
        )

    with pytest.raises(
        DorarTransportUnavailable,
        match="http_status:403",
    ):
        transport(
            handler,
            cache_root=tmp_path,
        ).fetch(
            url,
            purpose=DorarFetchPurpose.EVIDENCE,
        )


def test_cache_hash_mismatch_is_blocked(
    tmp_path,
):
    url = "https://dorar.net/tafseer/2/43"

    _write_cache(
        tmp_path,
        url=url,
        purpose=DorarFetchPurpose.EVIDENCE,
        body=b"<html>cached</html>",
        expected_sha256=("0" * 64),
    )

    def handler(request):
        return httpx.Response(
            403,
            headers={
                "content-type": "text/html",
            },
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="cache_hash_mismatch",
    ):
        transport(
            handler,
            cache_root=tmp_path,
        ).fetch(
            url,
            purpose=DorarFetchPurpose.EVIDENCE,
        )


def test_blocked_live_response_never_uses_cache(
    tmp_path,
):
    url = "https://dorar.net/tafseer/2/43"

    _write_cache(
        tmp_path,
        url=url,
        purpose=DorarFetchPurpose.EVIDENCE,
        body=b"<html>cached</html>",
    )

    def handler(request):
        return httpx.Response(
            302,
            headers={
                "location": url,
                "content-type": "text/html",
            },
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="redirect_not_allowed",
    ):
        transport(
            handler,
            cache_root=tmp_path,
        ).fetch(
            url,
            purpose=DorarFetchPurpose.EVIDENCE,
        )




def _write_redirect_cache(
    root,
    *,
    requested_url,
    target_url,
    target_sha256=None,
):
    digest = sha256(
        target_url.encode("utf-8")
    ).hexdigest()

    manifest = {
        "cache_version": 1,
        "provider": "Dorar al-Sunniyyah",
        "fetches": [],
        "redirects": [
            {
                "requested_url":
                    requested_url,
                "target_url":
                    target_url,
                "target_sha256": (
                    target_sha256
                    if target_sha256
                    is not None
                    else digest
                ),
            }
        ],
    }

    (root / "manifest.json").write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_unavailable_redirect_probe_uses_exact_cached_mapping(
    tmp_path,
):
    requested = (
        "https://dorar.net/"
        "feqhia/short/example"
    )

    target = (
        "https://dorar.net/"
        "feqhia/7199/example"
    )

    _write_redirect_cache(
        tmp_path,
        requested_url=requested,
        target_url=target,
    )

    def handler(request):
        return httpx.Response(
            403,
            request=request,
        )

    result = transport(
        handler,
        cache_root=tmp_path,
    ).resolve_redirect_target(
        requested
    )

    assert result == target


def test_live_redirect_wins_over_cached_mapping(
    tmp_path,
):
    requested = (
        "https://dorar.net/"
        "feqhia/short/example"
    )

    cached_target = (
        "https://dorar.net/"
        "feqhia/7199/cached"
    )

    live_target = (
        "https://dorar.net/"
        "feqhia/6885/live"
    )

    _write_redirect_cache(
        tmp_path,
        requested_url=requested,
        target_url=cached_target,
    )

    def handler(request):
        return httpx.Response(
            302,
            headers={
                "location": live_target,
            },
            request=request,
        )

    result = transport(
        handler,
        cache_root=tmp_path,
    ).resolve_redirect_target(
        requested
    )

    assert result == live_target


def test_successful_nonredirect_never_uses_redirect_cache(
    tmp_path,
):
    requested = (
        "https://dorar.net/"
        "feqhia/short/example"
    )

    target = (
        "https://dorar.net/"
        "feqhia/7199/example"
    )

    _write_redirect_cache(
        tmp_path,
        requested_url=requested,
        target_url=target,
    )

    def handler(request):
        return httpx.Response(
            200,
            content=b"not a redirect",
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="redirect_expected",
    ):
        transport(
            handler,
            cache_root=tmp_path,
        ).resolve_redirect_target(
            requested
        )


def test_cached_redirect_hash_mismatch_is_blocked(
    tmp_path,
):
    requested = (
        "https://dorar.net/"
        "feqhia/short/example"
    )

    target = (
        "https://dorar.net/"
        "feqhia/7199/example"
    )

    _write_redirect_cache(
        tmp_path,
        requested_url=requested,
        target_url=target,
        target_sha256=("0" * 64),
    )

    def handler(request):
        return httpx.Response(
            403,
            request=request,
        )

    with pytest.raises(
        DorarTransportBlocked,
        match="cache_redirect_hash_mismatch",
    ):
        transport(
            handler,
            cache_root=tmp_path,
        ).resolve_redirect_target(
            requested
        )
