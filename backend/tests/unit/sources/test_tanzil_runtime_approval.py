from pathlib import Path

from basira.models.source_manifest import (
    SourceManifest,
)
from basira.models.source_usage import (
    RuntimeUse,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)


def test_tanzil_manifest_is_runtime_approved() -> None:
    path = Path(
        "data/manifests/quran/"
        "tanzil-quran-v1.1-uthmani.json"
    )

    manifest = SourceManifest.model_validate_json(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert manifest.is_runtime_approved

    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )

    decision = runtime.decide(
        source_id=manifest.source_id,
        runtime_use=(
            RuntimeUse.RETRIEVE_PASSAGES
        ),
    )

    assert decision.allowed
