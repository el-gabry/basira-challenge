from types import SimpleNamespace

from basira.api.presenter import (
    _may_display_supporting_text,
    _supporting_excerpt,
)
from basira.models.source_usage import (
    EvidenceAuthorityLevel,
    RuntimeUse,
    SourceUsageRole,
)
from basira.sources.policy_catalog import (
    get_source_usage_policy,
)

SOURCE_ID = "dorar-tafsir-v1"


def test_dorar_tafsir_policy_allows_governed_public_support() -> None:
    policy = get_source_usage_policy(SOURCE_ID)

    assert policy.authority_level is EvidenceAuthorityLevel.ATTRIBUTED_SCHOLARLY

    assert SourceUsageRole.RETRIEVAL_CORPUS in policy.roles
    assert SourceUsageRole.SECONDARY_EVIDENCE in policy.roles

    assert policy.allows(RuntimeUse.RETRIEVE_PASSAGES)
    assert policy.allows(RuntimeUse.SUPPORT_ANSWER)
    assert policy.allows(RuntimeUse.CITE_TO_USER)

    assert policy.requires_human_review is False

    assert _may_display_supporting_text(source_id=SOURCE_ID)


def test_dorar_tafsir_supporting_text_is_bounded_excerpt() -> None:
    text = (
        "الكُرسيُّ جسمٌ عظيم، مخلوق بين يدي العرش، "
        "والعرش أعظم منه، والكرسي موضع القدمين. " * 12
    )

    node = SimpleNamespace(
        domain=SimpleNamespace(value="tafsir"),
        source_id=SOURCE_ID,
        text=text,
    )

    excerpt = _supporting_excerpt(node)

    assert excerpt is not None
    assert len(excerpt) <= 321
    assert excerpt != text
