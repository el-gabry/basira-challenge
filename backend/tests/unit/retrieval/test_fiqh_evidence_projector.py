from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.retrieval.fiqh_evidence_projector import (
    FiqhEvidenceProjector,
)


def _passage(
    text: str,
) -> ScholarlyPassage:
    return ScholarlyPassage(
        passage_id="book:1:page:10",
        source_id="shamela-test",
        domain=ScholarlyDomain.FIQH,
        work_id="book-1",
        work_title="كتاب فقهي",
        text=text,
        section_title="نواقض الوضوء",
        page="10",
        metadata={
            "shamela_book_id": "book-1",
            "shamela_page_id": "10",
            "snapshot_id": "snapshot-1",
            "snapshot_sha256": "a" * 64,
            "madhhab": "shafii",
        },
    )


def test_returns_only_relevant_exact_fragment():
    source = (
        "باب المياه. "
        "ولا ينتقض الوضوء بالنوم اليسير. "
        "وينتقض الوضوء بلمس المرأة عند تحقق شروطه. "
        "ثم ذكر المصنف مسائل المسح على الخفين."
    )

    passage = _passage(
        source
    )

    projected = (
        FiqhEvidenceProjector()
        .project_passage(
            passage,
            query_hints=(
                "لمس المرأة ونقض الوضوء",
            ),
        )
    )

    assert projected is not None

    assert projected.text == (
        "وينتقض الوضوء بلمس المرأة "
        "عند تحقق شروطه."
    )

    assert (
        projected.text
        in source
    )

    assert (
        "باب المياه"
        not in projected.text
    )

    assert (
        "المسح على الخفين"
        not in projected.text
    )


def test_uses_adaptive_classical_query_hint():
    source = (
        "وتجري أحكام الصرف عند اتحاد علة الثمنية. "
        "ويشترط التقابض في المجلس في موضعه. "
        "وهذه مسألة أخرى في الإجارة."
    )

    passage = _passage(
        source
    )

    projected = (
        FiqhEvidenceProjector()
        .project_passage(
            passage,
            query_hints=(
                "ما حكم البيتكوين؟",
                "الثمنية الصرف التقابض",
            ),
        )
    )

    assert projected is not None

    assert (
        "الصرف"
        in projected.text
        or "التقابض"
        in projected.text
        or "الثمنية"
        in projected.text
    )

    assert (
        projected.text
        in source
    )


def test_expands_only_when_fragment_depends_on_previous_context():
    source = (
        "ويشترط القبض قبل التفرق في هذا النوع. "
        "ويثبت الحكم على ما تقدم. "
        "ثم انتقل إلى مسألة أخرى."
    )

    passage = _passage(
        source
    )

    projected = (
        FiqhEvidenceProjector()
        .project_passage(
            passage,
            query_hints=(
                "يثبت الحكم ما تقدم",
            ),
        )
    )

    assert projected is not None

    assert projected.text == (
        "ويشترط القبض قبل التفرق في هذا النوع. "
        "ويثبت الحكم على ما تقدم."
    )

    assert (
        projected.metadata[
            "projection_context_expanded"
        ]
        == "true"
    )


def test_no_match_fails_narrow_instead_of_returning_whole_page():
    source = (
        "هذا نص في أحكام الطهارة. "
        "وهذا نص آخر في أحكام الصلاة."
    )

    passage = _passage(
        source
    )

    projected = (
        FiqhEvidenceProjector()
        .project_passage(
            passage,
            query_hints=(
                "البيتكوين والعملات الرقمية",
            ),
        )
    )

    assert projected is None


def test_projection_preserves_parent_provenance():
    source = (
        "مقدمة. "
        "ويشترط التقابض في المجلس. "
        "خاتمة."
    )

    passage = _passage(
        source
    )

    projected = (
        FiqhEvidenceProjector()
        .project_passage(
            passage,
            query_hints=(
                "التقابض",
            ),
        )
    )

    assert projected is not None

    assert (
        projected.source_id
        == passage.source_id
    )

    assert (
        projected.work_id
        == passage.work_id
    )

    assert (
        projected.page
        == passage.page
    )

    assert (
        projected.metadata[
            "parent_passage_id"
        ]
        == passage.passage_id
    )

    start = int(
        projected.metadata[
            "projection_char_start"
        ]
    )
    end = int(
        projected.metadata[
            "projection_char_end"
        ]
    )

    assert (
        source[start:end]
        == projected.text
    )


def test_query_conjunction_before_definite_article_matches_source_token():
    source = (
        "يشترط التقابض في المجلس "
        "في هذه الصورة."
    )

    passage = _passage(
        source
    )

    projected = (
        FiqhEvidenceProjector()
        .project_passage(
            passage,
            query_hints=(
                "بيع الذهب والتقابض",
            ),
        )
    )

    assert projected is not None

    assert (
        "التقابض"
        in projected.text
    )

    assert (
        projected.text
        in source
    )
