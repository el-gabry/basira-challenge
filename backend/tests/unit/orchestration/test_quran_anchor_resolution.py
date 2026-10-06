from __future__ import annotations

from basira.models.quran import (
    QuranVerse,
)
from basira.orchestration.evidence_acceptance import (
    AnchorKind,
    AnchorOrigin,
)
from basira.orchestration.quran_anchor_resolution import (
    AnchorResolutionDisposition,
    QuranCanonicalAnchorResolver,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.sources.quran.repository import (
    QuranRepository,
)


def verse(
    *,
    surah: int,
    ayah: int,
    text: str,
) -> QuranVerse:
    return QuranVerse(
        source_id="quran:test",
        surah_number=surah,
        ayah_number=ayah,
        text_uthmani=text,
        text_search=text,
    )


def repository() -> QuranRepository:
    return QuranRepository(
        (
            verse(
                surah=2,
                ayah=255,
                text=(
                    "الله لا إله إلا هو الحي القيوم "
                    "لا تأخذه سنة ولا نوم "
                    "وسع كرسيه السماوات والأرض "
                    "ولا يؤوده حفظهما "
                    "وهو العلي العظيم"
                ),
            ),
            verse(
                surah=2,
                ayah=43,
                text=("وأقيموا الصلاة وآتوا الزكاة واركعوا مع الراكعين"),
            ),
            verse(
                surah=3,
                ayah=1,
                text=("إن الله غفور رحيم في هذا المثال"),
            ),
            verse(
                surah=4,
                ayah=1,
                text=("إن الله غفور رحيم في مثال آخر"),
            ),
        )
    )


def understand(
    text: str,
):
    return BasiraQueryUnderstandingService().understand(text)


def resolver() -> QuranCanonicalAnchorResolver:
    return QuranCanonicalAnchorResolver(
        repository=repository(),
    )


def test_explicit_reference_is_verified():
    result = resolver().resolve(understand("اشرح الآية 2:255"))

    assert result.disposition is AnchorResolutionDisposition.RESOLVED

    assert len(result.anchors) == 1

    anchor = result.anchors[0]

    assert anchor.reference == "2:255"

    assert anchor.kind is AnchorKind.QURAN_AYAH

    assert anchor.origin is AnchorOrigin.EXPLICIT_REFERENCE


def test_invalid_explicit_reference_fails_closed():
    result = resolver().resolve(understand("اشرح الآية 2:999"))

    assert result.disposition is AnchorResolutionDisposition.ASK_USER

    assert result.anchors == ()

    assert result.reason == ("explicit_quran_reference_not_found")


def test_canonical_quote_resolves_to_2_255():
    result = resolver().resolve(
        understand("ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟")
    )

    assert result.disposition is AnchorResolutionDisposition.RESOLVED

    assert result.anchors[0].reference == "2:255"

    assert result.anchors[0].origin is AnchorOrigin.CANONICAL_TEXT_MATCH

    assert "وسع كرسيه السماوات والارض" in (result.anchors[0].matched_text or "")


def test_plain_concept_does_not_secretly_become_2_255():
    result = resolver().resolve(understand("ما هو الكرسي؟"))

    assert result.disposition is AnchorResolutionDisposition.NO_ANCHOR

    assert result.anchors == ()

    assert result.candidate_references == ()


def test_anchor_seeking_without_canonical_identity_asks_user():
    result = resolver().resolve(understand("ما معنى هذه الآية؟"))

    assert result.disposition is AnchorResolutionDisposition.ASK_USER

    assert result.anchors == ()


def test_multiple_canonical_matches_are_bounded_not_hardened():
    result = resolver().resolve(understand("إن الله غفور رحيم"))

    assert result.disposition is AnchorResolutionDisposition.BOUNDED_BRANCH

    assert result.anchors == ()

    assert result.candidate_references == (
        "3:1",
        "4:1",
    )


def test_explicit_reference_conflicting_with_quote_asks_user():
    result = resolver().resolve(
        understand("اشرح 2:43 في قوله تعالى وسع كرسيه السماوات والأرض")
    )

    assert result.disposition is AnchorResolutionDisposition.ASK_USER

    assert result.anchors == ()

    assert "2:43" in result.candidate_references

    assert "2:255" in result.candidate_references

    assert result.reason == ("explicit_reference_conflicts_with_canonical_text")


def test_planner_inference_is_not_part_of_verified_resolution():
    result = resolver().resolve(understand("ما هو الكرسي؟"))

    assert all(
        anchor.origin is not AnchorOrigin.PLANNER_INFERENCE for anchor in result.anchors
    )
