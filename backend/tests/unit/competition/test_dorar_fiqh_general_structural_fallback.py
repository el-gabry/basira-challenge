from types import SimpleNamespace

from basira.competition.dorar_fiqh import (
    DorarFiqhArticle,
    extract_primary_article_text,
)
from basira.competition.dorar_fiqh_adapter import (
    _project_single_article_structurally,
)


def test_dorar_h1_may_extend_beyond_title() -> None:
    title = (
        "المطلب الثالث: البيع بالتقسيط "
        "- الموسوعة الفقهية - الدرر السنية"
    )

    html = """
    <html>
      <head>
        <title>
          المطلب الثالث: البيع بالتقسيط
          - الموسوعة الفقهية - الدرر السنية
        </title>
      </head>
      <body>
        <h1>
          المطلب الثالث: البيع بالتقسيط
          يجوز البيع بالتقسيط بشروطه المعتبرة.
        </h1>
        <p>
          وهذا نص تابع للمادة.
        </p>
      </body>
    </html>
    """

    body = extract_primary_article_text(
        html=html,
        article_title=title,
    )

    assert (
        "يجوز البيع بالتقسيط"
        in body
    )


def test_single_ruling_article_becomes_exact_fiqh_evidence() -> None:
    text = (
        "البيع بالتقسيط هو بيع بثمن مؤجل. "
        "يجوز البيع بالتقسيط بشروطه المعتبرة. "
        "وهذا نص آخر في المسألة."
    )

    article = DorarFiqhArticle(
        source_id="dorar:fiqh:9999",
        canonical_url=(
            "https://dorar.net/feqhia/9999/"
            "example"
        ),
        article_title=(
            "البيع بالتقسيط "
            "- الموسوعة الفقهية "
            "- الدرر السنية"
        ),
        full_text=text,
        explicit_disagreement=False,
        explicit_consensus_language=False,
        positions=(),
    )

    admission = SimpleNamespace(
        response_sha256="a" * 64,
        provider="Dorar al-Sunniyyah",
    )

    nodes = (
        _project_single_article_structurally(
            query=(
                "ما حكم البيع بالتقسيط؟"
            ),
            article=article,
            admission=admission,  # type: ignore[arg-type]
        )
    )

    assert nodes

    root = nodes[0]

    assert (
        root.claim_type
        == "fiqh_position"
    )

    assert (
        root.text
        in text
    )

    assert (
        root.source_id
        == "dorar:fiqh:9999"
    )

    assert (
        root.source_version
        == "a" * 64
    )


def test_structural_fallback_does_not_invent_disagreement() -> None:
    article = DorarFiqhArticle(
        source_id="dorar:fiqh:9998",
        canonical_url=(
            "https://dorar.net/feqhia/9998/"
            "example"
        ),
        article_title=(
            "بيع الذهب "
            "- الموسوعة الفقهية "
            "- الدرر السنية"
        ),
        full_text=(
            "في بيع الذهب يشترط التقابض "
            "في هذه الصورة."
        ),
        explicit_disagreement=False,
        explicit_consensus_language=False,
        positions=(),
    )

    admission = SimpleNamespace(
        response_sha256="b" * 64,
        provider="Dorar al-Sunniyyah",
    )

    nodes = (
        _project_single_article_structurally(
            query="بيع الذهب والتقابض",
            article=article,
            admission=admission,  # type: ignore[arg-type]
        )
    )

    assert nodes

    assert not any(
        node.claim_type
        == "fiqh_disagreement"
        for node in nodes
    )

    assert not any(
        node.claim_type
        == "fiqh_ruling"
        for node in nodes
    )



def test_article_title_cannot_bootstrap_unrelated_body():
    article = DorarFiqhArticle(
        source_id="dorar:fiqh:9901",
        canonical_url=(
            "https://dorar.net/feqhia/9901/"
            "example"
        ),
        article_title=(
            "البيع بالتقسيط "
            "- الموسوعة الفقهية "
            "- الدرر السنية"
        ),
        full_text=(
            "المبحث الرابع: بيع السلم. "
            "وهذا نص لا يتناول التقسيط."
        ),
        explicit_disagreement=False,
        explicit_consensus_language=False,
        positions=(),
    )

    admission = SimpleNamespace(
        response_sha256="c" * 64,
        provider="Dorar al-Sunniyyah",
    )

    nodes = (
        _project_single_article_structurally(
            query="ما حكم البيع بالتقسيط؟",
            article=article,
            admission=admission,  # type: ignore[arg-type]
        )
    )

    assert nodes == ()


def test_one_shared_word_is_not_enough_for_multi_term_issue():
    article = DorarFiqhArticle(
        source_id="dorar:fiqh:9902",
        canonical_url=(
            "https://dorar.net/feqhia/9902/"
            "example"
        ),
        article_title=(
            "زكاة الذهب الأبيض "
            "- الموسوعة الفقهية "
            "- الدرر السنية"
        ),
        full_text=(
            "الذهب الأبيض تجري عليه "
            "أحكام الزكاة."
        ),
        explicit_disagreement=False,
        explicit_consensus_language=False,
        positions=(),
    )

    admission = SimpleNamespace(
        response_sha256="d" * 64,
        provider="Dorar al-Sunniyyah",
    )

    nodes = (
        _project_single_article_structurally(
            query="ما حكم بيع الذهب؟",
            article=article,
            admission=admission,  # type: ignore[arg-type]
        )
    )

    assert nodes == ()


def test_dorar_presentation_chrome_never_becomes_fiqh_body():
    from basira.competition.dorar_fiqh import (
        extract_primary_article_text,
    )

    html = """
    <html>
      <head>
        <title>
          البيع بالتقسيط
          - الموسوعة الفقهية
          - الدرر السنية
        </title>
      </head>
      <body>
        <h1>البيع بالتقسيط</h1>
        محتويات الصفحة
        انظر أيضا
        الرابط المختصر
        يجوز البيع بالتقسيط.
      </body>
    </html>
    """

    body = extract_primary_article_text(
        html=html,
        article_title=(
            "البيع بالتقسيط "
            "- الموسوعة الفقهية "
            "- الدرر السنية"
        ),
    )

    assert body.startswith(
        "يجوز البيع بالتقسيط"
    )

    assert (
        "محتويات الصفحة"
        not in body
    )

    assert (
        "الرابط المختصر"
        not in body
    )


def test_three_term_issue_cannot_drop_qualifier():
    article = DorarFiqhArticle(
        source_id="dorar:fiqh:9903",
        canonical_url=(
            "https://dorar.net/feqhia/"
            "9903/example"
        ),
        article_title=(
            "بيع الذهب "
            "- الموسوعة الفقهية "
            "- الدرر السنية"
        ),
        full_text=(
            "بيع الذهب له أحكام "
            "متعلقة بالصرف."
        ),
        explicit_disagreement=False,
        explicit_consensus_language=False,
        positions=(),
    )

    admission = SimpleNamespace(
        response_sha256="e" * 64,
        provider="Dorar al-Sunniyyah",
    )

    nodes = (
        _project_single_article_structurally(
            query=(
                "بيع الذهب بالتقسيط"
            ),
            article=article,
            admission=admission,  # type: ignore[arg-type]
        )
    )

    assert nodes == ()
