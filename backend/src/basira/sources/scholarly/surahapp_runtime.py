from __future__ import annotations

from pathlib import Path

from basira.models.source_manifest import (
    SourceManifest,
)
from basira.sources.policy_catalog import (
    get_source_usage_policy,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)

SURAHAPP_TAFSIR_SOURCE_IDS = (
    "surahapp-tafsir-katheer",
    "surahapp-tafsir-saadi",
    "surahapp-tafsir-mokhtasar",
)

SURAHAPP_REVELATION_CONTEXT_SOURCE_IDS = ("surahapp-ayat-nozool",)

SURAHAPP_SCHOLARLY_SOURCE_IDS = (
    *SURAHAPP_TAFSIR_SOURCE_IDS,
    *SURAHAPP_REVELATION_CONTEXT_SOURCE_IDS,
)

DEFAULT_MANIFEST_DIR = Path("data/manifests/scholarly")


def build_surahapp_scholarly_runtime(
    manifest_dir: Path = DEFAULT_MANIFEST_DIR,
) -> FailClosedSourceRuntime:
    manifests: list[SourceManifest] = []

    for source_id in SURAHAPP_SCHOLARLY_SOURCE_IDS:
        path = manifest_dir / f"{source_id}.json"

        manifest = SourceManifest.model_validate_json(path.read_text(encoding="utf-8"))

        if manifest.source_id != source_id:
            raise ValueError(
                "Scholarly manifest source id "
                "does not match its configured id: "
                f"{source_id}"
            )

        policy = get_source_usage_policy(source_id)

        manifests.append(
            manifest.model_copy(
                update={
                    "usage_policy": policy,
                }
            )
        )

    return FailClosedSourceRuntime(TrustedSourceRegistry(manifests))
