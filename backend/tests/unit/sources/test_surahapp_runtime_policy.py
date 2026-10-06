from basira.models.source_usage import RuntimeUse
from basira.sources.scholarly.surahapp_runtime import (
    SURAHAPP_SCHOLARLY_SOURCE_IDS,
    build_surahapp_scholarly_runtime,
)


def test_all_surahapp_sources_pass_user_facing_gates() -> None:
    runtime = build_surahapp_scholarly_runtime()

    runtime_uses = (
        RuntimeUse.RETRIEVE_PASSAGES,
        RuntimeUse.SUPPORT_ANSWER,
        RuntimeUse.CITE_TO_USER,
    )

    for source_id in SURAHAPP_SCHOLARLY_SOURCE_IDS:
        for runtime_use in runtime_uses:
            decision = runtime.decide(
                source_id=source_id,
                runtime_use=runtime_use,
            )

            assert decision.allowed
