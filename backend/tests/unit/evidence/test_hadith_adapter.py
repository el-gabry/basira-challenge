from __future__ import annotations

from basira.evidence.hadith_adapter import (
    HadithEvidenceAdapter,
)
from basira.models.hadith import (
    HadithGradeAssessment,
    HadithGradeCategory,
    HadithRecord,
    HadithReference,
    HadithTextVariant,
)
from basira.retrieval.hadith_index import (
    HadithEvidenceBundle,
)
from basira.verification.hadith_identity import (
    HadithCanonicalIdentity,
    HadithIdentityScope,
)


def test_hadith_bundle_becomes_separate_evidence_nodes() -> None:
    record = HadithRecord(
        record_id=(
            "hadeethenc-official:1751"
        ),
        primary_reference=(
            HadithReference(
                source_id=(
                    "hadeethenc-official"
                ),
                collection_id="hadeethenc",
                hadith_number="1751",
                source_reference=(
                    "hadeethenc:1751"
                ),
            )
        ),
        text_variants=(
            HadithTextVariant(
                source_id=(
                    "hadeethenc-official"
                ),
                arabic_text="نص الحديث",
                english_translation=(
                    "Hadith text"
                ),
                translation_source_id=(
                    "hadeethenc-official"
                ),
            ),
        ),
        grade_assessments=(
            HadithGradeAssessment(
                source_id=(
                    "hadeethenc-official"
                ),
                grader_name=(
                    "HadeethEnc editorial board"
                ),
                grade_text="صحيح",
                category=(
                    HadithGradeCategory.SAHIH
                ),
                source_reference=(
                    "hadeethenc:1751:grade"
                ),
                source_url=(
                    "https://hadeethenc.com/"
                    "ar/browse/hadith/1751"
                ),
                conflict_group=(
                    "hadeethenc:1751:"
                    "grade:test"
                ),
                conflict_type=(
                    "cross_version_grade_conflict"
                ),
            ),
        ),
    )

    bundle = HadithEvidenceBundle(
        identity=(
            HadithCanonicalIdentity(
                key="hadeethenc:1751",
                scope=(
                    HadithIdentityScope
                    .SHARED_EXTERNAL_REFERENCE
                ),
                collection_id=(
                    "hadeethenc"
                ),
                hadith_number="1751",
            )
        ),
        records=(record,),
    )

    nodes = (
        HadithEvidenceAdapter()
        .from_bundle(bundle)
    )

    claim_types = {
        node.claim_type
        for node in nodes
    }

    assert claim_types == {
        "hadith_text",
        "hadith_translation",
        "hadith_grade",
    }

    grade = next(
        node
        for node in nodes
        if (
            node.claim_type
            == "hadith_grade"
        )
    )

    assert grade.text == "صحيح"
    assert grade.topic == "sahih"

    assert (
        grade.author_name
        == "HadeethEnc editorial board"
    )

    assert (
        grade.reference
        == "hadeethenc:1751:grade"
    )

    assert (
        grade.source_url
        == (
            "https://hadeethenc.com/"
            "ar/browse/hadith/1751"
        )
    )

    assert (
        grade.conflict_group
        == (
            "hadeethenc:1751:"
            "grade:test"
        )
    )

    assert (
        grade.conflict_type
        == "cross_version_grade_conflict"
    )

    assert (
        grade.related_hadith
        == ("hadeethenc:1751",)
    )
