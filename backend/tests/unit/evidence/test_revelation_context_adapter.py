from basira.evidence.models import (
    EvidenceDomain,
)
from basira.evidence.scholarly_adapter import (
    ScholarlyEvidenceAdapter,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)


def test_revelation_context_has_dedicated_domain() -> None:
    passage = ScholarlyPassage(
        passage_id=(
            "surahapp-ayat-nozool:58:1"
        ),
        source_id=(
            "surahapp-ayat-nozool"
        ),
        domain=(
            ScholarlyDomain
            .REVELATION_CONTEXT
        ),
        work_id="ayat-nozool",
        work_title=(
            "صحيح أسباب النزول"
        ),
        text=(
            "نص سبب النزول."
        ),
        surah_number=58,
        ayah_start=1,
        ayah_end=1,
    )

    evidence = (
        ScholarlyEvidenceAdapter()
        .from_passage(
            passage
        )
    )

    assert (
        evidence.domain
        == EvidenceDomain
        .REVELATION_CONTEXT
    )

    assert (
        evidence.reference
        == "58:1"
    )

    assert (
        evidence.claim_type
        == (
            "revelation_context"
            "_passage"
        )
    )
