from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from basira.competition.dorar_fiqh_english_adapter import (
    DorarEnglishFiqhSourceClient,
    DorarFiqhEnglishEvidenceAdapter,
    parse_english_fiqh_page,
)
from basira.competition.dorar_fiqh_english_admission import (
    DorarEnglishFiqhAdmissionError,
    DorarEnglishFiqhRuntimeGate,
)
from basira.competition.dorar_transport import (
    DorarFetchPurpose,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalRequest,
)

ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)


INDEX = b"""
<html><body>
<a href="/en/feqhia/44">
Section I: Defining Nullifiers of Ablution:
What Nullifies it and What Does Not
</a>
<a href="/en/feqhia/500">
Marriage and Family
</a>
</body></html>
"""


ARTICLE = b"""
<html>
<head>
<title>
Summary of Feqh - Section I:
Defining Nullifiers of Ablution
</title>
</head>
<body>

<div>
<b>- Touching the private parts:</b><br>
Scholars have differed over touching the private
parts and whether it nullifies ablution according
to two views:<br>
<b>The first:</b>
It nullifies ablution.
This is the position of the Shafi`is
and Hanbalis.<br>
<b>The second:</b>
It does not nullify ablution.
This is the position of the Hanafis
and Malikis.
</div>

<div>
Unrelated material without a two-view structure.
</div>

</body>
</html>
"""


class Transport:
    def fetch(
        self,
        url: str,
        *,
        purpose: DorarFetchPurpose,
    ):
        if (
            purpose
            is DorarFetchPurpose.DISCOVERY
        ):
            body = INDEX

            return SimpleNamespace(
                final_url=(
                    "https://dorar.net/en/feqhia"
                ),
                body=body,
                response_sha256=(
                    sha256(body).hexdigest()
                ),
                content_type="text/html",
            )

        assert (
            url
            == "https://dorar.net/en/feqhia/44"
        )

        body = ARTICLE

        return SimpleNamespace(
            final_url=url,
            body=body,
            response_sha256=(
                sha256(body).hexdigest()
            ),
            content_type="text/html",
        )


def test_parser_extracts_source_authored_positions() -> None:
    page = parse_english_fiqh_page(
        html=ARTICLE.decode("utf-8"),
        canonical_url=(
            "https://dorar.net/en/feqhia/44"
        ),
        article_id="44",
    )

    assert len(page.issues) == 1

    issue = page.issues[0]

    assert len(issue.positions) == 2

    assert (
        issue.positions[0].madhhabs
        == (
            "shafii",
            "hanbali",
        )
    )

    assert (
        issue.positions[1].madhhabs
        == (
            "hanafi",
            "maliki",
        )
    )

    assert (
        issue.positions[0].text
        in issue.full_text
    )

    assert (
        issue.positions[1].text
        in issue.full_text
    )


def test_adapter_returns_source_native_english() -> None:
    adapter = (
        DorarFiqhEnglishEvidenceAdapter(
            client=(
                DorarEnglishFiqhSourceClient(
                    transport=Transport()
                )
            ),
            gate=(
                DorarEnglishFiqhRuntimeGate
                .from_repo(ROOT)
            ),
        )
    )

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(
                OfficialDomain.GENERAL_FIQH
            ),
            query=(
                "Does touching the private part "
                "invalidate wudu?"
            ),
            limit=5,
        )
    )

    assert len(nodes) == 4

    assert {
        node.authority_scope
        for node in nodes
    } == {
        "hanafi",
        "maliki",
        "shafii",
        "hanbali",
    }

    assert all(
        node.source_id
        == "dorar:fiqh:en:44"
        for node in nodes
    )

    assert all(
        node.source_url
        == "https://dorar.net/en/feqhia/44"
        for node in nodes
    )

    assert all(
        node.claim_type
        == "fiqh_position"
        for node in nodes
    )

    assert all(
        node.work_id
        == "dorar-fiqh-en"
        for node in nodes
    )


def test_gate_rejects_arabic_route() -> None:
    gate = (
        DorarEnglishFiqhRuntimeGate
        .from_repo(ROOT)
    )

    with pytest.raises(
        DorarEnglishFiqhAdmissionError
    ):
        gate.admit(
            canonical_url=(
                "https://dorar.net/feqhia/44"
            ),
            body=ARTICLE,
            response_sha256=(
                sha256(ARTICLE).hexdigest()
            ),
            content_type="text/html",
        )


def test_gate_rejects_tampered_hash() -> None:
    gate = (
        DorarEnglishFiqhRuntimeGate
        .from_repo(ROOT)
    )

    with pytest.raises(
        DorarEnglishFiqhAdmissionError
    ):
        gate.admit(
            canonical_url=(
                "https://dorar.net/en/feqhia/44"
            ),
            body=ARTICLE + b"tampered",
            response_sha256=(
                sha256(ARTICLE).hexdigest()
            ),
            content_type="text/html",
        )


def test_query_returns_only_best_matching_issue() -> None:
    multi_article = b"""
    <html>
    <head>
    <title>
    Summary of Feqh - Nullifiers of Ablution
    </title>
    </head>
    <body>

    <div>
    <b>- Vaginal wind:</b><br>
    Scholars differed concerning vaginal wind:
    <br>
    <b>The first:</b>
    It nullifies ablution.
    This is the position of the Shafi`is
    and Hanbalis.
    <br>
    <b>The second:</b>
    It does not nullify ablution.
    This is the position of the Hanafis
    and Malikis.
    </div>

    <div>
    <b>- Touching the private parts:</b><br>
    Scholars differed concerning touching
    the private parts:
    <br>
    <b>The first:</b>
    It nullifies ablution.
    This is the position of the Shafi`is
    and Hanbalis.
    <br>
    <b>The second:</b>
    It does not nullify ablution.
    This is the position of the Hanafis
    and Malikis.
    </div>

    </body>
    </html>
    """

    class MultiIssueTransport:
        def fetch(
            self,
            url: str,
            *,
            purpose: DorarFetchPurpose,
        ):
            if (
                purpose
                is DorarFetchPurpose.DISCOVERY
            ):
                body = INDEX

                return SimpleNamespace(
                    final_url=(
                        "https://dorar.net/en/feqhia"
                    ),
                    body=body,
                    response_sha256=(
                        sha256(body).hexdigest()
                    ),
                    content_type="text/html",
                )

            assert (
                url
                == "https://dorar.net/en/feqhia/44"
            )

            return SimpleNamespace(
                final_url=url,
                body=multi_article,
                response_sha256=(
                    sha256(
                        multi_article
                    ).hexdigest()
                ),
                content_type="text/html",
            )

    adapter = (
        DorarFiqhEnglishEvidenceAdapter(
            client=(
                DorarEnglishFiqhSourceClient(
                    transport=(
                        MultiIssueTransport()
                    )
                )
            ),
            gate=(
                DorarEnglishFiqhRuntimeGate
                .from_repo(ROOT)
            ),
        )
    )

    nodes = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(
                OfficialDomain.GENERAL_FIQH
            ),
            query=(
                "Does touching the private part "
                "invalidate wudu?"
            ),
            limit=5,
        )
    )

    assert nodes

    assert len(
        {
            node.conflict_group
            for node in nodes
        }
    ) == 1

    assert all(
        "Touching the private parts"
        in (node.reference or "")
        for node in nodes
    )

    assert all(
        "Vaginal wind"
        not in (node.reference or "")
        for node in nodes
    )


def test_generic_ablution_terms_cannot_admit_wrong_issue() -> None:
    query = (
        "Does touching the private part "
        "invalidate wudu?"
    )

    from basira.competition.dorar_fiqh_english_adapter import (
        _score,
        _tokens,
        _topic_tokens,
    )

    topic = _topic_tokens(query)

    assert "touching" in topic
    assert "private" in topic
    assert "ablution" not in topic
    assert "wudu" not in topic
    assert "invalidate" not in topic

    wrong_context = (
        "Dry ablution is invalidated by "
        "the presence of water."
    )

    correct_context = (
        "Touching the private parts."
    )

    wrong_overlap = len(
        topic
        & _tokens(
            wrong_context,
            expand=False,
        )
    )

    correct_overlap = len(
        topic
        & _tokens(
            correct_context,
            expand=False,
        )
    )

    assert wrong_overlap == 0
    assert correct_overlap > 0

    # Generic vocabulary may still have a lexical
    # score, but cannot cross the hard topic gate.
    assert _score(
        query,
        wrong_context,
    ) >= 0


def test_one_div_can_contain_multiple_bounded_fiqh_issues() -> None:
    html = """
    <html>
    <head>
    <title>
    Summary of Feqh - Nullifiers of Ablution
    </title>
    </head>
    <body>

    <div>
    <b>- Touching the private parts:</b><br>

    <b>1- A man touching his penis:</b><br>
    Scholars have differed over ablution being
    nullified due to a man touching his penis
    according to two views:<br>
    <b>The first:</b>
    It nullifies ablution.
    This is the position of the Malikis,
    Shafi`is and Hanbalis.<br>
    <b>The second:</b>
    It does not nullify ablution.
    This is the position of the Hanafis
    and some Malikis.<br>

    <b>2- A woman touching her private parts:</b><br>
    Scholars have differed over ablution being
    nullified due to a woman touching her private
    parts according to two views:<br>
    <b>The first:</b>
    A woman touching her private parts does not
    nullify ablution.
    This is the position of the Hanafis
    and Malikis.<br>
    <b>The second:</b>
    A woman touching her private parts nullifies
    ablution.
    This is the position of the Shafi`is
    and Hanbalis.<br>

    <b>3- Touching another's private parts:</b><br>
    Scholars have differed over touching another's
    private parts according to two views:<br>
    <b>The first:</b>
    It nullifies ablution.
    This is the position of the Shafi`is
    and Hanbalis.<br>
    <b>The second:</b>
    It does not nullify ablution.
    This is the position of the Hanafis
    and Malikis.

    </div>
    </body>
    </html>
    """

    page = parse_english_fiqh_page(
        html=html,
        canonical_url=(
            "https://dorar.net/en/feqhia/44"
        ),
        article_id="44",
    )

    assert len(page.issues) == 3

    woman = tuple(
        issue
        for issue in page.issues
        if (
            "woman touching her private parts"
            in issue.context.casefold()
        )
    )

    assert len(woman) == 1

    issue = woman[0]

    assert (
        issue.positions[0].madhhabs
        == (
            "hanafi",
            "maliki",
        )
    )

    assert (
        issue.positions[1].madhhabs
        == (
            "shafii",
            "hanbali",
        )
    )
