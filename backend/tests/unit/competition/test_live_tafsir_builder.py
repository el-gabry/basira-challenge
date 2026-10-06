from __future__ import annotations

from pathlib import Path

from basira.competition.dorar_tafsir_adapter import (
    DorarTafsirEvidenceAdapter,
)
from basira.competition.retrieval_adapters import (
    build_live_dorar_tafsir_adapter,
)

ROOT = Path(__file__).resolve().parents[3]


class NoNetworkTransport:
    def fetch(
        self,
        url,
        *,
        purpose,
    ):
        del url
        del purpose

        raise AssertionError("builder must not perform network IO")


def test_live_tafsir_builder_composes_without_network():
    adapter = build_live_dorar_tafsir_adapter(
        repo_root=ROOT,
        transport=NoNetworkTransport(),
    )

    assert isinstance(
        adapter,
        DorarTafsirEvidenceAdapter,
    )
