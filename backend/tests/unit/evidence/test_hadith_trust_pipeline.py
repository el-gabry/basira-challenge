from __future__ import annotations

from basira.evidence.bundle import (
    EvidenceBundleBuilder,
    EvidenceRequirementState,
)
from basira.evidence.decision import (
    EvidenceDecisionAction,
    EvidenceDecisionPolicy,
    EvidenceDecisionReason,
)
from basira.evidence.models import EvidenceDomain
from basira.models.hadith import HadithGradeCategory
from basira.models.source_manifest import (
    IntegrityStatus,
    SourceDomain,
    SourceManifest,
    SourceRole,
    SourceStatus,
)
from basira.retrieval.hadith_index import HadithLocalIndex
from basira.retrieval.hadith_retriever import HadithDomainRetriever
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import BasiraRetrievalPlanner
from basira.retrieval.unified_retriever import BasiraUnifiedRetriever
from basira.sources.hadith.hadeethenc.models import (
    HadeethEncLanguage,
    HadeethEncRelease,
)
from basira.sources.hadith.hadeethenc.parser import (
    HadeethEncOfficialParser,
)
from basira.sources.registry import TrustedSourceRegistry
from basira.sources.runtime_access import FailClosedSourceRuntime

AR_RELEASE = HadeethEncRelease(
    language=HadeethEncLanguage.ARABIC,
    version="v1.7.0",
    last_updated="2025-11-12 00:00:55",
    source_url="https://hadeethenc.com/ar",
    update_check_url=("https://hadeethenc.com/en/check/ar/v1.7.0"),
)

EN_RELEASE = HadeethEncRelease(
    language=HadeethEncLanguage.ENGLISH,
    version="v1.25.0",
    last_updated="2026-05-10 17:43:35",
    source_url="https://hadeethenc.com/en",
    update_check_url=("https://hadeethenc.com/en/check/en/v1.25.0"),
)


def conflicting_record():
    arabic = {
        "id": 65065,
        "title": "عنوان",
        "hadith_text": "نص الحديث",
        "explanation": "شرح",
        "word_meanings": "",
        "benefits": "",
        "grade": "ضعيف",
        "takhrij": "رواه الترمذي",
        "link": ("https://hadeethenc.com/ar/browse/hadith/65065"),
    }

    english = {
        "id": 65065,
        "title_ar": "عنوان",
        "title": "Title",
        "hadith_text_ar": "نص الحديث",
        "hadith_text": "Hadith text",
        "explanation_ar": "شرح",
        "explanation": "Explanation",
        "benefits_ar": "",
        "benefits": "",
        "grade_ar": "صحيح",
        "takhrij_ar": "رواه الترمذي",
        "grade": "[Authentic hadith]",
        "takhrij": "Reported by al-Tirmidhi",
        "lang": "en",
        "link": ("https://hadeethenc.com/en/browse/hadith/65065"),
    }

    return HadeethEncOfficialParser().parse(
        arabic,
        arabic_release=AR_RELEASE,
        english_payload=english,
        english_release=EN_RELEASE,
    )


def test_real_semantics_conflict_reaches_expert_decision() -> None:
    record = conflicting_record()

    assert len(record.grade_assessments) == 2

    assert {assessment.grade_text for assessment in record.grade_assessments} == {
        "ضعيف",
        "صحيح",
    }

    assert {assessment.category for assessment in record.grade_assessments} == {
        HadithGradeCategory.DAIF,
        HadithGradeCategory.SAHIH,
    }

    manifest = SourceManifest(
        source_id="hadeethenc-official",
        source_name=("HadeethEnc Official Hadith Releases"),
        domain=SourceDomain.HADITH,
        role=(SourceRole.AUTHORITATIVE_REFERENCE),
        status=SourceStatus.APPROVED,
        integrity_status=(IntegrityStatus.VERIFIED),
    )

    runtime = FailClosedSourceRuntime(TrustedSourceRegistry([manifest]))

    index = HadithLocalIndex(runtime=runtime)

    index.add(record)

    understanding = BasiraQueryUnderstandingService().understand(
        "ما صحة حديث رقم 65065؟"
    )

    assert understanding.primary_intent is BasiraIntent.HADITH_AUTHENTICITY

    plan = BasiraRetrievalPlanner().build(understanding)

    result = BasiraUnifiedRetriever(
        {
            EvidenceDomain.HADITH: HadithDomainRetriever(
                index=index,
                default_collection_id=("hadeethenc"),
            )
        }
    ).retrieve(plan)

    grade_nodes = tuple(
        node for node in result.evidence if node.claim_type == "hadith_grade"
    )

    assert len(grade_nodes) == 2

    assert {node.text for node in grade_nodes} == {
        "ضعيف",
        "صحيح",
    }

    assert {node.reference for node in grade_nodes} == {
        "hadeethenc:65065",
        ("hadeethenc:65065:official-en:v1.25.0:grade_ar"),
    }

    bundle = EvidenceBundleBuilder().build(result)

    assert all(
        assessment.state is EvidenceRequirementState.SATISFIED
        for assessment in bundle.required_assessments
    )

    assert len(bundle.conflicts) == 1

    conflict = bundle.conflicts[0]

    assert conflict.conflict_type.value == "hadith_grade"

    assert conflict.group_id == ("hadeethenc:65065:grade:cross-version")

    assert set(conflict.evidence_ids) == {
        ("hadeethenc-official:65065:grade:0"),
        ("hadeethenc-official:65065:grade:1"),
    }

    decision = EvidenceDecisionPolicy().decide(
        understanding=understanding,
        bundle=bundle,
    )

    assert decision.action is EvidenceDecisionAction.ESCALATE_TO_EXPERT

    assert decision.reasons == (EvidenceDecisionReason.EVIDENCE_CONFLICT,)

    assert decision.unresolved_needs == ()
