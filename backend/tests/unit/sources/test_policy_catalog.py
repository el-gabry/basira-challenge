from __future__ import annotations

import pytest

from basira.models.source_usage import EvidenceAuthorityLevel, RuntimeUse
from basira.sources.policy_catalog import (
    SourceUsagePolicyNotFoundError,
    get_source_usage_policy,
    has_source_usage_policy,
    list_source_usage_policies,
)

EXPECTED_SOURCE_IDS = {
    "islamic-faith-qa",
    "kfgqpc-hafs-mirror-v18",
    "mafqa",
    "openiti",
    "quran-nlp",
    "sahm-fatwa-qa",
    "quranlab-hadith",
    "hadeethenc-official",
    "sanadset",
    "sunnah-ar-en-dataset",
    "tanzil-quran-v1.1-simple-plain",
    "tanzil-quran-v1.1-uthmani",
    "surahapp-tafsir-katheer",
    "surahapp-tafsir-saadi",
    "surahapp-tafsir-mokhtasar",
    "surahapp-ayat-nozool",
    "dorar-tafsir-v1",
}


def test_catalog_contains_expected_sources() -> None:
    policies = list_source_usage_policies()

    assert {policy.source_id for policy in policies} == EXPECTED_SOURCE_IDS


def test_unknown_source_is_denied_by_default() -> None:
    assert not has_source_usage_policy("unknown-source")

    with pytest.raises(SourceUsagePolicyNotFoundError):
        get_source_usage_policy("unknown-source")


def test_blank_source_id_is_denied() -> None:
    assert not has_source_usage_policy("   ")

    with pytest.raises(SourceUsagePolicyNotFoundError):
        get_source_usage_policy("   ")


def test_source_id_whitespace_is_normalized() -> None:
    policy = get_source_usage_policy("  openiti  ")

    assert policy.source_id == "openiti"


def test_kfgqpc_mirror_is_not_user_authority() -> None:
    policy = get_source_usage_policy("kfgqpc-hafs-mirror-v18")

    assert policy.allows(RuntimeUse.CROSS_VALIDATE)

    assert policy.allows(RuntimeUse.RETRIEVE_PASSAGES)

    assert not policy.allows(RuntimeUse.CITE_TO_USER)

    assert not policy.allows(RuntimeUse.SUPPORT_ANSWER)

    assert not policy.allows(RuntimeUse.VERIFY_CANONICAL_TEXT)


def test_tanzil_uthmani_can_verify_canonical_text() -> None:
    policy = get_source_usage_policy("tanzil-quran-v1.1-uthmani")

    assert policy.allows(RuntimeUse.VERIFY_CANONICAL_TEXT)

    assert policy.allows(RuntimeUse.CROSS_VALIDATE)

    assert policy.allows(RuntimeUse.RETRIEVE_PASSAGES)

    assert not policy.allows(RuntimeUse.SUPPORT_ANSWER)


def test_tanzil_simple_plain_is_search_representation() -> None:
    policy = get_source_usage_policy("tanzil-quran-v1.1-simple-plain")

    assert policy.allows(RuntimeUse.RETRIEVE_PASSAGES)

    assert policy.allows(RuntimeUse.CROSS_VALIDATE)

    assert not policy.allows(RuntimeUse.VERIFY_CANONICAL_TEXT)

    assert not policy.allows(RuntimeUse.CITE_TO_USER)


def test_openiti_is_research_corpus_not_direct_authority() -> None:
    policy = get_source_usage_policy("openiti")

    assert policy.allows(RuntimeUse.RETRIEVE_PASSAGES)

    assert policy.allows(RuntimeUse.ENRICH_METADATA)

    assert policy.allows(RuntimeUse.DISCOVER_SOURCES)

    assert not policy.allows(RuntimeUse.SUPPORT_ANSWER)

    assert not policy.allows(RuntimeUse.CITE_TO_USER)


def test_sanadset_does_not_authenticate_hadith() -> None:
    policy = get_source_usage_policy("sanadset")

    assert policy.allows(RuntimeUse.RETRIEVE_PASSAGES)

    assert policy.allows(RuntimeUse.ENRICH_METADATA)

    assert not policy.allows(RuntimeUse.SUPPORT_ANSWER)

    assert not policy.allows(RuntimeUse.CITE_TO_USER)


def test_sunnah_dataset_can_translate_but_not_act_as_authority() -> None:
    policy = get_source_usage_policy("sunnah-ar-en-dataset")

    assert policy.allows(RuntimeUse.RETRIEVE_PASSAGES)

    assert policy.allows(RuntimeUse.ENRICH_METADATA)

    assert policy.allows(RuntimeUse.PROVIDE_TRANSLATION)

    assert not policy.allows(RuntimeUse.SUPPORT_ANSWER)

    assert not policy.allows(RuntimeUse.CITE_TO_USER)


def test_quran_nlp_is_discovery_and_metadata_only() -> None:
    policy = get_source_usage_policy("quran-nlp")

    assert policy.allows(RuntimeUse.DISCOVER_SOURCES)

    assert policy.allows(RuntimeUse.ENRICH_METADATA)

    assert not policy.allows(RuntimeUse.SUPPORT_ANSWER)

    assert not policy.allows(RuntimeUse.CITE_TO_USER)

    assert not policy.allows(RuntimeUse.VERIFY_CANONICAL_TEXT)


@pytest.mark.parametrize(
    "source_id",
    (
        "islamic-faith-qa",
        "mafqa",
        "sahm-fatwa-qa",
    ),
)
def test_benchmarks_are_evaluation_only(
    source_id: str,
) -> None:
    policy = get_source_usage_policy(source_id)

    assert policy.allows(RuntimeUse.EVALUATE_MODEL)

    assert not policy.allows(RuntimeUse.SUPPORT_ANSWER)

    assert not policy.allows(RuntimeUse.CITE_TO_USER)

    assert not policy.allows(RuntimeUse.VERIFY_CANONICAL_TEXT)


def test_runtime_filter_returns_only_evaluation_sources() -> None:
    policies = list_source_usage_policies(runtime_use=RuntimeUse.EVALUATE_MODEL)

    assert {policy.source_id for policy in policies} == {
        "islamic-faith-qa",
        "mafqa",
        "sahm-fatwa-qa",
    }


def test_runtime_filter_returns_canonical_verifiers() -> None:
    policies = list_source_usage_policies(
        runtime_use=(RuntimeUse.VERIFY_CANONICAL_TEXT)
    )

    assert {policy.source_id for policy in policies} == {
        "tanzil-quran-v1.1-uthmani",
    }


def test_catalog_listing_is_deterministic() -> None:
    policies = list_source_usage_policies()

    source_ids = [policy.source_id for policy in policies]

    assert source_ids == sorted(source_ids)


def test_returned_policy_does_not_mutate_catalog() -> None:
    first = get_source_usage_policy("openiti")

    original_notes = first.notes

    first.notes = "mutated by caller"

    second = get_source_usage_policy("openiti")

    assert second.notes == original_notes
    assert second.notes != "mutated by caller"


def test_catalog_never_exposes_benchmark_as_answer_source() -> None:
    answer_sources = list_source_usage_policies(runtime_use=RuntimeUse.SUPPORT_ANSWER)

    benchmark_ids = {
        "islamic-faith-qa",
        "mafqa",
        "sahm-fatwa-qa",
    }

    returned_ids = {policy.source_id for policy in answer_sources}

    assert returned_ids.isdisjoint(benchmark_ids)


def test_quranlab_is_research_corpus() -> None:
    policy = get_source_usage_policy("quranlab-hadith")

    assert policy.authority_level is EvidenceAuthorityLevel.RESEARCH_CORPUS


def test_quranlab_can_retrieve_and_enrich_metadata() -> None:
    policy = get_source_usage_policy("quranlab-hadith")

    assert policy.allows(RuntimeUse.RETRIEVE_PASSAGES)
    assert policy.allows(RuntimeUse.ENRICH_METADATA)
    assert policy.allows(RuntimeUse.DISCOVER_SOURCES)


def test_quranlab_cannot_directly_support_answer() -> None:
    policy = get_source_usage_policy("quranlab-hadith")

    assert not policy.allows(RuntimeUse.SUPPORT_ANSWER)


def test_quranlab_cannot_be_cited_to_user() -> None:
    policy = get_source_usage_policy("quranlab-hadith")

    assert not policy.allows(RuntimeUse.CITE_TO_USER)


def test_quranlab_cannot_verify_canonical_text() -> None:
    policy = get_source_usage_policy("quranlab-hadith")

    assert not policy.allows(RuntimeUse.VERIFY_CANONICAL_TEXT)


def test_quranlab_requires_human_review() -> None:
    policy = get_source_usage_policy("quranlab-hadith")

    assert policy.requires_human_review
