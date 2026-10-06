from __future__ import annotations

from basira.models.source_usage import (
    EvidenceAuthorityLevel,
    RuntimeUse,
    SourceUsagePolicy,
    SourceUsageRole,
)


class SourceUsagePolicyNotFoundError(KeyError):
    """
    Raised when Basira has no registered usage policy
    for a source.
    """


_POLICIES: dict[str, SourceUsagePolicy] = {
    # =================================================
    # Quran
    # =================================================
    "kfgqpc-hafs-mirror-v18": SourceUsagePolicy(
        source_id="kfgqpc-hafs-mirror-v18",
        roles=frozenset(
            {
                SourceUsageRole.CROSS_CHECK,
                SourceUsageRole.RETRIEVAL_CORPUS,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.UNVERIFIED),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.CROSS_VALIDATE,
                RuntimeUse.RETRIEVE_PASSAGES,
            }
        ),
        requires_attribution=True,
        requires_human_review=True,
        notes=(
            "Development mirror of KFGQPC Hafs data. "
            "The current snapshot was not acquired "
            "directly from the official upstream "
            "source. It must not be treated as "
            "user-facing religious authority."
        ),
    ),
    "tanzil-quran-v1.1-uthmani": SourceUsagePolicy(
        source_id="tanzil-quran-v1.1-uthmani",
        roles=frozenset(
            {
                SourceUsageRole.CANONICAL_TEXT,
                SourceUsageRole.CROSS_CHECK,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.CANONICAL),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.VERIFY_CANONICAL_TEXT,
                RuntimeUse.CROSS_VALIDATE,
                RuntimeUse.RETRIEVE_PASSAGES,
            }
        ),
        requires_attribution=True,
        requires_human_review=False,
        notes=(
            "Tanzil Uthmani representation used for "
            "canonical Quran comparison. Runtime use "
            "still requires the associated manifest "
            "to be approved and integrity-verified."
        ),
    ),
    "tanzil-quran-v1.1-simple-plain": SourceUsagePolicy(
        source_id="tanzil-quran-v1.1-simple-plain",
        roles=frozenset(
            {
                SourceUsageRole.RETRIEVAL_CORPUS,
                SourceUsageRole.CROSS_CHECK,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.RESEARCH_CORPUS),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.RETRIEVE_PASSAGES,
                RuntimeUse.CROSS_VALIDATE,
            }
        ),
        requires_attribution=True,
        requires_human_review=False,
        notes=(
            "Search and alignment representation. "
            "It must not replace the Uthmani "
            "canonical display representation."
        ),
    ),
    # =================================================
    # Islamic books / historical corpora
    # =================================================
    "openiti": SourceUsagePolicy(
        source_id="openiti",
        roles=frozenset(
            {
                SourceUsageRole.RETRIEVAL_CORPUS,
                SourceUsageRole.METADATA,
                SourceUsageRole.SECONDARY_EVIDENCE,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.RESEARCH_CORPUS),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.RETRIEVE_PASSAGES,
                RuntimeUse.ENRICH_METADATA,
                RuntimeUse.DISCOVER_SOURCES,
            }
        ),
        requires_attribution=True,
        requires_human_review=True,
        notes=(
            "Research corpus for locating attributed "
            "passages in Islamic works. Individual "
            "works and editions require provenance "
            "review before evidentiary use."
        ),
    ),
    # =================================================
    # Hadith research / ingestion
    # =================================================
    "hadeethenc-official": SourceUsagePolicy(
        source_id="hadeethenc-official",
        roles=frozenset(
            {
                SourceUsageRole.RETRIEVAL_CORPUS,
                SourceUsageRole.SECONDARY_EVIDENCE,
                SourceUsageRole.CROSS_CHECK,
                SourceUsageRole.TRANSLATION,
                SourceUsageRole.METADATA,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.ATTRIBUTED_SCHOLARLY),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.SUPPORT_ANSWER,
                RuntimeUse.CITE_TO_USER,
                RuntimeUse.RETRIEVE_PASSAGES,
                RuntimeUse.CROSS_VALIDATE,
                RuntimeUse.PROVIDE_TRANSLATION,
                RuntimeUse.ENRICH_METADATA,
            }
        ),
        requires_attribution=True,
        requires_human_review=False,
        notes=(
            "Official versioned HadeethEnc releases "
            "may support retrieval, attributed answers, "
            "user-facing citation, translation, and "
            "cross-source validation. Grading remains "
            "attributed evidence rather than an absolute "
            "property of a hadith. Record-level version "
            "conflicts must be surfaced for review. "
            "This source must not be used to verify "
            "canonical text or as unrestricted training "
            "authority."
        ),
    ),
    "quranlab-hadith": SourceUsagePolicy(
        source_id="quranlab-hadith",
        roles=frozenset(
            {
                SourceUsageRole.RETRIEVAL_CORPUS,
                SourceUsageRole.METADATA,
                SourceUsageRole.SECONDARY_EVIDENCE,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.RESEARCH_CORPUS),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.RETRIEVE_PASSAGES,
                RuntimeUse.ENRICH_METADATA,
                RuntimeUse.DISCOVER_SOURCES,
            }
        ),
        requires_attribution=True,
        requires_human_review=True,
        notes=(
            "Structured Hadith ingestion corpus with "
            "Arabic text, references, and attributed "
            "grading metadata. QuranLab records must "
            "resolve to reviewed upstream sources "
            "before being treated as religious "
            "evidence or user-facing authority."
        ),
    ),
    "sanadset": SourceUsagePolicy(
        source_id="sanadset",
        roles=frozenset(
            {
                SourceUsageRole.RETRIEVAL_CORPUS,
                SourceUsageRole.METADATA,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.RESEARCH_CORPUS),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.RETRIEVE_PASSAGES,
                RuntimeUse.ENRICH_METADATA,
            }
        ),
        requires_attribution=True,
        requires_human_review=True,
        notes=(
            "Research corpus for isnad and narrator "
            "metadata. It must not be interpreted as "
            "an automatic hadith authenticity "
            "judgment."
        ),
    ),
    "sunnah-ar-en-dataset": SourceUsagePolicy(
        source_id="sunnah-ar-en-dataset",
        roles=frozenset(
            {
                SourceUsageRole.RETRIEVAL_CORPUS,
                SourceUsageRole.METADATA,
                SourceUsageRole.TRANSLATION,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.UNVERIFIED),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.RETRIEVE_PASSAGES,
                RuntimeUse.ENRICH_METADATA,
                RuntimeUse.PROVIDE_TRANSLATION,
            }
        ),
        requires_attribution=True,
        requires_human_review=True,
        notes=(
            "Bilingual hadith development corpus. "
            "Collection reference, Arabic matn, "
            "translation, and grading provenance "
            "must be independently validated before "
            "evidentiary use."
        ),
    ),
    # =================================================
    # Aggregators / discovery
    # =================================================
    "quran-nlp": SourceUsagePolicy(
        source_id="quran-nlp",
        roles=frozenset(
            {
                SourceUsageRole.DISCOVERY_ONLY,
                SourceUsageRole.METADATA,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.AGGREGATOR),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.DISCOVER_SOURCES,
                RuntimeUse.ENRICH_METADATA,
            }
        ),
        requires_attribution=True,
        requires_human_review=True,
        notes=(
            "Aggregator used for source discovery "
            "and metadata enrichment. Runtime "
            "evidence must resolve back to its "
            "original upstream source."
        ),
    ),
    # =================================================
    # Evaluation benchmarks
    # =================================================
    "islamic-faith-qa": SourceUsagePolicy(
        source_id="islamic-faith-qa",
        roles=frozenset(
            {
                SourceUsageRole.EVALUATION,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.BENCHMARK),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.EVALUATE_MODEL,
            }
        ),
        requires_attribution=True,
        requires_human_review=False,
        notes=(
            "Evaluation benchmark only. Benchmark "
            "answers must never become runtime "
            "religious evidence."
        ),
    ),
    "mafqa": SourceUsagePolicy(
        source_id="mafqa",
        roles=frozenset(
            {
                SourceUsageRole.EVALUATION,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.BENCHMARK),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.EVALUATE_MODEL,
            }
        ),
        requires_attribution=True,
        requires_human_review=False,
        notes=(
            "Multi-hop fatwa QA evaluation benchmark. Not a runtime authority source."
        ),
    ),
    "sahm-fatwa-qa": SourceUsagePolicy(
        source_id="sahm-fatwa-qa",
        roles=frozenset(
            {
                SourceUsageRole.EVALUATION,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.BENCHMARK),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.EVALUATE_MODEL,
            }
        ),
        requires_attribution=True,
        requires_human_review=False,
        notes=(
            "Fatwa QA evaluation benchmark. "
            "Not permitted to support or determine "
            "runtime religious answers."
        ),
    ),
}


# =========================================================
# Surah App / Tafsir Center scholarly snapshot
# =========================================================

_SURAHAPP_SCHOLARLY_SOURCE_IDS = (
    "surahapp-tafsir-katheer",
    "surahapp-tafsir-saadi",
    "surahapp-tafsir-mokhtasar",
    "surahapp-ayat-nozool",
)

for _surahapp_source_id in _SURAHAPP_SCHOLARLY_SOURCE_IDS:
    _POLICIES[_surahapp_source_id] = SourceUsagePolicy(
        source_id=_surahapp_source_id,
        roles=frozenset(
            {
                SourceUsageRole.RETRIEVAL_CORPUS,
                SourceUsageRole.SECONDARY_EVIDENCE,
            }
        ),
        authority_level=(EvidenceAuthorityLevel.ATTRIBUTED_SCHOLARLY),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.RETRIEVE_PASSAGES,
                RuntimeUse.SUPPORT_ANSWER,
                RuntimeUse.CITE_TO_USER,
            }
        ),
        requires_attribution=True,
        requires_human_review=False,
        notes=(
            "Pinned and Quran-anchor-audited "
            "Surah App scholarly source. "
            "Approved for attributed retrieval, "
            "answer support, and user-facing citation. "
            "Corpus redistribution remains outside "
            "this runtime permission."
        ),
    )

del _surahapp_source_id


# =========================================================
# Dorar Tafsir — competition-admitted scholarly source
# =========================================================

_POLICIES["dorar-tafsir-v1"] = SourceUsagePolicy(
    source_id="dorar-tafsir-v1",
    roles=frozenset(
        {
            SourceUsageRole.RETRIEVAL_CORPUS,
            SourceUsageRole.SECONDARY_EVIDENCE,
        }
    ),
    authority_level=(
        EvidenceAuthorityLevel.ATTRIBUTED_SCHOLARLY
    ),
    allowed_runtime_uses=frozenset(
        {
            RuntimeUse.RETRIEVE_PASSAGES,
            RuntimeUse.SUPPORT_ANSWER,
            RuntimeUse.CITE_TO_USER,
        }
    ),
    requires_attribution=True,
    requires_human_review=False,
    notes=(
        "Competition-admitted and Quran-anchor-audited "
        "Dorar Tafsir source. Approved for attributed "
        "retrieval, answer support, and user-facing "
        "citation. Supporting public text remains bounded "
        "by the presenter excerpt gate; full evidence text "
        "remains limited to composer-selected evidence."
    ),
)


def has_source_usage_policy(
    source_id: str,
) -> bool:
    """
    Return whether an explicit policy exists.

    Unknown sources are denied by default.
    """

    normalized = " ".join(source_id.split())

    if not normalized:
        return False

    return normalized in _POLICIES


def get_source_usage_policy(
    source_id: str,
) -> SourceUsagePolicy:
    """
    Return an independent copy of a registered policy.

    No fallback policy is created for unknown sources.
    """

    normalized = " ".join(source_id.split())

    if not normalized:
        raise SourceUsagePolicyNotFoundError("Source id must not be blank.")

    try:
        policy = _POLICIES[normalized]
    except KeyError as exc:
        raise SourceUsagePolicyNotFoundError(
            f"No SourceUsagePolicy is registered for source '{normalized}'."
        ) from exc

    return policy.model_copy(deep=True)


def list_source_usage_policies(
    *,
    runtime_use: RuntimeUse | None = None,
) -> tuple[SourceUsagePolicy, ...]:
    """
    Return independent policy copies in deterministic
    source-id order.

    When runtime_use is supplied, return only sources
    explicitly permitted for that operation.
    """

    source_ids = sorted(_POLICIES)

    if runtime_use is None:
        return tuple(
            _POLICIES[source_id].model_copy(deep=True) for source_id in source_ids
        )

    return tuple(
        _POLICIES[source_id].model_copy(deep=True)
        for source_id in source_ids
        if _POLICIES[source_id].allows(runtime_use)
    )
