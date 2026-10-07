from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace
from urllib.parse import (
    parse_qs,
    urlsplit,
)

import pytest

from basira.competition.dorar_tafsir_retrieval import (
    DORAR_TAFSIR_SEARCH_URL,
    DorarTafsirPayloadError,
    DorarTafsirRetriever,
    build_dorar_tafsir_search_url,
    extract_canonical_tafsir_urls,
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
):
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
    ):
        self.pages = dict(pages)
        self.calls = []

    def fetch(
        self,
        url,
        *,
        purpose,
    ):
        self.calls.append(
            (
                url,
                purpose,
            )
        )

        return response(
            url,
            self.pages[url],
            purpose=purpose,
        )


class FakeGate:
    def __init__(
        self,
    ):
        self.calls = []

    def admit(
        self,
        *,
        html,
        canonical_url,
    ):
        self.calls.append(
            (
                html,
                canonical_url,
            )
        )

        return SimpleNamespace(
            canonical_url=(canonical_url),
            admitted=True,
        )


def test_search_url_is_official_tafsir_search():
    url = build_dorar_tafsir_search_url("الحي القيوم")

    parsed = urlsplit(url)

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == DORAR_TAFSIR_SEARCH_URL

    assert DORAR_TAFSIR_SEARCH_URL == "https://dorar.net/site/search"

    params = parse_qs(parsed.query)

    assert params["skeys"] == ["الحي القيوم"]

    assert params["div"] == ["2"]


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
        build_dorar_tafsir_search_url(query)


def test_canonical_link_extraction_is_fail_closed():
    html = """
    <html>
      <body>
        <a href="/tafseer/2">
          surah discovery page
        </a>

        <a href="/tafseer/2/255">
          canonical
        </a>

        <a href="https://dorar.net/tafseer/2/255">
          duplicate canonical
        </a>

        <a href="/tafseer/2/256?x=1">
          query must not enter
        </a>

        <a href="/hadith/123">
          wrong domain
        </a>

        <a href="https://evil.example/tafseer/2/255">
          wrong host
        </a>
      </body>
    </html>
    """

    result = extract_canonical_tafsir_urls(
        html,
        base_url=(DORAR_TAFSIR_SEARCH_URL),
    )

    assert result == (("https://dorar.net/tafseer/2/255"),)


def test_search_discovers_fetches_and_admits():
    search_url = build_dorar_tafsir_search_url("الحي القيوم")

    canonical = "https://dorar.net/tafseer/2/255"

    discovery = b"""
    <html>
      <a href="/tafseer/2/255">
        result
      </a>
    </html>
    """

    evidence = b"<html>canonical</html>"

    transport = FakeTransport(
        {
            search_url: discovery,
            canonical: evidence,
        }
    )

    gate = FakeGate()

    result = DorarTafsirRetriever(
        transport=transport,
        gate=gate,
    ).search(
        "الحي القيوم",
        limit=3,
    )

    assert result.discovered_urls == (canonical,)

    assert len(result.passages) == 1

    assert result.passages[0].canonical_url == canonical

    assert result.passages[0].response_sha256 == sha256(evidence).hexdigest()

    assert gate.calls == [
        (
            evidence,
            canonical,
        )
    ]

    assert transport.calls == [
        (
            search_url,
            DorarFetchPurpose.DISCOVERY,
        ),
        (
            canonical,
            DorarFetchPurpose.EVIDENCE,
        ),
    ]


def test_zero_discovery_hits_is_valid_empty_result():
    search_url = build_dorar_tafsir_search_url("لا توجد نتيجة")

    transport = FakeTransport(
        {
            search_url: b"<html></html>",
        }
    )

    result = DorarTafsirRetriever(
        transport=transport,
        gate=FakeGate(),
    ).search("لا توجد نتيجة")

    assert result.discovered_urls == ()

    assert result.passages == ()


def test_limit_bounds_admitted_passages():
    search_url = build_dorar_tafsir_search_url("test")

    first = "https://dorar.net/tafseer/1/1"

    second = "https://dorar.net/tafseer/2/1"

    discovery = f"""
    <a href="{first}">a</a>
    <a href="{second}">b</a>
    """.encode()

    transport = FakeTransport(
        {
            search_url: discovery,
            first: b"<html>1</html>",
            second: b"<html>2</html>",
        }
    )

    result = DorarTafsirRetriever(
        transport=transport,
        gate=FakeGate(),
    ).search(
        "test",
        limit=1,
    )

    assert len(result.passages) == 1

    assert result.passages[0].canonical_url == first

    assert len(transport.calls) == 2


def test_invalid_utf8_discovery_fails_closed():
    search_url = build_dorar_tafsir_search_url("test")

    transport = FakeTransport(
        {
            search_url: b"\xff\xfe\xff",
        }
    )

    with pytest.raises(
        DorarTafsirPayloadError,
        match="valid UTF-8",
    ):
        DorarTafsirRetriever(
            transport=transport,
            gate=FakeGate(),
        ).search("test")


def test_gate_failure_is_not_converted_to_zero_hits():
    search_url = build_dorar_tafsir_search_url("test")

    canonical = "https://dorar.net/tafseer/1/1"

    class RejectingGate:
        def admit(
            self,
            *,
            html,
            canonical_url,
        ):
            del (
                html,
                canonical_url,
            )

            raise RuntimeError("admission failed")

    transport = FakeTransport(
        {
            search_url: (b'<a href="/tafseer/1/1">result</a>'),
            canonical: b"<html></html>",
        }
    )

    with pytest.raises(
        RuntimeError,
        match="admission failed",
    ):
        DorarTafsirRetriever(
            transport=transport,
            gate=RejectingGate(),
        ).search("test")


def test_anchored_search_skips_bad_candidate_and_keeps_first_matching():
    query = "وسع كرسيه السماوات والأرض"

    search_url = build_dorar_tafsir_search_url(query)

    bad = "https://dorar.net/tafseer/2/99"

    matching = "https://dorar.net/tafseer/2/43"

    discovery = f"""
    <a href="{bad}">bad</a>
    <a href="{matching}">matching</a>
    """.encode()

    transport = FakeTransport(
        {
            search_url: discovery,
            bad: ("<h6>الآيات (1-2)</h6><h5>الآيات (3-4)</h5>").encode(),
            matching: ("<h6>الآيات (254-257)</h6>").encode(),
        }
    )

    result = DorarTafsirRetriever(
        transport=transport,
        gate=FakeGate(),
        max_candidates=30,
    ).search(
        query,
        limit=1,
        required_quran_references=("2:255",),
    )

    assert len(result.passages) == 1

    passage = result.passages[0]

    assert passage.canonical_url == matching

    assert "2:255" in passage.quran_references



def test_anchored_zero_lexical_hits_uses_structural_surah_fallback():
    query = "قل هو الله أحد"

    search_url = (
        build_dorar_tafsir_search_url(
            query
        )
    )

    collection = (
        "https://dorar.net/tafseer/112"
    )

    passage = (
        "https://dorar.net/tafseer/112/1"
    )

    passage_body = (
        "<h6>الآيات (1-4)</h6>"
    ).encode()

    transport = FakeTransport(
        {
            search_url: b"<html></html>",
            collection: (
                b'<a href="/tafseer/112/1">'
                b"first"
                b"</a>"
            ),
            passage: passage_body,
        }
    )

    gate = FakeGate()

    result = DorarTafsirRetriever(
        transport=transport,
        gate=gate,
    ).search(
        query,
        limit=1,
        required_quran_references=(
            "112:1",
        ),
    )

    assert len(result.passages) == 1

    assert (
        result.passages[0].canonical_url
        == passage
    )

    assert (
        "112:1"
        in result.passages[0].quran_references
    )

    # The lexical search itself had zero canonical hits.
    assert result.discovered_urls == ()

    assert transport.calls == [
        (
            search_url,
            DorarFetchPurpose.DISCOVERY,
        ),
        (
            collection,
            DorarFetchPurpose.DISCOVERY,
        ),
        (
            passage,
            DorarFetchPurpose.EVIDENCE,
        ),
    ]

    assert gate.calls == [
        (
            passage_body,
            passage,
        )
    ]


def test_structural_fallback_follows_source_native_next_until_anchor():
    query = "unseen anchored tafsir"

    search_url = (
        build_dorar_tafsir_search_url(
            query
        )
    )

    collection = (
        "https://dorar.net/tafseer/2"
    )

    first = (
        "https://dorar.net/tafseer/2/1"
    )

    second = (
        "https://dorar.net/tafseer/2/2"
    )

    first_body = (
        '<h6>الآيات (1-5)</h6>'
        '<a href="/tafseer/2/2">'
        'التالي'
        '</a>'
    ).encode()

    second_body = (
        "<h6>الآيات (6-7)</h6>"
    ).encode()

    transport = FakeTransport(
        {
            search_url: b"<html></html>",
            collection: (
                b'<a href="/tafseer/2/1">'
                b"first"
                b"</a>"
            ),
            first: first_body,
            second: second_body,
        }
    )

    gate = FakeGate()

    result = DorarTafsirRetriever(
        transport=transport,
        gate=gate,
    ).search(
        query,
        limit=1,
        required_quran_references=(
            "2:6",
        ),
    )

    assert len(result.passages) == 1

    assert (
        result.passages[0].canonical_url
        == second
    )

    assert (
        "2:6"
        in result.passages[0].quran_references
    )

    assert gate.calls == [
        (
            first_body,
            first,
        ),
        (
            second_body,
            second,
        ),
    ]

    assert transport.calls == [
        (
            search_url,
            DorarFetchPurpose.DISCOVERY,
        ),
        (
            collection,
            DorarFetchPurpose.DISCOVERY,
        ),
        (
            first,
            DorarFetchPurpose.EVIDENCE,
        ),
        (
            second,
            DorarFetchPurpose.EVIDENCE,
        ),
    ]


def test_structural_fallback_never_crosses_surah_boundary():
    query = "anchored no cross surah"

    search_url = (
        build_dorar_tafsir_search_url(
            query
        )
    )

    collection = (
        "https://dorar.net/tafseer/2"
    )

    first = (
        "https://dorar.net/tafseer/2/1"
    )

    first_body = (
        '<h6>الآيات (1-5)</h6>'
        '<a href="/tafseer/3/1">'
        'التالي'
        '</a>'
    ).encode()

    transport = FakeTransport(
        {
            search_url: b"<html></html>",
            collection: (
                b'<a href="/tafseer/2/1">'
                b"first"
                b"</a>"
            ),
            first: first_body,
        }
    )

    result = DorarTafsirRetriever(
        transport=transport,
        gate=FakeGate(),
    ).search(
        query,
        limit=1,
        required_quran_references=(
            "2:6",
        ),
    )

    assert result.passages == ()

    assert transport.calls == [
        (
            search_url,
            DorarFetchPurpose.DISCOVERY,
        ),
        (
            collection,
            DorarFetchPurpose.DISCOVERY,
        ),
        (
            first,
            DorarFetchPurpose.EVIDENCE,
        ),
    ]
